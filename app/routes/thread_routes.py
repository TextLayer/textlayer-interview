from flask import Blueprint, request

from app.controllers.thread_controller import ThreadController
from app.decorators import handle_exceptions
from app.schemas.thread_schemas import chat_messages_schema, ingest_db_schema
from app.utils.response import Response

thread_routes = Blueprint("thread_routes", __name__)
thread_controller = ThreadController()


@thread_routes.post("/chat")
@handle_exceptions
def chat():
    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = thread_controller.process_chat_message(validated_request_data.get("messages"))
    return Response.make(messages, Response.HTTP_SUCCESS)


@thread_routes.post("/ingest")
@handle_exceptions
def ingest():
    validated_request_data = ingest_db_schema.load(request.get_json())
    messages = thread_controller.ingest_db(validated_request_data.get("source"))
    return Response.make(messages, Response.HTTP_SUCCESS)