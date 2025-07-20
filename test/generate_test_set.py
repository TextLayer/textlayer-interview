import os
import json
import duckdb
from openai import OpenAI

# Initialize OpenAI with Doppler-managed API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Step 1: Connect to database and extract schema
con = duckdb.connect("../data.db")
tables = con.execute("SHOW TABLES").fetchall()

schema = {}
for (table_name,) in tables:
    columns = con.execute(f"DESCRIBE {table_name}").fetchall()
    schema[table_name] = [col[0] for col in columns]  # just column names

# Step 2: Build prompt to generate test cases
prompt = f"""
You are an AI that generates test sets for a text-to-SQL system.

The database schema is:
{json.dumps(schema, indent=2)}

Generate 20 diverse test cases as a JSON array in the following format:
[
  {{
    "user_query": "How many entries are in the product table?",
    "sql_query": "SELECT COUNT(*) FROM product;",
    "natural_language_answer": "There are X entries in the product table."
  }},
  ...
]

Rules:
- Use only the table and column names shown above.
- Do not invent tables or columns.
- Use DuckDB SQL syntax only.
- Avoid MySQL-specific functions like DATE_SUB.
- Output only the JSON array. No extra text or markdown.
"""

# Step 3: Send prompt to OpenAI
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a SQL test case generator."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3
)

# Step 4: Parse response
response_text = response.choices[0].message.content.strip()
if response_text.startswith("```json"):
    response_text = response_text.lstrip("```json").rstrip("```").strip()
elif response_text.startswith("```"):
    response_text = response_text.lstrip("```").rstrip("```").strip()

try:
    test_cases = json.loads(response_text)
except json.JSONDecodeError:
    print("[ERROR] GPT response is not valid JSON:\n")
    print(response_text)
    exit(1)

# Step 5: Try executing each SQL query and store actual result
for tc in test_cases:
    sql = tc.get("sql_query", "")
    try:
        result = con.execute(sql).fetchall()
        tc["actual_result"] = result
    except Exception as e:
        tc["actual_result"] = f"Error executing SQL: {str(e)}"

# Step 6: Save test cases with actual results
with open("sample_test_set.json", "w") as f:
    json.dump(test_cases, f, indent=2)

print("Saved 20 test cases to sample_test_set.json with actual SQL results.")
