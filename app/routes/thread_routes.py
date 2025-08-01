from flask import Blueprint, request
from flask import Response as FlaskResponse, request
import time
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
def chat_stream():
    
    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = validated_request_data.get("messages")
    def event_stream():

        chat_responses = thread_controller.process_chat_message(messages)
        for msg in chat_responses:
            if msg["role"] in ("assistant", "judge", "tool"):
                yield f"data: {msg}\n\n"

    return FlaskResponse(event_stream(), mimetype="text/event-stream")