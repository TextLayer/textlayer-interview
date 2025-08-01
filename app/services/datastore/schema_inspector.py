"""
Schema inspection service for database analysis and context generation.
"""
import json
from typing import Dict, List, Optional
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app import logger


class SchemaInspector:
    """
    Service for inspecting database schema and generating context for LLM prompts.
    """
    
    def __init__(self, database_path: str):
        self.datastore = DuckDBDatastore(database=database_path)
        self._schema_cache = None
        self._sample_data_cache = {}
    
    def get_database_schema(self) -> Dict:
        """
        Get complete database schema information.
        
        Returns:
            Dict: Complete schema information including tables, columns, and sample data
        """
        if self._schema_cache is not None:
            return self._schema_cache
            
        try:
            # Get all tables
            tables_df = self.datastore.execute("SHOW TABLES")
            tables = tables_df['name'].tolist() if not tables_df.empty else []
            
            schema_info = {
                "tables": {},
                "total_tables": len(tables),
                "database_type": "DuckDB",
                "description": "Financial dataset with transaction and account information"
            }
            
            for table_name in tables:
                try:
                    # Get column information
                    columns_df = self.datastore.execute(f"DESCRIBE {table_name}")
                    columns = []
                    
                    for _, row in columns_df.iterrows():
                        columns.append({
                            "name": row['column_name'],
                            "type": row['column_type'],
                            "nullable": row.get('null', 'YES') == 'YES'
                        })
                    
                    # Get sample data (first 3 rows)
                    sample_df = self.datastore.get_sample_data(table_name, limit=3)
                    sample_data = sample_df.to_dict('records') if not sample_df.empty else []
                    
                    # Get row count
                    count_df = self.datastore.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    row_count = count_df.iloc[0]['count'] if not count_df.empty else 0
                    
                    schema_info["tables"][table_name] = {
                        "columns": columns,
                        "sample_data": sample_data,
                        "row_count": row_count,
                        "description": self._infer_table_description(table_name, columns)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not inspect table {table_name}: {e}")
                    schema_info["tables"][table_name] = {
                        "columns": [],
                        "sample_data": [],
                        "row_count": 0,
                        "description": "Table inspection failed"
                    }
            
            self._schema_cache = schema_info
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}")
            return {
                "tables": {},
                "total_tables": 0,
                "database_type": "DuckDB",
                "description": "Schema inspection failed"
            }
    
    def _infer_table_description(self, table_name: str, columns: List[Dict]) -> str:
        """
        Infer table description based on name and columns.
        """
        column_names = [col['name'].lower() for col in columns]
        table_lower = table_name.lower()
        
        # Map actual table names to descriptions
        table_descriptions = {
            'account': 'Account information and financial account details',
            'customer': 'Customer information and demographics', 
            'other': 'Additional financial data and transaction details',
            'product': 'Product information and financial products',
            'time': 'Time and date dimension data',
            'time_perspective': 'Time perspective and period definitions',
            'version': 'Version control and data versioning information'
        }
        
        # Return specific description if available
        if table_lower in table_descriptions:
            return table_descriptions[table_lower]
        
        # Fallback to pattern matching
        if any(word in table_lower for word in ['transaction', 'trans', 'payment']):
            return "Transaction records with financial movement data"
        elif any(word in table_lower for word in ['account', 'customer', 'user']):
            return "Account or customer information"
        elif any(word in table_lower for word in ['balance', 'position']):
            return "Account balance or position data"
        elif 'amount' in column_names or 'value' in column_names:
            return "Financial data with monetary amounts"
        elif 'date' in column_names or 'time' in column_names:
            return "Time-series financial data"
        else:
            return f"Financial data table with {len(columns)} columns"
    
    def get_schema_context_for_prompt(self) -> str:
        """
        Generate schema context string for LLM prompts.
        
        Returns:
            str: Formatted schema information for prompt inclusion
        """
        schema = self.get_database_schema()
        
        if not schema["tables"]:
            return "No database schema available."
        
        context_parts = [
            f"Database: {schema['database_type']} with {schema['total_tables']} tables",
            f"Description: {schema['description']}\n"
        ]
        
        for table_name, table_info in schema["tables"].items():
            context_parts.append(f"Table: {table_name}")
            context_parts.append(f"  Description: {table_info['description']}")
            context_parts.append(f"  Rows: {table_info['row_count']:,}")
            context_parts.append("  Columns:")
            
            for col in table_info["columns"]:
                nullable = " (nullable)" if col["nullable"] else ""
                context_parts.append(f"    - {col['name']}: {col['type']}{nullable}")
            
            if table_info["sample_data"]:
                context_parts.append("  Sample data:")
                for i, row in enumerate(table_info["sample_data"][:2], 1):
                    row_str = ", ".join([f"{k}={v}" for k, v in row.items()])
                    context_parts.append(f"    Row {i}: {row_str}")
            
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_relevant_tables_for_query(self, query: str) -> List[str]:
        """
        Identify which tables are most relevant for a given query.
        
        Args:
            query: Natural language query
            
        Returns:
            List of relevant table names
        """
        schema = self.get_database_schema()
        query_lower = query.lower()
        relevant_tables = []
        
        # Map query keywords to actual table names in our database
        table_mapping = {
            'transaction': ['other', 'account'],  # 'other' likely contains transaction data
            'account': ['account', 'customer'],
            'customer': ['customer', 'account'],
            'amount': ['other', 'account'],  # Financial amounts likely in these tables
            'balance': ['account', 'other'],
            'total': ['other', 'account'],
            'time': ['time', 'time_perspective'],
            'date': ['time', 'time_perspective'],
            'product': ['product'],
            'version': ['version']
        }
        
        # Score tables based on query content
        for table_name, table_info in schema["tables"].items():
            score = 0
            table_lower = table_name.lower()
            
            # Direct table name match
            if table_lower in query_lower:
                score += 10
            
            # Check mapped keywords
            for keyword, mapped_tables in table_mapping.items():
                if keyword in query_lower and table_lower in mapped_tables:
                    score += 8
            
            # Check column names for relevance
            column_names = [col['name'].lower() for col in table_info['columns']]
            query_words = query_lower.split()
            for word in query_words:
                if any(word in col_name for col_name in column_names):
                    score += 3
            
            # Default relevance for financial queries
            if any(word in query_lower for word in ['total', 'amount', 'sum', 'count', 'financial']):
                if table_lower in ['other', 'account', 'customer']:  # Most likely financial tables
                    score += 5
            
            if score > 0:
                relevant_tables.append((table_name, score))
        
        # If no specific matches, return the most likely financial tables
        if not relevant_tables:
            return ['other', 'account', 'customer']  # Default financial tables
        
        # Sort by relevance score and return table names
        relevant_tables.sort(key=lambda x: x[1], reverse=True)
        return [table[0] for table in relevant_tables]
