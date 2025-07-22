from flask import Blueprint
from flask import Response as FlaskResponse
from flask import request

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
    messages = thread_controller.process_chat_message(
        validated_request_data.get("messages")
    )
    return Response.make(messages, Response.HTTP_SUCCESS)


@thread_routes.post("/chat/stream")
@handle_exceptions
def chat_stream():
    import json
    import time

    from flask import current_app

    from app.services.llm.prompts.chat_prompt import chat_prompt
    from app.services.llm.session import LLMSession
    from app.services.sql.sql_executor import get_sql_executor

    validated_request_data = chat_messages_schema.load(request.get_json())
    messages = validated_request_data.get("messages")

    def generate():
        try:
            # Send status: Starting
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting analysis...'})}\n\n"
            time.sleep(0.3)

            # Send status: Fetching schema
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching database schema...'})}\n\n"
            time.sleep(0.5)

            # Get LLM response (non-streaming)
            llm_session = LLMSession(
                chat_model=current_app.config.get("CHAT_MODEL"),
                embedding_model=current_app.config.get("EMBEDDING_MODEL"),
            )

            # Send status: Preparing messages
            yield f"data: {json.dumps({'type': 'status', 'message': 'Preparing chat context...'})}\n\n"
            time.sleep(0.3)

            # Prepare messages with system prompt
            system_prompt = chat_prompt()
            full_messages = system_prompt + messages

            # Send status: Generating response
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating SQL and analysis...'})}\n\n"
            time.sleep(0.5)

            # Get response
            response = llm_session.chat(messages=full_messages, max_tokens=4000, temperature=0.1)
            content = response.choices[0].message.content or ""

            # Send status: Processing SQL
            yield f"data: {json.dumps({'type': 'status', 'message': 'Executing SQL queries...'})}\n\n"
            time.sleep(0.3)

            # Process SQL
            sql_executor = get_sql_executor()
            content = sql_executor.extract_and_execute_sql(content)

            # Send status: Finalizing
            yield f"data: {json.dumps({'type': 'status', 'message': 'Finalizing response...'})}\n\n"
            time.sleep(0.2)

            # Send start message
            yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': '123', 'role': 'assistant', 'content': '', 'streaming': True}})}\n\n"

            # Stream content word by word
            words = content.split(' ')
            for i, word in enumerate(words):
                chunk = word + (' ' if i < len(words) - 1 else '')
                yield f"data: {json.dumps({'type': 'content_delta', 'delta': {'content': chunk}})}\n\n"
                time.sleep(0.008)  # Slightly faster streaming

            # Send completion
            yield f"data: {json.dumps({'type': 'message_complete', 'message': {'id': '123', 'role': 'assistant', 'content': content, 'finish_reason': 'stop', 'streaming': False}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': {'content': f'Error: {str(e)}', 'role': 'assistant'}})}\n\n"

    return FlaskResponse(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )


@thread_routes.get("/status")
@handle_exceptions
def api_status():
    status = thread_controller.get_api_status()
    return Response.make(status, Response.HTTP_SUCCESS)


@thread_routes.get("/test-stream")
@handle_exceptions
def test_stream():
    """Simple test endpoint for debugging streaming."""
    def generate():
        import json
        import time

        # Send a few test messages
        for i in range(5):
            data = {"type": "test", "message": f"Test message {i+1}"}
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)

        # Send completion
        final_data = {"type": "complete", "message": "Stream test completed"}
        yield f"data: {json.dumps(final_data)}\n\n"

    return FlaskResponse(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )