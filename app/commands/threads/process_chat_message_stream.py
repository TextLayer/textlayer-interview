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


class ProcessChatMessageStreamCommand(ReadCommand):
    """
    Process a chat message with streaming response.
    Falls back to simulated streaming if real streaming fails.
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

    def execute_stream(self):
        """
        Execute the command with streaming response.
        Falls back to simulated streaming if real streaming fails.
        """
        logger.debug(
            f'Streaming command {self.__class__.__name__} started with '
            f'{len(self.chat_messages)} messages.'
        )

        self.validate()

        # Skip real streaming for now due to LiteLLM/Claude compatibility issues
        # Go directly to simulated streaming which works reliably
        logger.info("Using simulated streaming (LiteLLM/Claude streaming has issues)")
        yield from self._execute_simulated_streaming()

    def _execute_real_streaming(self):
        """Execute with real LLM streaming."""
        # Check if the model supports tools
        # (disabled due to LiteLLM Anthropic bug)
        model_supports_tools = False

        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "max_tokens": 4000,  # Increase token limit to prevent cutoff
            "temperature": 0.1,  # Lower for more consistent results
        }

        if model_supports_tools:
            toolkit = Toolkit()
            toolkit.add_tools(text_to_sql_tool)
            chat_kwargs["tools"] = toolkit.tool_schemas()

        try:
            response_stream = self.llm_session.chat_stream(**chat_kwargs)
            logger.debug("LLM Streaming Response initiated")
        except BadRequestError as e:
            logger.error(f"BadRequestError: {e}")
            # Fall back to chat without tools if tool calling fails
            logger.info(
                "Falling back to streaming chat without tools due to "
                "tool calling error"
            )
            chat_kwargs.pop("tools", None)
            response_stream = self.llm_session.chat_stream(**chat_kwargs)
        except Exception as e:
            logger.error(f"Failed to fetch streaming chat response: {e}")
            logger.error(f"Chat kwargs: {chat_kwargs}")
            raise ValidationException(
                f"Error in fetching streaming chat response: {str(e)}"
            )

        # Accumulate the full response for SQL processing
        accumulated_content = ""
        message_id = str(uuid4())

        # Send initial message structure
        initial_message = {
            "id": message_id,
            "role": "assistant",
            "content": "",
            "timestamp": get_timestamp(with_nanoseconds=True),
            "streaming": True
        }

        yield json.dumps({"type": "message_start", "message": initial_message})

        try:
            chunks_received = 0
            for chunk in response_stream:
                chunks_received += 1
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    if hasattr(delta, 'content') and delta.content:
                        content_chunk = delta.content
                        accumulated_content += content_chunk

                        # Send content chunk
                        yield json.dumps({
                            "type": "content_delta",
                            "delta": {"content": content_chunk}
                        })

                    # Check for finish reason
                    if (hasattr(chunk.choices[0], 'finish_reason') and
                            chunk.choices[0].finish_reason):
                        finish_reason = chunk.choices[0].finish_reason

                        # Process SQL if content exists
                        final_content = accumulated_content
                        if final_content:
                            sql_executor = get_sql_executor()
                            final_content = sql_executor.extract_and_execute_sql(
                                final_content
                            )

                        # Send final message
                        final_message = {
                            "id": message_id,
                            "role": "assistant",
                            "content": final_content,
                            "finish_reason": finish_reason,
                            "timestamp": get_timestamp(with_nanoseconds=True),
                            "streaming": False
                        }

                        yield json.dumps({
                            "type": "message_complete",
                            "message": final_message
                        })
                        logger.debug(f"Streaming completed with {chunks_received} chunks")
                        return

            # If we get here, streaming ended without a finish reason
            if chunks_received == 0:
                raise Exception("No chunks received from streaming response")

        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            raise

    def _execute_simulated_streaming(self):
        """Fallback to simulated streaming using regular chat."""
        logger.info("Using simulated streaming")

        # Use regular chat instead of streaming
        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "max_tokens": 4000,
            "temperature": 0.1,
        }

        try:
            response = self.llm_session.chat(**chat_kwargs)

            if not response.choices or len(response.choices) == 0:
                raise Exception("No response choices received")

            content = response.choices[0].message.content or ""

            # Process SQL if content exists
            if content:
                sql_executor = get_sql_executor()
                content = sql_executor.extract_and_execute_sql(content)

        except Exception as e:
            logger.error(f"Simulated streaming failed: {e}")
            content = f"Sorry, I encountered an error: {str(e)}"

        # Simulate streaming by breaking content into chunks
        message_id = str(uuid4())

        # Send initial message structure
        initial_message = {
            "id": message_id,
            "role": "assistant",
            "content": "",
            "timestamp": get_timestamp(with_nanoseconds=True),
            "streaming": True
        }

        yield json.dumps({"type": "message_start", "message": initial_message})

        # Break content into words and stream them
        import time
        words = content.split(' ')
        for i, word in enumerate(words):
            chunk = word + (' ' if i < len(words) - 1 else '')

            yield json.dumps({
                "type": "content_delta",
                "delta": {"content": chunk}
            })

            # Small delay to simulate typing (reduced for better UX)
            time.sleep(0.01)

        # Send final message
        final_message = {
            "id": message_id,
            "role": "assistant",
            "content": content,
            "finish_reason": "stop",
            "timestamp": get_timestamp(with_nanoseconds=True),
            "streaming": False
        }

        yield json.dumps({
            "type": "message_complete",
            "message": final_message
        })

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