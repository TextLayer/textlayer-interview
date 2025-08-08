"""
SQL Execution Tool

Executes SQL queries against the database with proper validation and error handling.
Based on Miguel Grinberg's retry patterns for reliability.
"""

import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from langfuse.decorators import observe
import sqlparse
import re

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore


class SqlExecutionRequest(BaseModel):
    """Validated SQL execution request."""
    
    db_name: str = Field(
        default="main",
        title="Database name",
        description="Name of the database to query"
    )
    
    sql: str = Field(
        ...,
        title="SQL query",
        description="The SQL query to execute",
        min_length=1
    )
    
    explanation: str = Field(
        ...,
        title="Query explanation", 
        description="Brief explanation of what this SQL query does",
        min_length=10
    )

    @field_validator('sql')
    @classmethod
    def validate_sql_safety(cls, v: str) -> str:
        """Validate SQL query for safety and proper structure."""
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty")
        
        v = v.strip()
        
        # Basic SQL keyword validation - only allow SELECT for safety
        if not v.upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed for safety")
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r'\b(DROP|DELETE|INSERT|UPDATE|TRUNCATE|ALTER|CREATE)\b',
            r'(--|/\*|\*/)',  # Comments that might hide malicious code
            r'(\bUNION\b.*\bSELECT\b)',  # Potential injection
            r'\b(EXEC|EXECUTE|SP_|XP_)\b',  # Stored procedures
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v.upper()):
                raise ValueError(f"Query contains potentially dangerous pattern: {pattern}")
        
        # Parse SQL to validate syntax
        try:
            parsed = sqlparse.parse(v)
            if not parsed:
                raise ValueError("Query could not be parsed as valid SQL")
        except Exception as e:
            raise ValueError(f"SQL parsing error: {str(e)}")
        
        return v


class SqlExecutionResult(BaseModel):
    """Result of SQL execution."""
    
    success: bool = Field(..., title="Execution success")
    data: Optional[str] = Field(None, title="Query result data")
    row_count: Optional[int] = Field(None, title="Number of rows returned")
    execution_time_ms: Optional[float] = Field(None, title="Execution time in milliseconds")
    error: Optional[str] = Field(None, title="Error message if execution failed")
    query_executed: str = Field(..., title="The actual SQL query that was executed")


class ExecuteSqlTool:
    """
    Tool for executing SQL queries with retry logic and proper error handling.
    
    Implements retry patterns based on Miguel Grinberg's microservices reliability guide.
    """
    
    def __init__(self, database_path: str = "app/data/data.db"):
        """Initialize the SQL execution tool."""
        self.database_path = database_path
        self.max_retries = 3
        self.base_retry_delay = 0.5  # Start with 500ms
    
    @observe()
    def execute(self, request: Dict[str, Any]) -> SqlExecutionResult:
        """
        Execute SQL query with validation and retry logic.
        
        Args:
            request: Dictionary containing sql, db_name, and explanation
            
        Returns:
            SqlExecutionResult with execution details
        """
        try:
            # Validate the request
            validated_request = SqlExecutionRequest(**request)
            logger.info(f"Executing SQL tool: {validated_request.explanation}")
            logger.debug(f"SQL Query: {validated_request.sql}")
            
            # Execute with retry logic
            return self._execute_with_retry(validated_request)
            
        except Exception as e:
            logger.error(f"SQL tool validation failed: {e}")
            return SqlExecutionResult(
                success=False,
                error=f"Request validation failed: {str(e)}",
                query_executed=request.get('sql', 'Invalid query')
            )
    
    def _execute_with_retry(self, request: SqlExecutionRequest) -> SqlExecutionResult:
        """
        Execute SQL with retry logic based on Miguel Grinberg's patterns.
        
        Implements exponential backoff with jitter for database connection issues.
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                # Initialize datastore
                datastore = DuckDBDatastore(database=self.database_path)
                
                # Log SQL execution details
                logger.info(f"🗃️ EXECUTING SQL QUERY:")
                logger.info(f"📝 SQL: {request.sql}")
                logger.info(f"💬 EXPLANATION: {request.explanation}")
                
                # Execute the query
                result_df = datastore.execute(request.sql)
                
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                
                # Format results
                if result_df is not None and not result_df.empty:
                    data = result_df.to_markdown(index=False, floatfmt=".2f")
                    row_count = len(result_df)
                    logger.info(f"✅ SQL EXECUTION SUCCESSFUL: {row_count} rows in {execution_time_ms:.2f}ms")
                    logger.info(f"📊 SQL RESULT DATA:\n{data}")
                else:
                    data = "No results returned."
                    row_count = 0
                    logger.info(f"✅ SQL EXECUTION SUCCESSFUL: No results in {execution_time_ms:.2f}ms")
                
                return SqlExecutionResult(
                    success=True,
                    data=data,
                    row_count=row_count,
                    execution_time_ms=execution_time_ms,
                    query_executed=request.sql
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"SQL execution attempt {attempt + 1} failed: {e}")
                
                # If this was the last attempt, don't retry
                if attempt == self.max_retries:
                    break
                
                # Calculate retry delay with exponential backoff and jitter
                delay = self.base_retry_delay * (2 ** attempt)
                # Add jitter (up to 25% randomization)
                import random
                jitter = random.uniform(0.75, 1.25)
                actual_delay = delay * jitter
                
                logger.info(f"Retrying SQL execution in {actual_delay:.2f}s (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(actual_delay)
        
        # All retries failed
        error_msg = f"SQL execution failed after {self.max_retries + 1} attempts. Last error: {str(last_error)}"
        logger.error(error_msg)
        
        return SqlExecutionResult(
            success=False,
            error=error_msg,
            query_executed=request.sql
        )
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about this tool."""
        return {
            "name": "execute_sql_tool",
            "description": "Execute SQL queries against the database",
            "max_retries": self.max_retries,
            "base_retry_delay": self.base_retry_delay,
            "database_path": self.database_path
        }


# Tool instance for use in the application
sql_tool = ExecuteSqlTool()