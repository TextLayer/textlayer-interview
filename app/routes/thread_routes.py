from flask import Blueprint, request

from app.controllers.thread_controller import ThreadController
from app.decorators import handle_exceptions
from app.schemas.thread_schemas import chat_messages_schema
from app.utils.response import Response
from flask import Response as FlaskResponse, stream_with_context  

thread_routes = Blueprint("thread_routes", __name__)
thread_controller = ThreadController()


@thread_routes.post("/chat")
@handle_exceptions
def chat():
    """
    Synchronous chat endpoint for full-response LLM chat.
    """
    request_data = chat_messages_schema.load(request.get_json())
    messages = request_data.get("messages")

    output = thread_controller.process_chat_message(messages)
    return Response.make(output, Response.HTTP_SUCCESS)

@thread_routes.post("/chat/stream")
@handle_exceptions
def chat_stream():
    """
    Streams response chunks from the LLM to the frontend.
    """
    request_data = chat_messages_schema.load(request.get_json())
    messages = request_data.get("messages")

    def generate():
        for chunk in thread_controller.stream_chat_message(messages):  
            yield f"data: {chunk}\n\n"  

    return FlaskResponse(stream_with_context(generate()), mimetype="text/event-stream") 