import os
import litellm

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # LLM
    KNN_EMBEDDING_DIMENSION = int(os.environ.get('KNN_EMBEDDING_DIMENSION', 1536))
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    # Langfuse
    LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY')
    LANGFUSE_HOST = os.environ.get('LANGFUSE_HOST')

    if all([LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST]):
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
    else:
        litellm.success_callback = ["default"]
        litellm.failure_callback = ["default"]
    
    # DuckDB
    DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "app/data/data.db")

    # Retrieval parameters
    TABLE_TOP_K = os.environ.get("TABLE_TOP_K", "4")
    COLUMN_TOP_K = os.environ.get("COLUMN_TOP_K", "4")
    ROW_TOP_K = os.environ.get("ROW_TOP_K", "2")


    # Process Chat Message config
    MAX_TURNS = os.environ.get("MAX_TURNS", "4")
    MAX_TOOL_CALLS_PER_TURN = os.environ.get("MAX_TOOL_CALLS_PER_TURN", "10")

    # Text to SQL Workflow
    MAX_RETRIES = os.environ.get("MAX_RETRIES", "3")
    RETRY_DELAY_SECONDS = os.environ.get("RETRY_DELAY_SECONDS", "1")
    SQL_QUERY_REWRITE_ATTEMPT = os.environ.get("SQL_QUERY_REWRITE_ATTEMPT", "1")

    # Weaviate config
    WV_HTTP_HOST = os.environ.get("WV_HTTP_HOST", "localhost")
    WV_HTTP_PORT = os.environ.get("WV_HTTP_PORT", "8081")
    WV_GRPC_PORT = os.environ.get("WV_GRPC_PORT", "5051")
    WV_SCHEMA_INDEX = os.environ.get("WV_GRPC_PORT", "data_db")

    # SQL dilect
    SQL_DILECT = os.environ.get("SQL_DILECT", "duckdb")


    # Environment
    ENV_VARS = []  # List of environment variables to pass to the container/batch

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    FLASK_CONFIG = 'DEV'
    TESTING = True
    DEBUG = True


class TestingConfig(Config):
    FLASK_CONFIG = 'TEST'
    TESTING = True
    DEBUG = True


class StagingConfig(Config):
    FLASK_CONFIG = 'STAGING'
    TESTING = False
    DEBUG = False


class ProductionConfig(Config):
    FLASK_CONFIG = 'PROD'
    TESTING = False
    DEBUG = False


config = {
    'DEV': DevelopmentConfig,
    'TEST': TestingConfig,
    'STAGING': StagingConfig,
    'PROD': ProductionConfig,
}