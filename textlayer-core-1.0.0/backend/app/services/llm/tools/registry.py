"""
Tool Registry - Central registry for all agent tools
"""

from app.services.llm.tools.db import text_to_sql
from app.services.llm.tools.perplexity import perplexity_research
from app.services.llm.tools.prompting import think

TOOL_REGISTRY = [
    perplexity_research,
    think,
    text_to_sql,
]
