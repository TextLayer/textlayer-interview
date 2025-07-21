from flask import Blueprint, request
import json

from app.controllers.thread_controller import ThreadController
from app.decorators import handle_exceptions
from app.schemas.thread_schemas import chat_messages_schema
from app.utils.response import Response

thread_routes = Blueprint("thread_routes", __name__)
thread_controller = ThreadController()


@thread_routes.post("/chat")
@handle_exceptions
def chat():
    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = thread_controller.process_chat_message(validated_request_data.get("messages"))
    
    # Format all messages to have required fields
    formatted_payload = []
    
    for msg in messages:
        # Extract content - handle tool responses that have JSON-stringified content
        content = msg.get("content")
        if msg.get("role") == "tool" and content:
            try:
                # Try to parse JSON content from tool responses
                parsed_content = json.loads(content)
                if isinstance(parsed_content, str):
                    content = parsed_content
            except:
                # If parsing fails, use original content
                pass
        
        # Format each message with required fields
        formatted_message = {
            "content": content,
            "finish_reason": msg.get("finish_reason", ""),
            "role": msg.get("role")
        }
        
        formatted_payload.append(formatted_message)
    
    return Response.make(formatted_payload, Response.HTTP_SUCCESS)


@thread_routes.post("/chat/stream")
@handle_exceptions
def chat_stream():
    from flask import Response as FlaskResponse
    import json
    
    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = thread_controller.process_chat_message(validated_request_data.get("messages"))
    
    def generate():
        # Use exactly the same logic as the regular chat endpoint
        formatted_payload = []
        
        for msg in messages:
            # Extract content - handle tool responses that have JSON-stringified content
            content = msg.get("content")
            if msg.get("role") == "tool" and content:
                try:
                    # Try to parse JSON content from tool responses
                    parsed_content = json.loads(content)
                    if isinstance(parsed_content, str):
                        content = parsed_content
                except:
                    # If parsing fails, use original content
                    pass
            
            # Format each message with required fields
            formatted_message = {
                "content": content,
                "finish_reason": msg.get("finish_reason", ""),
                "role": msg.get("role")
            }
            
            formatted_payload.append(formatted_message)
        
        # Extract the final meaningful content for streaming
        assistant_message = None
        
        # Look for the last message with meaningful content
        for msg in reversed(formatted_payload):
            content = msg.get("content")
            if content and content != "null" and str(content).strip():
                assistant_message = str(content)
                break
        
        # Final fallback
        if not assistant_message:
            assistant_message = "No response generated."
        
        # Stream the response word by word
        words = assistant_message.split()
        for i, word in enumerate(words):
            # Send word with space
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        
        # Send final done signal
        yield f"data: [DONE]\n\n"
    
    return FlaskResponse(
        generate(),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )