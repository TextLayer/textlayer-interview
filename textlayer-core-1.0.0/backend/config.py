import json
import os
from typing import Any

import litellm

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # List of environment variables used in the application for aws batch
    ENV_VARS = []

    # Track which variables were set through get_env to add to ENV_VARS
    _env_vars_set = set()

    @staticmethod
    def get_env(key: str, default: Any = None, required: bool = False, type: Any = str):
        value = os.environ.get(key, default)
        if required and value is None:
            raise ValueError(f"Environment variable {key} is required")

        if isinstance(type, list):
            value = json.loads(value)
        elif isinstance(type, int):
            value = int(value)
        elif isinstance(type, bool):
            value = value.lower() == "true"
        elif isinstance(type, float):
            value = float(value)
        elif isinstance(type, dict):
            value = json.loads(value)
        elif isinstance(type, tuple):
            value = tuple(json.loads(value))

        # Track that this variable was set through get_env
        Config._env_vars_set.add(key)

        return type(value)

    @staticmethod
    def init_app(app):
        """Initialize Flask application with configuration.

        Args:
            app: Flask application instance
        """
        # Add any Flask-specific initialization here
        app.config["PREFERRED_URL_SCHEME"] = "https"

    @classmethod
    def _init_aws_config(cls):
        cls.AWS_ACCESS_KEY_ID = cls.get_env("AWS_ACCESS_KEY_ID", required=True)
        cls.AWS_SECRET_ACCESS_KEY = cls.get_env("AWS_SECRET_ACCESS_KEY", required=True)
        cls.AWS_REGION = cls.get_env("AWS_REGION", required=True)

    @classmethod
    def _init_opensearch_config(cls):
        # Connection
        cls.OPENSEARCH_HOST = cls.get_env("OPENSEARCH_HOST")
        cls.OPENSEARCH_USER = cls.get_env("OPENSEARCH_USER")
        cls.OPENSEARCH_PASSWORD = cls.get_env("OPENSEARCH_PASSWORD")
        cls.OPENSEARCH_PORT = cls.get_env("OPENSEARCH_PORT", default=443, type=int)

        # Settings
        cls.OPENSEARCH_SHARDS = cls.get_env("OPENSEARCH_SHARDS", default=1, type=int)
        cls.OPENSEARCH_REPLICAS = cls.get_env("OPENSEARCH_REPLICAS", default=0, type=int)

        ## Index names
        cls.SOURCES_INDEX = cls.get_env("SOURCES_INDEX", default="sources-2024-08")
        cls.CHAT_MESSAGE_INDEX = cls.get_env("CHAT_MESSAGE_INDEX", default="textlayer-core-chat-messages-2025-05-06")

        # Other
        cls.KNN_EMBEDDING_DIMENSION = cls.get_env("KNN_EMBEDDING_DIMENSION", default=1536, type=int)

    @classmethod
    def _init_langfuse_config(cls):
        cls.LANGFUSE_PUBLIC_KEY = cls.get_env("LANGFUSE_PUBLIC_KEY")
        cls.LANGFUSE_SECRET_KEY = cls.get_env("LANGFUSE_SECRET_KEY")
        cls.LANGFUSE_HOST = cls.get_env("LANGFUSE_HOST")

        # Convert TEST_DATASETS from string to list
        cls.TEST_DATASETS = cls.get_env("TEST_DATASETS", default=[], type=list)

    @classmethod
    def _init_llm_config(cls):
        cls.CHAT_MODEL = cls.get_env("CHAT_MODEL", default="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
        cls.EMBEDDING_MODEL = cls.get_env("EMBEDDING_MODEL", default="amazon.titan-embed-text-v2:0")
        cls.OPENAI_API_KEY = cls.get_env("OPENAI_API_KEY", required=True)
        cls.PERPLEXITY_API_KEY = cls.get_env("PERPLEXITY_API_KEY", required=True)
        cls.ANTHROPIC_API_KEY = cls.get_env("ANTHROPIC_API_KEY")
        cls.BEDROCK_GUARDRAILS_ID = cls.get_env("BEDROCK_GUARDRAILS_ID")

    @classmethod
    def _configure_litellm_callbacks(cls):
        if all([cls.LANGFUSE_PUBLIC_KEY, cls.LANGFUSE_SECRET_KEY, cls.LANGFUSE_HOST]):
            litellm.success_callback = ["langfuse"]
            litellm.failure_callback = ["langfuse"]

            from langfuse.decorators import langfuse_context

            langfuse_context.configure(environment=cls.get_env("FLASK_CONFIG", default="DEV").lower())
        else:
            litellm.success_callback = ["default"]
            litellm.failure_callback = ["default"]

    @classmethod
    def _configure_eval_provider(cls):
        if cls.LANGFUSE_PUBLIC_KEY and cls.LANGFUSE_SECRET_KEY and cls.LANGFUSE_HOST:
            cls.EVAL_PROVIDER = "langfuse"
        else:
            cls.EVAL_PROVIDER = "default"

    @classmethod
    def _configure_prompt_provider(cls):
        if cls.LANGFUSE_PUBLIC_KEY and cls.LANGFUSE_SECRET_KEY and cls.LANGFUSE_HOST:
            cls.PROMPT_PROVIDER = "langfuse"
        else:
            cls.PROMPT_PROVIDER = "default"

    @classmethod
    def init(cls):
        # Initialize all configs
        cls._init_aws_config()
        cls._init_opensearch_config()
        cls._init_langfuse_config()
        cls._init_llm_config()
        cls._configure_litellm_callbacks()
        cls._configure_eval_provider()
        cls._configure_prompt_provider()
        # Add only the environment variables that were set through get_env
        cls.ENV_VARS = sorted(list(cls._env_vars_set))


class DevelopmentConfig(Config):
    FLASK_CONFIG = "DEV"
    TESTING = True
    DEBUG = True


class TestingConfig(Config):
    FLASK_CONFIG = "TEST"
    TESTING = True
    DEBUG = True


class StagingConfig(Config):
    FLASK_CONFIG = "STAGING"
    TESTING = False
    DEBUG = False


class ProductionConfig(Config):
    FLASK_CONFIG = "PROD"
    TESTING = False
    DEBUG = False


config = {
    "DEV": DevelopmentConfig,
    "TEST": TestingConfig,
    "STAGING": StagingConfig,
    "PROD": ProductionConfig,
}

# Initialize the config
Config.init()
