from pydantic import Field, field_validator, model_validator, ValidationInfo
from vaul import StructuredOutput
from typing import Optional, Dict, Any, Literal, List
import re
import json


class UserQueryDecision(StructuredOutput):
    """
    Decision model for determining whether to respond directly or use tools.
    
    Based on user query analysis, decides whether we have enough context to respond
    directly or need to use tools to gather more information.
    """
    
    decision: Literal["respond", "use_tool"] = Field(
        ...,
        title="Decision type",
        description="Whether to respond directly to user or use a tool for more information"
    )
    
    tool: Optional[str] = Field(
        None,
        title="Tool name",
        description="Name of the tool to use if decision is 'use_tool', null if decision is 'respond'"
    )
    
    tool_parameters: Optional[Dict[str, Any]] = Field(
        None,
        title="Tool parameters",
        description="Parameters to pass to the tool if decision is 'use_tool'"
    )
    
    response: Optional[str] = Field(
        None,
        title="Direct response",
        description="Direct response to user if decision is 'respond'"
    )
    
    reasoning: str = Field(
        ...,
        title="Decision reasoning",
        description="Explanation of why this decision was made and what it accomplishes",
        min_length=10
    )

    @field_validator('reasoning')
    @classmethod
    def validate_reasoning_quality(cls, v: str) -> str:
        """Ensure reasoning is meaningful and informative."""
        if not v or not v.strip():
            raise ValueError("Reasoning cannot be empty")
        
        v = v.strip()
        
        # Check minimum length for meaningful reasoning
        if len(v) < 15:
            raise ValueError("Reasoning must be at least 15 characters long")
        
        # Ensure reasoning contains meaningful content
        meaningful_words = [word for word in v.lower().split() 
                          if word not in ['this', 'the', 'a', 'an', 'is', 'will', 'does', 'because']]
        
        if len(meaningful_words) < 3:
            raise ValueError("Reasoning must contain more meaningful content explaining the decision")
        
        return v

    @model_validator(mode='after')
    def validate_decision_consistency(self) -> 'UserQueryDecision':
        """Validate that the decision fields are consistent with each other."""
        
        if self.decision == "respond":
            # For respond decisions, should have response but not tool info
            if not self.response:
                raise ValueError("Decision 'respond' requires a 'response' field")
            if self.tool is not None:
                raise ValueError("Decision 'respond' should not have a 'tool' field")
            if self.tool_parameters is not None:
                raise ValueError("Decision 'respond' should not have 'tool_parameters'")
                
        elif self.decision == "use_tool":
            # For use_tool decisions, should have tool info but not direct response
            if not self.tool:
                raise ValueError("Decision 'use_tool' requires a 'tool' field")
            if not self.tool_parameters:
                raise ValueError("Decision 'use_tool' requires 'tool_parameters'")
            if self.response is not None:
                raise ValueError("Decision 'use_tool' should not have a 'response' field")
        
        return self

    @field_validator('tool_parameters')
    @classmethod
    def validate_tool_parameters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate tool parameters structure."""
        if v is None:
            return v
        
        if not isinstance(v, dict):
            raise ValueError("Tool parameters must be a dictionary")
        
        # Ensure no empty string keys
        for key in v.keys():
            if not key or not key.strip():
                raise ValueError("Tool parameter keys cannot be empty")
        
        return v

    def get_decision_summary(self) -> Dict[str, Any]:
        """Get a summary of the decision for debugging and logging."""
        return {
            "decision_type": self.decision,
            "has_tool": bool(self.tool),
            "has_response": bool(self.response),
            "tool_name": self.tool,
            "parameter_count": len(self.tool_parameters) if self.tool_parameters else 0,
            "reasoning_length": len(self.reasoning)
        }


# Legacy model for backward compatibility (simplified)
class SqlQuery(StructuredOutput):
    """Legacy SQL query model - kept for backward compatibility."""
    
    query: str = Field(..., title="Generated SQL query")
    confidence: float = Field(..., title="Confidence score", ge=0.0, le=1.0)
    explanation: str = Field(..., title="Query explanation", min_length=10)