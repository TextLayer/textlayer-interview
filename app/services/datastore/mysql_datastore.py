"""
MySQL Database Datastore Implementation

This module provides MySQL-specific implementation of the BaseDatastore interface.
"""

from typing import List

import pandas as pd

try:
    import pymysql
    import sqlalchemy
    from sqlalchemy import create_engine, text
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from app.services.datastore.base_datastore import BaseDatastore, ConnectionError


class MySQLDatastore(BaseDatastore):
    """MySQL implementation of the database datastore interface."""

    def __init__(self, connection_string: str):
        """
        Initialize MySQL datastore.

        Args:
            connection_string: MySQL connection string
                             (e.g., 'mysql://user:pass@host:port/db')
        """
        if not MYSQL_AVAILABLE:
            raise ImportError(
                "MySQL dependencies not installed. "
                "Run: pip install pymysql sqlalchemy"
            )

        super().__init__(connection_string)
        self._engine = None

        # Add charset to connection string if not present
        if '?' not in self.connection_string:
            self.connection_string += '?charset=utf8mb4'
        elif 'charset' not in self.connection_string:
            self.connection_string += '&charset=utf8mb4'

    def _get_engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            try:
                self._engine = create_engine(
                    self.connection_string,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            except Exception as e:
                raise ConnectionError(f"Failed to connect to MySQL: {e}")
        return self._engine

    def execute(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                result = pd.read_sql(text(sql), conn)
                return result
        except Exception as e:
            raise Exception(f"MySQL query execution failed: {e}")

    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_type = 'BASE TABLE'
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
        AND table_schema = DATABASE()
        ORDER BY ordinal_position
        """
        return self.execute(sql)

    def get_sample_data(self, table_name: str, limit: int = 3) -> pd.DataFrame:
        """Get sample data from a table."""
        sql = f"SELECT * FROM `{table_name}` LIMIT {limit}"
        return self.execute(sql)

    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table."""
        sql = f"SELECT COUNT(*) as count FROM `{table_name}`"
        result = self.execute(sql)
        return int(result['count'].iloc[0])

    def _get_dialect(self) -> str:
        """Get the SQL dialect name."""
        return 'mysql'

    def test_connection(self) -> bool:
        """Test if the database connection is working."""
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self):
        """Close database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close()