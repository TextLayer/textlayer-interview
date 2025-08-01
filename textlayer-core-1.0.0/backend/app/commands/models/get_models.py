from app import logger
from app.core.commands import ReadCommand
from app.services.llm.client import LLMClient
from app.utils.models import CHAT_MODELS, EMBEDDING_MODELS


class GetModelsCommand(ReadCommand):
    """Command to retrieve available chat and embedding models with metadata."""

    def execute(self):
        """Fetches chat and embedding models with metadata from litellm."""
        logger.debug(f"Command: {self.__class__.__name__} \n")

        models = CHAT_MODELS + EMBEDDING_MODELS

        chat_models = []
        embedding_models = []

        client = LLMClient()

        for model in models:
            try:
                model_info = client.get_model_info(model)
            except Exception as e:
                logger.warning(f"Could not get model info for {model}: {e}")
                continue

            if model_info and model_info["mode"] == "chat":
                chat_models.append({"id": model, "name": model_info["key"], "metadata": model_info})
            elif model_info and model_info["mode"] == "embedding":
                embedding_models.append({"id": model, "name": model_info["key"], "metadata": model_info})

        return {
            "chat_models": chat_models,
            "embedding_models": embedding_models,
        }
