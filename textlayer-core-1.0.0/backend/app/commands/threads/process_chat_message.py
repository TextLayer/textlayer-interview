from typing import Any, Dict, Generator, List, Optional, Union

from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit

from app import logger
from app.core.commands import ReadCommand
from app.errors import ProcessingException, ValidationException
from app.services.llm.client.chat import ChatClient
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.tools import TOOL_REGISTRY
from app.utils.models import CHAT_MODELS


class ProcessChatMessageCommand(ReadCommand):
    def __init__(self, messages: List[Dict[str, Any]], stream: bool = False, model: Optional[str] = None):
        self.messages = messages
        self.stream = stream
        self.models = [model] if model else CHAT_MODELS

    def validate(self) -> bool:
        if not self.messages:
            raise ValidationException("Messages are required")

        if not isinstance(self.stream, bool):
            raise ValidationException("Stream must be a boolean")

        return True

    @observe(name="chat_message", capture_input=False, capture_output=False)
    def execute(self) -> Union[List[Dict[str, Any]], Generator[str, None, None]]:
        logger.debug(f"Command: {self.__class__.__name__} \nMessages: {self.messages} \nStream: {self.stream} \n")

        self.validate()

        # Create a session for communicating with the LLM (with fallback models)
        llm_session = ChatClient(
            models=self.models,
        )

        # Define the system prompt
        system_prompt = chat_prompt()

        # Combine the system prompt with the user messages
        formatted_messages = system_prompt + self.messages

        # Set up the toolkit of available tools the LLM can use
        toolkit = Toolkit()
        toolkit.add_tools(*TOOL_REGISTRY)

        try:
            return llm_session.chat(messages=formatted_messages, stream=self.stream, tools=toolkit)
        except BadRequestError:
            raise
        except Exception as error:
            logger.error(f"Failed to fetch chat response: {error}")
            raise ProcessingException(f"Error in fetching chat response: {str(error)}") from error
