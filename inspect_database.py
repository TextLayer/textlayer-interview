"""
Simple script to inspect the database schema and understand the data structure.
"""
import duckdb
import pandas as pd

def inspect_database():
    """Inspect the database to understand its structure."""
    conn = duckdb.connect('app/data/data.db')
    
    # Get all tables
    tables = conn.execute('SHOW TABLES').fetchall()
    print("Available tables:")
    for table in tables:
        table_name = table[0]
        print(f"- {table_name}")
    
    print("\nDetailed table information:")
    print("=" * 50)
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get column information
        try:
            columns = conn.execute(f'DESCRIBE {table_name}').fetchall()
            print("Columns:")
            for col in columns:
                col_name, col_type = col[0], col[1]
                print(f"  - {col_name}: {col_type}")
            
            # Get row count
            count = conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
            print(f"Row count: {count:,}")
            
            # Get sample data (first 3 rows)
            if count > 0:
                sample = conn.execute(f'SELECT * FROM {table_name} LIMIT 3').fetchall()
                print("Sample data:")
                for i, row in enumerate(sample, 1):
                    print(f"  Row {i}: {row}")
            
        except Exception as e:
            print(f"Error inspecting {table_name}: {e}")
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
