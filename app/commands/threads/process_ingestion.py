import time
from typing import Any, Dict
from uuid import uuid4

import pandas as pd
from flask import current_app
from langfuse.decorators import observe

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.datastore.qdrant_datastore import QdrantVectorDatastore
from app.services.kg.kg import KnowledgeGraph
from app.services.llm.prompts.column_filter_prompt import column_filter_prompt
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs.text_to_sql import DomainFilter
from app.utils.batch_jobs import create_batch


class ProcessIngestionCommand(ReadCommand):
    """
    Process a database ingestion.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
        self.datastore = DuckDBDatastore(self.source)  # SQL database
        self.collection_name = self.source.split("/")[-1].split(".")[0]
        self.qdrant_datastore = QdrantVectorDatastore(
            host=current_app.config.get("QDRANT_HOST"),
            port=current_app.config.get("QDRANT_PORT"),
            collection_name=self.collection_name
        )
        self.kg = KnowledgeGraph(graph_name=self.collection_name)

    def validate(self) -> bool:
        """
        Validate the command.
        """
        if not self.source:
            raise ValidationException("Source is required.")

        return True

    def execute(self) -> Dict[str, Any]:
        """
        Execute the command.
        """
        logger.debug(f"Command {self.__class__.__name__} started with {self.source}.")

        self.validate()

        # Create the collection in the vector database if it doesn't already exist
        self.qdrant_datastore.create_collection()

        # Add the schema node
        schema_id = f"schema:{self.collection_name}"
        self.kg.add_node(schema_id, type="schema", name=self.collection_name)

        # Get the tables from the schema
        tables = self.datastore.get_tables()

        # Collect all schema elements for vectorization
        value_locations = {}  # {value: [location_info, ...]}

        for table in tables["table_name"]:
            logger.info(f"Processing table: {table}")

            table_id = f"table:{table}"
            self.kg.add_node(table_id, type="table", name=table)
            self.kg.add_edge(schema_id, table_id, relation="has_table")

            # Add column descriptions
            columns = self.datastore.get_columns(table_name=table)

            for _, col_row in columns.iterrows():
                col_name = col_row["column_name"]
                data_type = col_row["data_type"]

                # build the column node and the edge to the table node
                col_id = f"column:{table}.{col_name}"
                self.kg.add_node(
                    col_id, type="column", name=col_name, data_type=data_type
                )
                self.kg.add_edge(table_id, col_id, relation="has_column")

                # Early filtering: Skip non-VARCHAR columns immediately
                if data_type.upper() not in ["VARCHAR", "TEXT", "STRING"]:
                    logger.debug(
                        f"Skipping {table}.{col_name} ({data_type}) - not text column"
                    )
                    continue
                
                # Pre-filter obviously bad columns before asking LLM (performance optimization)
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in ["key", "id", "parentid", "guid", "uuid"]):
                    logger.info(f"Skipping {table}.{col_name} - contains system identifier pattern")
                    continue
                
                # Skip clearly technical calculation fields
                technical_patterns = ["method", "formula", "calculation", "conversion", "operator", "format", "entry"]
                if any(pattern in col_lower for pattern in technical_patterns):
                    logger.info(f"Skipping {table}.{col_name} - technical field pattern")
                    continue

                logger.info(f"Processing column: {col_name}")

                # Get sample values for LLM analysis (limited to avoid huge datasets)
                sample_values_query = self.datastore.execute(
                    f"""
                    SELECT DISTINCT "{col_name}" 
                    FROM "{table}" 
                    WHERE "{col_name}" IS NOT NULL 
                    AND LENGTH(TRIM("{col_name}")) > 0
                    LIMIT 15
                """
                )
                sample_values = sample_values_query[col_name].tolist()
                
                # Skip columns with too few distinct values (likely not useful)
                if len(sample_values) < 2:
                    logger.info(f"Skipping {table}.{col_name} - too few distinct values ({len(sample_values)})")
                    continue

                # LLM-as-a-judge for filtering out non-domain values
                self.chat_messages = [
                    {
                        "role": "user",
                        "content": f"""Analyze this database column to determine if it contains business domain terms:

                        TABLE: {table}
                        COLUMN: {col_name}
                        DATA TYPE: {data_type}
                        SAMPLE VALUES: {sample_values}
                        """,
                    }
                ]
                messages = self.prepare_chat_messages()

                try:
                    logger.info(f"Analyzing column {col_name} with LLM...")
                    llm_response = self.llm_session.get_structured_output(
                        messages=messages, structured_output=DomainFilter()
                    )
                    logger.info(
                        f"Column {col_name} has domain values: {llm_response.has_domain_values}"
                    )
                except Exception as e:
                    logger.error(f"LLM analysis failed for {col_name}: {e}")
                    # Default to False if LLM fails - conservative approach
                    llm_response = DomainFilter(has_domain_values=False)

                if llm_response.has_domain_values:
                    try:
                        # Get distinct values from this column (limit to prevent explosion)
                        distinct_values = self.datastore.execute(
                            f"""
                                SELECT DISTINCT "{col_name}" 
                                FROM "{table}" 
                                WHERE "{col_name}" IS NOT NULL 
                                AND LENGTH(TRIM("{col_name}")) > 0
                                LIMIT 200
                        """
                        )
                        
                        # Additional safety check - if too many values, log and skip
                        value_count = len(distinct_values)
                        if value_count > 150:
                            logger.warning(f"Column {table}.{col_name} has {value_count} values - might be too many. Consider if this is really a domain column.")
                        elif value_count > 100:
                            logger.info(f"Column {table}.{col_name} has {value_count} values - this is quite a lot.")

                        for _, value_row in distinct_values.iterrows():
                            value = str(value_row[col_name]).strip()
                            # Track this location for the value
                            location_info = {
                                "table": table,
                                "column": col_name,
                                "data_type": data_type,
                            }

                            if value not in value_locations:
                                value_locations[value] = []
                            value_locations[value].append(location_info)

                    except Exception as e:
                        logger.debug(
                            f"Could not sample values for {table}.{col_name}: {e}"
                        )

        # After collecting value_locations, build unique schema elements
        schema_elements = []

        for value, locations in value_locations.items():
            # Build metadata with ALL locations for this value
            tables = ",".join([loc["table"] for loc in locations])
            columns = ",".join([loc["column"] for loc in locations])
            data_types = ",".join([loc["data_type"] for loc in locations])
            if len(locations) == 1:
                embedding_text = f"value: {value} found in {locations[0]['table']}.{locations[0]['column']}"
            else:
                # Create clean combined description
                location_pairs = [
                    f"{loc['table']}.{loc['column']}" for loc in locations
                ]
                embedding_text = f"value: {value} found in {', '.join(location_pairs)}"

            schema_element = {
                "id": str(uuid4()),
                "value": value,
                "table": tables,
                "column": columns,
                "data_type": data_types,
                "context": embedding_text,
                "location_count": len(locations),
            }

            schema_elements.append(schema_element)

        # Generate embeddings and upsert to Qdrant in batches
        batches = create_batch(schema_elements, 100)
        for i, batch in enumerate(batches, 1):
            logger.info(f"Processing batch {i}/{len(batches)}")
            batch_embeddings = []
            batch_metadata = []
            
            for element in batch:
                embedding = self.llm_session.generate_embedding(element["context"])
                batch_embeddings.append(embedding)
                batch_metadata.append(element)
                time.sleep(0.1)  # Prevent thread exhaustion
            
            # Convert batch to DataFrames and upsert immediately
            batch_embeddings_df = pd.DataFrame(batch_embeddings)
            batch_metadata_df = pd.DataFrame(batch_metadata)
            
            logger.info(f"Upserting batch {i} to Qdrant...")
            self.qdrant_datastore.upsert(batch_embeddings_df, batch_metadata_df)
        self.kg.save(self.kg.graph)
        self.kg.save_diagram()

        # Get detailed stats from KG
        kg_stats = self.kg.get_stats()
        
        return {
            "collection_name": self.collection_name,
            "schema_stats": kg_stats,
            "unique_domain_values_processed": len(schema_elements),
            "message": f"Successfully processed {len(schema_elements)} unique domain values into Qdrant collection '{self.collection_name}'",
        }

    @observe()
    def prepare_chat_messages(self) -> list:
        trimmed_messages = self.llm_session.trim_message_history(
            messages=self.chat_messages,
        )

        system_prompt = column_filter_prompt()

        trimmed_messages = system_prompt + trimmed_messages

        return trimmed_messages
