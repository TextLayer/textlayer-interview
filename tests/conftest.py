"""
Test Configuration and Fixtures

This module provides pytest fixtures and configuration for the test suite.
Includes database setup, API client configuration, and mock data.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from flask import Flask

from app import create_app
from app.services.llm.session import LLMSession
from app.services.tools.tool_registry import ToolRegistry


@pytest.fixture
def app():
    """
    Create a Flask application configured for testing.
    
    Returns:
        Flask: Configured Flask application instance for testing
    """
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'FLASK_CONFIG': 'TEST',
        'GOOGLE_API_KEY': 'test-key',
        'GEMINI_API_KEY': 'test-key',
        'CHAT_MODEL': 'gemini/gemini-2.5-flash',
        'EMBEDDING_MODEL': 'gemini-embedding-001',
        'KNN_EMBEDDING_DIMENSION': 768,
        'DATABASE_PATH': db_path,
    })
    
    with app.app_context():
        yield app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """
    Create a test client for the Flask application.
    
    Args:
        app: Flask application fixture
        
    Returns:
        FlaskClient: Test client for making HTTP requests
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Create a test runner for CLI commands.
    
    Args:
        app: Flask application fixture
        
    Returns:
        CliRunner: Test runner for CLI commands
    """
    return app.test_cli_runner()


@pytest.fixture
def mock_llm_session():
    """
    Create a mock LLM session for testing without API calls.
    
    Returns:
        Mock: Mocked LLMSession instance
    """
    with patch('app.services.llm.session.LLMSession') as mock:
        mock_instance = Mock(spec=LLMSession)
        mock_instance.chat.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[Mock(
                        function=Mock(
                            name='make_decision',
                            arguments='{"decision": "response", "response": "Test response", "reasoning": "Test reasoning"}'
                        )
                    )]
                )
            )]
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_tool_registry():
    """
    Create a mock tool registry for testing.
    
    Returns:
        Mock: Mocked ToolRegistry instance
    """
    with patch('app.services.tools.tool_registry.tool_registry') as mock:
        mock.get_available_tools.return_value = ['execute_sql_tool']
        mock.validate_tool_parameters.return_value = {"valid": True}
        mock.execute_tool.return_value = {
            "success": True,
            "data": "| customer_count |\n|---------------:|\n|         26112 |",
            "row_count": 1,
            "execution_time_ms": 10.5,
            "query_executed": "SELECT COUNT(*) as customer_count FROM customer"
        }
        yield mock


@pytest.fixture
def sample_user_queries():
    """
    Provide sample user queries for testing.
    
    Returns:
        dict: Dictionary of test queries categorized by type
    """
    return {
        "conversational": [
            "hello",
            "hi there",
            "how are you",
            "what can you do",
            "help me",
            "thanks",
            "goodbye"
        ],
        "data_queries": [
            "how many customers are there",
            "show me the customer table",
            "count all records",
            "display customer data",
            "what tables exist",
            "analyze the data"
        ],
        "edge_cases": [
            "",
            "   ",
            "SELECT * FROM users; DROP TABLE users;",  # SQL injection attempt
            "a" * 1000,  # Very long query
            "🤖 AI query with emojis 💻",
        ]
    }


@pytest.fixture
def sample_api_payloads():
    """
    Provide sample API payloads for testing endpoints.
    
    Returns:
        dict: Dictionary of sample API request payloads
    """
    return {
        "valid_chat": {
            "messages": [
                {"role": "user", "content": "how many customers are there?"}
            ]
        },
        "conversational_chat": {
            "messages": [
                {"role": "user", "content": "hello there!"}
            ]
        },
        "invalid_chat": {
            "messages": [
                {"role": "invalid", "content": "test"}
            ]
        },
        "empty_chat": {
            "messages": []
        },
        "missing_content": {
            "messages": [
                {"role": "user"}
            ]
        }
    }


@pytest.fixture
def expected_response_schemas():
    """
    Provide expected response schemas for validation.
    
    Returns:
        dict: Dictionary of expected response structures
    """
    return {
        "success_response": {
            "required_fields": ["correlation_id", "payload", "status"],
            "payload_structure": {
                "required_fields": ["role", "content", "decision", "final_response"],
                "optional_fields": ["tool", "tool_parameters", "reasoning", "timestamp"]
            }
        },
        "error_response": {
            "required_fields": ["error", "status"],
            "optional_fields": ["details", "correlation_id"]
        }
    }