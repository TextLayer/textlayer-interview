"""
Schema Generation Script for Text-to-SQL Prompt Engineering

This script automatically generates a comprehensive database schema description
that can be used in prompts for better SQL generation.
"""

import json
import sys
import os
from pathlib import Path

# Add app to path so we can use the same datastore
sys.path.append(str(Path(__file__).parent.parent))

from app.services.datastore.duckdb_datastore import DuckDBDatastore


class SchemaGenerator:
    """Generate comprehensive schema information for prompt engineering."""
    
    def __init__(self, database_path: str = "app/data/data.db"):
        """Initialize with database path."""
        self.datastore = DuckDBDatastore(database_path)
        
    def get_all_tables(self):
        """Get list of all tables in the database."""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
        ORDER BY table_name
        """
        return self.datastore.execute(query)
    
    def get_table_schema(self, table_name: str):
        """Get detailed schema for a specific table."""
        query = f"DESCRIBE {table_name}"
        return self.datastore.execute(query)
    
    def get_sample_data(self, table_name: str, limit: int = 3):
        """Get sample data for understanding the table content."""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        try:
            return self.datastore.execute(query)
        except Exception as e:
            print(f"⚠️ Could not get sample data for {table_name}: {e}")
            return None
    
    def get_table_relationships(self):
        """Analyze relationships between tables based on Key/ParentId patterns."""
        relationships = {}
        
        # Check each table for Key/ParentId structure
        tables = self.get_all_tables()
        for _, row in tables.iterrows():
            table_name = row['table_name']
            try:
                schema = self.get_table_schema(table_name)
                columns = schema['column_name'].tolist()
                
                if 'Key' in columns and 'ParentId' in columns:
                    relationships[table_name] = {
                        "type": "hierarchical",
                        "primary_key": "Key",
                        "parent_key": "ParentId",
                        "description": f"Self-referencing hierarchy in {table_name}"
                    }
            except Exception as e:
                print(f"⚠️ Could not analyze {table_name}: {e}")
        
        return relationships
    
    def generate_comprehensive_schema(self):
        """Generate a comprehensive schema description for prompts."""
        schema_info = {
            "database_type": "DuckDB",
            "description": "Financial business intelligence database with hierarchical account, customer, and product structures",
            "tables": {},
            "relationships": {},
            "business_context": {
                "domain": "Financial Analytics",
                "key_concepts": [
                    "Account hierarchy (revenue, costs, margins)",
                    "Customer geographic regions",
                    "Product line categorization",
                    "Time-based financial tracking"
                ]
            }
        }
        
        # Get all tables
        tables = self.get_all_tables()
        print(f"📊 Found {len(tables)} tables")
        
        # Analyze each table
        for _, row in tables.iterrows():
            table_name = row['table_name']
            print(f"🔍 Analyzing table: {table_name}")
            
            try:
                # Get schema
                schema = self.get_table_schema(table_name)
                
                # Get sample data
                sample = self.get_sample_data(table_name)
                
                # Build table info
                table_info = {
                    "columns": [],
                    "row_count_sample": len(sample) if sample is not None else 0,
                    "sample_data": sample.to_dict('records') if sample is not None else [],
                    "business_purpose": self._get_business_purpose(table_name)
                }
                
                # Add column details
                for _, col_row in schema.iterrows():
                    table_info["columns"].append({
                        "name": col_row['column_name'],
                        "type": col_row['column_type'],
                        "nullable": col_row['null'] == 'YES',
                        "description": self._get_column_description(table_name, col_row['column_name'])
                    })
                
                schema_info["tables"][table_name] = table_info
                
            except Exception as e:
                print(f"❌ Error analyzing {table_name}: {e}")
        
        # Analyze relationships
        schema_info["relationships"] = self.get_table_relationships()
        
        return schema_info
    
    def _get_business_purpose(self, table_name: str) -> str:
        """Get business purpose description for a table."""
        purposes = {
            "account": "Financial account hierarchy including revenue, costs, and calculated metrics",
            "customer": "Customer and geographic region hierarchy",
            "product": "Product categorization and line hierarchy", 
            "time": "Time dimension for financial reporting",
            "other": "Additional financial metrics and calculated fields",
            "time_perspective": "Time-based analysis perspectives",
            "version": "Data versioning for financial scenarios"
        }
        return purposes.get(table_name, "Business data table")
    
    def _get_column_description(self, table_name: str, column_name: str) -> str:
        """Get description for specific columns."""
        descriptions = {
            "Key": "Unique identifier/primary key",
            "ParentId": "Reference to parent in hierarchy",
            "Name": "Human-readable name/description", 
            "AccountType": "Type classification for accounts",
            "CalculationMethod": "Method used for financial calculations",
            "DebitCredit": "Debit (0) or Credit (1) indicator",
            "UNARY_OPERATOR": "Mathematical operator for calculations",
            "Channel": "Sales or distribution channel",
            "Location": "Geographic location",
            "Product Line": "Product categorization"
        }
        return descriptions.get(column_name, f"Data field in {table_name}")
    
    def save_schema_json(self, schema_info: dict, output_path: str = "scripts/database_schema.json"):
        """Save schema information to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema_info, f, indent=2, default=str)
        print(f"💾 Schema saved to {output_path}")
    
    def generate_prompt_schema_text(self, schema_info: dict) -> str:
        """Generate schema text optimized for LLM prompts."""
        prompt_text = []
        
        prompt_text.append("# DATABASE SCHEMA")
        prompt_text.append(f"Database: {schema_info['description']}")
        prompt_text.append("")
        
        # Business context
        prompt_text.append("## Business Context")
        for concept in schema_info['business_context']['key_concepts']:
            prompt_text.append(f"- {concept}")
        prompt_text.append("")
        
        # Tables
        prompt_text.append("## Tables")
        for table_name, table_info in schema_info['tables'].items():
            prompt_text.append(f"### {table_name.upper()}")
            prompt_text.append(f"Purpose: {table_info['business_purpose']}")
            prompt_text.append("Columns:")
            
            for col in table_info['columns']:
                nullable = " (nullable)" if col['nullable'] else ""
                prompt_text.append(f"- {col['name']}: {col['type']}{nullable} - {col['description']}")
            
            # Sample data
            if table_info['sample_data']:
                prompt_text.append("Sample data:")
                for i, row in enumerate(table_info['sample_data'][:2]):
                    row_str = ", ".join([f"{k}='{v}'" for k, v in row.items() if v is not None])
                    prompt_text.append(f"  {i+1}. {row_str}")
            prompt_text.append("")
        
        # Relationships
        if schema_info['relationships']:
            prompt_text.append("## Key Relationships")
            for table, rel_info in schema_info['relationships'].items():
                prompt_text.append(f"- {table}: {rel_info['description']}")
            prompt_text.append("")
        
        return "\n".join(prompt_text)


def main():
    """Main function to generate schema files."""
    print("🔧 Generating Database Schema for Text-to-SQL Prompts")
    print("=" * 55)
    
    # Initialize generator
    generator = SchemaGenerator()
    
    # Generate comprehensive schema
    schema_info = generator.generate_comprehensive_schema()
    
    # Save JSON version
    generator.save_schema_json(schema_info)
    
    # Generate prompt-optimized text
    prompt_text = generator.generate_prompt_schema_text(schema_info)
    
    # Save prompt text
    with open("scripts/database_schema_prompt.txt", 'w', encoding='utf-8') as f:
        f.write(prompt_text)
    print("💾 Prompt text saved to scripts/database_schema_prompt.txt")
    
    print("\n✅ Schema generation completed!")
    print(f"📊 Generated schema for {len(schema_info['tables'])} tables")
    print("Files created:")
    print("- scripts/database_schema.json (comprehensive)")
    print("- scripts/database_schema_prompt.txt (for prompts)")


if __name__ == "__main__":
    main()