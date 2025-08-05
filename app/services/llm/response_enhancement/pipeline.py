from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
from datetime import datetime

from app import logger
from app.services.llm.session import LLMSession
from app.services.llm.response_quality.evaluator import ResponseQualityEvaluator, ResponseEvaluation
from app.services.rag.financial_knowledge_base import get_financial_knowledge_base
from flask import current_app


@dataclass
class EnhancementResult:
    """Result of response enhancement process."""
    original_response: str
    enhanced_response: str
    quality_evaluation: ResponseEvaluation
    enhancement_applied: bool
    processing_time: float
    enhancement_notes: List[str]


class ResponseEnhancementPipeline:
    """
    Comprehensive pipeline for enhancing financial chat responses using multiple techniques.
    
    This pipeline combines:
    - Multi-step reasoning and chain-of-thought
    - RAG-enhanced context
    - LLM-as-a-Judge quality evaluation
    - Automatic response improvement
    - Error detection and correction
    """
    
    def __init__(self):
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
        self.quality_evaluator = ResponseQualityEvaluator()
        self.knowledge_base = get_financial_knowledge_base()
        
        # Enhancement thresholds
        self.quality_threshold = 0.75  # Minimum quality score to skip enhancement
        self.confidence_threshold = 0.6  # Minimum confidence for auto-enhancement
    
    def enhance_response(
        self, 
        user_query: str, 
        original_response: str,
        context: Optional[Dict] = None,
        enable_auto_improvement: bool = True
    ) -> EnhancementResult:
        """
        Enhance a response using the complete pipeline.
        
        Args:
            user_query: Original user question
            original_response: Response to enhance
            context: Additional context (tools used, data retrieved, etc.)
            enable_auto_improvement: Whether to automatically improve low-quality responses
        
        Returns:
            EnhancementResult with enhanced response and evaluation details
        """
        
        start_time = datetime.now()
        enhancement_notes = []
        
        logger.info(f"Starting response enhancement pipeline for query: {user_query[:100]}...")
        
        try:
            # Step 1: Evaluate current response quality
            quality_evaluation = self.quality_evaluator.evaluate_response(
                user_query, original_response, context
            )
            
            enhancement_notes.append(f"Initial quality score: {quality_evaluation.overall_score:.2f}")
            
            # Step 2: Determine if enhancement is needed
            if quality_evaluation.overall_score >= self.quality_threshold:
                enhancement_notes.append("Response quality above threshold - no enhancement needed")
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return EnhancementResult(
                    original_response=original_response,
                    enhanced_response=original_response,
                    quality_evaluation=quality_evaluation,
                    enhancement_applied=False,
                    processing_time=processing_time,
                    enhancement_notes=enhancement_notes
                )
            
            # Step 3: Apply enhancement techniques
            enhanced_response = original_response
            
            # Add contextual knowledge if missing
            if self._needs_context_enhancement(quality_evaluation):
                enhanced_response = self._add_contextual_knowledge(
                    user_query, enhanced_response
                )
                enhancement_notes.append("Added contextual financial knowledge")
            
            # Improve structure and clarity
            if self._needs_structure_improvement(quality_evaluation):
                enhanced_response = self._improve_response_structure(
                    user_query, enhanced_response, quality_evaluation
                )
                enhancement_notes.append("Improved response structure and clarity")
            
            # Add actionable insights
            if self._needs_actionability_improvement(quality_evaluation):
                enhanced_response = self._add_actionable_insights(
                    user_query, enhanced_response
                )
                enhancement_notes.append("Added actionable insights and recommendations")
            
            # Step 4: Apply automatic improvement if enabled and confidence is high
            if (enable_auto_improvement and 
                quality_evaluation.confidence >= self.confidence_threshold):
                
                improved_response = self.quality_evaluator.suggest_improvements(
                    user_query, enhanced_response, quality_evaluation
                )
                
                if improved_response != enhanced_response:
                    enhanced_response = improved_response
                    enhancement_notes.append("Applied LLM-as-a-Judge improvements")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EnhancementResult(
                original_response=original_response,
                enhanced_response=enhanced_response,
                quality_evaluation=quality_evaluation,
                enhancement_applied=True,
                processing_time=processing_time,
                enhancement_notes=enhancement_notes
            )
            
        except Exception as e:
            logger.error(f"Error in response enhancement pipeline: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EnhancementResult(
                original_response=original_response,
                enhanced_response=original_response,
                quality_evaluation=quality_evaluation if 'quality_evaluation' in locals() else None,
                enhancement_applied=False,
                processing_time=processing_time,
                enhancement_notes=[f"Enhancement failed: {str(e)}"]
            )
    
    def _needs_context_enhancement(self, evaluation: ResponseEvaluation) -> bool:
        """Check if response needs additional context."""
        
        # Check completeness and clarity scores
        completeness_score = next(
            (score.score for score in evaluation.dimension_scores 
             if score.dimension.value == "completeness"), 0.0
        )
        
        clarity_score = next(
            (score.score for score in evaluation.dimension_scores 
             if score.dimension.value == "clarity"), 0.0
        )
        
        return completeness_score < 0.7 or clarity_score < 0.7
    
    def _needs_structure_improvement(self, evaluation: ResponseEvaluation) -> bool:
        """Check if response needs structure improvement."""
        
        clarity_score = next(
            (score.score for score in evaluation.dimension_scores 
             if score.dimension.value == "clarity"), 0.0
        )
        
        return clarity_score < 0.6
    
    def _needs_actionability_improvement(self, evaluation: ResponseEvaluation) -> bool:
        """Check if response needs more actionable content."""
        
        actionability_score = next(
            (score.score for score in evaluation.dimension_scores 
             if score.dimension.value == "actionability"), 0.0
        )
        
        return actionability_score < 0.6
    
    def _add_contextual_knowledge(self, user_query: str, response: str) -> str:
        """Add relevant financial context to the response."""
        
        try:
            contextual_knowledge = self.knowledge_base.get_contextual_knowledge(user_query)
            
            if contextual_knowledge:
                enhanced_response = response + "\n\n" + contextual_knowledge
                return enhanced_response
            
        except Exception as e:
            logger.error(f"Error adding contextual knowledge: {e}")
        
        return response
    
    def _improve_response_structure(
        self, 
        user_query: str, 
        response: str, 
        evaluation: ResponseEvaluation
    ) -> str:
        """Improve the structure and clarity of the response."""
        
        try:
            improvement_prompt = f"""
Improve the structure and clarity of this financial analysis response while keeping all the original information.

**Original User Question:**
{user_query}

**Current Response:**
{response}

**Specific Issues to Address:**
{chr(10).join(['- ' + weakness for weakness in evaluation.weaknesses])}

**Instructions:**
1. Reorganize the information with clear headings and sections
2. Use bullet points and numbered lists for better readability
3. Ensure logical flow from summary to details
4. Add clear transitions between sections
5. Format numbers and percentages consistently
6. Keep all original data and insights

Provide the improved response:
"""
            
            improvement_response = self.llm_session.chat(
                messages=[{"role": "user", "content": improvement_prompt}],
                temperature=0.3
            )
            
            return improvement_response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error improving response structure: {e}")
            return response
    
    def _add_actionable_insights(self, user_query: str, response: str) -> str:
        """Add actionable insights and recommendations to the response."""
        
        try:
            insights_prompt = f"""
Add actionable insights and specific recommendations to this financial analysis response.

**User Question:**
{user_query}

**Current Response:**
{response}

**Instructions:**
Add a "Key Takeaways & Recommendations" section that includes:
1. 2-3 specific, actionable insights from the data
2. Concrete next steps the user should consider
3. Relevant questions for further analysis
4. Risk considerations or limitations to be aware of
5. Industry benchmarks or comparisons when relevant

Keep the existing response intact and add the new section at the end.

Provide the enhanced response:
"""
            
            insights_response = self.llm_session.chat(
                messages=[{"role": "user", "content": insights_prompt}],
                temperature=0.4
            )
            
            return insights_response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error adding actionable insights: {e}")
            return response


class MultiStepReasoningEngine:
    """
    Engine for breaking down complex financial queries into logical steps.
    """
    
    def __init__(self):
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
    
    def decompose_query(self, user_query: str) -> List[Dict[str, str]]:
        """
        Break down a complex query into logical steps.
        
        Args:
            user_query: Complex user question to decompose
        
        Returns:
            List of step dictionaries with 'step', 'description', and 'tool' keys
        """
        
        decomposition_prompt = f"""
Break down this complex financial question into logical, sequential steps that can be executed systematically.

**User Question:**
{user_query}

**Available Tools:**
- text_to_sql: Execute SQL queries against financial database
- get_database_schema: Get information about database structure
- rag_enhanced_financial_query: Execute queries with enhanced context
- get_financial_context: Get relevant financial knowledge

**Instructions:**
1. Identify the main components of the question
2. Determine what data is needed
3. Break into sequential steps that build on each other
4. Specify which tool should be used for each step
5. Ensure each step has a clear, specific objective

**Output Format:**
```json
[
  {{
    "step": 1,
    "description": "Clear description of what this step accomplishes",
    "tool": "tool_name",
    "parameters": {{"param1": "value1"}},
    "reasoning": "Why this step is necessary"
  }},
  {{
    "step": 2,
    "description": "Next step description",
    "tool": "tool_name", 
    "parameters": {{"param1": "value1"}},
    "reasoning": "How this builds on the previous step"
  }}
]
```

Provide the step-by-step breakdown:
"""
        
        try:
            response = self.llm_session.chat(
                messages=[{"role": "user", "content": decomposition_prompt}],
                temperature=0.2
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                steps_data = json.loads(json_match.group(1))
                return steps_data
            else:
                logger.warning("Could not parse step decomposition response")
                return []
                
        except Exception as e:
            logger.error(f"Error decomposing query: {e}")
            return []
    
    def synthesize_results(self, user_query: str, step_results: List[Dict]) -> str:
        """
        Synthesize results from multiple steps into a coherent response.
        
        Args:
            user_query: Original user question
            step_results: Results from each step execution
        
        Returns:
            Synthesized comprehensive response
        """
        
        synthesis_prompt = f"""
Synthesize the results from multiple analysis steps into a comprehensive, coherent response to the user's question.

**Original Question:**
{user_query}

**Step Results:**
{json.dumps(step_results, indent=2)}

**Instructions:**
1. Create a unified narrative that addresses the original question
2. Integrate insights from all steps logically
3. Highlight key findings and patterns
4. Provide clear conclusions and recommendations
5. Ensure the response flows naturally and is easy to follow
6. Include specific data points and evidence
7. Address any limitations or caveats

**Response Structure:**
1. Executive Summary (1-2 sentences)
2. Key Findings (main insights from the analysis)
3. Detailed Analysis (step-by-step breakdown with data)
4. Conclusions and Recommendations
5. Next Steps or Further Analysis Suggestions

Provide the synthesized response:
"""
        
        try:
            response = self.llm_session.chat(
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return "Error synthesizing analysis results. Please review individual step outputs."


# Global instances
_enhancement_pipeline = None
_reasoning_engine = None

def get_enhancement_pipeline() -> ResponseEnhancementPipeline:
    """Get or create the global enhancement pipeline instance."""
    global _enhancement_pipeline
    
    if _enhancement_pipeline is None:
        _enhancement_pipeline = ResponseEnhancementPipeline()
    
    return _enhancement_pipeline

def get_reasoning_engine() -> MultiStepReasoningEngine:
    """Get or create the global reasoning engine instance."""
    global _reasoning_engine
    
    if _reasoning_engine is None:
        _reasoning_engine = MultiStepReasoningEngine()
    
    return _reasoning_engine
