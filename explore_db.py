import duckdb

conn = duckdb.connect('app/data/data.db')
tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

for table in tables:
    print(f"\nTable: {table}")
    print("Schema:")
    for row in conn.execute(f"DESCRIBE {table}").fetchall():
        print(row)
    print("Sample data:")
    for row in conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall():
        print(row)