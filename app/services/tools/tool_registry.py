"""
Tool Registry

Manages available tools and their configurations based on config.json.
Provides a centralized way to discover and execute tools.
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from app import logger
from app.services.tools.execute_sql_tool import sql_tool


class ToolRegistry:
    """Registry for managing and executing tools."""
    
    def __init__(self, config_path: str = "app/services/tools/config.json"):
        """Initialize the tool registry."""
        self.config_path = config_path
        self.config = self._load_config()
        self.tools = self._register_tools()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load tool configuration from JSON file."""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"Tool config file not found: {self.config_path}")
                return {"tools": {}, "decision_guidelines": {}}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded tool configuration with {len(config.get('tools', {}))} tools")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load tool config: {e}")
            return {"tools": {}, "decision_guidelines": {}}
    
    def _register_tools(self) -> Dict[str, Any]:
        """Register available tool instances."""
        tools = {
            "execute_sql_tool": sql_tool,
        }
        
        logger.info(f"Registered {len(tools)} tools: {list(tools.keys())}")
        return tools
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())
    
    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific tool."""
        return self.config.get("tools", {}).get(tool_name)
    
    def get_all_tool_configs(self) -> Dict[str, Any]:
        """Get configurations for all tools."""
        return self.config.get("tools", {})
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Dict containing execution result
        """
        if tool_name not in self.tools:
            logger.error(f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            tool_instance = self.tools[tool_name]
            logger.info(f"🚀 EXECUTING TOOL: {tool_name}")
            logger.info(f"📋 PARAMETERS: {parameters}")
            
            # Execute the tool
            result = tool_instance.execute(parameters)
            
            # Convert Pydantic model to dict if needed
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
            else:
                result_dict = result
            
            logger.info(f"✅ TOOL EXECUTION SUCCESS: {tool_name}")
            logger.debug(f"📊 RESULT: {result_dict}")
            return result_dict
            
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }
    
    def get_decision_guidelines(self) -> Dict[str, List[str]]:
        """Get guidelines for making respond vs use_tool decisions."""
        return self.config.get("decision_guidelines", {
            "respond_directly": [
                "Greetings and general conversation",
                "Help requests and how-to questions"
            ],
            "use_tool": [
                "Questions asking for specific data from the database"
            ]
        })
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for a specific tool.
        
        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        tool_config = self.get_tool_config(tool_name)
        if not tool_config:
            return {
                "valid": False,
                "errors": [f"Tool '{tool_name}' not found in configuration"]
            }
        
        param_schema = tool_config.get("parameters", {})
        required_params = param_schema.get("required", [])
        param_properties = param_schema.get("properties", {})
        
        errors = []
        
        # Check required parameters
        for required_param in required_params:
            if required_param not in parameters:
                errors.append(f"Missing required parameter: {required_param}")
        
        # Check parameter types (basic validation)
        for param_name, param_value in parameters.items():
            if param_name in param_properties:
                expected_type = param_properties[param_name].get("type")
                if expected_type == "string" and not isinstance(param_value, str):
                    errors.append(f"Parameter '{param_name}' must be a string")
                elif expected_type == "number" and not isinstance(param_value, (int, float)):
                    errors.append(f"Parameter '{param_name}' must be a number")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def get_tool_examples(self, tool_name: str) -> List[Dict[str, Any]]:
        """Get usage examples for a specific tool."""
        tool_config = self.get_tool_config(tool_name)
        if tool_config:
            return tool_config.get("examples", [])
        return []


# Global registry instance
tool_registry = ToolRegistry()