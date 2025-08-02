import json
from typing import Dict, List


def convert_to_openai_messages(messages: List[Dict]) -> List[Dict]:
    """
    Convert client messages to OpenAI-compatible format.
    """

    openai_messages = []

    for message in messages:
        role = message.get("role")
        parts = message.get("parts", [])
        content = ""

        # handle content if parts are missing
        if parts:
            valid_parts = [part for part in parts if part.get("type") == "text" and part.get("text")]
            content = "\n".join(p["text"] for p in valid_parts) if valid_parts else ""
        elif message.get("content"):
            content = message["content"]

        tool_calls = []

        # Process tool calls if present
        if "toolInvocations" in message:
            for invocation in message["toolInvocations"]:
                args = invocation.get("args", {})
                if isinstance(args, dict):
                    args = json.dumps(args)

                tool_calls.append(
                    {
                        "id": invocation["toolCallId"],
                        "type": "function",
                        "function": {
                            "name": invocation["toolName"],
                            "arguments": args,
                        },
                    }
                )

        openai_message = {
            "role": role,
            "content": content if role in ("user", "assistant", "system") else None,
        }

        if tool_calls:
            openai_message["tool_calls"] = tool_calls

        openai_messages.append(openai_message)

        # Add tool results as separate "tool" messages
        if "toolInvocations" in message:
            for invocation in message["toolInvocations"]:
                if invocation.get("result") is not None:
                    result = invocation["result"]
                    if not isinstance(result, str):
                        result = json.dumps(result)

                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": invocation["toolCallId"],
                            "content": result,
                        }
                    )

    return openai_messages
