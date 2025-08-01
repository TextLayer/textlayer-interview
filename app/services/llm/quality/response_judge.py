"""
LLM-as-a-Judge service for evaluating and improving response quality.
"""
from typing import Dict, List, Optional, Tuple
from flask import current_app
from langfuse.decorators import observe

from app import logger
from app.services.llm.session import LLMSession


class ResponseQualityJudge:
    """
    Service for evaluating response quality using LLM-as-a-Judge methodology.
    """
    
    def __init__(self):
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
    
    @observe()
    def evaluate_response(
        self, 
        user_query: str, 
        assistant_response: str, 
        context: Optional[str] = None
    ) -> Dict:
        """
        Evaluate the quality of an assistant response.
        
        Args:
            user_query: Original user question
            assistant_response: Assistant's response to evaluate
            context: Additional context (schema, data, etc.)
            
        Returns:
            Dict with evaluation results and suggestions
        """
        
        evaluation_prompt = self._build_evaluation_prompt(
            user_query, assistant_response, context
        )
        
        try:
            response = self.llm_session.chat(messages=[
                {"role": "user", "content": evaluation_prompt}
            ])
            
            evaluation_text = response.choices[0].message.content
            return self._parse_evaluation_response(evaluation_text)
            
        except Exception as e:
            logger.error(f"Error in response evaluation: {e}")
            return {
                "overall_score": 5,  # Neutral score on error
                "criteria_scores": {},
                "strengths": [],
                "weaknesses": [],
                "suggestions": ["Evaluation failed - manual review recommended"],
                "needs_improvement": False
            }
    
    def _build_evaluation_prompt(
        self, 
        user_query: str, 
        assistant_response: str, 
        context: Optional[str]
    ) -> str:
        """Build the evaluation prompt for the judge LLM."""
        
        prompt = f"""
You are an expert evaluator for financial data analysis AI responses. Evaluate the following assistant response for quality and usefulness.

## User Query:
{user_query}

## Assistant Response:
{assistant_response}
"""
        
        if context:
            prompt += f"\n## Available Context:\n{context}\n"
        
        prompt += """
## Evaluation Criteria:
Rate each criterion on a scale of 1-10 (1=Poor, 10=Excellent):

1. **Accuracy**: Are the facts, calculations, and SQL queries correct?
2. **Completeness**: Does the response fully address the user's question?
3. **Clarity**: Is the response clear, well-structured, and easy to understand?
4. **Relevance**: Is the information provided relevant to the financial domain and user's needs?
5. **Actionability**: Does the response provide actionable insights or next steps?
6. **Data Quality**: Are data limitations and quality issues appropriately addressed?
7. **Professional Tone**: Is the response professional and appropriate for business use?

## Response Format:
Provide your evaluation in the following JSON format:

```json
{
    "overall_score": <1-10>,
    "criteria_scores": {
        "accuracy": <1-10>,
        "completeness": <1-10>,
        "clarity": <1-10>,
        "relevance": <1-10>,
        "actionability": <1-10>,
        "data_quality": <1-10>,
        "professional_tone": <1-10>
    },
    "strengths": [
        "List of specific strengths in the response"
    ],
    "weaknesses": [
        "List of specific weaknesses or areas for improvement"
    ],
    "suggestions": [
        "Specific suggestions for improving the response"
    ],
    "needs_improvement": <true/false>
}
```

Focus on providing constructive, specific feedback that would help improve future responses.
"""
        
        return prompt
    
    def _parse_evaluation_response(self, evaluation_text: str) -> Dict:
        """Parse the evaluation response from the judge LLM."""
        
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Find JSON block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', evaluation_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                evaluation = json.loads(json_str)
                
                # Validate required fields
                required_fields = [
                    'overall_score', 'criteria_scores', 'strengths', 
                    'weaknesses', 'suggestions', 'needs_improvement'
                ]
                
                for field in required_fields:
                    if field not in evaluation:
                        evaluation[field] = self._get_default_value(field)
                
                return evaluation
            else:
                logger.warning("Could not parse JSON from evaluation response")
                return self._get_default_evaluation()
                
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {e}")
            return self._get_default_evaluation()
    
    def _get_default_value(self, field: str):
        """Get default value for missing evaluation fields."""
        defaults = {
            'overall_score': 5,
            'criteria_scores': {
                'accuracy': 5, 'completeness': 5, 'clarity': 5,
                'relevance': 5, 'actionability': 5, 'data_quality': 5,
                'professional_tone': 5
            },
            'strengths': ["Response provided"],
            'weaknesses': ["Evaluation incomplete"],
            'suggestions': ["Manual review recommended"],
            'needs_improvement': False
        }
        return defaults.get(field, None)
    
    def _get_default_evaluation(self) -> Dict:
        """Get default evaluation when parsing fails."""
        return {
            "overall_score": 5,
            "criteria_scores": {
                'accuracy': 5, 'completeness': 5, 'clarity': 5,
                'relevance': 5, 'actionability': 5, 'data_quality': 5,
                'professional_tone': 5
            },
            "strengths": ["Response provided"],
            "weaknesses": ["Evaluation failed"],
            "suggestions": ["Manual review recommended"],
            "needs_improvement": False
        }
    
    @observe()
    def improve_response(
        self, 
        user_query: str, 
        original_response: str, 
        evaluation: Dict,
        context: Optional[str] = None
    ) -> str:
        """
        Generate an improved response based on evaluation feedback.
        
        Args:
            user_query: Original user question
            original_response: Original assistant response
            evaluation: Evaluation results from evaluate_response
            context: Additional context
            
        Returns:
            Improved response string
        """
        
        if not evaluation.get('needs_improvement', False):
            return original_response
        
        improvement_prompt = self._build_improvement_prompt(
            user_query, original_response, evaluation, context
        )
        
        try:
            response = self.llm_session.chat(messages=[
                {"role": "user", "content": improvement_prompt}
            ])
            
            improved_response = response.choices[0].message.content
            return improved_response
            
        except Exception as e:
            logger.error(f"Error improving response: {e}")
            return original_response
    
    def _build_improvement_prompt(
        self, 
        user_query: str, 
        original_response: str, 
        evaluation: Dict,
        context: Optional[str]
    ) -> str:
        """Build prompt for generating improved response."""
        
        weaknesses = evaluation.get('weaknesses', [])
        suggestions = evaluation.get('suggestions', [])
        
        prompt = f"""
You are a financial data analysis expert. Improve the following response based on the evaluation feedback.

## User Query:
{user_query}

## Original Response:
{original_response}

## Identified Weaknesses:
{chr(10).join(f"- {weakness}" for weakness in weaknesses)}

## Improvement Suggestions:
{chr(10).join(f"- {suggestion}" for suggestion in suggestions)}
"""
        
        if context:
            prompt += f"\n## Available Context:\n{context}\n"
        
        prompt += """
## Instructions:
1. Address all identified weaknesses
2. Implement the improvement suggestions
3. Maintain accuracy and professional tone
4. Ensure the response is complete and actionable
5. Keep the financial domain focus
6. Preserve any correct information from the original response

## Improved Response:
"""
        
        return prompt
    
    def get_quality_summary(self, evaluation: Dict) -> str:
        """
        Generate a human-readable quality summary.
        
        Args:
            evaluation: Evaluation results
            
        Returns:
            Formatted quality summary string
        """
        
        overall_score = evaluation.get('overall_score', 5)
        criteria_scores = evaluation.get('criteria_scores', {})
        
        # Determine quality level
        if overall_score >= 8:
            quality_level = "Excellent"
            emoji = "🟢"
        elif overall_score >= 6:
            quality_level = "Good"
            emoji = "🟡"
        else:
            quality_level = "Needs Improvement"
            emoji = "🔴"
        
        summary_parts = [
            f"{emoji} **Response Quality: {quality_level}** (Score: {overall_score}/10)",
            ""
        ]
        
        # Add criteria breakdown
        if criteria_scores:
            summary_parts.append("**Detailed Scores:**")
            for criterion, score in criteria_scores.items():
                criterion_name = criterion.replace('_', ' ').title()
                summary_parts.append(f"- {criterion_name}: {score}/10")
            summary_parts.append("")
        
        # Add strengths
        strengths = evaluation.get('strengths', [])
        if strengths:
            summary_parts.append("**Strengths:**")
            summary_parts.extend(f"✅ {strength}" for strength in strengths)
            summary_parts.append("")
        
        # Add areas for improvement
        weaknesses = evaluation.get('weaknesses', [])
        if weaknesses:
            summary_parts.append("**Areas for Improvement:**")
            summary_parts.extend(f"⚠️ {weakness}" for weakness in weaknesses)
            summary_parts.append("")
        
        return "\n".join(summary_parts)
