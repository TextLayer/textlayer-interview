from app.services.datastore.duckdb_datastore import DuckDBDatastore

def get_database_schema():
    """Get the complete database schema using the existing DuckDBDatastore."""
    
    # Use the existing datastore class
    datastore = DuckDBDatastore(database="app/data/data.db")
    
    # Get all tables
    tables = datastore.execute("SHOW TABLES")
    
    schema_text = "COMPLETE DATABASE SCHEMA:\n\n"
    
    for _, row in tables.iterrows():
        table_name = row['name']
        
        schema_text += f"Table: {table_name}\n"
        schema_text += "Schema:\n"
        
        # Get column details using datastore
        columns = datastore.execute(f"DESCRIBE {table_name}")
        for _, col_row in columns.iterrows():
            schema_text += f"{tuple(col_row)}\n"
        
        # Get sample data using existing method
        sample_data = datastore.get_sample_data(table_name, limit=3)
        schema_text += "Sample data:\n"
        for _, sample_row in sample_data.iterrows():
            schema_text += f"{tuple(sample_row)}\n"
        
        schema_text += "\n"
    
    return schema_text