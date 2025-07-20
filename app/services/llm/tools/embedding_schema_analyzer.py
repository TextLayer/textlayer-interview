import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any
from openai import OpenAI
from langfuse.decorators import observe

Base_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),"../../../.."))

class EmbeddingSchemaAnalyzer:
    """
    An analyzer that identifies relevant database tables and fields for a user query
    using embedding similarity.

    This tool uses precomputed vector embeddings of table names and field names to
    match them with the embedding of the user query. It also enriches output with
    field descriptions if available.

    Attributes:
        table_embeddings (dict): Table name to embedding vector mapping.
        field_embeddings (dict): Field (table.column) to embedding vector mapping.
        field_descriptions (dict): Descriptions of fields loaded from summary JSON files.
        top_k (int): Number of top matches to return.
    """

    def __init__(
        self,
        table_emb_path: str = os.path.join(Base_DIR,"models", "table_embeddings.pkl"),
        field_emb_path: str = os.path.join(Base_DIR,"models", "field_embeddings.pkl"),
        top_k: int = 3,
    ):
        """
        Initializes the analyzer with embedding files and optional descriptions.

        Args:
            table_emb_path: Path to the pickle file containing table embeddings.
            field_emb_path: Path to the pickle file containing field embeddings.
            top_k: Number of top results to consider for tables and fields.
        """
        table_path = os.path.abspath(table_emb_path)
        field_path = os.path.abspath(field_emb_path)

        with open(table_path, "rb") as f:
            self.table_embeddings = pickle.load(f)
        with open(field_path, "rb") as f:
            self.field_embeddings = pickle.load(f)

        self.top_k = top_k
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.field_descriptions = {}
        summary_dir = os.path.abspath("summary")
        if os.path.exists(summary_dir):
            for fname in os.listdir(summary_dir):
                if fname.endswith(".json"):
                    with open(os.path.join(summary_dir, fname)) as f:
                        summary = json.load(f)
                        table = summary["table_name"]
                        for col in summary.get("columns", []):
                            field_name = f"{table}.{col['name']}"
                            self.field_descriptions[field_name] = col.get("description", "")

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generates an embedding vector for a given text using OpenAI.

        Args:
            text: Input text string.

        Returns:
            A list of floats representing the embedding vector.
        """
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=[text]
        )
        return response.data[0].embedding

    def _cosine_similarity(self, v1, v2):
        """
        Computes cosine similarity between two vectors.

        Args:
            v1: First vector (array-like).
            v2: Second vector (array-like).

        Returns:
            Cosine similarity value as a float.
        """
        v1 = np.array(v1)
        v2 = np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    @observe()
    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Runs the analyzer to identify relevant tables and fields for a query.

        Args:
            user_query: Natural language user question or instruction.

        Returns:
            A dictionary containing:
                - inScope (bool): Whether relevant tables/fields were found.
                - tables (List[str]): List of matching table names.
                - fields (Dict[str, List[str]]): Fields grouped by table.
                - table_scores (List[Tuple[str, float]]): Top matched tables and scores.
                - field_scores (List[Dict]): Top matched fields with score and description.
        """
        query_embedding = self._get_embedding(user_query)

        # Rank tables
        table_scores = [
            (key, self._cosine_similarity(query_embedding, emb))
            for key, emb in self.table_embeddings.items()
        ]
        table_scores.sort(key=lambda x: x[1], reverse=True)
        top_tables = table_scores[:self.top_k]

        # Rank fields
        field_scores = [
            (key, self._cosine_similarity(query_embedding, emb))
            for key, emb in self.field_embeddings.items()
        ]
        field_scores.sort(key=lambda x: x[1], reverse=True)
        top_fields = field_scores[:self.top_k]

        # Build table/field match sets
        tables = set(t[0] for t in top_tables)
        fields: Dict[str, List[str]] = {}
        for field_key, _ in top_fields:
            if "." in field_key:
                table, field = field_key.split(".")
                tables.add(table)
                fields.setdefault(table, []).append(field)

        return {
            "inScope": len(tables) > 0,
            "tables": list(tables),
            "fields": fields,
            "table_scores": top_tables,
            "field_scores": [
                {
                    "field": key,
                    "score": score,
                    "description": self.field_descriptions.get(key, "")
                }
                for key, score in top_fields
            ],
        }
