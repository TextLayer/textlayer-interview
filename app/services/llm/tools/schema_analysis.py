import os
import json
from typing import Dict, Any

from openai import OpenAI
from app.services.llm.tools.llm_prompt_builder import LLMPromptBuilder

Base_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),"../../../.."))

from config import Config

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class SchemaAnalyzerTool:
    def __init__(self,
                 schema_path: str = os.path.join(Base_DIR,"models", "full_schema.json"),
                 summary_dir: str = os.path.join(Base_DIR, "summary"),
    ):
        # Load full schema
        with open(schema_path, "r") as f:
            self.schema = json.load(f)

        # Load summaries
        self.summaries = {}
        summary_path = os.path.abspath(summary_dir)
        if os.path.exists(summary_path):
            for filename in os.listdir(summary_path):
                if filename.endswith(".json"):
                    table_name = filename.replace(".json", "")
                    with open(os.path.join(summary_path, filename), "r") as sf:
                        self.summaries[table_name] = json.load(sf)

    def run(self, user_query: str) -> Dict[str, Any]:
        messages = LLMPromptBuilder.schema_analysis_prompt(
            user_query=user_query,
            schema=self.schema,
            summaries=self.summaries
        )

        try:
            response = client.chat.completions.create(
                model=Config.CHAT_MODEL,
                messages=messages,
                temperature=0.2,
            )
            result_text = response.choices[0].message.content.strip()

            if result_text.startswith("```") and result_text.endswith("```"):
                result_text = result_text.split("```")[1].strip()
                if result_text.startswith("json"):
                    result_text = result_text[len("json"):].strip()

            return json.loads(result_text)


        except json.JSONDecodeError as jde:
            print("[ERROR] GPT response was not valid JSON.")
            print("Raw response:\n", result_text)
            return {
                "inScope": False,
                "tables": [],
                "fields": {},
                "error": "Invalid JSON from GPT"
            }

        except Exception as e:
            print("Error during schema analysis:", e)
            return {
                "inScope": False,
                "tables": [],
                "fields": {},
                "error": str(e)
            }

