import json
from typing import Dict, List
from uuid import uuid4

from flask import current_app, g
from langfuse.decorators import observe
from openai import BadRequestError
from vaul import Toolkit

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.datastore.qdrant_datastore import QdrantVectorDatastore
from app.services.kg.kg import KnowledgeGraph
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs import text_to_sql
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.utils.formatters import get_timestamp


class ProcessChatMessageCommand(ReadCommand):
    """
    Process a chat message.
    """
    def __init__(self, chat_messages: List[Dict[str, str]]) -> None:
        self.chat_messages = chat_messages
        self.retry_count = 0
        self.max_retries = 2
        self.last_errors = []
        self.kg = KnowledgeGraph()
        loaded_graph = self.kg.load()  # Load existing schema graph
        if not loaded_graph:
            logger.warning("No schema graph found - schema context will be empty")
        self.qdrant_datastore = QdrantVectorDatastore(
            host=current_app.config.get("QDRANT_HOST"),
            port=current_app.config.get("QDRANT_PORT")
        )
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

        # Get the schema context from KG
        schema_context = self.kg.get_schema()
        logger.debug(f"Schema context loaded: {schema_context[:100]}...")

        # Embedding the user's message
        embedding = self.llm_session.generate_embedding(text=self.chat_messages[-1]["content"])

        # Search the vector database for similar messages
        search_results = self.qdrant_datastore.search(query_vector=embedding, limit=5)
        logger.info(f"Search results: {search_results}")

        # Get the most similar message
        if search_results:
            # Append the context to the chat messages
            self.chat_messages.append({
                "role": "assistant",
                "content": f"Schema context: {schema_context}\n\nDomain values context retrived from vector database: {search_results[0]}",
            })
        else:
            self.chat_messages.append({
                "role": "assistant",
                "content": f"Schema context: {schema_context}",
            })

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

        return self._process_llm_response(response)

    def _process_llm_response(self, response):
        """
        Process LLM response (extracted from execute method for reuse)
        """
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

            # Execute tools and check for errors
            has_errors = False
            error_details = []
            for tool_call in tool_calls:
                tool_run = self.execute_tool_call(tool_call)
                
                # Check if tool execution failed
                if isinstance(tool_run, dict) and "error" in tool_run:
                    has_errors = True
                    error_details.append(f"Tool {tool_run['tool_name']}: {tool_run['error']}")
                    logger.error(f"Tool {tool_run['tool_name']} failed: {tool_run['error']}")
                
                tool_messages.append(
                    self.format_message(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=json.dumps(tool_run),
                    )
                )
            
            # Store error details for retry context
            if has_errors:
                self.last_errors = error_details
            
            # Add current messages
            self.chat_messages.append(response_message)
            self.chat_messages.extend(tool_messages)
            
            # If there were errors, retry with error context
            if has_errors:
                return self.retry_with_error_context()
                
        else:
            response_message = self.format_message(**response_message_config)
            self.chat_messages.append(response_message)

        return self.chat_messages

    @observe()
    def retry_with_error_context(self) -> List[Dict[str, str]]:
        """
        Retry execution after tool errors, adding error context for the LLM to learn.
        """
        if self.retry_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) reached, returning with errors")
            return self.chat_messages
        
        self.retry_count += 1
        logger.info(f"Retrying execution (attempt {self.retry_count}/{self.max_retries}) with error context")
        
        # Add error context message to help LLM understand what went wrong
        error_summary = "\n".join(getattr(self, 'last_errors', ['Unknown error occurred']))
        error_context_message = {
            "role": "user", 
            "content": f"""The previous SQL query failed with the following error(s):

            {error_summary}

            Please analyze the error and generate a corrected query. 
                        
            Key points to remember:
            - The 'account' table does NOT have a 'Year' column
            - Time information is in the 'time' table 
            - If you need both account and time data, consider the relationship between tables
            - Focus on what the user actually asked for
            - Generate simpler queries that work with the available columns""",
        }
        
        self.chat_messages.append(error_context_message)
        
        # Get new response from LLM with error context
        chat_kwargs = {
            "messages": self.prepare_chat_messages(),
            "tools": self.toolkit.tool_schemas(),
        }
        
        try:
            response = self.llm_session.chat(**chat_kwargs)
        except Exception as e:
            logger.error(f"Failed to fetch retry chat response: {e}")
            return self.chat_messages
        
        # Process the new response (this will recursively call execute logic)
        return self._process_llm_response(response)

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
        try:
            return self.toolkit.run_tool(
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
        except Exception as e:
            # Return error info instead of raising
            return {
                "error": str(e),
                "tool_name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            }
