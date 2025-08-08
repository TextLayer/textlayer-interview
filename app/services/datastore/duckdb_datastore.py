import duckdb
import pandas as pd
from typing import Optional, Dict, Any



class DuckDBDatastore:
    """
    A datastore implementation for DuckDB.
    """

    def __init__(self, database: Optional[str] = None) -> None:
        """
        Initialize the DuckDBDataStore.

        Args:
            database (str, optional): Path to the DuckDB database file.
                                      If None, an in-memory database is used.
        """
        if database is None:
            database = ':memory:'
        self.connection = duckdb.connect(database=database)

    def execute(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return the result as a DataFrame.

        Args:
            query (str): The SQL query to execute.
            parameters (Dict[str, Any], optional): Parameters to include in the query.

        Returns:
            pd.DataFrame: The query result.
        """
        if parameters:
            return self.connection.execute(query, parameters).df()
        else:
            return self.connection.execute(query).df()
        

    def get_columns(
        self, table_name: str, schema_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retrieve column information for a specific table.

        Args:
            table_name (str): Name of the table.
            schema_name (str, optional): Schema name.

        Returns:
            pd.DataFrame: DataFrame with column information.
        """
        schema_filter = f"AND table_schema = '{schema_name}'" if schema_name else ""
        query = f"""
        SELECT column_name, data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = '{table_name}' {schema_filter}
        """
        return self.execute(query)

    def get_sample_data(
        self, table_name: str, limit: int = 5, schema_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retrieve a sample of data from a specific table.

        Args:
            table_name (str): Name of the table.
            limit (int, optional): Number of rows to retrieve. Defaults to 5.
            schema_name (str, optional): Schema name.

        Returns:
            pd.DataFrame: DataFrame with sample data.
        """
        schema_prefix = f"{schema_name}." if schema_name else ""
        query = f"""
        SELECT *
        FROM {schema_prefix}{table_name}
        ORDER BY RANDOM()
        LIMIT {limit}
        """
        return self.execute(query)

    def get_schema_info(self) -> str:
        """
        Get comprehensive schema information for the database.
        
        Returns:
            str: Formatted schema information including tables, columns, and data types
        """
        try:
            # Get all tables
            tables_query = """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_name
            """
            tables_df = self.execute(tables_query)
            
            if tables_df.empty:
                return "No tables found in the database."
            
            schema_info = "Database Schema:\n"
            schema_info += "=" * 50 + "\n\n"
            
            for _, table_row in tables_df.iterrows():
                table_name = table_row['table_name']
                table_type = table_row.get('table_type', 'TABLE')
                
                schema_info += f"{table_type}: {table_name}\n"
                schema_info += "-" * (len(table_type) + len(table_name) + 2) + "\n"
                
                # Get columns for this table
                try:
                    columns_query = f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                    """
                    columns_df = self.execute(columns_query)
                    
                    for _, col_row in columns_df.iterrows():
                        col_name = col_row['column_name']
                        col_type = col_row['data_type']
                        nullable = col_row.get('is_nullable', 'YES')
                        null_indicator = "" if nullable == 'YES' else " NOT NULL"
                        
                        schema_info += f"  • {col_name}: {col_type}{null_indicator}\n"
                        
                except Exception as e:
                    schema_info += f"  Error retrieving columns: {e}\n"
                
                schema_info += "\n"
            
            return schema_info
            
        except Exception as e:
            # Fallback: try to get basic table information using DuckDB system tables
            try:
                fallback_query = "SHOW TABLES"
                tables_df = self.execute(fallback_query)
                
                if tables_df.empty:
                    return "No tables found in the database."
                
                schema_info = "Database Tables (Basic Info):\n"
                schema_info += "=" * 35 + "\n\n"
                
                for _, table_row in tables_df.iterrows():
                    table_name = table_row.iloc[0]  # First column is table name
                    schema_info += f"Table: {table_name}\n"
                    
                    try:
                        # Get column info using DESCRIBE
                        describe_query = f"DESCRIBE {table_name}"
                        columns_df = self.execute(describe_query)
                        
                        for _, col_row in columns_df.iterrows():
                            col_name = col_row.get('column_name', col_row.iloc[0])
                            col_type = col_row.get('column_type', col_row.iloc[1] if len(col_row) > 1 else 'UNKNOWN')
                            schema_info += f"  • {col_name}: {col_type}\n"
                            
                    except Exception:
                        schema_info += f"  Could not retrieve column details\n"
                    
                    schema_info += "\n"
                
                return schema_info
                
            except Exception:
                return f"Could not retrieve schema information: {e}"
