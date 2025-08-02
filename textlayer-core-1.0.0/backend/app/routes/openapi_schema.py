"""
OpenAPI schema definition for TextLayer Core API.

This module contains the OpenAPI 3.0.3 schema definition for the TextLayer Core API,
which documents the API's endpoints, request/response formats, and error types.
"""


def get_openapi_schema():
    """
    Get the OpenAPI schema for the TextLayer Core API.

    Returns:
        dict: The complete OpenAPI 3.0.3 schema.
    """
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "TextLayer Core API",
            "description": "API for TextLayer Core - A comprehensive Flask application template for "
            "building AI-powered services.",
            "version": "1.0.0",
            "contact": {"name": "TextLayer", "url": "https://github.com/TextLayer/textlayer-core"},
        },
        "servers": [{"url": "/v1", "description": "TextLayer Core API v1"}],
        "paths": {
            "/": {
                "get": {
                    "summary": "API Root",
                    "description": "Returns API version and description",
                    "operationId": "getApiInfo",
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ApiInfoResponse"}}
                            },
                        }
                    },
                }
            },
            "/health": {
                "get": {
                    "summary": "Health Check",
                    "description": "Returns the health status of the API",
                    "operationId": "getHealthStatus",
                    "responses": {
                        "200": {
                            "description": "API is online",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}
                            },
                        }
                    },
                }
            },
            "/threads/chat": {
                "post": {
                    "summary": "Chat",
                    "description": "Process chat messages",
                    "operationId": "processChat",
                    "requestBody": {
                        "description": "Chat messages to process",
                        "required": True,
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ChatMessagesRequest"}}
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ChatResponse"}}},
                        },
                        "400": {
                            "description": "Bad request",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        },
                        "500": {
                            "description": "Server error",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        },
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "ApiInfoResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer", "example": 200},
                        "payload": {
                            "type": "object",
                            "properties": {
                                "api_version": {"type": "string", "example": "v1.0"},
                                "api_description": {
                                    "type": "string",
                                    "example": "TextLayer Core API",
                                },
                            },
                        },
                        "correlation_id": {
                            "type": "string",
                            "example": "123e4567-e89b-12d3-a456-426614174000",
                        },
                    },
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer", "example": 200},
                        "payload": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "example": "online"},
                            },
                        },
                        "correlation_id": {
                            "type": "string",
                            "example": "123e4567-e89b-12d3-a456-426614174000",
                        },
                    },
                },
                "ChatMessage": {
                    "type": "object",
                    "required": ["role", "content"],
                    "properties": {
                        "role": {
                            "type": "string",
                            "description": "The role of the message sender",
                            "example": "user",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content of the message",
                            "example": "Hello, how can you help me today?",
                        },
                    },
                },
                "ChatMessagesRequest": {
                    "type": "object",
                    "required": ["messages"],
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ChatMessage"},
                            "description": "Array of chat messages",
                        }
                    },
                },
                "ChatResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer", "example": 200},
                        "payload": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ChatMessage"},
                        },
                        "correlation_id": {
                            "type": "string",
                            "example": "123e4567-e89b-12d3-a456-426614174000",
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "integer", "example": 400},
                        "payload": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/ValidationError"},
                                {"$ref": "#/components/schemas/ProcessingError"},
                                {"$ref": "#/components/schemas/GenericError"},
                            ]
                        },
                        "correlation_id": {
                            "type": "string",
                            "example": "123e4567-e89b-12d3-a456-426614174000",
                        },
                    },
                },
                "ValidationError": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Failed to validate schema",
                        }
                    },
                },
                "ProcessingError": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "example": "Failed to process data"}},
                },
                "GenericError": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Request failed to complete",
                        }
                    },
                },
            }
        },
    }
