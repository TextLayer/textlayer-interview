import os
import re
import sys
import json

from openai import OpenAI
from app.services.llm.tools.llm_prompt_builder import LLMPromptBuilder

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from config import Config


def generate_sql_from_prompt(user_query, schema_info):
    print("[DEBUG] Called generate_sql_from_prompt with query:", user_query)
    print("[DEBUG] Schema info received:\n", json.dumps(schema_info, indent=2))

    try:
        messages = LLMPromptBuilder.generate_sql_prompt(schema_info, user_query)
        response = client.chat.completions.create(
            model=Config.CHAT_MODEL,
            messages=messages
        )

        message_content = response.choices[0].message.content.strip()
        print("[DEBUG] Raw LLM output:\n", message_content)

        # Remove markdown-style ```json or ``` blocks
        if message_content.startswith("```"):
            message_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", message_content.strip(), flags=re.MULTILINE)

        parsed = json.loads(message_content)

        return {
            "query": parsed.get("query", ""),
            "explanation": parsed.get("explanation", "No explanation returned.")
        }

    except Exception as e:
        print("[ERROR] Failed to parse/query:", e)
        return {
            "query": "",
            "explanation": f"Failed to generate query: {e}"
        }
