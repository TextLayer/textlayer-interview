from typing import Any

from flask import current_app
from openai import OpenAI


class PerplexityClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=current_app.config["PERPLEXITY_API_KEY"],
            base_url="https://api.perplexity.ai",
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search Perplexity for information based on a query.

        Args:
            query: The search query to send to Perplexity. Use a natural language query such as "What is the weather in
                   Tokyo?" or "Who won the presidential election in the United States?"
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an artificial intelligence assistant and you need to "
                    "engage in a helpful, detailed, polite conversation with a user."
                ),
            },
            {
                "role": "user",
                "content": (query),
            },
        ]

        return self.client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
        )
