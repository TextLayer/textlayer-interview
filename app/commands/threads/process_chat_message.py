from typing import Dict, List
from flask import current_app, g

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs import text_to_sql
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.services.llm.tools.enhanced_text_to_sql import enhanced_text_to_sql
from app.services.llm.quality.response_judge import ResponseQualityJudge
from app.services.datastore.schema_inspector import SchemaInspector
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
        # Use enhanced text-to-SQL tool instead of basic one
        self.toolkit.add_tools(*[enhanced_text_to_sql])
        
        # Initialize quality and schema services
        self.quality_judge = ResponseQualityJudge()
        self.schema_inspector = SchemaInspector(database_path="app/data/data.db")
        
        # Enable quality evaluation (can be configured)
        self.enable_quality_evaluation = current_app.config.get("ENABLE_QUALITY_EVALUATION", True)

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
        
        # Apply quality evaluation and improvement if enabled
        if self.enable_quality_evaluation and response_message.get("content"):
            self._evaluate_and_improve_response(response_message)

        return self.chat_messages
    

    @observe()
    def prepare_chat_messages(self) -> list:
        trimmed_messages = self.llm_session.trim_message_history(
            messages=self.chat_messages,
        )

        # Get enhanced context for the prompt
        schema_context = self.schema_inspector.get_schema_context_for_prompt()
        
        # Get the latest user message to determine relevant tables
        latest_user_message = ""
        for msg in reversed(self.chat_messages):
            if msg.get("role") == "user":
                latest_user_message = msg.get("content", "")
                break
        
        relevant_tables = self.schema_inspector.get_relevant_tables_for_query(latest_user_message)
        
        # Generate enhanced system prompt with context
        system_prompt = chat_prompt(
            schema_context=schema_context,
            relevant_tables=relevant_tables,
            domain_context="This is a financial dataset. Focus on providing business-relevant insights."
        )

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
    
    @observe()
    def _evaluate_and_improve_response(self, response_message: dict) -> None:
        """
        Evaluate response quality and improve if necessary.
        """
        try:
            # Get the original user query
            user_query = ""
            for msg in reversed(self.chat_messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break
            
            if not user_query:
                return
            
            # Get schema context for evaluation
            schema_context = self.schema_inspector.get_schema_context_for_prompt()
            
            # Evaluate the response
            evaluation = self.quality_judge.evaluate_response(
                user_query=user_query,
                assistant_response=response_message.get("content", ""),
                context=schema_context
            )
            
            logger.info(f"Response quality score: {evaluation.get('overall_score', 'N/A')}/10")
            
            # If response needs improvement and score is below threshold
            if (evaluation.get('needs_improvement', False) and 
                evaluation.get('overall_score', 10) < 7):
                
                logger.info("Attempting to improve response quality")
                
                improved_response = self.quality_judge.improve_response(
                    user_query=user_query,
                    original_response=response_message.get("content", ""),
                    evaluation=evaluation,
                    context=schema_context
                )
                
                # Update the response content with improved version
                if improved_response and improved_response != response_message.get("content", ""):
                    response_message["content"] = improved_response
                    response_message["quality_improved"] = True
                    response_message["original_score"] = evaluation.get('overall_score', 0)
                    logger.info("Response improved based on quality evaluation")
                
            # Add quality metadata to response
            response_message["quality_evaluation"] = {
                "score": evaluation.get('overall_score', 0),
                "evaluated": True,
                "timestamp": get_timestamp(with_nanoseconds=True)
            }
            
        except Exception as e:
            logger.error(f"Error in quality evaluation: {e}")
            # Don't fail the entire request if quality evaluation fails
            response_message["quality_evaluation"] = {
                "score": 0,
                "evaluated": False,
                "error": str(e),
                "timestamp": get_timestamp(with_nanoseconds=True)
            }
