import json
from typing import Dict, List

from flask import current_app
from langfuse.decorators import observe

from app import logger
from app.core.commands import ReadCommand
from app.errors import ValidationException
from app.services.llm.session import LLMSession


class LLMJudgeCommand(ReadCommand):
    """
    LLM-as-a-Judge command to evaluate and improve response quality.
    """
    def __init__(self, original_messages: List[Dict[str, str]],
                 response_messages: List[Dict[str, str]]) -> None:
        self.original_messages = original_messages
        self.response_messages = response_messages
        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )

    def validate(self) -> None:
        """
        Validate the command.
        """
        if not self.original_messages:
            raise ValidationException("Original messages are required.")
        if not self.response_messages:
            raise ValidationException("Response messages are required.")
        return True

    def execute(self) -> List[Dict[str, str]]:
        """
        Execute the LLM-as-a-Judge evaluation.
        """
        logger.debug("Starting LLM-as-a-Judge evaluation")

        self.validate()

        # Extract the assistant's response
        assistant_response = None
        for msg in self.response_messages:
            if msg.get('role') == 'assistant':
                assistant_response = msg
                break

        if not assistant_response:
            logger.warning("No assistant response found for evaluation")
            return self.response_messages

        # Get the original user query
        user_query = None
        for msg in reversed(self.original_messages):
            if msg.get('role') == 'user':
                user_query = msg.get('content', '')
                break

        if not user_query:
            logger.warning("No user query found for evaluation")
            return self.response_messages

        # Create evaluation prompt
        evaluation_messages = self.prepare_evaluation_messages(
            user_query,
            assistant_response.get('content', '')
        )

        try:
            # Get judge evaluation
            judge_response = self.llm_session.chat(
                messages=evaluation_messages,
                max_tokens=2000,
                temperature=0.0  # Use deterministic evaluation
            )

            if (not judge_response.choices or
                len(judge_response.choices) == 0):
                logger.warning("Invalid judge response structure")
                return self.response_messages

            judge_content = judge_response.choices[0].message.content or ""

            # Parse judge evaluation
            evaluation = self.parse_judge_evaluation(judge_content)

            # If quality is low, try to improve the response
            if evaluation.get('needs_improvement', False):
                logger.info("LLM Judge detected response needs improvement")
                improved_response = self.improve_response(
                    user_query,
                    assistant_response.get('content', ''),
                    evaluation.get('suggestions', '')
                )

                if improved_response:
                    # Replace the assistant response with improved version
                    updated_messages = []
                    for msg in self.response_messages:
                        if (msg.get('role') == 'assistant' and
                            msg.get('id') == assistant_response.get('id')):
                            # Update the response with improved content
                            updated_msg = msg.copy()
                            updated_msg['content'] = improved_response
                            updated_msg['improved_by_judge'] = True
                            updated_msg['original_content'] = (
                                assistant_response.get('content', '')
                            )
                            updated_msg['judge_evaluation'] = evaluation
                            updated_messages.append(updated_msg)
                        else:
                            updated_messages.append(msg)

                    logger.info("Response improved by LLM Judge")
                    return updated_messages
            else:
                logger.debug("LLM Judge approved response quality")
                # Add evaluation metadata to the response
                updated_messages = []
                for msg in self.response_messages:
                    if (msg.get('role') == 'assistant' and
                        msg.get('id') == assistant_response.get('id')):
                        updated_msg = msg.copy()
                        updated_msg['judge_evaluation'] = evaluation
                        updated_messages.append(updated_msg)
                    else:
                        updated_messages.append(msg)
                return updated_messages

        except Exception as e:
            logger.error(f"Error in LLM Judge evaluation: {e}")
            # Return original response if judge fails
            return self.response_messages

        return self.response_messages

    @observe()
    def prepare_evaluation_messages(self, user_query: str,
                                   assistant_response: str) -> List[Dict[str, str]]:
        """
        Prepare messages for judge evaluation.
        """
        system_prompt = """You are an expert evaluator for AI responses to financial data queries. Your task is to evaluate the quality of AI responses and determine if they need improvement.

Evaluate the response based on these criteria:
1. **Accuracy**: Is the response factually correct and based on available data?
2. **Completeness**: Does it fully address the user's question?
3. **Clarity**: Is the response clear and easy to understand?
4. **SQL Quality**: If SQL is involved, is it correct and efficient?
5. **Data Presentation**: Are results well-formatted and interpretable?

Respond in JSON format with:
{
    "quality_score": 1-10,
    "needs_improvement": true/false,
    "strengths": ["list of strengths"],
    "weaknesses": ["list of weaknesses"],
    "suggestions": "specific suggestions for improvement"
}

A score of 7+ is considered good quality. Scores below 7 need improvement."""

        evaluation_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Please evaluate this AI response to a financial data query:

**User Query:**
{user_query}

**AI Response:**
{assistant_response}

Provide your evaluation in the specified JSON format."""}
        ]

        return evaluation_messages

    @observe()
    def parse_judge_evaluation(self, judge_content: str) -> Dict:
        """
        Parse the judge's evaluation response.
        """
        try:
            # Try to extract JSON from the response
            start_idx = judge_content.find('{')
            end_idx = judge_content.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = judge_content[start_idx:end_idx]
                evaluation = json.loads(json_str)

                # Validate required fields
                if 'quality_score' not in evaluation:
                    evaluation['quality_score'] = 5
                if 'needs_improvement' not in evaluation:
                    evaluation['needs_improvement'] = (
                        evaluation.get('quality_score', 5) < 7
                    )

                return evaluation
            else:
                # Fallback parsing
                return {
                    'quality_score': 7,
                    'needs_improvement': False,
                    'strengths': ['Response provided'],
                    'weaknesses': [],
                    'suggestions': ''
                }

        except json.JSONDecodeError:
            logger.warning("Failed to parse judge evaluation as JSON")
            # Simple heuristic evaluation
            content_lower = judge_content.lower()
            needs_improvement = any(word in content_lower for word in
                                   ['improve', 'incorrect', 'missing',
                                    'unclear', 'error'])

            return {
                'quality_score': 5 if needs_improvement else 8,
                'needs_improvement': needs_improvement,
                'strengths': ['Response provided'],
                'weaknesses': ['Could not parse detailed evaluation'],
                'suggestions': judge_content[:500]  # First 500 chars
            }

    @observe()
    def improve_response(self, user_query: str, original_response: str,
                        suggestions: str) -> str:
        """
        Generate an improved response based on judge feedback.
        """
        try:
            improvement_messages = [
                {
                    "role": "system",
                    "content": """You are an expert AI assistant specializing in financial data analysis.
Your task is to improve an existing response based on feedback from an evaluation.

Provide ONLY the improved response content. Do not repeat the user's question, do not add any prefixes or headers. Just provide the direct, improved answer that addresses the feedback while maintaining accuracy and clarity."""
                },
                {
                    "role": "user",
                    "content": f"""
Please improve this response to the user query: "{user_query}"

Current response:
{original_response}

Feedback for improvement:
{suggestions}

Provide ONLY the improved response content. Do not repeat the query or add any prefixes. Just give the direct, improved answer that addresses the feedback."""
                }
            ]

            improvement_response = self.llm_session.chat(
                messages=improvement_messages,
                max_tokens=4000,
                temperature=0.2
            )

            if (improvement_response.choices and
                len(improvement_response.choices) > 0):
                improved_content = (
                    improvement_response.choices[0].message.content
                )
                if improved_content and len(improved_content.strip()) > 0:
                    return improved_content.strip()

        except Exception as e:
            logger.error(f"Error improving response: {e}")

        return None