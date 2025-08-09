import pandas as pd
import os
from pathlib import Path
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.readers.base import BasePydanticReader


from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.settings import Settings

# set default text embedding model
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

"""
This file generates a vector store index for a set of few shot examples and stores it locally.
"""


def create_index():
    class CustomParser(BasePydanticReader):
        """Custom CSV parser to read into CSV file - reading from CSVs is not the most efficient,
        can be modified to read other types of files or even database sources"""

        def load_data(self, file: Path, extra_info=None) -> list[Document]:
            df = pd.read_csv(file)
            documents = []
            # itertuples() is faster than iterrows()
            for row in df.itertuples():
                # custom fields
                # key
                user_query = str(row[1])
                # values
                sql_query = str(row[2])
                description = str(row[3])

                # The user_query column will be embedded, and metadata will be retrieved
                doc = Document(
                    text=user_query,
                    metadata={"sql_query": sql_query, "description": description},
                )
                documents.append(doc)
            return documents

    # create simple directory reader
    reader = SimpleDirectoryReader(
        input_dir="./data", file_extractor={".csv": CustomParser()}, recursive=True
    )

    # load docs, create index and then persist index
    docs = reader.load_data()
    index = VectorStoreIndex.from_documents(docs)

    # this persists the index locally. Can use a variety of RDS such as Postgres or even DynamoDB for rows < 400kb
    persist_dir = "./storage"
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir)
    index.storage_context.persist(persist_dir=persist_dir)


# call the function to create the index
create_index()
