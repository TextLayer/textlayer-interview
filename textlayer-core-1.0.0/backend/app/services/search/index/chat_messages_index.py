import copy
from typing import Any, Dict

from flask import current_app

from app.services.search.index import BASE_TEMPLATE


def chat_messages_index() -> Dict[str, Any]:
    """
    OpenSearch index for the LLM chat app.
    Field names are snake_case throughout.
    """
    index = copy.deepcopy(BASE_TEMPLATE)
    index["index"] = current_app.config["CHAT_MESSAGE_INDEX"]

    index["body"]["settings"]["similarity"] = {"b05_similarity": {"type": "BM25", "b": 0.5}}

    index["body"]["settings"]["analysis"] = {
        "char_filter": {
            "camel_case_splitter": {
                "type": "pattern_replace",
                "pattern": "([a-z])([A-Z])",
                "replacement": "$1 $2",
            }
        },
        "filter": {
            "english_stop": {"type": "stop", "stopwords": "_english_"},
            "english_stemmer": {"type": "stemmer", "language": "english"},
            "english_possessive_stemmer": {
                "type": "stemmer",
                "language": "possessive_english",
            },
        },
        "analyzer": {
            "custom_analyzer": {
                "char_filter": ["camel_case_splitter"],
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "english_stop",
                    "english_possessive_stemmer",
                    "english_stemmer",
                ],
            }
        },
    }

    props = index["body"]["mappings"]["properties"]
    props.update(
        {
            "thread_id": {"type": "keyword"},
            "message_id": {"type": "keyword"},
            "role": {"type": "keyword"},
            "content": {
                "type": "text",
                "similarity": "b05_similarity",
                "fields": {
                    "analyzed": {"type": "text", "analyzer": "custom_analyzer"},
                    "keyword": {"type": "keyword"},
                },
            },
            "created_at": {"type": "date", "format": "strict_date_time"},
            "updated_at": {"type": "date", "format": "strict_date_time"},
            "embedding": {
                "type": "knn_vector",
                "dimension": current_app.config["KNN_EMBEDDING_DIMENSION"],
                "method": {
                    "name": "hnsw",
                    "engine": "nmslib",
                    "space_type": "cosinesimil",
                },
            },
            "parts": {
                "type": "nested",
                "properties": {
                    "type": {"type": "keyword"},
                    "text": {
                        "type": "text",
                        "similarity": "b05_similarity",
                        "analyzer": "custom_analyzer",
                    },
                },
            },
            "tool_invocations": {"type": "object", "enabled": False},
        }
    )

    index["body"]["settings"]["index"] = {
        "knn": True,
    }

    return index
