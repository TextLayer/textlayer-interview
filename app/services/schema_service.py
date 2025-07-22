"""
Database Schema Service

This service manages database schema information using the universal
database abstraction layer, supporting multiple database types.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from app.services.datastore.base_datastore import BaseDatastore
from app.services.datastore.connection_factory import create_datastore
from app.services.sql_dialect_manager import dialect_manager
from config import Config


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[Dict[str, str]]
    row_count: int
    sample_data: pd.DataFrame


@dataclass
class DatabaseSchema:
    """Complete database schema information."""
    database_type: str
    connection_string: str
    tables: Dict[str, TableInfo]
    total_tables: int
    total_rows: int


class SchemaService:
    """
    Service for managing database schema information.
    Works with any supported database type through the abstraction layer.
    """

    def __init__(self):
        """Initialize schema service."""
        self._datastore: Optional[BaseDatastore] = None
        self._schema_cache: Optional[DatabaseSchema] = None
        self._connection_string = None

    def initialize(self, connection_string: Optional[str] = None) -> None:
        """
        Initialize the schema service with a database connection.

        Args:
            connection_string: Database connection string.
                             If None, uses default from config.
        """
        if connection_string is None:
            connection_string = Config.get_database_connection_string()

        if connection_string != self._connection_string:
            # Connection changed, reset cache
            self._schema_cache = None
            self._connection_string = connection_string

            # Create new datastore
            if self._datastore:
                self._datastore.close()

            self._datastore = create_datastore(connection_string)

    def get_schema(self, force_refresh: bool = False) -> DatabaseSchema:
        """
        Get complete database schema information.

        Args:
            force_refresh: If True, ignore cache and refresh schema

        Returns:
            DatabaseSchema: Complete schema information
        """
        if not self._datastore:
            self.initialize()

        if self._schema_cache and not force_refresh:
            return self._schema_cache

        # Build schema from database
        tables_info = {}
        total_rows = 0

        tables = self._datastore.get_tables()

        for table_name in tables:
            try:
                # Get column information
                columns_df = self._datastore.get_columns(table_name)
                columns = [
                    {
                        'name': row['column_name'],
                        'type': row['data_type'],
                        'nullable': row['is_nullable']
                    }
                    for _, row in columns_df.iterrows()
                ]

                # Get row count
                row_count = self._datastore.get_row_count(table_name)
                total_rows += row_count

                # Get sample data
                sample_data = self._datastore.get_sample_data(table_name, limit=3)

                tables_info[table_name] = TableInfo(
                    name=table_name,
                    columns=columns,
                    row_count=row_count,
                    sample_data=sample_data
                )

            except Exception:
                # Skip tables that can't be accessed
                continue

        self._schema_cache = DatabaseSchema(
            database_type=self._datastore.dialect,
            connection_string=self._connection_string,
            tables=tables_info,
            total_tables=len(tables_info),
            total_rows=total_rows
        )

        return self._schema_cache

    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """
        Get information about a specific table.

        Args:
            table_name: Name of the table

        Returns:
            TableInfo: Table information or None if not found
        """
        schema = self.get_schema()
        return schema.tables.get(table_name)

    def get_table_names(self) -> List[str]:
        """
        Get list of all table names.

        Returns:
            List[str]: Table names
        """
        schema = self.get_schema()
        return list(schema.tables.keys())

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get general database information.

        Returns:
            Dict: Database metadata
        """
        if not self._datastore:
            self.initialize()

        return self._datastore.get_database_info()

    def format_schema_for_llm(self) -> str:
        """
        Format schema information for LLM consumption.
        Includes database-specific SQL syntax information.

        Returns:
            str: Formatted schema string
        """
        schema = self.get_schema()

        # Get dialect information
        dialect_info = dialect_manager.get_dialect_info(schema.database_type)
        dialect_name = dialect_info.display_name if dialect_info else schema.database_type

        output = []
        output.append(f"=== DATABASE SCHEMA ({dialect_name}) ===")
        output.append(f"Total Tables: {schema.total_tables}")
        output.append(f"Total Rows: {schema.total_rows:,}")
        output.append("")

        # Add dialect-specific information
        if dialect_info:
            output.append("=== SQL DIALECT INFORMATION ===")
            output.append(f"Quote Character: {dialect_info.quote_char}")
            output.append(f"Limit Syntax: {dialect_info.limit_syntax}")
            output.append(f"Supported Features: {', '.join(dialect_info.features)}")
            output.append("")

            # Add key function examples
            output.append("=== KEY FUNCTIONS ===")
            output.append("Date Functions:")
            for func, sql in list(dialect_info.date_functions.items())[:3]:
                output.append(f"  {func}: {sql}")

            output.append("Aggregate Functions:")
            for func, sql in list(dialect_info.aggregate_functions.items())[:5]:
                output.append(f"  {func}: {sql}")
            output.append("")

        # Add table information
        output.append("=== TABLES ===")

        for table_name, table_info in schema.tables.items():
            output.append(f"\nTable: {table_name}")
            output.append(f"Rows: {table_info.row_count:,}")
            output.append("Columns:")

            for col in table_info.columns:
                nullable = "NULL" if col['nullable'] == 'YES' else "NOT NULL"
                output.append(f"  - {col['name']}: {col['type']} {nullable}")

            # Add sample data if available
            if not table_info.sample_data.empty:
                output.append("Sample Data:")
                # Convert to string representation
                sample_str = table_info.sample_data.to_string(index=False, max_rows=3)
                for line in sample_str.split('\n'):
                    output.append(f"  {line}")

        return '\n'.join(output)

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

    def get_dialect(self) -> str:
        """
        Get the database dialect name.

        Returns:
            str: Dialect name
        """
        if not self._datastore:
            self.initialize()

        return self._datastore.dialect

    def close(self):
        """Close database connection."""
        if self._datastore:
            self._datastore.close()
            self._datastore = None
        self._schema_cache = None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close()


# Global instance
schema_service = SchemaService()