"""
Configuration and integration module for enhanced financial chat interface.

This module provides configuration options and integration utilities for the
enhanced chat system with RAG, LLM-as-a-Judge, and response quality improvements.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EnhancementLevel(Enum):
    """Enhancement levels for response processing."""
    BASIC = "basic"           # Original functionality only
    STANDARD = "standard"     # Basic + improved prompts and tools
    ADVANCED = "advanced"     # Standard + RAG and context enhancement
    PREMIUM = "premium"       # Advanced + LLM-as-a-Judge and auto-improvement


@dataclass
class ChatEnhancementConfig:
    """Configuration for chat enhancement features."""
    
    # Enhancement level
    enhancement_level: EnhancementLevel = EnhancementLevel.PREMIUM
    
    # RAG settings
    enable_rag: bool = True
    knowledge_base_file: Optional[str] = None
    max_context_items: int = 3
    context_relevance_threshold: float = 0.1
    
    # Response quality evaluation
    enable_quality_evaluation: bool = True
    quality_threshold: float = 0.75
    confidence_threshold: float = 0.6
    auto_improvement_enabled: bool = True
    
    # Multi-step reasoning
    enable_multi_step_reasoning: bool = True
    max_reasoning_steps: int = 5
    
    # Tool preferences
    prefer_rag_enhanced_queries: bool = True
    include_schema_context: bool = True
    enable_sql_suggestions: bool = True
    
    # Response formatting
    include_quality_metrics: bool = False  # For debugging/monitoring
    include_enhancement_notes: bool = False  # For debugging/monitoring
    add_confidence_indicators: bool = True
    
    # Performance settings
    max_response_time_seconds: float = 30.0
    enable_caching: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enhancement_level': self.enhancement_level.value,
            'enable_rag': self.enable_rag,
            'knowledge_base_file': self.knowledge_base_file,
            'max_context_items': self.max_context_items,
            'context_relevance_threshold': self.context_relevance_threshold,
            'enable_quality_evaluation': self.enable_quality_evaluation,
            'quality_threshold': self.quality_threshold,
            'confidence_threshold': self.confidence_threshold,
            'auto_improvement_enabled': self.auto_improvement_enabled,
            'enable_multi_step_reasoning': self.enable_multi_step_reasoning,
            'max_reasoning_steps': self.max_reasoning_steps,
            'prefer_rag_enhanced_queries': self.prefer_rag_enhanced_queries,
            'include_schema_context': self.include_schema_context,
            'enable_sql_suggestions': self.enable_sql_suggestions,
            'include_quality_metrics': self.include_quality_metrics,
            'include_enhancement_notes': self.include_enhancement_notes,
            'add_confidence_indicators': self.add_confidence_indicators,
            'max_response_time_seconds': self.max_response_time_seconds,
            'enable_caching': self.enable_caching
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ChatEnhancementConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        for key, value in config_dict.items():
            if hasattr(config, key):
                if key == 'enhancement_level':
                    setattr(config, key, EnhancementLevel(value))
                else:
                    setattr(config, key, value)
        
        return config


# Default configurations for different use cases
DEFAULT_CONFIGS = {
    'development': ChatEnhancementConfig(
        enhancement_level=EnhancementLevel.ADVANCED,
        include_quality_metrics=True,
        include_enhancement_notes=True,
        max_response_time_seconds=60.0
    ),
    
    'production': ChatEnhancementConfig(
        enhancement_level=EnhancementLevel.PREMIUM,
        include_quality_metrics=False,
        include_enhancement_notes=False,
        max_response_time_seconds=20.0,
        enable_caching=True
    ),
    
    'demo': ChatEnhancementConfig(
        enhancement_level=EnhancementLevel.PREMIUM,
        include_quality_metrics=True,
        include_enhancement_notes=True,
        add_confidence_indicators=True,
        max_response_time_seconds=30.0
    ),
    
    'basic': ChatEnhancementConfig(
        enhancement_level=EnhancementLevel.BASIC,
        enable_rag=False,
        enable_quality_evaluation=False,
        enable_multi_step_reasoning=False,
        auto_improvement_enabled=False
    )
}


def get_chat_config(environment: str = 'production') -> ChatEnhancementConfig:
    """
    Get chat enhancement configuration for specified environment.
    
    Args:
        environment: Environment name ('development', 'production', 'demo', 'basic')
    
    Returns:
        ChatEnhancementConfig instance
    """
    return DEFAULT_CONFIGS.get(environment, DEFAULT_CONFIGS['production'])


def create_custom_config(**kwargs) -> ChatEnhancementConfig:
    """
    Create a custom configuration with specified overrides.
    
    Args:
        **kwargs: Configuration parameters to override
    
    Returns:
        ChatEnhancementConfig with custom settings
    """
    config = ChatEnhancementConfig()
    
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


# Integration utilities
class FeatureFlags:
    """Feature flags for gradual rollout of enhancements."""
    
    def __init__(self, config: ChatEnhancementConfig):
        self.config = config
    
    def should_use_rag(self) -> bool:
        """Check if RAG should be used."""
        return (self.config.enable_rag and 
                self.config.enhancement_level in [EnhancementLevel.ADVANCED, EnhancementLevel.PREMIUM])
    
    def should_evaluate_quality(self) -> bool:
        """Check if quality evaluation should be performed."""
        return (self.config.enable_quality_evaluation and
                self.config.enhancement_level == EnhancementLevel.PREMIUM)
    
    def should_auto_improve(self) -> bool:
        """Check if automatic improvement should be applied."""
        return (self.config.auto_improvement_enabled and
                self.should_evaluate_quality())
    
    def should_use_multi_step_reasoning(self) -> bool:
        """Check if multi-step reasoning should be used."""
        return (self.config.enable_multi_step_reasoning and
                self.config.enhancement_level in [EnhancementLevel.ADVANCED, EnhancementLevel.PREMIUM])
    
    def should_prefer_rag_queries(self) -> bool:
        """Check if RAG-enhanced queries should be preferred."""
        return (self.config.prefer_rag_enhanced_queries and
                self.should_use_rag())


def validate_config(config: ChatEnhancementConfig) -> List[str]:
    """
    Validate configuration and return list of warnings/errors.
    
    Args:
        config: Configuration to validate
    
    Returns:
        List of validation messages
    """
    warnings = []
    
    # Check for conflicting settings
    if not config.enable_rag and config.prefer_rag_enhanced_queries:
        warnings.append("RAG is disabled but prefer_rag_enhanced_queries is True")
    
    if not config.enable_quality_evaluation and config.auto_improvement_enabled:
        warnings.append("Quality evaluation is disabled but auto_improvement_enabled is True")
    
    # Check thresholds
    if config.quality_threshold < 0.0 or config.quality_threshold > 1.0:
        warnings.append("quality_threshold should be between 0.0 and 1.0")
    
    if config.confidence_threshold < 0.0 or config.confidence_threshold > 1.0:
        warnings.append("confidence_threshold should be between 0.0 and 1.0")
    
    # Check performance settings
    if config.max_response_time_seconds < 5.0:
        warnings.append("max_response_time_seconds is very low, may cause timeouts")
    
    return warnings
