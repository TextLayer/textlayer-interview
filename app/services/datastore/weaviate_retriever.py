import weaviate
from weaviate.connect import ConnectionParams
from app.errors import ProcessingException
from app import logger

class WeaviateRetriever:
    def __init__(self,
                 weaviate_host: str = "localhost",
                 weaviate_http_port: int = 8081,
                 weaviate_grpc_port: int = 5051,
            ):
        """
        Initialize WeaviateRetriever with connection parameters.
        
        Args:
            weaviate_host (str): Weaviate server hostname.
            weaviate_http_port (int): Weaviate HTTP port.
            weaviate_grpc_port (int): Weaviate gRPC port.
            
        Raises:
            ProcessingException: If connection to Weaviate fails.
        """
        try:
            self.client = weaviate.WeaviateClient(
                connection_params=ConnectionParams.from_params(
                    http_host=weaviate_host,
                    http_port=weaviate_http_port,
                    http_secure=False,
                    grpc_host=weaviate_host,
                    grpc_port=weaviate_grpc_port,
                    grpc_secure=False
                )
            )
            self.client.connect()
            
            if not self.client.is_ready():
                raise ProcessingException("Weaviate client is not ready after connection")
                
            logger.info(f"Successfully connected to Weaviate at {weaviate_host}:{weaviate_http_port}")
        
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate connection: {e}")
            raise ProcessingException(f"Failed to connect to Weaviate at {weaviate_host}:{weaviate_http_port}: {e}")
    
    def query_collection(self, class_name: str, query_vector: list[float], top_k: int):
        """
        Query a Weaviate collection using vector similarity search.

        Args:
            class_name (str): Name of the Weaviate collection to query.
            query_vector (list[float]): Embedding vector for similarity search.
            top_k (int): Number of most similar objects to return.

        Returns:
            list: List of Weaviate objects from the collection, or empty list if collection doesn't exist.

        Raises:
            ProcessingException: If query execution fails.
        """
        try:
            if not self.client.collections.exists(class_name):
                return []   

            collection = self.client.collections.get(class_name)
            results = collection.query.near_vector(query_vector, limit=top_k).objects
            return results
        
        except Exception as e:
            logger.error(f"Error querying Weaviate collection '{class_name}': {e}")
            raise ProcessingException(f"Failed to query Weaviate collection '{class_name}': {e}")
    
    def close(self):
        """Close the Weaviate connection"""
        if hasattr(self, 'client'):
            self.client.close()
