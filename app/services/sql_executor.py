"""
Universal SQL Executor Service

This service executes SQL queries against any supported database
using the universal database abstraction layer.
"""

import time
import traceback
from typing import Any, Dict, Optional

import pandas as pd

from app.services.datastore.base_datastore import BaseDatastore
from app.services.datastore.connection_factory import create_datastore
from app.services.sql_dialect_manager import dialect_manager
from config import Config


class Executor:
    """
    Universal SQL Executor that works with any supported database.
    Singleton pattern to ensure single database connection.
    """

    _instance: Optional['Executor'] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(Executor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize executor."""
        if not self._initialized:
            self._datastore: Optional[BaseDatastore] = None
            self._connection_string: Optional[str] = None
            self._initialized = True

    @classmethod
    def getInstance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, connection_string: Optional[str] = None) -> None:
        """
        Initialize the executor with a database connection.

        Args:
            connection_string: Database connection string.
                             If None, uses default from config.
        """
        if connection_string is None:
            connection_string = Config.get_database_connection_string()

        if connection_string != self._connection_string:
            # Connection changed, close old connection
            if self._datastore:
                self._datastore.close()

            # Create new datastore
            self._datastore = create_datastore(connection_string)
            self._connection_string = connection_string

    def execute(self, sql: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a SQL query and return results with metadata.

        Args:
            sql: SQL query string
            **kwargs: Additional parameters (for compatibility)

        Returns:
            Dict containing:
                - success: bool
                - data: pandas.DataFrame (if successful)
                - error: str (if failed)
                - execution_time: float
                - database_type: str
                - row_count: int
        """
        if not self._datastore:
            self.initialize()

        start_time = time.time()

        try:
            # Execute the query
            result_df = self._datastore.execute(sql)
            execution_time = time.time() - start_time

            return {
                'success': True,
                'data': result_df,
                'error': None,
                'execution_time': execution_time,
                'database_type': self._datastore.dialect,
                'row_count': len(result_df),
                'columns': list(result_df.columns) if not result_df.empty else [],
                'sql': sql
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)

            # Add dialect-specific error context
            if self._datastore:
                dialect_info = dialect_manager.get_dialect_info(self._datastore.dialect)
                if dialect_info:
                    error_msg += f" (Database: {dialect_info.display_name})"

            return {
                'success': False,
                'data': pd.DataFrame(),
                'error': error_msg,
                'execution_time': execution_time,
                'database_type': self._datastore.dialect if self._datastore else 'unknown',
                'row_count': 0,
                'columns': [],
                'sql': sql,
                'traceback': traceback.format_exc()
            }

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information.

        Returns:
            Dict: Database metadata
        """
        if not self._datastore:
            self.initialize()

        return self._datastore.get_database_info()

    def get_dialect(self) -> str:
        """
        Get the current database dialect.

        Returns:
            str: Database dialect name
        """
        if not self._datastore:
            self.initialize()

        return self._datastore.dialect

    def test_connection(self) -> bool:
        """
        Test if database connection is working.

        Returns:
            bool: True if connection is successful
        """
        if not self._datastore:
            try:
                self.initialize()
            except Exception:
                return False

        return self._datastore.test_connection()

    def validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL syntax by attempting to explain the query.

        Args:
            sql: SQL query to validate

        Returns:
            Dict containing validation results
        """
        if not self._datastore:
            self.initialize()

        try:
            # Try to explain the query (most databases support this)
            explain_sql = f"EXPLAIN {sql}"
            self._datastore.execute(explain_sql)

            return {
                'valid': True,
                'error': None,
                'database_type': self._datastore.dialect
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'database_type': self._datastore.dialect
            }

    def get_query_plan(self, sql: str) -> Dict[str, Any]:
        """
        Get query execution plan.

        Args:
            sql: SQL query

        Returns:
            Dict containing query plan information
        """
        if not self._datastore:
            self.initialize()

        try:
            explain_sql = f"EXPLAIN {sql}"
            plan_df = self._datastore.execute(explain_sql)

            return {
                'success': True,
                'plan': plan_df,
                'database_type': self._datastore.dialect
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'database_type': self._datastore.dialect
            }

    def switch_database(self, connection_string: str) -> bool:
        """
        Switch to a different database.

        Args:
            connection_string: New database connection string

        Returns:
            bool: True if switch was successful
        """
        try:
            old_datastore = self._datastore

            # Create new connection
            new_datastore = create_datastore(connection_string)

            # Test new connection
            if not new_datastore.test_connection():
                new_datastore.close()
                return False

            # Switch to new connection
            if old_datastore:
                old_datastore.close()

            self._datastore = new_datastore
            self._connection_string = connection_string

            return True

        except Exception:
            return False

    def close(self):
        """Close database connection."""
        if self._datastore:
            self._datastore.close()
            self._datastore = None
        self._connection_string = None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close()


# For backwards compatibility
def get_executor() -> Executor:
    """Get executor instance."""
    return Executor.getInstance()