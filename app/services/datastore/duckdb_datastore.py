"""
DuckDB Database Datastore Implementation

This module provides DuckDB-specific implementation of the BaseDatastore interface.
"""

from typing import List

import duckdb
import pandas as pd

from app.services.datastore.base_datastore import BaseDatastore, ConnectionError


class DuckDBDatastore(BaseDatastore):
    """DuckDB implementation of the database datastore interface."""

    def __init__(self, database: str):
        """
        Initialize DuckDB datastore.

        Args:
            database: Path to DuckDB database file
        """
        super().__init__(database)
        self.database = database
        self._connection = None

    def _get_connection(self):
        """Get or create database connection."""
        if self._connection is None:
            try:
                self._connection = duckdb.connect(self.database)
            except Exception as e:
                raise ConnectionError(f"Failed to connect to DuckDB: {e}")
        return self._connection

    def execute(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        try:
            conn = self._get_connection()
            result = conn.execute(sql).fetchdf()
            return result
        except Exception as e:
            raise Exception(f"DuckDB query execution failed: {e}")

    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
        result = self.execute(sql)
        return result['table_name'].tolist()

    def get_columns(self, table_name: str) -> pd.DataFrame:
        """Get column information for a specific table."""
        sql = f"""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        return self.execute(sql)

    def get_sample_data(self, table_name: str, limit: int = 3) -> pd.DataFrame:
        """Get sample data from a table."""
        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute(sql)

    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table."""
        sql = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute(sql)
        return int(result['count'].iloc[0])

    def _get_dialect(self) -> str:
        """Get the SQL dialect name."""
        return 'duckdb'

    def test_connection(self) -> bool:
        """Test if the database connection is working."""
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close()
