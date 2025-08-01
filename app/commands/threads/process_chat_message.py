from typing import Dict, List
from flask import current_app, g

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs import text_to_sql
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.utils.formatters import get_timestamp
#adding new imports for the sql judge and response enhancer
from app.services.llm.sql_judge import SQLJudge
from app.services.llm.prompts.schema_helper import get_database_schema
from app.services.llm.response_enhancer import ResponseEnhancer

from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit
from uuid import uuid4

import json


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
    
    def execute(self) -> None:
        """
        Execute the command.
        """
        logger.debug(
            f'Command {self.__class__.__name__} started with {len(self.chat_messages)} messages.'
        )

        self.validate()

        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "tools": self.toolkit.tool_schemas(),
        }

        try:
            response = self.llm_session.chat(**chat_kwargs)
        except BadRequestError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to fetch chat response: {e}")
            raise ValidationException("Error in fetching chat response.")

        tool_messages = []

        response_message_config = {
            "role": "assistant",
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
        }

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

            for tool_call in tool_calls:
                tool_run = self.execute_tool_call(tool_call)
                tool_messages.append(
                    self.format_message(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=json.dumps(tool_run),
                    )
                )
        else:
            response_message = self.format_message(**response_message_config)

        # Add the messages as the last elements of the list
        self.chat_messages.append(response_message)
        self.chat_messages.extend(tool_messages)

        return self.chat_messages
    

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
    def execute_tool_call(self, tool_call: dict) -> dict:
        tool_name = tool_call.function.name
        if tool_name == "text_to_sql":
            arguments = json.loads(tool_call.function.arguments)
            generated_sql = arguments.get("sql_query","")
            user_question = self.chat_messages[-1].get("content", "") if self.chat_messages else ""
            database_schema = get_database_schema()
            judge = SQLJudge()
            review = judge.review_sql(user_question, generated_sql, database_schema)

            if review["verdict"] == "rejected":
                error_message = f"Query rejected for safety: {review['reason']}"
                print(error_message)
                return error_message
            elif review["verdict"] == "needs_improvement" and review["suggested_sql"]:
                print(f"Judge feedback: {review.get('reason', 'SQL needs improvement')}")
                correction_prompt = f"""
                    The SQL query you generated needs improvement:
                    
                    Original question: {user_question}
                    Your SQL: {generated_sql}
                    Judge feedback: {review.get('reason', 'Please improve this query')}
                    
                    Please generate a corrected SQL query that addresses the feedback.
                    Return only the corrected SQL query, no explanations.
                    """
                correction_response = self.llm_session.complete(correction_prompt)
                corrected_sql = correction_response.choices[0].message.content.strip()

                if corrected_sql.startswith('```sql'):
                    corrected_sql = corrected_sql.replace('```sql', '').replace('```', '').strip()
                print(f"Corrected SQL: {corrected_sql}")

                arguments["sql_query"] = corrected_sql
                tool_call.function.arguments = json.dumps(arguments)
            else:
                print("approved the sql query")
        try:
            raw_results = self.toolkit.run_tool(
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
        except Exception as e:
            print(f"SQL execution error: {e}")
            return "I encountered an error while processing your query. Please try a simpler question or try again later."

        if tool_name == "text_to_sql":
            enhancer = ResponseEnhancer()
            better_response = enhancer.make_response_better(
                question=user_question,
                sql=generated_sql,
                results=raw_results,
                schema=database_schema
                )
            return better_response
        return raw_results
        

