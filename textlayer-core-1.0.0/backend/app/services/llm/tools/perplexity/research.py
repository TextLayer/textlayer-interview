from langfuse.decorators import observe
from vaul import tool_call

from app.services.llm.perplexity import PerplexityClient


@tool_call
@observe
def perplexity_research(query: str) -> str:
    """
    Search Perplexity for information based on a query.
    Args:
        query: The search query to send to Perplexity. Use a natural language query such as
               "What is the weather in Tokyo?" or "Who won the presidential election in the United States?"
    """
    perplexity_client = PerplexityClient()
    search_results = perplexity_client.search(query)

    return {
        "response": search_results.choices[0].message.content,
        "citations": [
            {
                "index": idx,
                "url": citation,
            }
            for idx, citation in enumerate(search_results.citations)
        ],
    }
