from langchain_openai import ChatOpenAI
from flask import current_app
from typing import Dict, Optional
import json
from app import logger

class JudgeAgent:
    """
    LLM-as-Judge agent that evaluates and improves responses
    """
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.1,
            api_key=current_app.config.get("OPENAI_API_KEY")
        )
    
    async def evaluate_response(self, 
                              user_query: str, 
                              sql_query: str,
                              sql_results: str,
                              analysis: str,
                              business_insights: str) -> Dict[str, str]:
        """
        Evaluate and potentially improve the response
        """
        evaluation_prompt = f"""You are a strict judge evaluating the quality of a financial analysis response.
Analyze the following components and provide scores and feedback in valid JSON format.

USER QUERY:
{user_query}

SQL QUERY:
{sql_query}

RESULTS:
{sql_results}

ANALYSIS:
{analysis}

BUSINESS INSIGHTS:
{business_insights}

Evaluate based on:
1. SQL Query Quality (0-10)
2. Analysis Quality (0-10)
3. Business Insights Quality (0-10)

Your response MUST be in the following JSON format, wrapped in a code block:
```json
{{
    "query_score": <score>,
    "analysis_score": <score>,
    "insights_score": <score>,
    "needs_improvement": <true/false>,
    "improved_response": "<improved version if needed>",
    "explanation": "<clear explanation of scores and suggested improvements>"
}}
```

Rules:
- All scores must be integers between 0 and 10
- needs_improvement must be a boolean
- improved_response should be empty string if no improvement needed
- explanation should be clear and constructive
- ALWAYS wrap the JSON in ```json code blocks
- Ensure all JSON strings are properly escaped
- Do not include any text outside the JSON code block

Example of valid response:
```json
{{
    "query_score": 8,
    "analysis_score": 7,
    "insights_score": 9,
    "needs_improvement": false,
    "improved_response": "",
    "explanation": "The SQL query is well-structured and efficient. The analysis covers key points but could use more depth. Business insights are excellent and actionable."
}}
```

YOUR EVALUATION (remember to wrap in ```json):"""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": evaluation_prompt}])
            logger.debug(f"Raw judge response: {response.content}")
            
            # Parse the JSON response safely
            try:
                # Try to extract JSON if it's embedded in the response
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                
                # Remove any invalid escape sequences
                content = content.replace("\\'", "'").replace('\\"', '"')
                
                evaluation = json.loads(content)
                logger.debug(f"Parsed judge evaluation: {evaluation}")
                
                # Create default evaluation if parsing fails
                default_evaluation = {
                    "query_score": 0,
                    "analysis_score": 0,
                    "insights_score": 0,
                    "needs_improvement": False,
                    "improved_response": "",
                    "explanation": "Unable to evaluate response properly."
                }
                
                # Ensure all required fields are present with correct types
                evaluation = {
                    "query_score": int(evaluation.get("query_score", default_evaluation["query_score"])),
                    "analysis_score": int(evaluation.get("analysis_score", default_evaluation["analysis_score"])),
                    "insights_score": int(evaluation.get("insights_score", default_evaluation["insights_score"])),
                    "needs_improvement": bool(evaluation.get("needs_improvement", default_evaluation["needs_improvement"])),
                    "improved_response": str(evaluation.get("improved_response", default_evaluation["improved_response"])),
                    "explanation": str(evaluation.get("explanation", default_evaluation["explanation"]))
                }
                
                return evaluation
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse judge response: {e}")
                logger.debug(f"Raw response: {response.content}")
                
                # Return a default evaluation on error
                return {
                    "query_score": 0,
                    "analysis_score": 0,
                    "insights_score": 0,
                    "needs_improvement": False,
                    "improved_response": "",
                    "explanation": f"Error evaluating response: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Error in judge evaluation: {e}")
            return {
                "query_score": 0,
                "analysis_score": 0,
                "insights_score": 0,
                "needs_improvement": False,
                "explanation": f"Error in evaluation: {str(e)}"
            }

def create_judge_agent() -> JudgeAgent:
    """Factory function to create a judge agent"""
    return JudgeAgent()
