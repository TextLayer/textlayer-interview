import json
from typing import Any, Dict, Generator, Iterable, List, Optional, Union
from uuid import uuid4

from flask import current_app
from litellm import Router
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from vaul import StructuredOutput, Toolkit

from app import logger
from app.services.llm.client.base import LLMClient


class ChatClient(LLMClient):
    """
    Simplified client for chat completions via LiteLLM with unified batch,
    streaming, and tool-call execution using the Vercel AI SDK data-stream protocol.
    """

    def __init__(
        self,
        models: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        names = models or [current_app.config["CHAT_MODEL"]]
        validated = self.validate_models(names, model_type="chat")
        self.primary = validated[0]
        router_conf = self._build_router_config(validated)
        self.router = Router(**router_conf)

    def chat(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        tools: Optional[Toolkit] = None,
        **kwargs: Any,
    ) -> Union[List[Dict[str, Any]], Generator[str, None, None]]:
        params = self._build_params(messages, stream, tools, **kwargs)
        native = self._send_request(params)
        if stream:
            return self.stream(native, tools, history=messages.copy())
        return self.batch(native, tools)

    def batch(
        self,
        response: ChatCompletion,
        tools: Toolkit,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        choice = response.choices[0]
        tool_messages = []
        # Add the assistant message to the results
        assistant_message = {
            "role": "assistant",
            "content": choice.message.content,
            "finish_reason": choice.finish_reason,
        }

        # Handle tool calls
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_calls_data = []
            for tc in choice.message.tool_calls:
                tool_calls_data.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

            # Add the tool calls to the assistant message
            assistant_message["tool_calls"] = tool_calls_data

        # Run the tool calls
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                    logger.info(f"Running tool: {tc.function.name}")
                    out = tools.run_tool(tc.function.name, args)
                except Exception as e:
                    out = {
                        "error": str(e),
                        "tool": tc.function.name,
                        "arguments": tc.function.arguments,
                    }

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(out),
                }
                tool_messages.append(tool_message)

        # Add the assistant message to the results
        results.append(assistant_message)

        # Add the tool messages to the results
        results.extend(tool_messages)

        return results

    def stream(
        self,
        chunks: Iterable[ChatCompletionChunk],
        tools: Toolkit,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        """
        Stream responses and handle tool calls according to the Vercel AI SDK data-stream protocol.
        """
        history = history or []
        message_id = uuid4().hex
        yield f'f:{{"messageId":"{message_id}"}}\n'

        draft_calls: List[Dict[str, Any]] = []
        draft_index = -1
        prompt_tokens = completion_tokens = 0

        # first pass – build up tool calls
        for chunk in chunks:
            if hasattr(chunk, "usage"):
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens

            for choice in chunk.choices:
                delta = getattr(choice, "delta", None)

                # build up tool-calls
                if delta and getattr(delta, "tool_calls", None):
                    for tc in delta.tool_calls:
                        if tc.id is not None:  # new call
                            draft_index += 1
                            draft_calls.append({"id": tc.id, "name": tc.function.name or "", "arguments": ""})
                            yield f'b:{{"toolCallId":"{tc.id}","toolName":"{tc.function.name or ""}"}}\n'
                        else:  # argument chunk
                            call = draft_calls[draft_index]
                            if tc.function.arguments:
                                call["arguments"] += tc.function.arguments
                                yield (
                                    f'c:{{"toolCallId":"{call["id"]}",'
                                    f'"argsTextDelta":{json.dumps(tc.function.arguments)}}}\n'
                                )

                # normal text delta
                if delta and getattr(delta, "content", None):
                    yield f"0:{json.dumps(delta.content)}\n"

                # anthropic reasoning delta (optional)
                if delta and getattr(delta, "system_reasoning", None):
                    yield f"g:{json.dumps(delta.system_reasoning)}\n"

                # stop handled after loop

        # if we have tool calls, we need to run them
        if draft_calls:
            tool_messages: List[Dict[str, Any]] = []

            for call in draft_calls:
                # run tool
                try:
                    result = tools.run_tool(call["name"], json.loads(call["arguments"]))
                except Exception as e:
                    result = {"error": str(e)}

                yield f'a:{{"toolCallId":"{call["id"]}","result":{json.dumps(result)}}}\n'

                # collect <tool> message for second pass
                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result),
                    }
                )

            # partial close, signal continuation
            yield (
                f'e:{{"finishReason":"tool-calls","isContinued":true,'
                f'"usage":{{"promptTokens":{prompt_tokens},'
                f'"completionTokens":{completion_tokens}}}}}\n'
            )

            # build prompt for second pass
            next_messages = history + [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]},
                        }
                        for c in draft_calls
                    ],
                    "content": None,
                },
                *tool_messages,
            ]

            # second completion (recursive stream)
            next_chunks = self._send_request(self._build_params(next_messages, True, tools))
            yield from self.stream(next_chunks, tools, next_messages)
            return  # prevent normal close below

        yield (
            f'd:{{"finishReason":"stop","usage":{{"promptTokens":{prompt_tokens},'
            f'"completionTokens":{completion_tokens}}}}}\n'
        )

    def get_structured_output(
        self,
        messages: List[Dict[str, Any]],
        structured_output: StructuredOutput,
    ) -> Any:
        if not messages:
            raise ValueError("Messages list cannot be empty")
        schema = structured_output.tool_call_schema
        params = self._build_params(
            messages,
            False,
            tools=[{"type": "function", "function": schema}],
            tool_choice={"type": "function", "function": {"name": schema["name"]}},
        )
        resp = self._send_request(params)
        try:
            return structured_output.from_response(resp)
        except Exception as e:
            logger.exception("Structured output failed: %s", e)
            raise ValueError(f"Structured output error: {e}") from e

    def _build_params(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        tools: Optional[Toolkit] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model": self.primary["key"],
            "messages": messages,
            "stream": stream,
        }
        if tools and tools.has_tools():
            params["tools"] = tools.tool_schemas()
        params.update(extra)
        return params

    def _send_request(self, params: Dict[str, Any]) -> Any:
        try:
            return self.router.completion(
                metadata=self._get_metadata(),
                **params,
            )
        except Exception as e:
            logger.error("Chat completion failed: %s", e, exc_info=True)
            raise
