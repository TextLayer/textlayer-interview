import json
from typing import Dict, Any, List


class LLMPromptBuilder:
    @staticmethod
    def schema_analysis_prompt(
        user_query: str,
        schema: Dict[str, List[str]],
        summaries: Dict[str, Any] = None
    ) -> List[Dict[str, str]]:
        schema_str = "\n".join([f"{table}: {', '.join(fields)}" for table, fields in schema.items()])

        # Add summaries if available
        summary_str = ""
        if summaries:
            summary_lines = []
            for table, summary in summaries.items():
                column_descriptions = [
                    f"{col['name']} ({col.get('description', 'unknown')}): sample values - {', '.join(map(str, col.get('sample_values', [])[:3]))}"
                    for col in summary.get("columns", [])
                ]
                summary_lines.append(f"{table}:\n  " + "\n  ".join(column_descriptions))
            summary_str = "\n\n# Table Summaries:\n" + "\n".join(summary_lines)

        prompt = f"""
    You are a data analyst assistant. Based on a user query and the database schema, your task is to:
    1. Identify the most relevant table(s)
    2. Identify the most relevant fields from those tables
    3. Output only a JSON response in the following format:

    {{
    "inScope": true/false,
    "tables": ["relevant_table1", "relevant_table2"],
    "fields": {{
        "relevant_table1": ["field1", "field2"],
        ...
    }}
    }}

    # Schema:
    {schema_str}
    {summary_str}

    # User Query:
    {user_query}

    Only return the JSON response, no explanation.
    """.strip()

        return [
            {
                "role": "system",
                "content": (
                    "You are an expert SQL assistant. "
                    "IMPORTANT: You MUST only use table and field names exactly as provided below. "
                    "NEVER guess, pluralize, or modify table names. "
                    "For example, if schema contains 'customer', DO NOT use 'customers'. "
                    "Queries with incorrect table names will fail."
                )
            },
            # Few-shot example
            {
                "role": "user",
                "content": """
# Schema:
orders: OrderID, CustomerID, Amount

# User Query:
How much money did each customer spend?

Only return the JSON response, no explanation.
"""
            },
            {
                "role": "assistant",
                "content": """{
  "inScope": true,
  "tables": ["orders"],
  "fields": {
    "orders": ["CustomerID", "Amount"]
  }
}"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

    @staticmethod
    def format_answer_prompt(user_query: str, sql_query: str, results: List[dict]) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """You are a helpful SQL assistant.
Given a user question, a SQL query used, and the query results, explain the answer briefly and clearly.

Respond in JSON:
{
  "answer": "string"
}
"""
            },
            # Few-shot example
            {
                "role": "user",
                "content": """Question: How much did each customer spend?
SQL Query: SELECT CustomerID, SUM(Amount) FROM orders GROUP BY CustomerID
Query Results: [{"CustomerID": "C001", "SUM(Amount)": 120.50}]"""
            },
            {
                "role": "assistant",
                "content": """{
  "answer": "Customer C001 spent a total of 120.50."
}"""
            },
            {
                "role": "user",
                "content": f"""Question: {user_query}
SQL Query: {sql_query}
Query Results: {json.dumps(results)}"""
            }
        ]

    @staticmethod
    def validate_answer_prompt(question: str, answer: str) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """You are a final validator of an AI-generated answer. Determine whether the answer reasonably answers the user's question.

Respond in JSON:
{
  "isAnswered": boolean,
  "reason": "string" // Only required if isAnswered is false
}
"""
            },
            # Few-shot example
            {
                "role": "user",
                "content": """Question: What is the average order amount?
Answer: The total orders were 1000."""
            },
            {
                "role": "assistant",
                "content": """{
  "isAnswered": false,
  "reason": "The answer does not provide the average order amount."
}"""
            },
            {
                "role": "user",
                "content": f"Question: {question}\nAnswer: {answer}"
            }
        ]

    @staticmethod
    def triage_prompt(user_query: str) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """You are a query classifier that categorizes user queries into two types:

1. "DATA_QUESTION": Questions that ask about specific data in our database tables (e.g., filters, aggregations, comparisons).
2. "OUT_OF_SCOPE": Any other questions, including greetings, general assistant inquiries, clarifications, jokes, personal opinions, or unrelated topics.

Respond ONLY in this exact JSON format:
{ "queryType": "DATA_QUESTION" | "OUT_OF_SCOPE" }
"""
            },
            # Few-shot examples
            {
                "role": "user",
                "content": "Classify this question: What are the top selling products?"
            },
            {
                "role": "assistant",
                "content": '{ "queryType": "DATA_QUESTION" }'
            },
            {
                "role": "user",
                "content": "Classify this question: What's your favorite movie?"
            },
            {
                "role": "assistant",
                "content": '{ "queryType": "OUT_OF_SCOPE" }'
            },
            {
                "role": "user",
                "content": f"Classify this question: {user_query}"
            }
        ]

    @staticmethod
    def sql_or_nl_prompt(user_message: str) -> list:
        return [
            {
                "role": "system",
                "content": (
                    "You are an expert assistant that classifies user input into one of two categories:\n\n"
                    "1. `SQL` – If the input is written directly in SQL syntax (e.g., starts with SELECT, INSERT, etc.).\n"
                    "2. `NL` – If the input is a natural language question or command (e.g., 'Show me 5 users who joined last week').\n\n"
                    "**Only classify as SQL if it is clearly written in valid SQL syntax. Do not assume or generate SQL.**\n"
                    "Respond strictly with this JSON format:\n"
                    "{ \"queryType\": \"SQL\" } or { \"queryType\": \"NL\" }\n\n"
                    "Examples:\n"
                    "Input: SELECT * FROM users;\nOutput: { \"queryType\": \"SQL\" }\n\n"
                    "Input: Show all users in the system.\nOutput: { \"queryType\": \"NL\" }\n\n"
                    "Input: DELETE FROM orders WHERE status = 'cancelled';\nOutput: { \"queryType\": \"SQL\" }\n\n"
                    "Input: What is the total number of products?\nOutput: { \"queryType\": \"NL\" }\n\n"
                    "Now classify the following input."
                )
            },
            {
                "role": "user",
                "content": f"{user_message}"
            }
        ]

    @staticmethod
    def generate_sql_prompt(schema_analysis: dict, user_query: str) -> List[Dict[str, str]]:
            return [
                {
                    "role": "system",
                    "content": """You are a DuckDB SQL query generator. Follow these rules:
    1. Use only tables and fields listed in the schema analysis.
    2. If a join is required, use the relationships array.
    3. Use "ILIKE" for case-insensitive pattern matches and "=" for exact matches.
    4. Use LIMIT 1000 if no limit is given.
    5. Avoid referencing any columns not explicitly listed.
    6. If the USER QUESTION itself appears to be a SQL statement (detected via keywords such as SELECT, WITH, INSERT, UPDATE, DELETE, EXPLAIN, etc.), treat it as direct SQL input. (An empty `schema_analysis` can be an additional hint but is NOT the primary criterion.)
        a. Validate the SQL syntax against DuckDB rules.    
        b. If the query is valid, return it unchanged.
        c. If the query contains errors (e.g., missing LIMIT, invalid identifiers, syntax mistakes), FIX the SQL so it runs successfully on DuckDB while preserving the user's intent.
        d. Always enforce rule #4 (add LIMIT 1000) if the query lacks a LIMIT clause.
    7. Preserve the exact casing and spelling of table or column names found in the schema (wrap them in double quotes only if they contain spaces or special characters).
    8. The final response MUST be valid, parsable JSON with exactly two keys: "query" and "explanation" — no markdown fences or extra text.

    Respond ONLY in JSON:
    {
    "query": "SELECT ...",
    "explanation": "This query does ..."
    }
    """
                },
                # Few-shot example
                {
                    "role": "user",
                    "content": """Schema Analysis:
    {
    "inScope": true,
    "tables": ["orders"],
    "fields": {
        "orders": ["CustomerID", "Amount"]
    }
    }

    User Question:
    How much did each customer spend?"""
                },
                {
                    "role": "assistant",
                    "content": """{
    "query": "SELECT CustomerID, SUM(Amount) AS total_spent FROM orders GROUP BY CustomerID LIMIT 1000",
    "explanation": "This query calculates the total amount spent by each customer."
    }"""
                },
                # Added few-shot example: direct SQL input with empty schema analysis
                {
                    "role": "user",
                    "content": """Schema Analysis:
    {}

    User Question:
    SELECT * FROM orders LIMIT 10"""
                },
                {
                    "role": "assistant",
                    "content": """{
    "query": "SELECT * FROM orders LIMIT 10",
    "explanation": "This query retrieves all columns from the orders table and limits the results to 10 rows."
    }"""
                },
                # Few-shot example: invalid SQL input that needs fixing
                {
                    "role": "user",
                    "content": """Schema Analysis:
    {}

    User Question:
    SELECT customerid, SUM(amount) FROM orders GROUP BY customerid"""
                },
                {
                    "role": "assistant",
                    "content": """{
    "query": "SELECT CustomerID, SUM(Amount) AS total_spent FROM orders GROUP BY CustomerID LIMIT 1000",
    "explanation": "Fixed identifier casing to match schema, added alias, and applied default LIMIT."
    }"""
                },
                {
                    "role": "user",
                    "content": f"""Schema Analysis:
    {json.dumps(schema_analysis, indent=2)}

    User Question:
    {user_query}"""
                }
            ]