from app.services.datastore.duckdb_datastore import DuckDBDatastore

def get_database_schema_summary() -> str:
    db = DuckDBDatastore("app/data/data.db")
    try:
        tables = db.execute("SHOW TABLES")
    except Exception:
        return "Error reading schema."

    schema_summaries = []

    for table in tables["name"]:
        try:
            cols = db.get_columns(table)
            col_defs = [
                f"{row['column_name']} ({row['data_type']})"
                for _, row in cols.iterrows()
            ]

            # Heuristically infer table purpose
            col_names = [row['column_name'].lower() for _, row in cols.iterrows()]
            if any("revenue" in c or "amount" in c or "debit" in c or "credit" in c for c in col_names):
                guess = "Likely contains financial transaction or revenue data."
            elif any("customer" in c or "channel" in c or "location" in c for c in col_names):
                guess = "Contains customer or market segmentation details."
            elif any("product" in c or "line" in c for c in col_names):
                guess = "Contains product or product line information."
            elif any("quarter" in c or "month" in c or "year" in c for c in col_names):
                guess = "Time dimension table with temporal breakdowns."
            elif any("version" in c or "status" in c or "ruleset" in c for c in col_names):
                guess = "Contains versioning or scenario planning metadata."
            else:
                guess = "General reference or hierarchy table."

            schema_summaries.append(
                f"Table `{table}`:\n  " +
                "\n  ".join(col_defs) +
                f"\n  -- {guess}"
            )
        except Exception:
            continue

    return "\n\n".join(schema_summaries)