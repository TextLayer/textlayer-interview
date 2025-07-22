"""
Dynamic Database Schema Service

This service dynamically fetches the current database schema and provides
contextual information for the AI model. It's designed to be easily toggleable
and will automatically adapt to database changes.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[Dict[str, str]]
    sample_data: pd.DataFrame
    row_count: Optional[int] = None


class DatabaseSchemaService:
    """Service for dynamically fetching and managing database schema
    information."""

    def __init__(self, database_path: str = "app/data/data.db"):
        self.database_path = database_path
        self.datastore = DuckDBDatastore(database=database_path)
        self._schema_cache = {}
        self._cache_valid = False

    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        try:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
            result = self.datastore.execute(query)
            return result['table_name'].tolist()
        except Exception as e:
            logger.error(f"Failed to fetch table names: {e}")
            return []

    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """Get comprehensive information about a specific table."""
        try:
            # Get column information
            columns_df = self.datastore.get_columns(table_name)
            columns = []
            for _, row in columns_df.iterrows():
                columns.append({
                    'name': row['column_name'],
                    'type': row['data_type'],
                    'nullable': row['is_nullable']
                })

            # Get sample data
            sample_data = self.datastore.get_sample_data(table_name, limit=3)

            # Get row count
            count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            count_result = self.datastore.execute(count_query)
            row_count = (count_result['row_count'].iloc[0]
                         if not count_result.empty else 0)

            return TableInfo(
                name=table_name,
                columns=columns,
                sample_data=sample_data,
                row_count=row_count
            )
        except Exception as e:
            logger.error(f"Failed to fetch info for table {table_name}: {e}")
            return None

    def get_database_context(self) -> str:
        """Generate comprehensive database context for AI model."""
        if not self._cache_valid:
            self._refresh_schema_cache()

        context_parts = []
        context_parts.append("**Database Schema Information:**\n")

        tables = self.get_all_tables()
        if not tables:
            return "Database schema information unavailable."

        for table_name in tables:
            table_info = self.get_table_info(table_name)
            if not table_info:
                continue

            context_parts.append(f"\n**{table_name}** Table:")
            context_parts.append(f"- Rows: {table_info.row_count:,}")

            # Column information
            context_parts.append("- Columns:")
            for col in table_info.columns:
                nullable = "NULL" if col['nullable'] == 'YES' else "NOT NULL"
                context_parts.append(
                    f"  * {col['name']} ({col['type']}) {nullable}")

            # Sample data preview
            if not table_info.sample_data.empty:
                context_parts.append("- Sample Data:")
                sample_str = table_info.sample_data.head(2).to_string(
                    index=False)
                context_parts.append(f"```\n{sample_str}\n```")

        return "\n".join(context_parts)

    def _refresh_schema_cache(self):
        """Refresh the internal schema cache."""
        try:
            self._schema_cache = {}
            tables = self.get_all_tables()
            for table in tables:
                self._schema_cache[table] = self.get_table_info(table)
            self._cache_valid = True
            logger.info(f"Schema cache refreshed for {len(tables)} tables")
        except Exception as e:
            logger.error(f"Failed to refresh schema cache: {e}")
            self._cache_valid = False

    def invalidate_cache(self):
        """Manually invalidate the schema cache."""
        self._cache_valid = False
        self._schema_cache = {}


# Singleton instance
_schema_service = None


def get_schema_service() -> DatabaseSchemaService:
    """Get the singleton schema service instance."""
    global _schema_service
    if _schema_service is None:
        _schema_service = DatabaseSchemaService()
    return _schema_service