from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import pandas as pd


class QdrantVectorDatastore:
    """
    A datastore implementation for Qdrant vector database.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: Optional[str] = "fpa_dev",
        embed_size: Optional[int] = 1536,
    ) -> None:
        """
        Initialize the VectorDatastore.

        Args:
            host (str, optional): Qdrant server host. Defaults to "localhost".
            port (int, optional): Qdrant server port. Defaults to 6333.
            collection_name (str, optional): Name of the collection. Defaults to "default".
            embed_size (int, optional): Size of the embedding vectors. Defaults to 1536.
        """
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.embed_size = embed_size

    def create_collection(self) -> bool:
        """
        Create a new collection in Qdrant if it doesn't already exist.

        Returns:
            bool: True if collection exists or was created successfully.

        Raises:
            Exception: If there's an error during collection creation or existence check.
        """
        try:
            # Only create collection if it doesn't already exist
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embed_size, distance=models.Distance.COSINE
                    ),
                )
            return True

        except Exception as e:
            raise e

    def upsert(self, embeddings: pd.DataFrame, metadata: pd.DataFrame) -> bool:
        """
        Upsert vectors and metadata into a Qdrant collection.

        Args:
            collection_name (str): Name of the collection.
            embeddings (pd.DataFrame): DataFrame containing embedding vectors.
            metadata (pd.DataFrame): DataFrame containing metadata for each vector.

        Returns:
            bool: True if upsert was successful.
        """
        self.client.upsert(
            collection_name=self.collection_name,
            points=models.Batch(
                ids=metadata["id"].tolist(),  # Use actual UUIDs from metadata
                payloads=metadata.to_dict("records"),
                vectors=embeddings.values.tolist(),
            ),
        )
        return True

    def search(
        self, query_vector: List[float], limit: int = 5
    ) -> List[models.ScoredPoint]:
        """
        Search for similar vectors in a Qdrant collection.

        Args:
            collection_name (str): Name of the collection to search.
            query_vector (List[float]): Query vector for similarity search.
            limit (int, optional): Maximum number of results to return. Defaults to 5.

        Returns:
            List[models.ScoredPoint]: List of search results with scores and metadata.
        """
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            score_threshold=0.5,
            limit=limit,
        )
