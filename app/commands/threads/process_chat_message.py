import json
from typing import Dict, List
from uuid import uuid4

from flask import current_app
from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.services.sql.sql_executor import get_sql_executor
from app.utils.formatters import get_timestamp


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

        # Remove duplicate consecutive messages as safeguard
        cleaned_messages = []
        for message in self.chat_messages:
            # Skip if content is empty or just quotes
            content = message.get('content', '').strip()
            if not content or content in ['""', "''"]:
                continue

            # Skip if it's a duplicate of the previous message
            if (cleaned_messages and
                    cleaned_messages[-1].get('role') == message.get('role') and
                    cleaned_messages[-1].get('content') == content):
                continue

            cleaned_messages.append({
                'role': message.get('role'),
                'content': content
            })

        self.chat_messages = cleaned_messages

        if not self.chat_messages:
            raise ValidationException("No valid chat messages provided.")

        return True

    def execute(self) -> None:
        """
        Execute the command.
        """
        logger.debug(
            f'Command {self.__class__.__name__} started with {len(self.chat_messages)} messages.'
        )

        self.validate()

        # Check if the model supports tools (disabled due to LiteLLM Anthropic bug)
        model_supports_tools = False  # LiteLLM has tool calling issues with Anthropic

        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "max_tokens": 4000,  # Increase token limit to prevent cutoff
            "temperature": 0.1,  # Lower temperature for more consistent results
        }

        if model_supports_tools:
            toolkit = Toolkit()
            toolkit.add_tools(text_to_sql_tool)
            chat_kwargs["tools"] = toolkit.tool_schemas()

        try:
            response = self.llm_session.chat(**chat_kwargs)
            logger.debug(f"LLM Response: {response}")
        except BadRequestError as e:
            logger.error(f"BadRequestError: {e}")
            # Fall back to chat without tools if tool calling fails
            logger.info("Falling back to chat without tools due to tool calling error")
            chat_kwargs.pop("tools", None)
            response = self.llm_session.chat(**chat_kwargs)
        except Exception as e:
            logger.error(f"Failed to fetch chat response: {e}")
            logger.error(f"Chat kwargs: {chat_kwargs}")
            raise ValidationException(f"Error in fetching chat response: {str(e)}")

        tool_messages = []

        # Validate response structure
        if not response.choices or len(response.choices) == 0:
            logger.error(f"Invalid response structure: {response}")
            raise ValidationException("Invalid response from LLM - no choices returned")

        response_choice = response.choices[0]
        if not hasattr(response_choice, 'message'):
            logger.error(f"Invalid choice structure: {response_choice}")
            raise ValidationException("Invalid response from LLM - no message in choice")

        response_message_config = {
            "role": "assistant",
            "content": response_choice.message.content or "",
            "finish_reason": response_choice.finish_reason,
        }

        # Extract and execute SQL queries from the response
        if response_message_config["content"]:
            sql_executor = get_sql_executor()
            enhanced_content = sql_executor.extract_and_execute_sql(
                response_message_config["content"]
            )
            response_message_config["content"] = enhanced_content

        # Only handle tool calls if the model supports them and tools were used
        if (model_supports_tools and
            response_choice.finish_reason == "tool_calls" and
            hasattr(response_choice.message, 'tool_calls') and
            response_choice.message.tool_calls):

            tool_calls = response_choice.message.tool_calls

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
        return self.toolkit.run_tool(
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments),
        )
