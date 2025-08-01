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
    def generate():
        validated_data = chat_messages_schema.load(request.get_json())
        for token in thread_controller.stream_chat_message(validated_data["messages"]):
            yield f"data: {token}\n\n"

    return FlaskResponse(generate(), content_type="text/event-stream")