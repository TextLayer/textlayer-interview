from unittest.mock import patch

import pytest

from app.services.llm.client.chat import ChatClient
from app.services.llm.client.embedding import EmbeddingClient
from tests import BaseTest
from tests.utils.assertion import is_equal


class TestChatClient(BaseTest):
    """Test the ChatClient functionality."""

    model_info = {"key": "gpt-4o", "mode": "chat", "context_window": 8192, "max_tokens": 8192}

    def test_chat_client_initialization(self):
        """Test ChatClient initialization with a valid model."""

        with self.app.app_context():
            with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
                client = ChatClient()
                model = client.primary["key"]
                is_equal(model, "gpt-4o")

    def test_llm_session_trim_message_history(self):
        """Test passing messages to the ChatClient."""
        client = ChatClient()

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
        ]

        with patch.object(client, "chat", return_value=messages):
            result = client.chat(messages=messages)
            is_equal(result, messages)

    def test_chat_client_initialization_invalid_model(self):
        """Test error handling for invalid model selection."""
        model_info = {"mode": "embedding"}

        with self.app.app_context():
            with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=model_info):
                with pytest.raises(ValueError):
                    ChatClient()

    def test_chat_completion(self):
        """Test basic chat completion functionality using LiteLLM's mock_response parameter."""
        messages = [{"role": "user", "content": "Hello"}]
        mock_content = "Hi! I'm a mock response from LiteLLM"

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch(
                "app.services.llm.client.ChatClient.chat", side_effect=lambda **kwargs: kwargs.get("mock_response")
            ) as mock_completion:
                client = ChatClient()
                response = client.chat(messages=messages, mock_response=mock_content)

                mock_completion.assert_called_once()
                call_kwargs = mock_completion.call_args.kwargs
                is_equal(call_kwargs.get("mock_response"), mock_content)
                is_equal(response, mock_content)

    def test_chat_completion_with_structured_mock(self):
        """Test chat completion with a structured mock response."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello! How can I help you today?"},
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "created": 1694459929,
            "model": "gpt-4",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch(
                "app.services.llm.client.chat.ChatClient.chat",
                side_effect=lambda **kwargs: kwargs.get("mock_response", mock_response),
            ):
                client = ChatClient()
                response = client.chat(messages=messages, mock_response=mock_response)

                is_equal(response, mock_response)
                is_equal(response["choices"][0]["message"]["content"], "Hello! How can I help you today?")

    def test_message_token_counting(self):
        """Test token counting functionality."""
        messages = [
            {"role": "user", "content": "First message with lots of text " * 10},
            {"role": "assistant", "content": "First response with lots of text " * 10},
        ]

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            client = ChatClient()
            with patch.object(client, "count_tokens", return_value=500):
                token_count = client.count_tokens(messages)
                is_equal(token_count, 500)

    def test_stream_chat_completion(self):
        """Test streaming chat completion with mock_response."""
        messages = [{"role": "user", "content": "Hello"}]
        mock_content = "This is a streaming response"

        def mock_stream():
            for word in mock_content.split():
                yield {"choices": [{"delta": {"content": word + " "}, "finish_reason": None}]}
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch("app.services.llm.client.chat.ChatClient.chat", return_value=mock_stream()):
                client = ChatClient()
                response = client.chat(messages=messages, stream=True)

                chunks = list(response)
                is_equal(len(chunks), len(mock_content.split()) + 1)

                content = ""
                for chunk in chunks[:-1]:
                    content += chunk["choices"][0]["delta"]["content"]

                is_equal(content.strip(), mock_content)


class TestEmbeddingClient(BaseTest):
    """Test the EmbeddingClient functionality."""

    dimension = 1536
    model_info = {
        "key": "text-embedding-3-small",
        "mode": "embedding",
        "context_window": 8192,
        "max_tokens": 8192,
        "output_vector_size": 1536,
    }

    def test_embedding_client_initialization(self):
        """Test EmbeddingClient initialization with a valid model."""

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            client = EmbeddingClient(self.dimension)
            is_equal(client.primary["key"], "text-embedding-3-small")
            is_equal(client.primary["output_vector_size"], 1536)

    def test_embedding_client_initialization_invalid_model(self):
        """Test error handling for invalid model selection."""
        model_info = {
            "key": "invalid-model",
            "mode": "chat",
        }

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=model_info):
            with pytest.raises(ValueError):
                EmbeddingClient(self.dimension)

    def test_embedding_generation_with_mock_response(self):
        """Test embedding generation using LiteLLM's mock_response parameter."""
        text = "Sample text"
        mock_embedding_response = [0.1] * 1536

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch(
                "app.services.llm.client.embedding.EmbeddingClient.embed",
                side_effect=lambda **kwargs: kwargs.get("mock_response", mock_embedding_response),
            ):
                with patch("app.services.llm.client.base.LLMClient.count_tokens", return_value=5):
                    client = EmbeddingClient(self.dimension)
                    embedding = client.embed(text=text, mock_response=mock_embedding_response)
                    is_equal(len(embedding), 1536)
                    is_equal(embedding, mock_embedding_response)

    def test_embedding_batch(self):
        """Test batch embedding functionality."""
        test_texts = ["Sample text 1", "Sample text 2"]
        expected_embedding = [0.1] * 1536

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch.object(EmbeddingClient, "embed", return_value=expected_embedding):
                client = EmbeddingClient(self.dimension)
                embeddings = client.embed_batch(test_texts)
                is_equal(len(embeddings), 2)
                is_equal(embeddings[0], expected_embedding)
                is_equal(embeddings[1], expected_embedding)

    def test_embedding_too_long_text(self):
        """Test handling of text that exceeds token limits."""
        long_text = "Sample text " * 1000
        mock_response = [0.1] * 1536

        with patch("app.services.llm.client.base.LLMClient.get_model_info", return_value=self.model_info):
            with patch("app.services.llm.client.base.LLMClient.count_tokens", side_effect=[10000, 5000, 100]):
                with patch("app.services.llm.client.embedding.EmbeddingClient.embed", return_value=mock_response):
                    client = EmbeddingClient(self.dimension)
                    embedding = client.embed(long_text)
                    is_equal(len(embedding), 1536)
                    is_equal(embedding, mock_response)
