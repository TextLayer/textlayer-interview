from flask import Blueprint, request, Response as FlaskResponse

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
    return Response.make(messages, Response.HTTP_SUCCESS)


@thread_routes.post("/chat/stream")
@handle_exceptions
def chat_stream():
    validated_request_data = chat_messages_schema.load(request.get_json())
    
    def generate_stream():
        """Generator function for streaming response."""
        import json
        
        try:
            # Process the chat message with all enhancements
            messages = thread_controller.process_chat_message_stream(validated_request_data.get("messages"))
            
            # Stream each message as Server-Sent Events
            for message in messages:
                if message.get('role') == 'assistant' and message.get('content'):
                    # Stream the assistant response in chunks
                    content = message.get('content', '')
                    words = content.split(' ')
                    
                    for i, word in enumerate(words):
                        chunk_data = {
                            "content": word + (' ' if i < len(words) - 1 else ''),
                            "role": "assistant",
                            "finish_reason": "continue" if i < len(words) - 1 else "stop"
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        
                elif message.get('role') == 'tool':
                    # Stream tool results
                    tool_data = {
                        "content": message.get('content', ''),
                        "role": "tool",
                        "tool_call_id": message.get('tool_call_id'),
                        "finish_reason": "tool_calls"
                    }
                    yield f"data: {json.dumps(tool_data)}\n\n"
            
            # Send final completion signal
            final_data = {"finish_reason": "stop"}
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            # Stream error message
            import json
            error_data = {
                "content": f"Error: {str(e)}",
                "role": "assistant", 
                "finish_reason": "error"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return FlaskResponse(
        generate_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )