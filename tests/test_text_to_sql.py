"""
Unit Tests for Text-to-SQL Decision System

Tests the intelligent decision-making system that determines whether to respond
directly or use SQL tools based on user queries.

This module tests:
- Decision logic for different query types
- LLM tool calling functionality
- SQL tool parameter generation
- Error handling and fallback mechanisms
- Response format validation
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from app.services.llm.tools.text_to_sql import text_to_sql
from app.services.llm.structured_outputs.text_to_sql import UserQueryDecision


class TestTextToSQLDecisionSystem:
    """Test suite for the text-to-SQL decision system."""
    
    def test_conversational_query_decision(self, mock_llm_session, mock_tool_registry):
        """
        Test that conversational queries trigger direct responses.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
            mock_tool_registry: Mocked tool registry fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            result = text_to_sql("hello how are you")
            
            assert result["decision"] == "response"
            assert result["success"] is True
            assert "response" in result
            assert "reasoning" in result
    
    def test_data_query_decision(self, mock_llm_session, mock_tool_registry):
        """
        Test that data queries trigger tool usage.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
            mock_tool_registry: Mocked tool registry fixture
        """
        # Configure mock to return use_tool decision
        mock_llm_session.chat.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[Mock(
                        function=Mock(
                            name='make_decision',
                            arguments=json.dumps({
                                "decision": "use_tool",
                                "tool": "execute_sql_tool",
                                "tool_parameters": {
                                    "sql": "SELECT COUNT(*) FROM customer",
                                    "explanation": "Count customers"
                                },
                                "reasoning": "Query requires database access"
                            })
                        )
                    )]
                )
            )]
        )
        
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            result = text_to_sql("how many customers are there")
            
            assert result["decision"] == "use_tool"
            assert result["success"] is True
            assert result["tool"] == "execute_sql_tool"
            assert "tool_parameters" in result
            assert "tool_result" in result
    
    def test_llm_tool_calling_format(self, mock_llm_session):
        """
        Test that the LLM tool calling uses correct format.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            text_to_sql("test query")
            
            # Verify tool calling was used correctly
            mock_llm_session.chat.assert_called_once()
            call_args = mock_llm_session.chat.call_args
            
            # Check that tools parameter is provided
            assert "tools" in call_args.kwargs
            tools = call_args.kwargs["tools"]
            assert len(tools) == 1
            
            # Verify tool structure
            tool = tools[0]
            assert tool["type"] == "function"
            assert tool["function"]["name"] == "make_decision"
            assert "parameters" in tool["function"]
    
    def test_sql_parameter_validation(self, mock_llm_session):
        """
        Test SQL parameter validation for tool calls.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
        """
        # Mock tool registry to return validation failure
        with patch('app.services.tools.tool_registry.tool_registry') as mock_registry:
            mock_registry.get_available_tools.return_value = ['execute_sql_tool']
            mock_registry.validate_tool_parameters.return_value = {
                "valid": False,
                "errors": ["Invalid SQL syntax"]
            }
            
            # Configure mock LLM to return use_tool decision
            mock_llm_session.chat.return_value = Mock(
                choices=[Mock(
                    message=Mock(
                        tool_calls=[Mock(
                            function=Mock(
                                name='make_decision',
                                arguments=json.dumps({
                                    "decision": "use_tool",
                                    "tool": "execute_sql_tool",
                                    "tool_parameters": {
                                        "sql": "INVALID SQL",
                                        "explanation": "Test"
                                    },
                                    "reasoning": "Test reasoning"
                                })
                            )
                        )]
                    )
                )]
            )
            
            with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
                result = text_to_sql("invalid query")
                
                # Should fallback to direct response due to validation failure
                assert result["decision"] == "response"
                assert result["success"] is False
                assert "error" in result
    
    def test_tool_execution_failure_handling(self, mock_llm_session):
        """
        Test handling of tool execution failures.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
        """
        # Mock tool registry to return execution failure
        with patch('app.services.tools.tool_registry.tool_registry') as mock_registry:
            mock_registry.get_available_tools.return_value = ['execute_sql_tool']
            mock_registry.validate_tool_parameters.return_value = {"valid": True}
            mock_registry.execute_tool.return_value = {
                "success": False,
                "error": "Database connection failed"
            }
            
            # Configure mock LLM to return use_tool decision
            mock_llm_session.chat.return_value = Mock(
                choices=[Mock(
                    message=Mock(
                        tool_calls=[Mock(
                            function=Mock(
                                name='make_decision',
                                arguments=json.dumps({
                                    "decision": "use_tool",
                                    "tool": "execute_sql_tool",
                                    "tool_parameters": {
                                        "sql": "SELECT COUNT(*) FROM customer",
                                        "explanation": "Count customers"
                                    },
                                    "reasoning": "Query requires database access"
                                })
                            )
                        )]
                    )
                )]
            )
            
            with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
                result = text_to_sql("test query")
                
                # Should return error response
                assert result["decision"] == "response"
                assert result["success"] is False
                assert "tool_error" in result
    
    def test_no_tool_call_fallback(self, mock_llm_session):
        """
        Test fallback when LLM doesn't return tool calls.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
        """
        # Configure mock to return no tool calls
        mock_llm_session.chat.return_value = Mock(
            choices=[Mock(
                message=Mock(tool_calls=None)
            )]
        )
        
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            result = text_to_sql("test query")
            
            assert result["decision"] == "response"
            assert result["success"] is True
            assert "No structured decision received" in result["reasoning"]
    
    def test_invalid_json_in_tool_call(self, mock_llm_session):
        """
        Test handling of invalid JSON in tool call arguments.
        
        Args:
            mock_llm_session: Mocked LLM session fixture
        """
        # Configure mock to return invalid JSON
        mock_llm_session.chat.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[Mock(
                        function=Mock(
                            name='make_decision',
                            arguments='{"invalid": json}'  # Invalid JSON
                        )
                    )]
                )
            )]
        )
        
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            result = text_to_sql("test query")
            
            assert result["decision"] == "response"
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.parametrize("query,expected_decision", [
        ("hello", "response"),
        ("how are you", "response"),
        ("what can you do", "response"),
        ("help", "response"),
        ("thanks", "response"),
    ])
    def test_conversational_queries(self, query, expected_decision, mock_llm_session, mock_tool_registry):
        """
        Test various conversational queries.
        
        Args:
            query: User query to test
            expected_decision: Expected decision type
            mock_llm_session: Mocked LLM session fixture
            mock_tool_registry: Mocked tool registry fixture
        """
        with patch('app.services.llm.tools.text_to_sql.LLMSession', return_value=mock_llm_session):
            result = text_to_sql(query)
            
            assert result["decision"] == expected_decision
            assert result["success"] is True


class TestUserQueryDecision:
    """Test suite for the UserQueryDecision structured output model."""
    
    def test_valid_response_decision(self):
        """Test valid response decision creation."""
        decision = UserQueryDecision(
            decision="respond",
            response="Hello! How can I help you?",
            reasoning="This is a greeting that doesn't require database access"
        )
        
        assert decision.decision == "respond"
        assert decision.response == "Hello! How can I help you?"
        assert decision.reasoning == "This is a greeting that doesn't require database access"
        assert decision.tool is None
        assert decision.tool_parameters is None
    
    def test_valid_use_tool_decision(self):
        """Test valid use_tool decision creation."""
        decision = UserQueryDecision(
            decision="use_tool",
            tool="execute_sql_tool",
            tool_parameters={"sql": "SELECT COUNT(*) FROM customer", "explanation": "Count customers"},
            reasoning="Query requires database access to count customers"
        )
        
        assert decision.decision == "use_tool"
        assert decision.tool == "execute_sql_tool"
        assert decision.tool_parameters == {"sql": "SELECT COUNT(*) FROM customer", "explanation": "Count customers"}
        assert decision.reasoning == "Query requires database access to count customers"
        assert decision.response is None
    
    def test_decision_summary(self):
        """Test decision summary generation."""
        decision = UserQueryDecision(
            decision="use_tool",
            tool="execute_sql_tool",
            tool_parameters={"sql": "SELECT * FROM customer", "explanation": "Show customers"},
            reasoning="User wants to see customer data"
        )
        
        summary = decision.get_decision_summary()
        
        assert summary["decision_type"] == "use_tool"
        assert summary["has_tool"] is True
        assert summary["has_response"] is False
        assert summary["tool_name"] == "execute_sql_tool"
        assert summary["parameter_count"] == 2
        assert summary["reasoning_length"] > 0