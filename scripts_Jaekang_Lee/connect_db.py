"""
Database Connection Utility for TextLayer Interview

This module provides utilities for connecting to and interacting with the DuckDB database
used in the text-to-SQL interview challenge.
"""

import duckdb
import pandas as pd
from typing import Optional, Dict, Any, List
import os
from pathlib import Path


class DatabaseConnector:
    """Utility class for connecting to and exploring the interview database."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path (str, optional): Path to database file. 
                                   Defaults to 'app/data/data.db' relative to project root.
        """
        if db_path is None:
            # Default to the interview database
            project_root = Path(__file__).parent.parent
            db_path = project_root / "app" / "data" / "data.db"
        
        self.db_path = str(db_path)
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = duckdb.connect(database=self.db_path)
            print(f"✅ Connected to database: {self.db_path}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.
        
        Args:
            query (str): SQL query to execute
            parameters (dict, optional): Query parameters
            
        Returns:
            pd.DataFrame: Query results
        """
        try:
            if parameters:
                result = self.connection.execute(query, parameters).df()
            else:
                result = self.connection.execute(query).df()
            return result
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            print(f"Query: {query}")
            raise
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        tables_df = self.execute_query("SHOW TABLES")
        return tables_df['name'].tolist()
    
    def describe_table(self, table_name: str) -> pd.DataFrame:
        """Get schema information for a specific table."""
        return self.execute_query(f"DESCRIBE {table_name}")
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Get sample data from a table."""
        return self.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive information about a table."""
        try:
            schema = self.describe_table(table_name)
            sample_data = self.get_sample_data(table_name)
            row_count = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            
            return {
                'table_name': table_name,
                'schema': schema,
                'sample_data': sample_data,
                'row_count': row_count.iloc[0]['count'],
                'column_count': len(schema)
            }
        except Exception as e:
            print(f"❌ Failed to get info for table {table_name}: {e}")
            return {}
    
    def explore_database(self) -> Dict[str, Any]:
        """Comprehensive database exploration."""
        print("🔍 Starting database exploration...\n")
        
        # Get all tables
        tables = self.get_tables()
        print(f"📋 Found {len(tables)} tables: {', '.join(tables)}\n")
        
        # Analyze each table
        table_info = {}
        for table in tables:
            print(f"📊 Analyzing table: {table}")
            info = self.get_table_info(table)
            table_info[table] = info
            
            if info:
                print(f"   - Rows: {info['row_count']:,}")
                print(f"   - Columns: {info['column_count']}")
                print(f"   - Key columns: {', '.join(info['schema']['column_name'].head(3).tolist())}")
            print()
        
        return {
            'database_path': self.db_path,
            'total_tables': len(tables),
            'table_names': tables,
            'table_details': table_info
        }
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")


def get_database_connection(db_path: Optional[str] = None) -> DatabaseConnector:
    """
    Factory function to create a database connection.
    
    Args:
        db_path (str, optional): Path to database file
        
    Returns:
        DatabaseConnector: Connected database instance
    """
    return DatabaseConnector(db_path)


if __name__ == "__main__":
    # Example usage when run directly
    print("🚀 TextLayer Interview Database Explorer")
    print("=" * 50)
    
    # Connect to database
    db = get_database_connection()
    
    # Explore database
    exploration_results = db.explore_database()
    
    # Close connection
    db.close()
    
    print("✅ Exploration complete!")