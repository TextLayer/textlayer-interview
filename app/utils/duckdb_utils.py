import pandas as pd
import os
from pathlib import Path

SCHEMA_PATH = "/app/data/auxiliary_data/schema.csv"
TABLE_EXAMPLES_PATH = "/app/data/auxiliary_data/table_examples.csv"

"""
This file contains utility helpers for database operations that provide context to the agent

Below is a duckdb SQL query to generate table names and associated schemas, the top level agent and optionally tools will need this 
context to reliably generate SQL statements from natural language, the schema can be pre generated to save latency
"""

schema_query = """
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS;
"""

"""
Below is a duckdb SQL query to generate 5 rows of non null example data from all tables in order to allow the agent  more context
on the actual contents of the tables to the agent
"""

# the above query is used to generate a CSV in app/data/auxiliary_data/schema.csv

# a set of valid datetime functions for DuckDB
VALID_DATETIME_FUNCTIONS = """
current_date
Description	Current date (at start of current transaction) in the local time zone. Note that parentheses should be omitted from the function call.
Example	current_date
Result	2022-10-08
date_add(date, interval)
Description	Add the interval to the date and return a DATETIME value.
Example	date_add(DATE '1992-09-15', INTERVAL 2 MONTH)
Result	1992-11-15 00:00:00
date_diff(part, startdate, enddate)
Description	The number of partition boundaries between the dates.
Example	date_diff('month', DATE '1992-09-15', DATE '1992-11-14')
Result	2
date_part(part, date)
Description	Get the subfield (equivalent to extract).
Example	date_part('year', DATE '1992-09-20')
Result	1992
date_sub(part, startdate, enddate)
Description	The number of complete partitions between the dates.
Example	date_sub('month', DATE '1992-09-15', DATE '1992-11-14')
Result	1
date_trunc(part, date)
Description	Truncate to specified precision.
Example	date_trunc('month', DATE '1992-03-07')
Result	1992-03-01
datediff(part, startdate, enddate)
Description	The number of partition boundaries between the dates.
Example	datediff('month', DATE '1992-09-15', DATE '1992-11-14')
Result	2
Alias	date_diff.
datepart(part, date)
Description	Get the subfield (equivalent to extract).
Example	datepart('year', DATE '1992-09-20')
Result	1992
Alias	date_part.
datesub(part, startdate, enddate)
Description	The number of complete partitions between the dates.
Example	datesub('month', DATE '1992-09-15', DATE '1992-11-14')
Result	1
Alias	date_sub.
datetrunc(part, date)
Description	Truncate to specified precision.
Example	datetrunc('month', DATE '1992-03-07')
Result	1992-03-01
Alias	date_trunc.
dayname(date)
Description	The (English) name of the weekday.
Example	dayname(DATE '1992-09-20')
Result	Sunday
extract(part from date)
Description	Get subfield from a date.
Example	extract('year' FROM DATE '1992-09-20')
Result	1992
greatest(date, date)
Description	The later of two dates.
Example	greatest(DATE '1992-09-20', DATE '1992-03-07')
Result	1992-09-20
isfinite(date)
Description	Returns true if the date is finite, false otherwise.
Example	isfinite(DATE '1992-03-07')
Result	true
isinf(date)
Description	Returns true if the date is infinite, false otherwise.
Example	isinf(DATE '-infinity')
Result	true
julian(date)
Description	Extract the Julian Day number from a date.
Example	julian(DATE '1992-09-20')
Result	2448886.0
last_day(date)
Description	The last day of the corresponding month in the date.
Example	last_day(DATE '1992-09-20')
Result	1992-09-30
least(date, date)
Description	The earlier of two dates.
Example	least(DATE '1992-09-20', DATE '1992-03-07')
Result	1992-03-07
make_date(year, month, day)
Description	The date for the given parts.
Example	make_date(1992, 9, 20)
Result	1992-09-20
monthname(date)
Description	The (English) name of the month.
Example	monthname(DATE '1992-09-20')
Result	September
strftime(date, format)
Description	Converts a date to a string according to the format string.
Example	strftime(DATE '1992-01-01', '%a, %-d %B %Y')
Result	Wed, 1 January 1992
time_bucket(bucket_width, date[, offset])
Description	Truncate date to a grid of width bucket_width. The grid is anchored at 2000-01-01[ + offset] when bucket_width is a number of months or coarser units, else 2000-01-03[ + offset]. Note that 2000-01-03 is a Monday.
Example	time_bucket(INTERVAL '2 months', DATE '1992-04-20', INTERVAL '1 month')
Result	1992-04-01
time_bucket(bucket_width, date[, origin])
Description	Truncate timestamptz to a grid of width bucket_width. The grid is anchored at the origin timestamp, which defaults to 2000-01-01 when bucket_width is a number of months or coarser units, else 2000-01-03. Note that 2000-01-03 is a Monday.
Example	time_bucket(INTERVAL '2 weeks', DATE '1992-04-20', DATE '1992-04-01')
Result	1992-04-15
today()
Description	Current date (start of current transaction) in UTC.
Example	today()
Result	2022-10-08
"""


def load_table_schema():
    df = pd.read_csv(Path(os.getcwd() + SCHEMA_PATH))
    return df.to_string()


def generate_table_examples(con, schema="main", limit=5):
    """
    For each BASE TABLE in `schema`, collect up to `limit` rows, preferring rows
    with the MOST non-empty fields (non-NULL and not empty string '').
    Returns: table_name, column_names, row_json
    """

    def quote_ident(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def json_key(key: str) -> str:
        return "'" + key.replace("'", "''") + "'"

    # 1) List tables in the schema
    tables = [
        r[0]
        for r in con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ? AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            [schema],
        ).fetchall()
    ]

    dfs = []
    for tbl in tables:
        # 2) Get ordered column names
        cols = [
            r[0]
            for r in con.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
                """,
                [schema, tbl],
            ).fetchall()
        ]
        if not cols:
            continue

        col_list = ", ".join(quote_ident(c) for c in cols)
        # Only consider columns non-empty if they are NOT NULL and not ''
        nn_any = " OR ".join(
            f"({quote_ident(c)} IS NOT NULL AND {quote_ident(c)} <> '')" for c in cols
        )
        json_pairs = ", ".join(f"{json_key(c)}, {quote_ident(c)}" for c in cols)

        # Count of non-empty fields
        nn_count_expr = " + ".join(
            f"CASE WHEN {quote_ident(c)} IS NOT NULL AND {quote_ident(c)} <> '' THEN 1 ELSE 0 END"
            for c in cols
        )

        sql = f"""
            SELECT table_name, column_names, row_json
            FROM (
                SELECT
                    '{schema}.{tbl}' AS table_name,
                    '{col_list}'     AS column_names,
                    json_object({json_pairs}) AS row_json,
                    ({nn_count_expr}) AS nn_count
                FROM {quote_ident(schema)}.{quote_ident(tbl)}
                WHERE {nn_any}
            )
            ORDER BY nn_count DESC
            LIMIT {int(limit)}
        """
        try:
            df = con.execute(sql).fetchdf()
            if not df.empty:
                dfs.append(df)
        except Exception:
            continue

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame(columns=["table_name", "column_names", "row_json"])


# the above query is used to generate a CSV in app/data/auxiliary_data/table_examples.csv


def load_table_examples():
    df = pd.read_csv(Path(os.getcwd() + TABLE_EXAMPLES_PATH))
    return df.to_string()
