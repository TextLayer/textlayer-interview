import sqlite3
from typing import Any, Dict, Optional

import pandas as pd


class SQLiteDatastore:
    """A datastore implementation for SQLite."""

    def __init__(self, database: Optional[str] = None) -> None:
        """
        Initialize the SQLiteDatastore.

        Args:
            database (str, optional): Path to the SQLite database file.
                                      If None, an in-memory database is used.
        """
        if database is None:
            database = ":memory:"
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row

    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return the result as a DataFrame.

        Args:
            query (str): The SQL query to execute.
            parameters (Dict[str, Any], optional): Parameters to include in the query.

        Returns:
            pd.DataFrame: The query result.
        """
        cursor = self.connection.cursor()
        if parameters:
            cursor.execute(query, parameters)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return pd.DataFrame(rows, columns=columns)

    def get_columns(self, table_name: str) -> pd.DataFrame:
        """
        Retrieve column information for a specific table.

        Args:
            table_name (str): Name of the table.
            schema_name (str, optional): Ignored in SQLite (no schema support).

        Returns:
            pd.DataFrame: DataFrame with column information.
        """
        query = f"PRAGMA table_info('{table_name}')"
        df = self.execute(query)
        df.rename(
            columns={"name": "column_name", "type": "data_type", "notnull": "is_nullable", "pk": "primary_key"},
            inplace=True,
        )
        df["is_nullable"] = ~df["is_nullable"].astype(bool)
        df["character_maximum_length"] = None
        return df[["column_name", "data_type", "is_nullable", "character_maximum_length"]]

    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """
        Retrieve a sample of data from a specific table.

        Args:
            table_name (str): Name of the table.
            limit (int, optional): Number of rows to retrieve. Defaults to 5.
            schema_name (str, optional): Ignored in SQLite (no schema support).

        Returns:
            pd.DataFrame: DataFrame with sample data.
        """
        query = f"""
        SELECT *
        FROM {table_name}
        ORDER BY RANDOM()
        LIMIT {limit}
        """
        return self.execute(query)
