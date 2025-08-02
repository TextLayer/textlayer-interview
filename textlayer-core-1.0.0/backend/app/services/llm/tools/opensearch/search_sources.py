from flask import current_app
from langfuse.decorators import observe
from opensearch_dsl import Search
from vaul import tool_call

from app.services.llm.client import EmbeddingClient
from app.services.search import opensearch_session
from app.utils.models import EMBEDDING_MODELS
from app.utils.pagination import format_results


@tool_call
@observe
def search_sources(query: str, page: int = 1, per_page: int = 10) -> str:
    """
    ### Search sources using semantic and keyword search.
    Args:
        query (str): Search query string.
        page (int, optional): Page number. Defaults to 1.
        per_page (int, optional): Number of results per page. Defaults to 10.
    Returns:
        str: Formatted results.
    """
    llm_embedding_session = EmbeddingClient(models=EMBEDDING_MODELS, dimension=1536)

    query_embedding = llm_embedding_session.embed(query)

    search = Search(
        using=opensearch_session(),
        index=current_app.config["SOURCES_INDEX"],
    )

    # Specify which fields to return
    search = search.source(["id", "title", "summary"])

    knn_query = {
        "bool": {
            "must": [
                {"knn": {"embeddings": {"vector": query_embedding, "k": 50}}},  # You can tune k
            ],
            "should": [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "summary.keyword^2", "summary.text^1"],
                        "type": "cross_fields",
                    }
                }
            ],
        }
    }

    search = search.extra(query=knn_query)

    # Apply pagination
    search = search[(page - 1) * per_page : page * per_page]

    response = search.execute()
    return format_results(response.to_dict(), page, per_page)
