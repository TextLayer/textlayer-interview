from typing import Dict, List
from flask import current_app
import asyncio

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.agents.financial_agent import create_financial_analysis_agent
from app.utils.formatters import get_timestamp
from uuid import uuid4


class ProcessChatMessageAgenticCommand(ReadCommand):
    """
    Process a chat message using multi-agent approach with LangGraph
    """
    def __init__(self, chat_messages: List[Dict[str, str]]) -> None:
        self.chat_messages = chat_messages
        self.agent = create_financial_analysis_agent()

    def validate(self) -> None:
        """
        Validate the command.
        """
        if not self.chat_messages:
            raise ValidationException("Chat messages are required.")
        
        return True
    
    def execute(self) -> None:
        """
        Execute the command using the multi-agent system.
        """
        logger.debug(
            f'Command {self.__class__.__name__} started with {len(self.chat_messages)} messages using agentic approach.'
        )

        self.validate()
        
        user_message = None
        for msg in reversed(self.chat_messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            raise ValidationException("No user message found.")

        try:
            logger.debug(f"Processing user query: {user_message}")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            logger.debug("Starting agent processing...")
            response_content = loop.run_until_complete(
                self.agent.process_query(user_message)
            )
            
            logger.debug(f"Agent response received: {response_content[:200]}...")
            
            # Create the response message
            response_message = self.format_message(
                role="assistant",
                content=response_content,
                finish_reason="stop",
                agent_type="multi_agent_langgraph"
            )
            
            # Add the response to the conversation
            self.chat_messages.append(response_message)
            
        except Exception as e:
            logger.error(f"Failed to process chat message with agents: {e}")
            raise ValidationException("Error in processing chat message with agentic approach.")

        return self.chat_messages

    def format_message(self, role: str, content: str, **kwargs) -> dict:
        """Format a message with timestamp and ID"""
        return {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "timestamp": (get_timestamp(with_nanoseconds=True),),
            **kwargs,
        }
