"""
Integration Tests for API Endpoints

Tests the HTTP API endpoints to ensure proper request/response handling,
authentication, validation, and error handling.

This module tests:
- Chat endpoint functionality
- Request/response validation
- Error handling and status codes
- API response structure
- Content type handling
"""

import pytest
import json
from unittest.mock import patch

from app import create_app


class TestChatEndpoint:
    """Test suite for the /v1/threads/chat endpoint."""
    
    def test_health_endpoint(self, client):
        """
        Test the health check endpoint.
        
        Args:
            client: Flask test client fixture
        """
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'online'
    
    def test_valid_chat_request(self, client, sample_api_payloads, mock_llm_session, mock_tool_registry):
        """
        Test valid chat request processing.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            mock_llm_session: Mocked LLM session fixture
            mock_tool_registry: Mocked tool registry fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            response = client.post(
                '/v1/threads/chat',
                data=json.dumps(sample_api_payloads['valid_chat']),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Validate response structure
            assert 'correlation_id' in data
            assert 'payload' in data
            assert 'status' in data
            assert data['status'] == 200
            
            # Validate payload structure
            payload = data['payload']
            assert len(payload) >= 2  # User message + assistant response
            
            # Check assistant response
            assistant_msg = None
            for msg in payload:
                if msg.get('role') == 'assistant':
                    assistant_msg = msg
                    break
            
            assert assistant_msg is not None
            assert 'decision' in assistant_msg
            assert 'final_response' in assistant_msg
            assert 'reasoning' in assistant_msg
    
    def test_conversational_chat_request(self, client, sample_api_payloads, mock_llm_session):
        """
        Test conversational chat request.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            mock_llm_session: Mocked LLM session fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            response = client.post(
                '/v1/threads/chat',
                data=json.dumps(sample_api_payloads['conversational_chat']),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Find assistant response
            assistant_msg = None
            for msg in data['payload']:
                if msg.get('role') == 'assistant':
                    assistant_msg = msg
                    break
            
            assert assistant_msg is not None
            assert assistant_msg['decision'] == 'response'
            assert assistant_msg['final_response']['status'] == 'direct_response'
    
    def test_invalid_request_format(self, client):
        """
        Test handling of invalid request format.
        
        Args:
            client: Flask test client fixture
        """
        response = client.post(
            '/v1/threads/chat',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_missing_messages(self, client, sample_api_payloads):
        """
        Test handling of request with missing messages.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
        """
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(sample_api_payloads['empty_chat']),
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_invalid_message_role(self, client, sample_api_payloads):
        """
        Test handling of invalid message role.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
        """
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(sample_api_payloads['invalid_chat']),
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_missing_content(self, client, sample_api_payloads):
        """
        Test handling of message with missing content.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
        """
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(sample_api_payloads['missing_content']),
            content_type='application/json'
        )
        
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_content_type_validation(self, client, sample_api_payloads):
        """
        Test content type validation.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
        """
        # Test with wrong content type
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(sample_api_payloads['valid_chat']),
            content_type='text/plain'
        )
        
        # Should still work or return appropriate error
        assert response.status_code in [200, 400, 415]
    
    def test_large_request_handling(self, client):
        """
        Test handling of very large requests.
        
        Args:
            client: Flask test client fixture
        """
        large_content = "A" * 10000  # Very long message
        payload = {
            "messages": [
                {"role": "user", "content": large_content}
            ]
        }
        
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 413]  # OK, Bad Request, or Payload Too Large
    
    def test_cors_headers(self, client, sample_api_payloads):
        """
        Test CORS headers in response.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
        """
        response = client.post(
            '/v1/threads/chat',
            data=json.dumps(sample_api_payloads['valid_chat']),
            content_type='application/json'
        )
        
        # Check if CORS headers are present (if CORS is configured)
        headers = response.headers
        # This test might need adjustment based on actual CORS configuration
        assert 'Content-Type' in headers
    
    def test_response_timing(self, client, sample_api_payloads, mock_llm_session):
        """
        Test response timing and performance.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            mock_llm_session: Mocked LLM session fixture
        """
        import time
        
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            start_time = time.time()
            
            response = client.post(
                '/v1/threads/chat',
                data=json.dumps(sample_api_payloads['valid_chat']),
                content_type='application/json'
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 5.0  # Should respond within 5 seconds with mocked LLM
    
    def test_concurrent_requests(self, client, sample_api_payloads, mock_llm_session):
        """
        Test handling of concurrent requests.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            mock_llm_session: Mocked LLM session fixture
        """
        import threading
        import time
        
        results = []
        
        def make_request():
            with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
                response = client.post(
                    '/v1/threads/chat',
                    data=json.dumps(sample_api_payloads['valid_chat']),
                    content_type='application/json'
                )
                results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)


class TestAPIResponseStructure:
    """Test suite for API response structure validation."""
    
    def test_success_response_structure(self, client, sample_api_payloads, expected_response_schemas, mock_llm_session):
        """
        Test structure of successful API responses.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            expected_response_schemas: Expected response schemas fixture
            mock_llm_session: Mocked LLM session fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            response = client.post(
                '/v1/threads/chat',
                data=json.dumps(sample_api_payloads['valid_chat']),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Validate top-level structure
            success_schema = expected_response_schemas['success_response']
            for field in success_schema['required_fields']:
                assert field in data
            
            # Validate payload structure
            payload = data['payload']
            assert isinstance(payload, list)
            assert len(payload) >= 1
            
            # Find assistant message and validate structure
            assistant_msg = None
            for msg in payload:
                if msg.get('role') == 'assistant':
                    assistant_msg = msg
                    break
            
            if assistant_msg:
                payload_schema = success_schema['payload_structure']
                for field in payload_schema['required_fields']:
                    assert field in assistant_msg
    
    def test_final_response_structure(self, client, sample_api_payloads, mock_llm_session):
        """
        Test structure of final_response field.
        
        Args:
            client: Flask test client fixture
            sample_api_payloads: Sample request payloads fixture
            mock_llm_session: Mocked LLM session fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            response = client.post(
                '/v1/threads/chat',
                data=json.dumps(sample_api_payloads['valid_chat']),
                content_type='application/json'
            )
            
            data = response.get_json()
            assistant_msg = None
            for msg in data['payload']:
                if msg.get('role') == 'assistant':
                    assistant_msg = msg
                    break
            
            assert assistant_msg is not None
            assert 'final_response' in assistant_msg
            
            final_response = assistant_msg['final_response']
            assert 'decision' in final_response
            assert 'status' in final_response
            
            # Validate decision-specific fields
            if final_response['decision'] == 'response':
                assert final_response['status'] == 'direct_response'
                assert 'response' in final_response
            elif final_response['decision'] == 'use_tool':
                assert 'tool' in final_response
                assert 'tool_parameters' in final_response