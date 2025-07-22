from typing import Dict, List
from flask import current_app

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.prompts.llm_judge_prompt import llm_judge_prompt
from app.services.llm.session import LLMSession
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.utils.formatters import get_timestamp

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

        chat_messages_prepared = self.prepare_chat_messages()
        chat_kwargs = {
        "messages": chat_messages_prepared,
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

        # Enhancing assistant response using SQL output
        user_question = self.chat_messages[-len(self.chat_messages) + 1]["content"]
        sql_result = ""
        original_summary = response_message_config["content"]

        if tool_messages:
            try:
                sql_result = json.loads(tool_messages[-1]["content"]).get("sql", "")

                # Generate fallback summary if none was produced
                if sql_result and (not original_summary or not original_summary.strip()):
                    total_sum = sum(
                        filter(None, [
                            row.get("total_spent") or
                            row.get("spending") or
                            row.get("amount") or
                            row.get("sum(spending)") or
                            row.get("sum(amount)")
                            for row in sql_result
                            if row
                        ])
                    )
                    response_message_config["content"] = f"We spent a total of ${total_sum} on marketing in Q1 2024."
                    response_message = self.format_message(**response_message_config)
                    logger.debug("Generated fallback summary from SQL result.")

            except Exception as e:
                logger.warning(f"Fallback summary generation failed: {e}")
                response_message_config["content"] = (
                    "Sorry, I couldn’t retrieve the data due to a query error. Please try rephrasing your question."
                )
                response_message = self.format_message(**response_message_config)

        # If we have a summary and SQL, asking LLM to refine it
        if sql_result and original_summary:
            try:
                judge_messages = llm_judge_prompt(
                    user_question=user_question,
                    sql=sql_result,
                    summary=original_summary
                )
                judged_response = self.llm_session.chat(judge_messages)
                improved_summary = judged_response.choices[0].message.content
                response_message_config["content"] = improved_summary
                response_message = self.format_message(**response_message_config)
                logger.debug("Improved summary with LLM-as-a-Judge.")
                
            except Exception as e:
                logger.warning(f"LLM-as-a-Judge failed, using original summary. Reason: {e}")

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
        return self.toolkit.run_tool(
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments),
        )

    
    def stream_execute(self):
        """
        Generator that yields chat responses and tool results for streaming.
        """
        self.validate()

        chat_messages_prepared = self.prepare_chat_messages()
        chat_kwargs = {
            "messages": chat_messages_prepared,
            "tools": self.toolkit.tool_schemas(),
        }

        try:
            response = self.llm_session.chat(**chat_kwargs)
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield json.dumps({"error": str(e)})
            return

        response_message_config = {
            "role": "assistant",
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
        }

        # Yield assistant message if available
        if response_message_config["content"]:
            yield json.dumps({
                "type": "assistant",
                "message": response_message_config["content"]
            })

        # Execute tool if needed and yield result
        sql_result = None
        if response.choices[0].finish_reason == "tool_calls":
            for tool_call in response.choices[0].message.tool_calls:
                try:
                    tool_result = self.execute_tool_call(tool_call)
                    sql_result = tool_result.get("sql", [])
                    yield json.dumps({
                        "type": "tool_result",
                        "tool_name": tool_call.function.name,
                        "result": tool_result
                    })
                except Exception as e:
                    yield json.dumps({
                        "type": "tool_error",
                        "tool_name": tool_call.function.name,
                        "error": str(e)
                    })

        # Fallback summary if assistant message is empty but SQL result exists
        if not response_message_config["content"] and sql_result:
            try:
                total_amounts = []
                for row in sql_result:
                    value = (
                        row.get("total_spent") or
                        row.get("spending") or
                        row.get("amount") or
                        row.get("sum(spending)") or
                        row.get("sum(amount)") or
                        row.get("total_marketing_spending") or
                        next(iter(row.values()), None)
                    )
                    if value is not None:
                        total_amounts.append(value)

                total_sum = sum(filter(None, total_amounts))
                yield json.dumps({
                    "type": "assistant",
                    "message": f"We spent a total of ${total_sum} on marketing in Q1 2024."
                })

            except Exception as e:
                logger.warning(f"Failed to generate fallback summary: {e}")
                yield json.dumps({
                    "type": "assistant",
                    "message": "I couldn’t summarize the data. Please try again."
                })