from langfuse.decorators import observe
from vaul import tool_call
from typing import Dict, Any
from pydantic import ValidationError
import json

from app import logger
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs.text_to_sql import UserQueryDecision
from app.services.tools.tool_registry import tool_registry
from flask import current_app


@tool_call
@observe
def text_to_sql(query: str) -> Dict[str, Any]:
    """
    Intelligent Text-to-SQL Decision System with LLM Tool Calling.
    
    This advanced system uses Gemini 2.5 Flash with LiteLLM tool calling to make
    intelligent decisions about user queries. Instead of hardcoded pattern matching,
    it leverages AI to determine the appropriate response strategy.
    
    Architecture:
        1. **Query Analysis**: LLM analyzes user intent and context
        2. **Decision Making**: Uses structured tool calling to decide action
        3. **Tool Execution**: Validates and executes SQL tools if needed
        4. **Response Formatting**: Returns structured, transparent results
    
    Decision Types:
        - **"response"**: Direct conversational responses (greetings, help, etc.)
        - **"use_tool"**: Data queries requiring database access
    
    Key Features:
        - ✅ Real AI decision making (no hardcoded rules)
        - ✅ Gemini 2.5 Flash with LiteLLM tool calling
        - ✅ Structured JSON schema validation
        - ✅ Complete transparency (decision, reasoning, parameters)
        - ✅ Comprehensive error handling and fallbacks
        - ✅ Langfuse observability integration
    
    Args:
        query (str): Natural language query from the user
        
    Returns:
        Dict[str, Any]: Structured response containing:
            - decision: "response" or "use_tool"
            - response: Direct response text (if decision="response")
            - tool: Tool name (if decision="use_tool")
            - tool_parameters: Tool parameters (if decision="use_tool")
            - tool_result: Tool execution result (if decision="use_tool")
            - reasoning: LLM explanation of the decision
            - success: Boolean indicating operation success
            - error: Error message (if success=False)
    
    Raises:
        Exception: For unexpected errors in LLM communication or tool execution
        
    Examples:
        >>> # Conversational query
        >>> result = text_to_sql("hello how are you")
        >>> assert result["decision"] == "response"
        >>> assert "response" in result
        
        >>> # Data query
        >>> result = text_to_sql("how many customers are there")
        >>> assert result["decision"] == "use_tool"
        >>> assert result["tool"] == "execute_sql_tool"
        >>> assert "tool_result" in result
    """

    logger.info(f"Processing user query: '{query}'")

    try:
        # Initialize the LLM session for decision generation
        llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL", "gemini/gemini-2.5-flash"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL", "gemini-embedding-001"),
        )

        # Get available tools and guidelines
        available_tools = tool_registry.get_available_tools()
        decision_guidelines = tool_registry.get_decision_guidelines()
        tool_configs = tool_registry.get_all_tool_configs()
        
        # Define the decision-making tool using LiteLLM tool calling format
        decision_tool = {
            "type": "function",
            "function": {
                "name": "make_decision",
                "description": "Decide how to handle a user query - respond directly or use tools",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["response", "use_tool"],
                            "description": "Whether to respond directly or use a tool"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation of why this decision was made",
                            "minLength": 10
                        },
                        "response": {
                            "type": "string",
                            "description": "Direct response text (only if decision is 'response')"
                        },
                        "tool": {
                            "type": "string",
                            "description": "Tool name to use (only if decision is 'use_tool')"
                        },
                        "tool_parameters": {
                            "type": "object",
                            "description": "Parameters for the tool (only if decision is 'use_tool')",
                            "properties": {
                                "sql": {
                                    "type": "string",
                                    "description": "SQL query to execute"
                                },
                                "explanation": {
                                    "type": "string", 
                                    "description": "Brief explanation of what the SQL query does"
                                }
                            }
                        }
                    },
                    "required": ["decision", "reasoning"]
                }
            }
        }

        # Prepare decision prompt for Gemini 2.5 Flash
        decision_prompt = f"""Analyze this user query and decide how to handle it.

Available tools: {list(available_tools)}

Decision guidelines:
- Use "response" for: greetings, help requests, general questions, explanations
- Use "use_tool" for: data queries, counting, searching, analysis requiring database access

User query: "{query}"

Call the make_decision function with your analysis."""

        messages = [
            {
                "role": "user",
                "content": decision_prompt
            }
        ]

        logger.info("🤖 GENERATING DECISION using Gemini 2.5 Flash with tool calling...")
        
        try:
            # Use LiteLLM tool calling for structured decision making
            response = llm_session.chat(
                messages=messages,
                tools=[decision_tool],
                tool_choice="auto"
            )
            
            # Extract tool call result
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                decision_data = json.loads(tool_call.function.arguments)
                
                logger.info(f"🎯 DECISION MADE: {decision_data.get('decision')}")
                logger.info(f"💭 REASONING: {decision_data.get('reasoning')}")
                if decision_data.get('tool'):
                    logger.info(f"🔧 SELECTED TOOL: {decision_data.get('tool')}")
                if decision_data.get('tool_parameters'):
                    logger.info(f"📋 TOOL PARAMETERS: {decision_data.get('tool_parameters')}")
                    
            else:
                # Fallback if no tool call
                logger.warning("No tool call received, defaulting to direct response")
                decision_data = {
                    "decision": "response",
                    "response": "I can help you with questions about your data or general conversation. What would you like to know?",
                    "reasoning": "No structured decision received from LLM"
                }
            
        except Exception as e:
            logger.error(f"Tool calling failed: {e}")
            
            # Fallback to direct response on tool calling failure
            return {
                "decision": "response", 
                "response": "I'm sorry, I had trouble understanding your query. Could you please rephrase it?",
                "reasoning": f"Tool calling failed: {e}",
                "success": False,
                "error": "Tool calling error"
            }
        
        # Execute based on decision
        if decision_data.get("decision") == "response":
            logger.info("Responding directly to user")
            return {
                "decision": "response",
                "response": decision_data.get("response", "I can help you with questions about your data or general conversation."),
                "reasoning": decision_data.get("reasoning"),
                "success": True
            }
        
        elif decision_data.get("decision") == "use_tool":
            tool_name = decision_data.get("tool", "execute_sql_tool")
            tool_parameters = decision_data.get("tool_parameters", {})
            
            logger.info(f"Using tool: {tool_name}")
            
            # Validate tool exists
            if tool_name not in available_tools:
                logger.error(f"Requested tool '{tool_name}' not available. Available: {available_tools}")
                return {
                    "decision": "response",
                    "response": f"I'm sorry, the requested tool '{tool_name}' is not available.",
                    "reasoning": f"Tool '{tool_name}' not found",
                    "success": False,
                    "error": f"Tool not found: {tool_name}"
                }
            
            # Validate tool parameters
            validation_result = tool_registry.validate_tool_parameters(tool_name, tool_parameters)
            if not validation_result["valid"]:
                logger.error(f"Tool parameter validation failed: {validation_result['errors']}")
                return {
                    "decision": "response", 
                    "response": "I'm sorry, there was an issue with the tool parameters. Please try rephrasing your question.",
                    "reasoning": f"Tool parameter validation failed: {validation_result['errors']}",
                    "success": False,
                    "error": "Tool parameter validation failed"
                }
            
            # Execute the tool
            logger.info(f"🔧 EXECUTING TOOL: {tool_name}")
            logger.info(f"📋 TOOL PARAMETERS: {tool_parameters}")
            tool_result = tool_registry.execute_tool(tool_name, tool_parameters)
            
            if tool_result.get("success", False):
                logger.info(f"✅ Tool '{tool_name}' executed successfully")
                logger.info(f"📊 TOOL RESULT: {tool_result}")
                return {
                    "decision": "use_tool",
                    "tool": tool_name,
                    "tool_parameters": tool_parameters,
                    "tool_result": tool_result,
                    "reasoning": decision_data.get("reasoning"),
                    "success": True
                }
            else:
                logger.error(f"Tool '{tool_name}' execution failed: {tool_result.get('error', 'Unknown error')}")
                return {
                    "decision": "response",
                    "response": "I'm sorry, I encountered an issue while trying to retrieve the data. Please try again later.",
                    "reasoning": f"Tool execution failed: {tool_result.get('error', 'Unknown error')}",
                    "tool_error": tool_result.get('error'),
                    "success": False,
                    "error": "Tool execution failed"
                }
        
        # Fallback for unexpected decision format
        else:
            logger.warning(f"Unknown decision type: {decision_data.get('decision')}")
            return {
                "decision": "response",
                "response": "I can help you with questions about your data or general conversation. What would you like to know?",
                "reasoning": f"Unknown decision type: {decision_data.get('decision')}",
                "success": True
            }

    except Exception as e:
        logger.error(f"Error in text_to_sql tool: {e}")
        return {
            "decision": "response",
            "response": "I'm sorry, I encountered an unexpected error. Please try again.",
            "reasoning": f"Unexpected error: {str(e)}",
            "success": False,
            "error": str(e)
        }


def _format_tools_for_prompt(tool_configs: Dict[str, Any]) -> str:
    """Format tool configurations for the decision prompt."""
    if not tool_configs:
        return "No tools available."
    
    formatted_tools = []
    for tool_name, config in tool_configs.items():
        description = config.get("description", "No description available")
        parameters = config.get("parameters", {}).get("properties", {})
        param_list = ", ".join(parameters.keys()) if parameters else "No parameters"
        
        formatted_tools.append(f"- **{tool_name}**: {description} (Parameters: {param_list})")
    
    return "\n".join(formatted_tools)


