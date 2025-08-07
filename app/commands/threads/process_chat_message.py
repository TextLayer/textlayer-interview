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

from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit
from uuid import uuid4

import json


class ProcessChatMessageCommand(ReadCommand):
    """
    Advanced Chat Message Processing Command with AI Decision System.
    
    This command orchestrates the entire chat processing pipeline, from user input
    to final response generation. It integrates with the intelligent text-to-SQL
    decision system to provide contextual, AI-driven responses.
    
    Processing Pipeline:
        1. **Input Validation**: Validates chat message structure and content
        2. **Decision Analysis**: Uses AI to determine response strategy
        3. **Tool Execution**: Executes database tools if needed
        4. **Response Enhancement**: Adds structured metadata and transparency
        5. **Final Formatting**: Prepares complete API response
    
    Key Features:
        - ✅ AI-powered decision making via Gemini 2.5 Flash
        - ✅ Dual response format (conversational + structured)
        - ✅ Complete tool execution transparency
        - ✅ Enhanced error handling and fallbacks
        - ✅ Langfuse observability integration
        - ✅ Comprehensive metadata in responses
    
    Response Structure:
        The command returns enhanced message objects with:
        - decision: AI decision type ("response" or "use_tool")
        - tool: Tool name and parameters (if applicable)
        - tool_success: Boolean indicating tool execution status
        - reasoning: AI explanation of decision logic
        - final_response: Clean, structured data for API consumers
        - timestamp: Precise execution timing
    
    Examples:
        >>> # Conversational query processing
        >>> command = ProcessChatMessageCommand([
        ...     {"role": "user", "content": "hello"}
        ... ])
        >>> messages = command.execute()
        >>> assistant_msg = messages[-1]
        >>> assert assistant_msg["decision"] == "response"
        >>> assert "final_response" in assistant_msg
        
        >>> # Data query processing
        >>> command = ProcessChatMessageCommand([
        ...     {"role": "user", "content": "how many customers?"}
        ... ])
        >>> messages = command.execute()
        >>> assistant_msg = messages[-1]
        >>> assert assistant_msg["decision"] == "use_tool"
        >>> assert assistant_msg["tool"] == "execute_sql_tool"
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

        # Get the latest user message for decision processing
        user_messages = [msg for msg in self.chat_messages if msg.get("role") == "user"]
        if not user_messages:
            raise ValidationException("No user message found for processing.")
        
        latest_user_query = user_messages[-1].get("content", "")
        logger.info(f"Processing user query with decision system: '{latest_user_query}'")
        
        try:
            # Use our decision-based text-to-SQL tool
            decision_result = text_to_sql_tool(latest_user_query)
            logger.info(f"Decision result: {decision_result.get('decision', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Decision processing failed: {e}")
            raise ValidationException("Error in processing user query with decision system.")

        tool_messages = []
        
        # Process based on decision type
        if decision_result.get("decision") == "response":
            # Direct response - no tool execution needed
            response_content = decision_result.get("response", "I apologize, but I couldn't generate a proper response.")
            final_response = {
                "status": "direct_response",
                "response": response_content,
                "decision": "response"
            }
            response_message_config = {
                "role": "assistant", 
                "content": response_content,
                "finish_reason": "stop",
                "decision": "response",
                "reasoning": decision_result.get("reasoning", "Direct response decision"),
                "final_response": final_response
            }
            response_message = self.format_message(**response_message_config)
            
        elif decision_result.get("decision") == "use_tool":
            # Tool execution result
            tool_result = decision_result.get("tool_result", {})
            tool_name = decision_result.get("tool", "unknown")
            
            if tool_result.get("success", False):
                # Format successful tool result
                if tool_name == "execute_sql_tool":
                    sql_data = tool_result.get("data", "No data returned")
                    row_count = tool_result.get("row_count", 0)
                    execution_time = tool_result.get("execution_time_ms", 0)
                    query_executed = tool_result.get("query_executed", "")
                    
                    response_content = f"""I found the answer to your question! Here are the results:

{sql_data}

Query executed successfully in {execution_time:.2f}ms, returning {row_count} row(s)."""
                    
                    # Create clean final response for easy consumption
                    final_response = {
                        "decision": "use_tool",
                        "tool": tool_name,
                        "tool_parameters": decision_result.get("tool_parameters", {}),
                        "query": query_executed,
                        "result": sql_data,
                        "row_count": row_count,
                        "execution_time_ms": execution_time,
                        "status": "success"
                    }
                else:
                    response_content = f"Tool execution completed: {tool_result}"
                    final_response = {
                        "decision": "use_tool",
                        "tool": tool_name,
                        "tool_parameters": decision_result.get("tool_parameters", {}),
                        "status": "success", 
                        "result": tool_result
                    }
            else:
                # Handle tool execution failure
                error_msg = tool_result.get("error", "Unknown error occurred")
                response_content = f"I encountered an issue while retrieving the data: {error_msg}"
                final_response = {
                    "decision": "use_tool",
                    "tool": tool_name,
                    "tool_parameters": decision_result.get("tool_parameters", {}),
                    "status": "error", 
                    "error": error_msg
                }
            
            response_message_config = {
                "role": "assistant",
                "content": response_content, 
                "finish_reason": "stop",
                "decision": "use_tool",
                "tool": tool_name,
                "tool_parameters": decision_result.get("tool_parameters", {}),
                "tool_used": tool_name,
                "tool_success": tool_result.get("success", False),
                "reasoning": decision_result.get("reasoning", "Tool execution decision"),
                "final_response": final_response
            }
            response_message = self.format_message(**response_message_config)
            
        else:
            # Fallback for unknown decision
            fallback_content = "I'm sorry, I had trouble understanding your request. Could you please rephrase it?"
            final_response = {
                "decision": "error",
                "status": "error",
                "error": "Unknown decision type",
                "response": fallback_content
            }
            response_message_config = {
                "role": "assistant",
                "content": fallback_content,
                "finish_reason": "stop",
                "decision": "error",
                "error": "Unknown decision type",
                "final_response": final_response
            }
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
