"""
Base Database Datastore Interface

This module defines the abstract base class for database datastores,
enabling support for multiple database engines (DuckDB, PostgreSQL, MySQL, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class BaseDatastore(ABC):
    """
    Abstract base class for database datastores.
    Each database engine should implement this interface.
    """

    def __init__(self, connection_string: str):
        """
        Initialize the datastore with a connection string.

        Args:
            connection_string: Database connection string or file path
        """
        self.connection_string = connection_string
        self.dialect = self._get_dialect()

    @abstractmethod
    def execute(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string

        Returns:
            pandas.DataFrame: Query results
        """
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the database.

        Returns:
            List[str]: Table names
        """
        pass

    @abstractmethod
    def get_columns(self, table_name: str) -> pd.DataFrame:
        """
        Get column information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            pandas.DataFrame: Column information with columns:
                - column_name: str
                - data_type: str
                - is_nullable: str ('YES' or 'NO')
        """
        pass

    @abstractmethod
    def get_sample_data(self, table_name: str, limit: int = 3) -> pd.DataFrame:
        """
        Get sample data from a table.

        Args:
            table_name: Name of the table
            limit: Number of rows to return

        Returns:
            pandas.DataFrame: Sample data
        """
        pass

    @abstractmethod
    def get_row_count(self, table_name: str) -> int:
        """
        Get total row count for a table.

        Args:
            table_name: Name of the table

        Returns:
            int: Row count
        """
        pass

    @abstractmethod
    def _get_dialect(self) -> str:
        """
        Get the SQL dialect name for this datastore.

        Returns:
            str: Dialect name (e.g., 'duckdb', 'postgresql', 'mysql')
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the database connection is working.

        Returns:
            bool: True if connection is successful
        """
        pass

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get general database information.

        Returns:
            Dict containing database metadata
        """
        try:
            tables = self.get_tables()
            total_tables = len(tables)

            # Get row counts for all tables
            table_info = {}
            for table in tables:
                try:
                    table_info[table] = self.get_row_count(table)
                except Exception:
                    table_info[table] = 0

            return {
                'dialect': self.dialect,
                'connection_string': self.connection_string,
                'total_tables': total_tables,
                'tables': table_info,
                'connection_status': self.test_connection()
            }
        except Exception as e:
            return {
                'dialect': self.dialect,
                'connection_string': self.connection_string,
                'error': str(e),
                'connection_status': False
            }


class DatastoreError(Exception):
    """Custom exception for datastore operations."""
    pass


class UnsupportedDatabaseError(DatastoreError):
    """Raised when trying to use an unsupported database type."""
    pass


class ConnectionError(DatastoreError):
    """Raised when database connection fails."""
    pass