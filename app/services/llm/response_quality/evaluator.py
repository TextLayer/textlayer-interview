from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re

from app import logger
from app.services.llm.session import LLMSession
from flask import current_app


class QualityDimension(Enum):
    """Quality dimensions for response evaluation."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    RELEVANCE = "relevance"
    ACTIONABILITY = "actionability"


@dataclass
class QualityScore:
    """Quality score for a specific dimension."""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    explanation: str
    suggestions: List[str]


@dataclass
class ResponseEvaluation:
    """Complete evaluation of a response."""
    overall_score: float
    dimension_scores: List[QualityScore]
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]
    confidence: float


class ResponseQualityEvaluator:
    """
    LLM-as-a-Judge system for evaluating and improving response quality.
    """
    
    def __init__(self):
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
    
    def evaluate_response(
        self, 
        user_query: str, 
        response: str, 
        context: Optional[Dict] = None
    ) -> ResponseEvaluation:
        """
        Evaluate the quality of a response using LLM-as-a-Judge.
        
        Args:
            user_query: The original user question
            response: The generated response to evaluate
            context: Additional context (e.g., data retrieved, tools used)
        
        Returns:
            ResponseEvaluation with detailed quality assessment
        """
        
        logger.info("Evaluating response quality using LLM-as-a-Judge")
        
        evaluation_prompt = self._create_evaluation_prompt(user_query, response, context)
        
        try:
            evaluation_response = self.llm_session.chat(
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.1  # Low temperature for consistent evaluation
            )
            
            evaluation_text = evaluation_response.choices[0].message.content
            return self._parse_evaluation_response(evaluation_text)
            
        except Exception as e:
            logger.error(f"Error in response evaluation: {e}")
            return self._create_fallback_evaluation()
    
    def suggest_improvements(
        self, 
        user_query: str, 
        original_response: str, 
        evaluation: ResponseEvaluation
    ) -> str:
        """
        Generate specific improvement suggestions for a response.
        
        Args:
            user_query: The original user question
            original_response: The response to improve
            evaluation: Quality evaluation results
        
        Returns:
            Improved response suggestions
        """
        
        if evaluation.overall_score >= 0.8:
            return original_response  # Already high quality
        
        improvement_prompt = self._create_improvement_prompt(
            user_query, original_response, evaluation
        )
        
        try:
            improvement_response = self.llm_session.chat(
                messages=[{"role": "user", "content": improvement_prompt}],
                temperature=0.3
            )
            
            return improvement_response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating improvements: {e}")
            return original_response
    
    def _create_evaluation_prompt(
        self, 
        user_query: str, 
        response: str, 
        context: Optional[Dict] = None
    ) -> str:
        """Create the evaluation prompt for LLM-as-a-Judge."""
        
        context_info = ""
        if context:
            context_info = f"\n\n**Additional Context:**\n{json.dumps(context, indent=2)}"
        
        return f"""
You are an expert evaluator of financial data analysis responses. Your task is to evaluate the quality of a response to a user's financial question.

**User Question:**
{user_query}

**Response to Evaluate:**
{response}{context_info}

**Evaluation Criteria:**

Evaluate the response on these 5 dimensions (score 0.0-1.0 for each):

1. **ACCURACY** (0.0-1.0): Are the facts, numbers, and calculations correct?
2. **COMPLETENESS** (0.0-1.0): Does it fully address the user's question?
3. **CLARITY** (0.0-1.0): Is it easy to understand and well-structured?
4. **RELEVANCE** (0.0-1.0): Is the information directly relevant to the question?
5. **ACTIONABILITY** (0.0-1.0): Does it provide actionable insights or next steps?

**Required Output Format:**

```json
{{
  "overall_score": 0.0,
  "dimension_scores": [
    {{
      "dimension": "accuracy",
      "score": 0.0,
      "explanation": "Brief explanation of the score",
      "suggestions": ["Specific improvement suggestion 1", "Suggestion 2"]
    }},
    {{
      "dimension": "completeness",
      "score": 0.0,
      "explanation": "Brief explanation of the score",
      "suggestions": ["Specific improvement suggestion 1", "Suggestion 2"]
    }},
    {{
      "dimension": "clarity",
      "score": 0.0,
      "explanation": "Brief explanation of the score",
      "suggestions": ["Specific improvement suggestion 1", "Suggestion 2"]
    }},
    {{
      "dimension": "relevance",
      "score": 0.0,
      "explanation": "Brief explanation of the score",
      "suggestions": ["Specific improvement suggestion 1", "Suggestion 2"]
    }},
    {{
      "dimension": "actionability",
      "score": 0.0,
      "explanation": "Brief explanation of the score",
      "suggestions": ["Specific improvement suggestion 1", "Suggestion 2"]
    }}
  ],
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "improvement_suggestions": ["Overall improvement 1", "Overall improvement 2"],
  "confidence": 0.0
}}
```

Provide your evaluation in the exact JSON format above. Be specific and constructive in your feedback.
"""
    
    def _create_improvement_prompt(
        self, 
        user_query: str, 
        original_response: str, 
        evaluation: ResponseEvaluation
    ) -> str:
        """Create prompt for generating improved response."""
        
        weaknesses_text = "\n- ".join([""] + evaluation.weaknesses) if evaluation.weaknesses else "None identified"
        suggestions_text = "\n- ".join([""] + evaluation.improvement_suggestions) if evaluation.improvement_suggestions else "None provided"
        
        return f"""
You are an expert financial analyst tasked with improving a response to a user's question.

**Original User Question:**
{user_query}

**Original Response:**
{original_response}

**Quality Issues Identified:**
{weaknesses_text}

**Improvement Suggestions:**
{suggestions_text}

**Your Task:**
Rewrite the response to address the identified issues while maintaining all the good aspects. Focus on:

1. Fixing any accuracy or completeness issues
2. Improving clarity and structure
3. Adding more actionable insights
4. Enhancing professional presentation
5. Including appropriate caveats and context

**Guidelines:**
- Keep all correct information from the original
- Add missing context or explanations
- Use clear, professional financial language
- Structure the response logically
- Include specific recommendations when appropriate
- Maintain appropriate confidence levels

Provide the improved response:
"""
    
    def _parse_evaluation_response(self, evaluation_text: str) -> ResponseEvaluation:
        """Parse the LLM evaluation response into structured format."""
        
        try:
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', evaluation_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_str = evaluation_text.strip()
            
            eval_data = json.loads(json_str)
            
            # Parse dimension scores
            dimension_scores = []
            for dim_data in eval_data.get("dimension_scores", []):
                dimension = QualityDimension(dim_data["dimension"])
                score = QualityScore(
                    dimension=dimension,
                    score=float(dim_data["score"]),
                    explanation=dim_data["explanation"],
                    suggestions=dim_data.get("suggestions", [])
                )
                dimension_scores.append(score)
            
            return ResponseEvaluation(
                overall_score=float(eval_data.get("overall_score", 0.0)),
                dimension_scores=dimension_scores,
                strengths=eval_data.get("strengths", []),
                weaknesses=eval_data.get("weaknesses", []),
                improvement_suggestions=eval_data.get("improvement_suggestions", []),
                confidence=float(eval_data.get("confidence", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {e}")
            return self._create_fallback_evaluation()
    
    def _create_fallback_evaluation(self) -> ResponseEvaluation:
        """Create a fallback evaluation when parsing fails."""
        
        return ResponseEvaluation(
            overall_score=0.5,
            dimension_scores=[
                QualityScore(
                    dimension=QualityDimension.ACCURACY,
                    score=0.5,
                    explanation="Unable to evaluate - parsing error",
                    suggestions=["Manual review recommended"]
                )
            ],
            strengths=["Unable to determine"],
            weaknesses=["Evaluation system error"],
            improvement_suggestions=["Manual review and improvement needed"],
            confidence=0.0
        )


def evaluate_financial_response(
    user_query: str, 
    response: str, 
    context: Optional[Dict] = None
) -> ResponseEvaluation:
    """
    Convenience function for evaluating financial responses.
    
    Args:
        user_query: The user's question
        response: The response to evaluate
        context: Additional context information
    
    Returns:
        ResponseEvaluation with quality assessment
    """
    evaluator = ResponseQualityEvaluator()
    return evaluator.evaluate_response(user_query, response, context)
