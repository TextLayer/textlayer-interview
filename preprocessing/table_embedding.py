import json
import openai
import pickle
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Use OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set the models directory relative to the current file (preprocessing/)
models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))

# Load schema
with open(os.path.join(models_dir, "schema_fields.json"), "r") as f:
    schema = json.load(f)

# Load summaries from ../models/summary folder
summary_dir = os.path.join(models_dir, "summary")
summaries = {}

for file in os.listdir(summary_dir):
    if file.endswith(".json"):
        with open(os.path.join(summary_dir, file), "r") as f:
            summary = json.load(f)
            summaries[summary["table_name"]] = summary

# Helper: get OpenAI embedding
def get_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding

# Embedding storage
table_embeddings = {}
field_embeddings = {}

# Table name embeddings
for table in schema:
    print(f"Embedding table: {table}")
    table_embeddings[table] = get_embedding(table)

# Field embeddings with context
for table, fields in schema.items():
    for field in fields:
        qualified_name = f"{table}.{field}"
        print(f"Embedding field: {qualified_name}")

        summary = summaries.get(table, {})
        col_info = next((col for col in summary.get("columns", []) if col["name"] == field), None)

        if col_info:
            dtype = col_info.get("type", "unknown")
            sample_values = col_info.get("sample_values", [])
            sample_str = ", ".join(map(str, sample_values[:5]))
            text = f"Field: {field}\nType: {dtype}\nSample values: {sample_str}"
        else:
            text = qualified_name

        field_embeddings[qualified_name] = get_embedding(text)

# Save embeddings to ../models
with open(os.path.join(models_dir, "table_embeddings.pkl"), "wb") as f:
    pickle.dump(table_embeddings, f)

with open(os.path.join(models_dir, "field_embeddings.pkl"), "wb") as f:
    pickle.dump(field_embeddings, f)

print("Saved table embeddings to `table_embeddings.pkl`")
print("Saved field embeddings to `field_embeddings.pkl`")
