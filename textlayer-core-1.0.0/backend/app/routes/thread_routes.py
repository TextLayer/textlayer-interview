from flask import Blueprint, request

from app.controllers.thread_controller import ThreadController
from app.decorators import handle_exceptions
from app.schemas.thread_schemas import chat_messages_schema
from app.utils.response import Response
from app.utils.streaming import convert_to_openai_messages

thread_routes = Blueprint("thread_routes", __name__)
thread_controller = ThreadController()


@thread_routes.post("/chat")
@handle_exceptions
def chat():
    validated_request_body = chat_messages_schema.load(request.get_json())

    response = thread_controller.process_chat_message(
        messages=convert_to_openai_messages(validated_request_body["messages"]),
        stream=False,
        model=validated_request_body["model"],
    )

    return Response.make(response, Response.HTTP_SUCCESS)


@thread_routes.post("/chat/stream")
@handle_exceptions
def chat_stream():
    validated_request_body = chat_messages_schema.load(request.get_json())

    response = thread_controller.process_chat_message(
        messages=validated_request_body["messages"],
        stream=True,
        model=validated_request_body["model"],
    )

    return Response.stream(response)
