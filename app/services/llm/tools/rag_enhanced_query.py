from app.utils.langfuse_compat import observe
from vaul import tool_call
from typing import Optional, Dict, Any
import json

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.rag.faiss_knowledge_base import get_faiss_financial_knowledge_base
from app.services.llm.tools.text_to_sql import (
    _format_financial_result, 
    _format_error_response, 
    _format_empty_result,
    _check_data_quality
)


@tool_call
@observe
def rag_enhanced_financial_query(
    user_question: str, 
    sql_query: str,
    include_context: bool = True
) -> str:
    """
    Execute a financial data query with RAG-enhanced context and insights.
    
    This tool combines SQL query execution with relevant financial knowledge
    to provide comprehensive, contextual responses.
    
    Args:
        user_question: The user's original natural language question
        sql_query: The SQL query to execute against the financial database
        include_context: Whether to include relevant financial context
    
    Returns:
        Enhanced response with data results and contextual financial insights
    """
    
    logger.info(f"Executing RAG-enhanced query for: {user_question}")
    logger.info(f"SQL Query: {sql_query}")
    
    try:
        # Get the FAISS knowledge base
        knowledge_base = get_faiss_financial_knowledge_base()
        
        # Execute the SQL query
        datastore = DuckDBDatastore(database="app/data/data.db")
        result = datastore.execute(sql_query)
        
        # Get relevant financial context with references
        contextual_knowledge = ""
        knowledge_sources = []
        if include_context:
            context_result = knowledge_base.get_contextual_knowledge_with_sources(
                user_question, sql_query
            )
            logger.info(f"Context result type: {type(context_result)}")
            if isinstance(context_result, tuple):
                contextual_knowledge, knowledge_sources = context_result
                logger.info(f"Got {len(knowledge_sources)} knowledge sources")
                logger.info(f"Knowledge sources: {knowledge_sources}")
            else:
                # Fallback for existing implementation
                contextual_knowledge = context_result
                knowledge_sources = []
                logger.info("Using fallback - no sources available")
        
        # Process the query result
        if result is None or result.empty:
            base_response = _format_empty_result(sql_query)
        else:
            # Check for data quality issues
            quality_warnings = _check_data_quality(result)
            
            # Format the result with financial context
            base_response = _format_financial_result(result, sql_query)
            
            # Add quality warnings if any
            if quality_warnings:
                base_response += f"\n\n**Data Quality Notes:**\n{quality_warnings}"
        
        # Enhance the response with RAG context and references
        enhanced_response = _enhance_response_with_context(
            user_question=user_question,
            base_response=base_response,
            contextual_knowledge=contextual_knowledge,
            knowledge_sources=knowledge_sources,
            query_result=result if result is not None and not result.empty else None
        )
        
        return enhanced_response
        
    except Exception as e:
        logger.error(f"Error in RAG-enhanced query: {e}")
        return _format_error_response(sql_query, str(e))


def _enhance_response_with_context(
    user_question: str,
    base_response: str,
    contextual_knowledge: str,
    knowledge_sources: list = None,
    query_result: Optional[Any] = None
) -> str:
    """
    Enhance the base response with contextual knowledge and insights.
    
    Args:
        user_question: Original user question
        base_response: Base SQL query response
        contextual_knowledge: Relevant financial knowledge
        knowledge_sources: List of knowledge sources for references
        query_result: DataFrame with query results (if any)
    
    Returns:
        Enhanced response with context and insights including references
    """
    
    enhanced_response = base_response
    
    # Add contextual knowledge if available
    if contextual_knowledge:
        enhanced_response += f"\n\n{contextual_knowledge}"
    
    # Add domain-specific insights based on the query type
    insights = _generate_domain_insights(user_question, query_result)
    if insights:
        enhanced_response += f"\n\n## Financial Analysis Insights:\n\n{insights}"
    
    # Add actionable recommendations
    recommendations = _generate_recommendations(user_question, query_result)
    if recommendations:
        enhanced_response += f"\n\n## Recommendations:\n\n{recommendations}"
    
    # Add references section if knowledge sources are available
    if knowledge_sources and len(knowledge_sources) > 0:
        logger.info(f"Adding {len(knowledge_sources)} references to response")
        enhanced_response += "\n\n## References:\n\n"
        for i, source in enumerate(knowledge_sources, 1):
            if isinstance(source, dict):
                title = source.get('title', 'Unknown Source')
                description = source.get('description', '')
                url = source.get('url', '')
                
                enhanced_response += f"[{i}] **{title}**"
                if description:
                    enhanced_response += f" - {description}"
                if url:
                    enhanced_response += f" ([Link]({url}))"
                enhanced_response += "\n\n"
        logger.info(f"References section added to response. Response length: {len(enhanced_response)}")
    else:
        logger.warning(f"No knowledge sources available for references. Sources: {knowledge_sources}")
    
    return enhanced_response


def _generate_domain_insights(user_question: str, query_result: Optional[Any]) -> str:
    """Generate domain-specific financial insights based on the query."""
    
    if query_result is None or query_result.empty:
        return ""
    
    insights = []
    question_lower = user_question.lower()
    
    # Trend analysis insights
    if any(term in question_lower for term in ['trend', 'over time', 'growth', 'change']):
        insights.append(
            "📈 **Trend Analysis**: When analyzing trends, consider seasonal patterns, "
            "market cycles, and external factors that might influence the data. "
            "Look for consistent patterns and identify any anomalies that might require further investigation."
        )
    
    # Ratio analysis insights
    if any(term in question_lower for term in ['ratio', 'margin', 'percentage', 'rate']):
        insights.append(
            "📊 **Ratio Analysis**: Financial ratios are most meaningful when compared to "
            "industry benchmarks, historical performance, or peer companies. "
            "Consider the business context and industry norms when interpreting these metrics."
        )
    
    # Risk analysis insights
    if any(term in question_lower for term in ['risk', 'volatility', 'variance', 'deviation']):
        insights.append(
            "⚠️ **Risk Assessment**: High volatility may indicate higher risk but also potential "
            "for higher returns. Consider the risk-return tradeoff and ensure proper "
            "diversification strategies are in place."
        )
    
    # Performance analysis insights
    if any(term in question_lower for term in ['performance', 'return', 'profit', 'revenue']):
        insights.append(
            "💰 **Performance Evaluation**: Strong performance metrics should be sustainable "
            "and supported by solid business fundamentals. Look for consistency across "
            "multiple periods and compare against relevant benchmarks."
        )
    
    # Portfolio analysis insights
    if any(term in question_lower for term in ['portfolio', 'allocation', 'diversification']):
        insights.append(
            "🎯 **Portfolio Considerations**: Effective portfolio management requires balancing "
            "risk and return across different asset classes, sectors, and geographies. "
            "Regular rebalancing and monitoring are essential for maintaining optimal allocation."
        )
    
    return "\n\n".join(insights)


def _generate_recommendations(user_question: str, query_result: Optional[Any]) -> str:
    """Generate actionable recommendations based on the analysis."""
    
    if query_result is None or query_result.empty:
        return """
- Verify the query parameters and date ranges
- Check if the data exists for the specified criteria
- Consider broadening the search parameters
- Review the database schema for available data
"""
    
    recommendations = []
    question_lower = user_question.lower()
    
    # Data-driven recommendations based on query type
    if any(term in question_lower for term in ['compare', 'comparison', 'vs', 'versus']):
        recommendations.extend([
            "📋 **Next Steps for Comparison Analysis**:",
            "- Perform statistical significance tests to validate differences",
            "- Consider additional factors that might explain variations",
            "- Analyze the time periods to ensure fair comparison",
            "- Look into qualitative factors that numbers might not capture"
        ])
    
    if any(term in question_lower for term in ['forecast', 'predict', 'future', 'projection']):
        recommendations.extend([
            "🔮 **Forecasting Considerations**:",
            "- Use multiple forecasting methods for validation",
            "- Consider external factors and market conditions",
            "- Establish confidence intervals for predictions",
            "- Regularly update forecasts with new data"
        ])
    
    if any(term in question_lower for term in ['optimize', 'improve', 'enhance']):
        recommendations.extend([
            "⚡ **Optimization Strategies**:",
            "- Identify key performance drivers from the data",
            "- Test different scenarios and sensitivity analysis",
            "- Consider implementation costs and feasibility",
            "- Monitor results and adjust strategies accordingly"
        ])
    
    # General recommendations if no specific pattern is detected
    if not recommendations:
        recommendations.extend([
            "📈 **General Recommendations**:",
            "- Monitor these metrics regularly for trend identification",
            "- Set up alerts for significant changes or thresholds",
            "- Consider additional data sources for comprehensive analysis",
            "- Document assumptions and methodology for future reference"
        ])
    
    return "\n".join(recommendations)

# Removed get_financial_context tool to prevent confusion
# All financial concept questions should use rag_enhanced_financial_query instead
