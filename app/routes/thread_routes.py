from flask import Blueprint, request

from app.controllers.thread_controller import ThreadController
from app.decorators import handle_exceptions
from app.schemas.thread_schemas import chat_messages_schema
from app.utils.response import Response

thread_routes = Blueprint("thread_routes", __name__)
thread_controller = ThreadController()


@thread_routes.get("/")
@handle_exceptions
def list_threads():
    """List all threads"""
    # For now, return mock threads since we don't have persistent storage
    threads = [
        {
            "id": "thread_1",
            "title": "General Chat",
            "preview": "Welcome to TextLayer AI",
            "created_at": "2025-07-21T22:00:00Z"
        }
    ]
    return Response.make({
        "threads": threads,
        "count": len(threads)
    }, Response.HTTP_SUCCESS)


@thread_routes.post("/")
@handle_exceptions
def create_thread():
    """Create a new thread"""
    import uuid
    from datetime import datetime
    
    request_data = request.get_json() or {}
    thread_id = str(uuid.uuid4())
    
    new_thread = {
        "id": thread_id,
        "title": request_data.get("title", "New Chat"),
        "preview": "No messages yet",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "metadata": request_data.get("metadata", {})
    }
    
    return Response.make({
        "thread": new_thread,
        "message": "Thread created successfully"
    }, Response.HTTP_SUCCESS)


@thread_routes.get("/info")
@handle_exceptions
def threads_info():
    return Response.make({
        "message": "Threads API",
        "available_endpoints": [
            "GET /v1/threads - List all threads",
            "POST /v1/threads - Create new thread",
            "POST /v1/threads/chat - Process chat messages"
        ]
    }, Response.HTTP_SUCCESS)


@thread_routes.post("/chat")
@handle_exceptions
def chat():
    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = thread_controller.process_chat_message(validated_request_data.get("messages"))
    return Response.make(messages, Response.HTTP_SUCCESS)