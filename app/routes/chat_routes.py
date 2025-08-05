from flask import Blueprint, render_template, request, jsonify, Response, stream_template
from app.controllers.thread_controller import ThreadController
from app import logger
import json
import time
import sys

# Create blueprint for chat routes
chat_routes = Blueprint('chat', __name__)

# Initialize controller
thread_controller = ThreadController()


@chat_routes.route('/')
def chat_interface():
    """
    Serve the main chat interface.
    """
    return render_template('chat.html')


@chat_routes.route('/chat', methods=['POST'])
def chat_endpoint():
    """
    Handle chat messages from the web interface.
    
    This endpoint receives messages from the chat UI and processes them
    using the enhanced financial analysis system.
    """
    try:
        # Get the request data
        data = request.get_json()
        
        if not data or 'messages' not in data:
            return jsonify({
                'error': 'Invalid request format. Expected {"messages": [...]}'
            }), 400
        
        messages = data['messages']
        
        if not messages or not isinstance(messages, list):
            return jsonify({
                'error': 'Messages must be a non-empty list'
            }), 400
        
        # Validate message format
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                return jsonify({
                    'error': 'Each message must have "role" and "content" fields'
                }), 400
        
        logger.info(f"Processing chat request with {len(messages)} messages")
        
        # Process the chat messages using the enhanced system
        response_messages = thread_controller.process_chat_message(messages)
        
        # Return the response
        return jsonify(response_messages)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


@chat_routes.route('/debug', methods=['GET'])
def debug_endpoint():
    """Debug endpoint to test blueprint registration."""
    logger.info("=== DEBUG ENDPOINT CALLED ===")
    return jsonify({'status': 'Chat blueprint is working!', 'timestamp': time.time()})


@chat_routes.route('/stream', methods=['POST'])
def chat_stream_endpoint():
    """
    Handle streaming chat messages using Server-Sent Events (SSE).
    
    This endpoint provides real-time streaming responses for a more
    interactive chat experience.
    """
    logger.info("=== STREAMING ENDPOINT CALLED ===")
    
    try:
        # Get the request data
        data = request.get_json()
        
        if not data or 'messages' not in data:
            logger.error("Invalid request format")
            return jsonify({'error': 'Invalid request format'}), 400
        
        messages = data['messages']
        logger.info(f"Processing streaming chat request with {len(messages)} messages")
        
        # Initialize the thread controller for processing
        thread_controller = ThreadController()
        
        def generate_real_stream():
            """Generate streaming response from real chat processing."""
            try:
                # Process the chat messages using the enhanced system
                response_messages = thread_controller.process_chat_message(messages)
                
                # Find the assistant's response
                assistant_response = "I apologize, but I couldn't generate a proper response. Please try again."
                
                if response_messages and hasattr(response_messages, 'payload'):
                    payload = response_messages.payload
                    for msg in reversed(payload):
                        if isinstance(msg, dict):
                            if msg.get('role') == 'assistant' and msg.get('content'):
                                assistant_response = msg['content']
                                break
                elif isinstance(response_messages, list) and len(response_messages) > 0:
                    for msg in reversed(response_messages):
                        if isinstance(msg, dict):
                            if msg.get('role') == 'assistant' and msg.get('content'):
                                assistant_response = msg['content']
                                break
                
                # Clean up JSON-escaped content if needed
                if isinstance(assistant_response, str) and assistant_response.startswith('"') and assistant_response.endswith('"'):
                    try:
                        assistant_response = json.loads(assistant_response)
                    except json.JSONDecodeError:
                        assistant_response = assistant_response.strip('"').replace('\\n', '\n').replace('\\"', '"')
                
                # Smart streaming that preserves formatting
                def create_streaming_chunks(text):
                    """Create smart chunks that preserve formatting structure."""
                    chunks = []
                    
                    # Check if content has tables or complex formatting
                    if '|' in text and '---' in text:  # Markdown table detected
                        # Split by lines and group table content
                        lines = text.split('\n')
                        current_chunk = ""
                        in_table = False
                        
                        for line in lines:
                            if '|' in line and ('---' in line or in_table):
                                # Table content - add full lines at once
                                in_table = True
                                current_chunk += line + '\n'
                                if line.strip() and not line.strip().startswith('|'):
                                    chunks.append(current_chunk.strip())
                                    current_chunk = ""
                                    in_table = False
                            else:
                                if in_table:
                                    chunks.append(current_chunk.strip())
                                    current_chunk = ""
                                    in_table = False
                                
                                # Regular content - split by sentences
                                if line.strip():
                                    sentences = line.split('. ')
                                    for j, sentence in enumerate(sentences):
                                        if j < len(sentences) - 1:
                                            chunks.append((current_chunk + sentence + '.').strip())
                                            current_chunk = ""
                                        else:
                                            current_chunk += sentence
                                    current_chunk += '\n'
                        
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                    else:
                        # Regular content - split by sentences for natural flow
                        sentences = text.replace('\n', ' ').split('. ')
                        current_chunk = ""
                        
                        for i, sentence in enumerate(sentences):
                            current_chunk += sentence
                            if i < len(sentences) - 1:
                                current_chunk += '. '
                                chunks.append(current_chunk)
                                current_chunk = ""
                        
                        if current_chunk.strip():
                            chunks.append(current_chunk)
                    
                    return [chunk for chunk in chunks if chunk.strip()]
                
                # Create smart chunks
                chunks = create_streaming_chunks(assistant_response)
                current_text = ""
                
                logger.info(f"Starting to stream {len(chunks)} chunks")
                
                for i, chunk in enumerate(chunks):
                    current_text += chunk + " "
                    
                    chunk_data = {
                        'content': current_text.strip(),
                        'done': i == len(chunks) - 1,
                        'chunk_count': i + 1,
                        'total_chunks': len(chunks)
                    }
                    
                    logger.debug(f"Streaming chunk {i+1}/{len(chunks)}: {chunk[:50]}...")
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    # Much slower, human-readable streaming delays
                    if '|' in chunk:  # Table content
                        time.sleep(1.5)  # Longer delay for table rows to be readable
                    elif chunk.endswith(('.', '!', '?')):
                        time.sleep(2.0)  # Long pause after complete thoughts (2 seconds)
                    elif chunk.endswith((',', ';', ':')):
                        time.sleep(1.2)  # Medium pause after clauses
                    else:
                        time.sleep(1.5)  # Base delay between chunks (1.5 seconds)
                
                logger.info("Real streaming complete")
                
            except Exception as e:
                logger.error(f"Error in real streaming: {str(e)}")
                error_msg = f"I encountered an error while processing your request: {str(e)}"
                yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
        
        return Response(
            generate_real_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in streaming endpoint: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@chat_routes.route('/health')
def chat_health():
    """
    Health check endpoint for the chat system.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'FinanceGPT Chat Interface',
        'features': [
            'Enhanced Financial Analysis',
            'RAG-powered Context',
            'LLM-as-a-Judge Quality',
            'Multi-step Reasoning'
        ]
    })


@chat_routes.route('/suggestions')
def get_suggestions():
    """
    Get suggested questions based on available data.
    """
    try:
        # You can enhance this to dynamically generate suggestions
        # based on your actual database schema
        suggestions = [
            {
                'text': 'What tables are available in the database?',
                'category': 'exploration',
                'icon': '📋'
            },
            {
                'text': 'What is the total revenue for 2024?',
                'category': 'metrics',
                'icon': '💰'
            },
            {
                'text': 'Show me the trend over the last 6 months',
                'category': 'trends',
                'icon': '📈'
            },
            {
                'text': 'What are the top 10 performers?',
                'category': 'rankings',
                'icon': '🏆'
            },
            {
                'text': 'Compare this month to last month',
                'category': 'comparison',
                'icon': '⚖️'
            },
            {
                'text': 'What are the highest and lowest values?',
                'category': 'analysis',
                'icon': '📊'
            }
        ]
        
        return jsonify(suggestions)
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return jsonify([])  # Return empty list on error
