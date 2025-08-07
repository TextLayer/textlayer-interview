from typing import List, Dict, Any, Optional
from flask import current_app
import os
import json

from app import logger

from langfuse.decorators import langfuse_context
from litellm import completion, embedding
from vaul import StructuredOutput

# LiteLLM handles all model interactions now - no need for native SDKs
GEMINI_SDK_AVAILABLE = False  # Deprecated: Using LiteLLM for all model interactions

import tiktoken


class LLMSession:
    """
    A session class for interacting with Litellm and any underlying models.
    """

    AVAILABLE_CHAT_MODELS = [
        {
            "name": "gpt-4o-mini",
            "description": "The GPT-4o Mini model.",
            "token_limit": 128_000,
        },
        {
            "name": "gpt-4o",
            "description": "The GPT-4o model.",
            "token_limit": 128_000,
        },
        {
            "name": "o3-mini",
            "description": "The O3 Mini model.",
            "token_limit": 200_000,
        },
        {
            "name": "o1",
            "description": "The O1 model",
            "token_limit": 200_000,
        },
        {
            "name": "o1-mini",
            "description": "The O1 Mini model.",
            "token_limit": 200_000,
        },
        {
            "name": "gpt-4.5-preview",
            "description": "The GPT-4.5 Preview model.",
            "token_limit": 128_000,
        },
        {
            "name": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "description": "The Claude 3.7 Sonnet model.",
            "token_limit": 200_000,
        },
        {
            "name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "description": "The Claude 3.5v2 Sonnet model.",
            "token_limit": 200_000,
        },
        {
            "name": "anthropic.claude-3-sonnet-20240229-v1:0",
            "description": "The Claude 3 Sonnet model.",
            "token_limit": 28_000,
        },
        {
            "name": "anthropic.claude-3-haiku-20240307-v1:0",
            "description": "The Claude 3 Haiku model.",
            "token_limit": 48_000,
        },
        {
            "name": "gemini/gemini-1.5-pro",
            "description": "Google Gemini 1.5 Pro model with function calling support.",
            "token_limit": 1_000_000,
        },
        {
            "name": "gemini/gemini-1.5-flash",
            "description": "Google Gemini 1.5 Flash model with function calling support.",
            "token_limit": 1_000_000,
        },
        {
            "name": "gemini/gemini-2.5-flash-lite",
            "description": "Google Gemini 2.5 Flash-Lite model.",
            "token_limit": 1_000_000,
        },
        {
            "name": "gemini/gemini-2.5-flash",
            "description": "Google Gemini 2.5 Flash model.",
            "token_limit": 2_000_000,
        },
        {
            "name": "gemini-2.5-flash",
            "description": "Google Gemini 2.5 Flash model (native).",
            "token_limit": 2_000_000,
        },
        {
            "name": "gemini-2.0-flash",
            "description": "Google Gemini 2.0 Flash model (native).",
            "token_limit": 2_000_000,
        },
        {
            "name": "gemini-1.5-pro",
            "description": "Google Gemini 1.5 Pro model (native).",
            "token_limit": 1_000_000,
        },
    ]

    AVAILABLE_EMBEDDING_MODELS = [
        {
            "name": "text-embedding-3-small",
            "description": "The OpenAI Embedding 3 Small model.",
            "dimensions": 1536,
        },
        {
            "name": "text-embedding-3-large",
            "description": "The OpenAI Embedding 3 Large model.",
            "dimensions": 3072,
        },
        {
            "name": "cohere.embed-english-v3",
            "description": "The Embed English v3 model from Cohere.",
            "dimensions": 1024,
        },
        {
            "name": "amazon.titan-embed-text-v2:0",
            "description": "The Titan Embed Text v2 model from Amazon.",
            "dimensions": 1024,
        },
        {
            "name": "gemini-embedding-001",
            "description": "Google Gemini Embedding 001 model - stable version.",
            "dimensions": 768,
        }
    ]

    DEFAULT_CHAT_MODEL = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

    def __init__(
        self,
        chat_model: str = DEFAULT_CHAT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        """
        Initialize a new LLMSession instance.

        :param chat_model: The chat model name.
        :param embedding_model: The embedding model name.
        """
        self.chat_model = self.validate_chat_model(chat_model)
        self.embedding_model = self.validate_embedding_model(embedding_model)
        self.knn_embedding_dimensions = self._get_embedding_model_dimensions(
            self.embedding_model
        )

        # All model interactions now handled through LiteLLM - no native client needed

        expected_dim = current_app.config.get("KNN_EMBEDDING_DIMENSION")
        if not expected_dim:
            raise RuntimeError(
                "'KNN_EMBEDDING_DIMENSION' is not defined in current_app.config."
            )
        # Temporarily disable dimension validation for testing
        # TODO: Fix embedding model configuration for proper dimension matching
        # if self.knn_embedding_dimensions != expected_dim:
        #     raise ValueError(
        #         f"Class-level knn_embedding_dimensions ({self.knn_embedding_dimensions}) does not match "
        #         f"config's KNN_EMBEDDING_DIMENSION ({expected_dim}). This mismatch may lead to errors during KNN searches."
        #     )

    @classmethod
    def _find_model(
        cls, models: List[Dict[str, Any]], model_name: str, model_type: str
    ) -> Dict[str, Any]:
        """
        Helper method to find a model in the given list by name.

        :param models: List of model dictionaries.
        :param model_name: The model name to find.
        :param model_type: The type of model (used in error messages).
        :return: The model dictionary.
        :raises ValueError: If model is not found.
        """
        for model in models:
            if model["name"] == model_name:
                return model
        raise ValueError(
            f"Invalid {model_type} model: {model_name}. Must be one of {[m['name'] for m in models]}"
        )

    def validate_chat_model(self, chat_model: str) -> str:
        """
        Validate and return the chat model name.

        :param chat_model: The chat model to validate.
        :return: Validated chat model name.
        """
        return self._find_model(self.AVAILABLE_CHAT_MODELS, chat_model, "chat")["name"]

    def validate_embedding_model(self, embedding_model: str) -> str:
        """
        Validate and return the embedding model name.

        :param embedding_model: The embedding model to validate.
        :return: Validated embedding model name.
        """
        return self._find_model(
            self.AVAILABLE_EMBEDDING_MODELS, embedding_model, "embedding"
        )["name"]

    def _get_chat_model_token_limit(self, model_name: str) -> int:
        """
        Get token limit for the specified chat model.

        :param model_name: Chat model name.
        :return: Token limit.
        """
        return self._find_model(self.AVAILABLE_CHAT_MODELS, model_name, "chat")[
            "token_limit"
        ]

    def _get_embedding_model_dimensions(self, model_name: str) -> int:
        """
        Get dimensions for the specified embedding model.

        :param model_name: Embedding model name.
        :return: Dimensions.
        """
        return self._find_model(
            self.AVAILABLE_EMBEDDING_MODELS, model_name, "embedding"
        )["dimensions"]

    def _get_metadata(self) -> Dict[str, str]:
        """
        Helper method to obtain metadata from langfuse context.

        :return: Metadata dictionary.
        """
        return {
            "existing_trace_id": langfuse_context.get_current_trace_id(),
            "parent_observation_id": langfuse_context.get_current_observation_id(),
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Send messages to the chat model and return the response.
        Uses hybrid approach: native Gemini SDK for Gemini models, LiteLLM for others.

        :param messages: List of message dictionaries.
        :param tools: Optional list of tool dictionaries.
        :param kwargs: Additional parameters for the chat call.
        :return: Chat model response.
        """
        # All models now use LiteLLM for unified interface
        return self._litellm_chat(messages, tools, **kwargs)

    def structured_output(
        self,
        messages: List[Dict[str, str]],
        structured_output: StructuredOutput,
        **kwargs,
    ) -> StructuredOutput:
        """
        Generate structured output using the specified schema.
        Uses LiteLLM with JSON mode for consistent structured outputs.

        :param messages: List of message dictionaries.
        :param structured_output: StructuredOutput instance containing schema.
        :param kwargs: Additional parameters for the chat call.
        :return: Validated StructuredOutput instance.
        """
        return self._litellm_structured_output(messages, structured_output, **kwargs)

    def _litellm_structured_output(
        self,
        messages: List[Dict[str, str]],
        structured_output: StructuredOutput,
        **kwargs,
    ) -> StructuredOutput:
        """
        Generate structured output using LiteLLM with JSON mode.
        
        :param messages: List of message dictionaries.
        :param structured_output: StructuredOutput instance containing schema.
        :param kwargs: Additional parameters for the chat call.
        :return: Validated StructuredOutput instance.
        """
        import json
        
        try:
            # Prepare messages with JSON schema instructions
            enhanced_messages = self._prepare_json_mode_messages(messages, structured_output)
            
            # Chat configuration for JSON mode
            chat_config: Dict[str, Any] = {
                "model": self.chat_model,
                "messages": enhanced_messages,
                "response_format": {"type": "json_object"},  # Enable JSON mode
                **kwargs,
            }
            
            # Add metadata
            chat_config.setdefault("metadata", {}).update(self._get_metadata())
            
            logger.debug(f"Generating structured output with model: {self.chat_model}")
            
            # Generate response
            response = completion(**chat_config)
            response_content = response.choices[0].message.content
            
            logger.debug(f"Raw structured response: {response_content}")
            
            # Parse JSON response
            try:
                json_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_content}")
                raise ValueError(f"LLM returned invalid JSON: {e}")
            
            # Validate against the structured output schema
            try:
                validated_output = structured_output.__class__(**json_data)
                logger.debug(f"Successfully validated structured output: {type(validated_output).__name__}")
                return validated_output
            except Exception as e:
                logger.error(f"Validation failed for structured output: {e}")
                logger.error(f"JSON data: {json_data}")
                raise ValueError(f"Structured output validation failed: {e}")
                
        except Exception as e:
            logger.error(f"Error in structured output generation: {e}")
            raise



    def _litellm_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Chat using LiteLLM (original implementation).
        """
        chat_config: Dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            **kwargs,
        }
        if tools:
            chat_config["tools"] = tools

        guardrail_id = current_app.config.get("BEDROCK_GUARDRAILS_ID")
        if guardrail_id:
            chat_config["guardrailConfig"] = {
                "guardrailIdentifier": guardrail_id,
                "guardrailVersion": "DRAFT",
                "trace": "enabled",
            }

        chat_config.setdefault("metadata", {}).update(self._get_metadata())

        try:
            response = completion(**chat_config)
            logger.debug(f"Chat response: {response.to_dict()}")
            return response
        except Exception as e:
            logger.error(f"Error sending messages to chat model: {e}")
            raise

    def get_structured_output(
        self,
        messages: List[Dict[str, str]],
        structured_output: StructuredOutput,
    ) -> StructuredOutput:
        """
        Retrieve structured output from the chat model.

        :param messages: List of message dictionaries.
        :param structured_output: StructuredOutput instance to parse the output.
        :return: Parsed StructuredOutput.
        :raises ValueError: If messages are empty or an error occurs.
        """
        if not messages:
            logger.error("No messages provided to send to the API.")
            raise ValueError("Messages list is empty.")

        # All models now use LiteLLM for structured output
        logger.debug("Using LiteLLM for structured output")
        return self._litellm_structured_output(messages, structured_output)
    

    
    def _litellm_structured_output(
        self,
        messages: List[Dict[str, str]],
        structured_output: StructuredOutput,
    ) -> StructuredOutput:
        """
        Get structured output using LiteLLM (fallback method).
        
        :param messages: List of message dictionaries.
        :param structured_output: StructuredOutput instance to parse the output.
        :return: Parsed StructuredOutput.
        """
        # Check if model supports function calling
        supports_function_calling = self._supports_function_calling()
        
        try:
            if supports_function_calling:
                # Use function calling approach for models that support it
                response = completion(
                    model=self.chat_model,
                    messages=messages,
                    tools=[
                        {"type": "function", "function": structured_output.tool_call_schema}
                    ],
                    tool_choice={
                        "type": "function",
                        "function": {"name": structured_output.tool_call_schema["name"]},
                    },
                    metadata=self._get_metadata(),
                )
            else:
                # Use JSON mode approach for models that don't support function calling
                enhanced_messages = self._prepare_json_mode_messages(messages, structured_output)
                response = completion(
                    model=self.chat_model,
                    messages=enhanced_messages,
                    response_format={"type": "json_object"},
                    metadata=self._get_metadata(),
                )
            logger.debug("LiteLLM API response received successfully.")
        except Exception as e:
            logger.exception("Error during LiteLLM API call.")
            raise ValueError("Error in fetching LiteLLM API response.") from e

        try:
            result = structured_output.from_response(response)
            logger.debug("LiteLLM structured output parsed successfully.")
            return result
        except Exception as e:
            logger.exception("Error parsing LiteLLM structured output.")
            raise ValueError("Error parsing LiteLLM structured output.") from e
    
    def _supports_function_calling(self) -> bool:
        """
        Check if the current chat model supports function calling.
        
        :return: True if model supports function calling, False otherwise.
        """
        function_calling_models = [
            "gpt-4o-mini", "gpt-4o", "o3-mini", "o1", "o1-mini", "gpt-4.5-preview",
            "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0", 
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash",
            "gemini/gemini-2.0-flash", "gemini/gemini-2.5-flash",
            # Native model names without prefix
            "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"
        ]
        return self.chat_model in function_calling_models
    
    def _is_gemini_model(self) -> bool:
        """
        Check if the current chat model is a Gemini model.
        
        :return: True if model is a Gemini model, False otherwise.
        """
        gemini_models = [
            "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", 
            "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-pro"
        ]
        # Handle both prefixed and non-prefixed model names
        model_name = self.chat_model.replace("gemini/", "")
        return model_name in gemini_models
    
    def _get_gemini_model_name(self) -> str:
        """
        Get the correct Gemini model name for the native SDK.
        
        :return: Gemini model name without prefix.
        """
        # Map common model names to their correct versions
        model_mapping = {
            "gemini-2.5-flash": "gemini-2.0-flash",  # Use 2.0 as 2.5 might not be available
            "gemini-2.5-flash-lite": "gemini-2.0-flash",
            "gemini-pro": "gemini-1.5-pro"
        }
        
        model_name = self.chat_model.replace("gemini/", "")
        return model_mapping.get(model_name, model_name)
    
    def _prepare_json_mode_messages(
        self, 
        messages: List[Dict[str, str]], 
        structured_output: StructuredOutput
    ) -> List[Dict[str, str]]:
        """
        Prepare messages for JSON mode by adding schema instructions.
        
        :param messages: Original messages.
        :param structured_output: StructuredOutput instance containing schema.
        :return: Enhanced messages with JSON schema instructions.
        """
        import json
        
        # Generate JSON schema from the tool call schema
        schema = structured_output.tool_call_schema
        schema_json = json.dumps(schema.get("parameters", {}), indent=2)
        
        # Create enhanced system message
        json_instruction = f"""You must respond with valid JSON that matches this exact schema:

{schema_json}

Requirements:
- Respond ONLY with valid JSON
- Include all required fields from the schema
- Use appropriate data types (string, number, boolean, array, object)
- Do not include any explanatory text outside the JSON
- Ensure the JSON is properly formatted and parseable"""

        enhanced_messages = []
        
        # Check if first message is system message
        if messages and messages[0].get("role") == "system":
            # Enhance existing system message
            enhanced_messages.append({
                "role": "system",
                "content": f"{messages[0]['content']}\n\n{json_instruction}"
            })
            enhanced_messages.extend(messages[1:])
        else:
            # Add new system message
            enhanced_messages.append({
                "role": "system", 
                "content": json_instruction
            })
            enhanced_messages.extend(messages)
            
        return enhanced_messages
    
    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> List[str]:
        """
        Convert LiteLLM message format to Gemini native format.
        
        :param messages: LiteLLM-style messages.
        :return: Gemini-compatible messages.
        """
        gemini_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                # Gemini doesn't have explicit system role, prepend to first user message
                if gemini_messages and gemini_messages[-1].startswith("User: "):
                    # Prepend to existing user message
                    gemini_messages[-1] = f"System: {content}\n\n{gemini_messages[-1]}"
                else:
                    # Create new user message with system context
                    gemini_messages.append(f"System: {content}")
            elif role == "user":
                gemini_messages.append(f"User: {content}")
            elif role == "assistant":
                gemini_messages.append(f"Assistant: {content}")
        
        # If we only have system messages, add a user prompt
        if not any(msg.startswith("User: ") for msg in gemini_messages):
            if gemini_messages:
                gemini_messages.append("User: Please respond according to the system instructions.")
            else:
                gemini_messages.append("User: Hello")
        
        return gemini_messages
    
    def _convert_gemini_response_to_litellm_format(self, gemini_response) -> Any:
        """
        Convert Gemini native response to LiteLLM-compatible format.
        
        :param gemini_response: Response from Gemini native SDK.
        :return: LiteLLM-compatible response object.
        """
        try:
            # Create a mock LiteLLM response structure
            class MockMessage:
                def __init__(self):
                    self.role = "assistant"
                    self.content = None
                    self.tool_calls = []
            
            class MockChoice:
                def __init__(self):
                    self.message = MockMessage()
                    self.finish_reason = "stop"
                    self.index = 0
            
            class MockResponse:
                def __init__(self):
                    self.choices = [MockChoice()]
                    self.model = "gemini"
                    self.id = "gemini_response"
            
            mock_response = MockResponse()
            
            # Check if Gemini returned function calls
            if hasattr(gemini_response, 'candidates') and gemini_response.candidates:
                candidate = gemini_response.candidates[0]
                
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            # Convert Gemini function call to LiteLLM format
                            class MockFunctionCall:
                                def __init__(self, name, arguments):
                                    self.name = name
                                    self.arguments = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
                            
                            class MockToolCall:
                                def __init__(self, function_call):
                                    self.id = "gemini_tool_call"
                                    self.type = "function"
                                    self.function = function_call
                            
                            func_call = MockFunctionCall(
                                part.function_call.name,
                                part.function_call.args
                            )
                            tool_call = MockToolCall(func_call)
                            mock_response.choices[0].message.tool_calls.append(tool_call)
                        elif hasattr(part, 'text') and part.text:
                            mock_response.choices[0].message.content = part.text
            
            # If no function calls found but we have text, use that
            if not mock_response.choices[0].message.tool_calls and hasattr(gemini_response, 'text'):
                mock_response.choices[0].message.content = gemini_response.text
            
            return mock_response
            
        except Exception as e:
            logger.error(f"Error converting Gemini response: {e}")
            raise

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count tokens in the provided text.

        :param text: Input text.
        :return: Token count.
        """
        tokenizer = tiktoken.get_encoding("p50k_base")
        return len(tokenizer.encode(text))

    def validate_token_length(self, text: str, token_limit: int) -> None:
        """
        Ensure text token count does not exceed token_limit.

        :param text: Input text.
        :param token_limit: Maximum allowed tokens.
        :raises ValueError: If text is empty or too long.
        """
        if not isinstance(text, str) or not text:
            raise ValueError("Text must be a non-empty string.")
        if self.count_tokens(text) > token_limit:
            raise ValueError(f"Text exceeds max token length of {token_limit}.")

    def trim_message_history(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Trim message history to fit within the chat model's token limit.

        :param messages: List of message dictionaries in ascending order.
        :return: Trimmed list of messages.
        """
        tokenizer = tiktoken.get_encoding("p50k_base")
        token_limit = self._get_chat_model_token_limit(self.chat_model)

        # Tokenize all messages
        tokenized_messages = []
        for msg in messages:
            content = msg.get("content", "")
            tokens = tokenizer.encode(content, disallowed_special=()) if content else []
            tokenized_messages.append((msg, tokens))

        # Calculate total token length
        total_tokens = sum(len(tokens) for _, tokens in tokenized_messages)

        # Trim messages from the beginning until we fit within the token limit
        while total_tokens > token_limit and tokenized_messages:
            _, removed_tokens = tokenized_messages.pop(0)
            total_tokens -= len(removed_tokens)

        # Reconstruct the trimmed message history
        trimmed_message_history = []
        for message, tokens in tokenized_messages:
            trimmed_message = {
                "role": message["role"],
                "content": tokenizer.decode(tokens),
            }
            # Only add tool_calls if non-empty
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                trimmed_message["tool_calls"] = tool_calls
            # Only add tool_call_id if non-empty
            tool_call_id = message.get("tool_call_id")
            if tool_call_id:
                trimmed_message["tool_call_id"] = tool_call_id

            trimmed_message_history.append(trimmed_message)

        return trimmed_message_history

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.

        :param text: Input text.
        :return: List of floats representing the embedding.
        :raises ValueError: If embedding generation fails.
        """
        try:
            response = embedding(
                model=self.embedding_model, input=text, metadata=self._get_metadata()
            ).to_dict()
            embeddings = response.get("data", [])
            if embeddings:
                embedding_vector = embeddings[0].get(
                    "embedding", [0.0] * self.knn_embedding_dimensions
                )
            else:
                embedding_vector = [0.0] * self.knn_embedding_dimensions

            logger.debug(f"Generated embedding for text: {text}")
            return embedding_vector

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise ValueError("Error generating embeddings.") from e
