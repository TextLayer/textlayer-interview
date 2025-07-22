import os

import litellm
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()


class Config:
    # API Mode Configuration
    API_MODE = os.getenv("API_MODE", "LOCAL")  # LOCAL or REMOTE
    TEXTLAYER_API_BASE = os.getenv(
        "TEXTLAYER_API_BASE",
        "https://core.dev.textlayer.ai/v1"
    )
    TEXTLAYER_API_KEY = os.getenv("TEXTLAYER_API_KEY", "")

    # Local Configuration (existing)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/financial_data.db")
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'auto')  # auto, duckdb, postgresql, mysql
    DATABASE_URL = os.getenv('DATABASE_URL', None)  # Full connection string

    # LLM Configuration
    CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-3-5-sonnet-20241022")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # API Keys (for local mode)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST = os.getenv(
        "LANGFUSE_HOST",
        "https://cloud.langfuse.com"
    )

    # Additional configuration
    KNN_EMBEDDING_DIMENSION = int(
        os.getenv("KNN_EMBEDDING_DIMENSION", "1536")
    )
    BEDROCK_GUARDRAILS_ID = os.getenv("BEDROCK_GUARDRAILS_ID", "")

    # Flask Configuration
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-change-in-production"
    )
    DEBUG = ENVIRONMENT == "development"

    # Database & Tools Configuration
    ENABLE_REAL_DB_ACCESS = os.environ.get(
        'ENABLE_REAL_DB_ACCESS', 'false'
    ).lower() == 'true'
    USE_DYNAMIC_SCHEMA = os.environ.get(
        'USE_DYNAMIC_SCHEMA', 'true'
    ).lower() == 'true'

    # Alternative database connection parameters
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'textlayer')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # Configure Langfuse callbacks for LiteLLM
    if all([LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST]):
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
    else:
        litellm.success_callback = ["default"]
        litellm.failure_callback = ["default"]

    # Environment
    ENV_VARS = []  # List of environment variables to pass to the container/batch

    @staticmethod
    def init_app(app):
        pass

    # Set the default environment to development for local testing
    if not os.environ.get('ENVIRONMENT'):
        os.environ['ENVIRONMENT'] = 'development'

    @classmethod
    def is_local_mode(cls):
        """Check if running in local processing mode"""
        return cls.API_MODE.upper() == "LOCAL"

    @classmethod
    def is_remote_mode(cls):
        """Check if using remote TextLayer API"""
        return cls.API_MODE.upper() == "REMOTE"

    @classmethod
    def get_api_config(cls):
        """Get API configuration for current mode"""
        return {
            "mode": cls.API_MODE,
            "base_url": (
                cls.TEXTLAYER_API_BASE if cls.is_remote_mode() else None
            ),
            "api_key": (
                cls.TEXTLAYER_API_KEY if cls.is_remote_mode() else None
            ),
            "local_enabled": cls.is_local_mode()
        }

    @classmethod
    def get_database_connection_string(cls) -> str:
        """
        Get the database connection string based on configuration.

        Returns:
            str: Database connection string
        """
        # If DATABASE_URL is provided, use it directly
        if cls.DATABASE_URL:
            return cls.DATABASE_URL

        # If DATABASE_TYPE is specified, build connection string
        if cls.DATABASE_TYPE.lower() == 'postgresql':
            return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

        elif cls.DATABASE_TYPE.lower() == 'mysql':
            port = cls.DB_PORT if cls.DB_PORT != '5432' else '3306'  # Default MySQL port
            return f"mysql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{port}/{cls.DB_NAME}"

        elif cls.DATABASE_TYPE.lower() == 'duckdb':
            return cls.DATABASE_PATH

        # Default to DATABASE_PATH (auto-detection)
        return cls.DATABASE_PATH

    @classmethod
    def get_database_info(cls) -> dict:
        """
        Get database configuration information.

        Returns:
            dict: Database configuration details
        """
        connection_string = cls.get_database_connection_string()

        return {
            'connection_string': connection_string,
            'database_type': cls.DATABASE_TYPE,
            'database_path': cls.DATABASE_PATH,
            'database_url': cls.DATABASE_URL,
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database_name': cls.DB_NAME,
            'user': cls.DB_USER,
            'auto_detection': cls.DATABASE_TYPE.lower() == 'auto'
        }


class DevelopmentConfig(Config):
    FLASK_CONFIG = 'DEV'
    TESTING = True
    DEBUG = True
    # Enable real DB access in development
    ENABLE_REAL_DB_ACCESS = os.environ.get(
        'ENABLE_REAL_DB_ACCESS', 'true'
    ).lower() == 'true'


class TestingConfig(Config):
    FLASK_CONFIG = 'TEST'
    TESTING = True
    DEBUG = True
    # Disable real DB access in testing
    ENABLE_REAL_DB_ACCESS = False


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