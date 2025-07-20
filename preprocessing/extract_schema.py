import duckdb
import json
import os

# Resolve absolute paths
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "../app/data/data.db")
models_dir = os.path.join(base_dir, "../models")

# Ensure the output directory exists
os.makedirs(models_dir, exist_ok=True)

# Connect to the local DuckDB database
con = duckdb.connect(db_path)

# Get all table names
tables = con.execute("SHOW TABLES").fetchall()
schema = {}

# Loop through tables and get column names
for (table,) in tables:
    columns = con.execute(f"DESCRIBE {table}").fetchall()
    column_names = [col[0] for col in columns]
    schema[table] = column_names

# Save the full schema structure
with open(os.path.join(models_dir, "full_schema.json"), "w") as f:
    json.dump(schema, f, indent=2)

# Save the same dictionary-style schema as schema_fields.json too
with open(os.path.join(models_dir, "schema_fields.json"), "w") as f:
    json.dump(schema, f, indent=2)

print("Saved schema to `models/full_schema.json` and `models/schema_fields.json`")
