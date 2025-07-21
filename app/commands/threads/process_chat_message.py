from typing import Dict, List
from flask import current_app, g

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.prompts.chat_prompt import chat_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs import text_to_sql
from app.services.llm.tools.text_to_sql import text_to_sql as text_to_sql_tool
from app.services.datastore.duckdb_datastore import DuckDBDatastore
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

        # Get dynamic schema information
        datastore = DuckDBDatastore(database="app/data/data.db")
        schema_info = self.get_dynamic_database_schema(datastore)

        # Pass dynamic schema to chat_prompt
        system_prompt = chat_prompt(schema_info=schema_info)

        trimmed_messages = system_prompt + trimmed_messages

        return trimmed_messages

    def get_dynamic_database_schema(self, datastore: DuckDBDatastore) -> str:
        """Get a dynamic description of the database schema."""
        
        try:
            # Get all tables
            tables = datastore.execute("SHOW TABLES")
            table_names = [row.name for row in tables.itertuples()]
            
            schema_description = "# Financial Data Warehouse Schema\n\n"
            schema_description += "This database contains the following tables:\n\n"
            
            for table_name in table_names:
                # Get table schema
                schema = datastore.execute(f"DESCRIBE {table_name}")
                
                # Get row count
                count = datastore.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = count.iloc[0, 0]
                
                # Get sample data for examples
                sample = datastore.execute(f"SELECT * FROM {table_name} LIMIT 3")
                
                schema_description += f"## {table_name.upper()} Table ({row_count:,} records)\n"
                
                # Add column information
                for row in schema.itertuples():
                    schema_description += f"- **{row.column_name}**: {row.column_type}\n"
                
                # Add sample data examples
                if not sample.empty:
                    # Show sample data structure
                    sample_dict = sample.iloc[0].to_dict()
                    schema_description += f"- **Sample data**: {sample_dict}\n"
                    
                    # Analyze hierarchical structure
                    if 'ParentId' in sample.columns:
                        schema_description += f"- **Hierarchical structure**: Uses ParentId for parent-child relationships\n"
                    
                    # Check for key patterns
                    if 'Key' in sample.columns:
                        schema_description += f"- **Key patterns**: Hierarchical keys (e.g., 40 → 400 → 4000)\n"
                
                schema_description += "\n"
            
            # Add important guidelines
            schema_description += """**Important Guidelines:**
- **CRITICAL**: Use ONLY the tables and columns listed above - no others exist
- **Hierarchical data**: Use ParentId relationships for drill-down analysis
- **Key structure**: Keys follow hierarchical patterns (parent → child → grandchild)
- **JOINs**: Connect tables using appropriate key relationships
- **DuckDB syntax**: Use proper DuckDB SQL syntax
- **No financial amounts**: Focus on dimensional relationships, not transactional values

**Anti-Hallucination Rules:**
- Never use table names not listed above
- Never assume columns exist beyond those shown
- If requested data doesn't exist, return appropriate message
- Base all queries strictly on the schema provided above"""
            
            return schema_description
            
        except Exception as e:
            logger.error(f"Error getting dynamic database schema: {e}")
            # Fallback to basic description
            return """# Financial Data Warehouse Schema

Database schema information unavailable. Please use standard SQL queries to explore the available tables and columns.

**Available Commands:**
- SHOW TABLES - to see all tables
- DESCRIBE table_name - to see table structure
- SELECT * FROM table_name LIMIT 5 - to see sample data

**CRITICAL**: Only use tables and columns that actually exist in the database."""

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
