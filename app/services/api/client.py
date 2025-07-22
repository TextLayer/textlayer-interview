import json
from typing import Any, Dict, Generator, List

import requests
from flask import current_app

from app import logger
from app.commands.threads.llm_judge import LLMJudgeCommand
from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from app.commands.threads.process_chat_message_stream import (
    ProcessChatMessageStreamCommand,
)
from app.core.executor import Executor
from app.errors import ValidationException


class TextLayerAPIClient:
    """
    Unified API client that can handle both local and remote API calls
    """

    def __init__(self):
        self._config = None
        self._executor = None

    @property
    def config(self):
        """Lazy-load configuration to avoid application context issues"""
        if self._config is None:
            from config import Config
            self._config = Config.get_api_config()
        return self._config

    @property
    def executor(self):
        """Lazy-load executor to avoid application context issues"""
        if self._executor is None and self.config['local_enabled']:
            self._executor = Executor.getInstance()
        return self._executor

    def is_local_mode(self) -> bool:
        """Check if running in local mode"""
        return self.config['mode'].upper() == 'LOCAL'

    def is_remote_mode(self) -> bool:
        """Check if using remote API"""
        return self.config['mode'].upper() == 'REMOTE'

    def process_chat_message(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Process chat message using either local or remote processing
        """
        if self.is_local_mode():
            return self._process_chat_local(messages)
        else:
            return self._process_chat_remote(messages)

    def process_chat_message_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Process chat message with streaming using local or remote processing
        """
        if self.is_local_mode():
            return self._process_chat_stream_local(messages)
        else:
            return self._process_chat_stream_remote(messages)

    def _process_chat_local(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Process chat using local LLM and database with judge evaluation
        """
        try:
            logger.info("Processing chat message locally")

            # Execute main chat command
            response = self.executor.execute_write(
                ProcessChatMessageCommand(messages)
            )

            # Apply LLM-as-a-Judge evaluation
            if response and len(response) > 0:
                judge_command = LLMJudgeCommand(messages, response)
                return self.executor.execute_read(judge_command)

            return response

        except Exception as e:
            logger.error(f"Local chat processing failed: {e}")
            raise ValidationException(f"Local processing error: {str(e)}")

    def _process_chat_remote(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Process chat using remote TextLayer API
        """
        try:
            logger.info("Processing chat message via remote API")

            url = f"{self.config['base_url']}/threads/chat"
            headers = {
                'Content-Type': 'application/json'
            }

            if self.config['api_key']:
                headers['Authorization'] = f"Bearer {self.config['api_key']}"

            payload = {"messages": messages}

            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            data = response.json()
            logger.info("Remote API call successful")

            # Transform remote response to match local format
            return self._transform_remote_response(data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Remote API call failed: {e}")
            if self._should_fallback_to_local():
                logger.info("Falling back to local processing")
                return self._process_chat_local(messages)
            else:
                raise ValidationException(f"Remote API error: {str(e)}")
        except Exception as e:
            logger.error(f"Remote chat processing failed: {e}")
            raise ValidationException(f"Remote processing error: {str(e)}")

    def _process_chat_stream_local(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Process streaming chat using local processing
        """
        try:
            logger.info("Processing streaming chat message locally")
            command = ProcessChatMessageStreamCommand(messages)
            return command.execute_stream()
        except Exception as e:
            logger.error(f"Local streaming failed: {e}")
            # Yield error message in expected format
            error_data = {
                "type": "error",
                "message": {
                    "content": f"Local streaming error: {str(e)}",
                    "role": "assistant"
                }
            }
            yield json.dumps(error_data)

    def _process_chat_stream_remote(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Process streaming chat using remote TextLayer API
        """
        try:
            logger.info("Processing streaming chat message via remote API")

            url = f"{self.config['base_url']}/threads/chat/stream"
            headers = {
                'Content-Type': 'application/json'
            }

            if self.config['api_key']:
                headers['Authorization'] = f"Bearer {self.config['api_key']}"

            payload = {"messages": messages}

            response = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)
            response.raise_for_status()

            logger.info("Remote streaming API call initiated")

            # Stream the response
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    if data_str.strip():
                        # Transform remote response to match local format if needed
                        yield data_str

        except requests.exceptions.RequestException as e:
            logger.error(f"Remote streaming API call failed: {e}")
            if self._should_fallback_to_local():
                logger.info("Falling back to local streaming")
                yield from self._process_chat_stream_local(messages)
            else:
                error_data = {
                    "type": "error",
                    "message": {
                        "content": f"Remote streaming error: {str(e)}",
                        "role": "assistant"
                    }
                }
                yield json.dumps(error_data)
        except Exception as e:
            logger.error(f"Remote streaming failed: {e}")
            error_data = {
                "type": "error",
                "message": {
                    "content": f"Remote streaming error: {str(e)}",
                    "role": "assistant"
                }
            }
            yield json.dumps(error_data)

    def _transform_remote_response(self, remote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform remote API response to match local response format
        """
        # If remote response already matches our expected format, return as-is
        if 'payload' in remote_data and isinstance(remote_data['payload'], list):
            return remote_data['payload']

        # If remote response has different structure, adapt it
        if 'messages' in remote_data:
            return remote_data['messages']

        # Default transformation for unknown response format
        return [remote_data] if isinstance(remote_data, dict) else remote_data

    def _should_fallback_to_local(self) -> bool:
        """
        Determine if we should fallback to local processing on remote failure
        """
        # Only fallback if local processing is available and enabled
        return (self.executor is not None and
                current_app.config.get('ENABLE_LOCAL_FALLBACK', True))

    def get_api_status(self) -> Dict[str, Any]:
        """
        Get current API configuration and status
        """
        status = {
            "mode": self.config['mode'],
            "local_available": self.executor is not None,
            "remote_configured": bool(self.config['base_url'])
        }

        if self.is_remote_mode():
            status.update({
                "remote_base_url": self.config['base_url'],
                "has_api_key": bool(self.config['api_key'])
            })

        return status