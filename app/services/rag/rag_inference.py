from llama_index.core import StorageContext, load_index_from_storage
from pathlib import Path
import os

# load local index globally and create retriever, this cuts down on latency and memory use
# earlier versions of llamaindex had thread safety issues with global retrievers but hopefully this is resolved now
# in production it is crucial to use retrievers that have a database connector and/or spawn a separate microservice
# to offload the RAG retrieval handling

# this local path hack is not ideal, like I mentioned, should be replaced with a database connected source
storage_context = StorageContext.from_defaults(
    persist_dir=Path(os.getcwd() + "/app/services/rag/storage")
)
loaded_index = load_index_from_storage(storage_context=storage_context)
retriever = loaded_index.as_retriever(similarity_top_k=5)


def rag_index_retrieve(query_str: str):
    """
    Queries vector index retriever for response
    """

    retrieved_nodes = retriever.retrieve(query_str)
    # extract "key" and "values" from result nodes
    retrieved_nodes_metadata = [(x.text, x.metadata) for x in retrieved_nodes]
    return retrieved_nodes_metadata
