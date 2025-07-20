from typing import Dict, List
from flask import current_app, g
import json
import traceback

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs import text_to_sql
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.utils.formatters import get_timestamp
from app.services.llm.tools.sql_generator import generate_sql_from_prompt

from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit
from uuid import uuid4

from app.services.llm.tools.schema_analysis import SchemaAnalyzerTool
from app.services.llm.tools.embedding_schema_analyzer import EmbeddingSchemaAnalyzer
from app.services.llm.tools.llm_prompt_builder import LLMPromptBuilder

class ProcessChatMessageCommand(ReadCommand):
    """
    Process a chat message.
    """
    def __init__(self, chat_messages: List[Dict[str, str]]) -> None:
        self.chat_messages = chat_messages
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
        self.toolkit = Toolkit()
        self.toolkit.add_tools(*[text_to_sql_tool])

    def validate(self) -> None:
        """
        Validate the command.
        """
        if not self.chat_messages:
            raise ValidationException("Chat messages are required.")
        
        return True

    @observe()
    def prepare_chat_messages(self) -> list:
        trimmed_messages = self.llm_session.trim_message_history(
            messages=self.chat_messages,
        )

        system_prompt = chat_prompt()

        trimmed_messages = system_prompt + trimmed_messages

        return trimmed_messages

    @observe()
    def format_message(self, role: str, content: str, **kwargs) -> dict:
        return {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "timestamp": (get_timestamp(with_nanoseconds=True),),
            **kwargs,
        }

 
    @observe()
    def execute(self) -> None:
        """
        Executes the chat command:
        1. Validates input.
        2. Classifies query using LLM.
        3. If out-of-scope: return early with assistant response.
        4. If raw SQL: call SQL tool directly and return result.
        5. Else: ask LLM to suggest a tool and run schema analyzers.
        """
        logger.debug(f'\n Command {self.__class__.__name__} started with {len(self.chat_messages)} messages.')

        # Step 1: Validate input
        self.validate()

        # Step 2: Get user query
        user_message = self.chat_messages[-1]["content"]

        # Step 3: Classify query (DATA_QUESTION vs OUT_OF_SCOPE)
        try:
            triage_result = json.loads(
                self.llm_session.chat(messages=LLMPromptBuilder.triage_prompt(user_message))
                .choices[0]
                .message
                .content
            )
            query_type = triage_result.get("queryType", "")
            logger.debug(f"Query Type: {query_type}")
        except Exception as e:
            logger.error(f"\n Triage classification failed: {e}")
            raise ValidationException("Could not classify the user query.")

        # Step 4: OUT_OF_SCOPE response
        if query_type != "DATA_QUESTION":
            response_message = self.format_message(
                role="assistant",
                content="This question appears to be unrelated to our data. Please ask a specific data-related question."
            )
            self.chat_messages.append(response_message)
            return self.chat_messages

        # Step 4.5: Detect if input is raw SQL and call tool directly
        try:
            sql_check_prompt = LLMPromptBuilder.sql_or_nl_prompt(user_message)
            sql_check_response = self.llm_session.chat(messages=sql_check_prompt)
            sql_type = json.loads(sql_check_response.choices[0].message.content).get("queryType", "")
            logger.debug(f"\n LLM SQL Check: {sql_type}")
        except Exception as e:
            logger.warning(f"Failed to detect SQL query type: {e}")
            sql_type = "NL"

        if sql_type == "SQL":
            logger.debug("\n Skipping tool suggestion. Executing SQL directly.")
            tool_result = text_to_sql(user_query=user_message, schema_info={})

            self.chat_messages.append(
                self.format_message(role="assistant", content="Here is the result of your SQL query.")
            )
            self.chat_messages.append(
                self.format_message(
                    role="tool",
                    tool_call_id="raw_sql",
                    content=json.dumps(tool_result),
                )
            )
            return self.chat_messages

        # Step 5: Let LLM suggest a tool (e.g., text_to_sql)
        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "tools": self.toolkit.tool_schemas(),
        }

        try:
            response = self.llm_session.chat(**chat_kwargs)
        except BadRequestError as e:
            raise e
        except Exception as e:
            traceback.print_exc()
            logger.error(f"\n LLM failed to respond: {e}")
            raise ValidationException("LLM failed to generate a tool call.")

        response_message_config = {
            "role": "assistant",
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
        }

        tool_messages = []

        if response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls
            response_message_config["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ]

            response_message = self.format_message(**response_message_config)

            # Step 6: Run schema analyzers (GPT first, fallback to embedding)
            gpt_analyzer = SchemaAnalyzerTool()
            embedding_analyzer = EmbeddingSchemaAnalyzer()

            gpt_schema = gpt_analyzer.run(user_message)
            embedding_schema = embedding_analyzer.run(user_message)

            if gpt_schema.get("inScope", False):
                self.schema_info = gpt_schema
                logger.debug("\n Using GPT schema analysis.")
            elif embedding_schema.get("inScope", False):
                self.schema_info = embedding_schema
                logger.debug("\n Using embedding schema analysis.")
            else:
                response_message = self.format_message(
                    role="assistant",
                    content="I couldn't identify relevant tables or columns to answer your question."
                )
                self.chat_messages.append(response_message)
                return self.chat_messages

            # Step 7: Call tools
            for tool_call in tool_calls:
                tool_result = self.execute_tool_call(tool_call)
                # The final output
                try:
                    output = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
                    print("\n========= OUTPUT =========")
                    print(f"SQL Query:\n{output.get('sql_query', 'N/A')}")
                    print(f"\nNatural Language Answer:\n{output.get('natural_language_answer', 'N/A')}")
                    if "error_message" in output:
                        print(f"\n[ERROR] {output['error_message']}")
                    print("==========================\n")
                except Exception as e:
                    logger.debug(f"Failed to parse tool output: {e}")

                tool_messages.append(
                    self.format_message(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=json.dumps(tool_result),
                    )
                )


            self.chat_messages.append(response_message)
            self.chat_messages.extend(tool_messages)
            return self.chat_messages

        # Step 8: If no tool call, just append LLM message
        response_message = self.format_message(**response_message_config)
        self.chat_messages.append(response_message)
        return self.chat_messages


    @observe()
    def execute_tool_call(self, tool_call: dict) -> dict:
        args = json.loads(tool_call.function.arguments)

        if "schema_info" not in args:
            args["schema_info"] = self.schema_info
        return self.toolkit.run_tool(
            name=tool_call.function.name,
            arguments=args,
        )
