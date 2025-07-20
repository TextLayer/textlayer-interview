import os
import json
import duckdb
import re
from typing import List, Dict
from collections import Counter

def summarize_column(col_name: str, values: List) -> str:
    if not values:
        return f"{col_name} has no values to summarize."

    value_counts = Counter(values)
    most_common = value_counts.most_common(3)
    examples = [str(v) for v, _ in most_common if v is not None]

    description = f"{col_name} "

    if all(isinstance(v, (int, float)) for v in values):
        min_val = min(values)
        max_val = max(values)
        if min_val >= 0 and max_val <= 1 and len(set(values)) <= 3:
            description += "is a binary or boolean-like numeric field. "
        else:
            description += f"contains numeric values ranging from {min_val} to {max_val}. "
        description += f"Example values: {', '.join(examples)}."
    elif all(isinstance(v, str) for v in values):
        lower_vals = [v.lower() for v in values]
        unique_vals = set(lower_vals)
        is_id_like = all(re.match(r"^[A-Za-z]?\d+$", v) for v in values if v)

        if is_id_like:
            description += "appears to contain ID-like strings (e.g., codes or unique identifiers). "
        elif any(k in lower_vals for k in ["yes", "no", "true", "false"]):
            description += "may represent binary labels such as yes/no or true/false. "
        elif any("name" in col_name.lower() or "name" in v.lower() for v in values):
            description += "seems to store names or named entities. "
        elif len(unique_vals) < 15:
            description += f"is likely a categorical field with values such as: {', '.join(set(examples))}. "
        elif any(x in v.lower() for v in values for x in ["west", "east", "north", "south"]):
            description += "may represent geographical directions or regions. "
        else:
            description += "contains various text labels or string categories. "

        description += f" Example values: {', '.join(examples)}."
    else:
        description += f"contains mixed or unrecognized types. Sample values include: {', '.join(examples)}."

    return description.strip()

def summarize_table_schema(con: duckdb.DuckDBPyConnection, table_name: str, sample_limit: int = 1000) -> Dict:
    column_info = con.execute(f"DESCRIBE {table_name}").fetchall()
    sample_data = con.execute(f"SELECT * FROM {table_name} LIMIT {sample_limit}").fetchdf()
    sample_rows = sample_data.to_dict(orient="records")

    columns = []
    for col_name, col_type, *_ in column_info:
        values = sample_data[col_name].dropna().tolist()
        description = summarize_column(col_name, values[:200])
        unique_examples = list(dict.fromkeys(values))[:5]

        columns.append({
            "name": col_name,
            "sample_values": unique_examples,
            "description": description
        })

    return {
        "table_name": table_name,
        "columns": columns,
        "sample_rows": sample_rows[:10]
    }

def build_per_table_schema_json(db_path: str = "data.db", output_dir: str = "./summary", sample_limit: int = 1000):
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    con = duckdb.connect(database=os.path.abspath(db_path))
    tables = con.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    for table in table_names:
        print(f"Processing table: {table}")
        schema_summary = summarize_table_schema(con, table, sample_limit=sample_limit)
        file_path = os.path.join(output_dir, f"{table}.json")
        with open(file_path, "w") as f:
            json.dump(schema_summary, f, indent=2)

    con.close()
    print(f"Summaries saved to {output_dir}")

if __name__ == "__main__":
    build_per_table_schema_json(db_path="../../../data/data.db", output_dir="./summary")
