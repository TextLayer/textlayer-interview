from typing import Dict, List, TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from flask import current_app
import json
import os

from app.services.agents.tools import text_to_sql_langchain
from app.services.agents.judge_agent import create_judge_agent
from app import logger


class AgentState(TypedDict):
    """State shared between all agents in the graph"""
    messages: Annotated[List, add_messages]
    user_query: str
    sql_query: str
    sql_results: str
    analysis: str
    business_insights: str
    current_step: str
    retry_count: int
    data_quality_check: str


class FinancialAnalysisAgent:
    """
    Multi-agent system for financial data analysis using LangGraph
    
    Agents:
    1. SQL Agent: Converts natural language to SQL
    2. Data Agent: Executes SQL and formats results
    3. Analysis Agent: Analyzes the data
    4. Business Intelligence Agent: Provides business insights
    """
    
    def __init__(self, openai_api_key: str = None, model: str = "gpt-4o-mini"):
        self.model = model
        self.openai_api_key = openai_api_key or current_app.config.get("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.openai_api_key,
            temperature=0.1
        )
        
        # Tools for the SQL agent
        self.tools = [text_to_sql_langchain]
        self.tool_node = ToolNode(self.tools)
        
        # Create judge agent
        self.judge = create_judge_agent()
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph"""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("sql_agent", self._sql_agent)
        workflow.add_node("tools", self.tool_node)
        workflow.add_node("data_agent", self._data_agent)
        workflow.add_node("analysis_agent", self._analysis_agent)
        workflow.add_node("business_intelligence_agent", self._business_intelligence_agent)
        
        # Define the flow
        workflow.add_edge(START, "sql_agent")
        workflow.add_conditional_edges(
            "sql_agent",
            self._should_use_tools,
            {
                "tools": "tools",
                "data_agent": "data_agent"
            }
        )
        workflow.add_edge("tools", "data_agent")
        
        # Add conditional edge for data_agent retry logic
        workflow.add_conditional_edges(
            "data_agent",
            self._should_retry_sql,
            {
                "retry_sql": "sql_agent",
                "continue": "analysis_agent"
            }
        )
        
        workflow.add_edge("analysis_agent", "business_intelligence_agent")
        workflow.add_edge("business_intelligence_agent", "judge_agent")
        workflow.add_edge("judge_agent", END)
        workflow.add_node("judge_agent", self._judge_agent)
        
        return workflow.compile()
    
    def _should_use_tools(self, state: AgentState) -> str:
        """Determine if tools should be used"""
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "data_agent"
    
    def _should_retry_sql(self, state: AgentState) -> str:
        """Determine if SQL should be retried based on data quality"""
        logger.info("🔄 Checking if SQL retry is needed")
        
        # Get retry count, default to 0 if not set
        retry_count = state.get("retry_count", 0)
        max_retries = 3  # Maximum number of retry attempts
        
        # Check data quality
        data_quality = state.get("data_quality_check", "unknown")
        
        logger.info(f"Data quality: {data_quality}, Retry count: {retry_count}/{max_retries}")
        
        # If data quality is poor and we haven't exceeded max retries
        if data_quality == "poor" and retry_count < max_retries:
            logger.warning(f"🔄 Retrying SQL generation (attempt {retry_count + 1}/{max_retries})")
            return "retry_sql"
        elif data_quality == "poor" and retry_count >= max_retries:
            logger.error(f"❌ Maximum retries exceeded ({max_retries}), proceeding with poor data")
            return "continue"
        else:
            logger.info("✅ Data quality acceptable, continuing to analysis")
            return "continue"
    
    async def _sql_agent(self, state: AgentState) -> Dict:
        """SQL Agent: Converts natural language to SQL queries"""
        
        retry_count = state.get("retry_count", 0)
        
        if retry_count > 0:
            logger.warning(f"🔄 SQL Agent: Retry attempt #{retry_count + 1}")
        else:
            logger.info("🔍 SQL Agent: Converting natural language to SQL")
        
        system_prompt = """You are an expert SQL generation specialist for financial data analysis with deep understanding of the database schema.

CRITICAL SCHEMA DETAILS:
======================

MAIN FACT TABLE:
- financial_data: (account_key, customer_key, product_key, time_period, version_key, time_perspective_key, amount)

DIMENSION TABLES (use these exact column names):
- account: (Key, Name, ParentId, AccountType, DebitCredit)
  * Filter AccountType = '1' for revenue analysis (NOT 'Revenue'!)
  * AccountType codes: '1'=Revenue, '0'=Cost/Expense, '3'=Other, '4'=KPI
  
- customer: (Key, Name, Channel, Location, "Sales Manager")
  * Channel: distribution channel (Online, Retail, Direct, etc.)
  * Location: geographic location
  
- product: (Key, Name, ParentId) 
  * Name contains product categories/names (NOT "Product Line")
  * ParentId for product hierarchy
  
- time: (Month, Name, Year, Quarter, StartPeriod, EndPeriod, ...)
  * Month: Primary key linking to financial_data.time_period (2018M01, 2018M02, etc.)
  * Quarter: 2018Q1, 2018Q2, etc.
  * Year: 2018, 2019, etc. (stored as VARCHAR)
  
- version: (Key, Name, VersionType)
  * VersionType: 'Actual', 'Budget', 'Forecast'

MANDATORY SQL REQUIREMENTS:
==========================
1. ALWAYS JOIN dimension tables to get descriptive names
2. For revenue queries: JOIN account table and filter AccountType = '1' (NOT 'Revenue'!)
3. Use p.Name (not p."Product Line") for product categories
4. For time filtering: use CAST(t.Year AS INTEGER) and t.Quarter columns
5. Time JOIN: JOIN time t ON fd.time_period = t.Month (NOT t.Key!)
6. Handle NULL values in window functions with NULLIF()
7. Use proper window function syntax with PARTITION BY and ORDER BY
8. Include CTEs for complex multi-step calculations
9. Add meaningful column aliases
10. Use proper JOIN syntax (avoid implicit joins)

EXAMPLE PATTERNS:
================
Revenue by Product & Channel:
SELECT p.Name as product_category, c.Channel, SUM(fd.amount) as revenue
FROM financial_data fd
JOIN product p ON fd.product_key = p.Key  
JOIN customer c ON fd.customer_key = c.Key
JOIN account a ON fd.account_key = a.Key
WHERE a.AccountType = '1'
GROUP BY p.Name, c.Channel

Growth Rate Calculation:
LAG(SUM(fd.amount)) OVER (PARTITION BY p.Name, c.Channel ORDER BY t.Year, t.Quarter)

Time Filtering (past 2 years):
WHERE CAST(t.Year AS INTEGER) >= (SELECT MAX(CAST(Year AS INTEGER)) - 1 FROM time)

Your task: Use the text_to_sql tool with this enhanced schema understanding to generate precise, executable SQL queries."""
        
        # Add retry context to the system prompt if this is a retry
        if retry_count > 0:
            system_prompt += f"""

RETRY CONTEXT:
=============
This is retry attempt #{retry_count + 1} because the previous SQL query had issues.
Please analyze the previous attempt and generate an improved SQL query that addresses potential problems:
- Check table names and column names for typos
- Verify JOIN conditions are correct
- Ensure proper filtering conditions
- Add error handling for empty results
- Consider different approaches to the same query

Previous SQL results had quality issues. Please generate a more robust query."""
        
        # Filter and clean messages for retry scenarios
        clean_messages = []
        for msg in state["messages"]:
            # Keep only HumanMessage for retries to avoid tool call conflicts
            if retry_count > 0:
                if hasattr(msg, 'type') and msg.type == 'human':
                    clean_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, dict) and msg.get("role") == "user":
                    clean_messages.append(msg)
            else:
                # First attempt: include all messages
                if hasattr(msg, 'type'):
                    clean_messages.append({"role": msg.type, "content": msg.content})
                else:
                    clean_messages.append(msg)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ] + clean_messages
        
        llm_with_tools = self.llm.bind_tools(self.tools)
        response = llm_with_tools.invoke(messages)
        
        return {
            "messages": [response],
            "current_step": "sql_generated",
            "retry_count": retry_count + 1  # Increment retry count for next iteration
        }
    
    async def _data_agent(self, state: AgentState) -> Dict:
        """Data Agent: Processes SQL results and formats data"""
        logger.info("📊 Data Agent: Processing SQL results")
        
        # Initialize or increment retry counter
        retry_count = state.get("retry_count", 0)
        if state.get("current_step") == "sql_generated":
            # First attempt or retry from SQL agent
            pass
        else:
            # This shouldn't happen but handle it gracefully
            pass
        
        sql_results = ""
        data_quality = "good"  # Default assumption
        
        for msg in state["messages"]:
            logger.debug(f"Processing message type: {type(msg)}, content preview: {str(msg)[:200]}")
            if isinstance(msg, ToolMessage):
                try:
                    tool_result = json.loads(msg.content)
                    sql_results = tool_result
                    logger.debug(f"Parsed tool result: {sql_results}")
                    break
                except:
                    sql_results = msg.content
                    logger.debug(f"Using raw tool content: {sql_results}")
        
        # Perform data quality checks
        data_quality = self._assess_data_quality(sql_results, state.get("user_query", ""))
        
        logger.info(f"Final SQL results for analysis: {str(sql_results)[:500]}")
        logger.info(f"Data quality assessment: {data_quality}")
        
        return {
            "sql_results": str(sql_results),
            "current_step": "data_processed",
            "retry_count": retry_count,
            "data_quality_check": data_quality
        }
    
    def _assess_data_quality(self, sql_results: str, user_query: str) -> str:
        """Assess the quality of SQL results to determine if retry is needed"""
        logger.info("🔍 Assessing data quality")
        
        # Convert results to string for analysis
        results_str = str(sql_results).lower()
        
        # Check for common error indicators
        error_indicators = [
            "error",
            "exception",
            "failed",
            "no such table",
            "no such column", 
            "syntax error",
            "invalid",
            "could not",
            "unable to",
            "permission denied",
            "connection failed",
            "timeout"
        ]
        
        # Check for empty or null results
        empty_indicators = [
            "[]",
            "none",
            "null",
            "no results",
            "empty",
            "no data found"
        ]
        
        # Check for SQL errors
        for indicator in error_indicators:
            if indicator in results_str:
                logger.warning(f"❌ Found error indicator: '{indicator}' in results")
                return "poor"
        
        # Check for empty results (might indicate wrong query)
        for indicator in empty_indicators:
            if indicator in results_str:
                logger.warning(f"⚠️ Found empty result indicator: '{indicator}' in results")
                # For empty results, check if the query expects data
                if self._query_expects_data(user_query):
                    logger.warning("Query expected data but got empty results - marking as poor quality")
                    return "poor"
        
        # Check if results seem too generic or unhelpful
        if len(results_str.strip()) < 20:  # Very short results might indicate problems
            logger.warning("⚠️ Results seem too short, might indicate poor query")
            return "poor"
        
        # If we made it here, data quality seems acceptable
        logger.info("✅ Data quality assessment: good")
        return "good"
    
    def _query_expects_data(self, user_query: str) -> bool:
        """Determine if the user query expects to return data"""
        query_lower = user_query.lower()
        
        # Queries that typically expect data
        data_expecting_keywords = [
            "show", "list", "find", "get", "what", "which", "how much", "how many",
            "total", "sum", "count", "average", "top", "bottom", "revenue", "sales",
            "profit", "customers", "products", "accounts"
        ]
        
        for keyword in data_expecting_keywords:
            if keyword in query_lower:
                return True
        
        return False
    
    async def _analysis_agent(self, state: AgentState) -> Dict:
        """Analysis Agent: Analyzes the data and provides statistical insights"""
        logger.info("🔬 Analysis Agent: Analyzing data patterns")
        
        analysis_prompt = f"""You are a financial data analyst. Analyze the following SQL results and provide detailed statistical analysis.

User Query: {state.get('user_query', '')}
SQL Results: {state.get('sql_results', '')}

Provide a structured analysis with these sections:

## 1. Key Statistical Findings
- Calculate totals, averages, and distributions
- Identify highest and lowest performers
- Calculate any relevant percentages or ratios

## 2. Data Patterns and Trends  
- Describe notable patterns in the data
- Identify trends, correlations, or relationships
- Point out any seasonal or cyclical patterns

## 3. Notable Observations
- Highlight unusual or interesting findings
- Call out outliers or anomalies  
- Note any data quality issues

## 4. Data Quality Assessment
- Assess completeness and accuracy
- Note any missing values or inconsistencies
- Comment on data reliability

Be specific and quantitative in your analysis. Use actual numbers from the data."""
        
        response = self.llm.invoke([{"role": "user", "content": analysis_prompt}])
        
        return {
            "analysis": response.content,
            "current_step": "analysis_complete"
        }
    
    async def _business_intelligence_agent(self, state: AgentState) -> Dict:
        """Business Intelligence Agent: Provides business insights and recommendations"""
        logger.info("💼 Business Intelligence Agent: Generating business insights")
        
        bi_prompt = f"""You are a senior business intelligence analyst specializing in financial analysis. 

User Query: {state.get('user_query', '')}
SQL Results: {state.get('sql_results', '')}
Analysis: {state.get('analysis', '')}

Provide comprehensive business insights with clear section headers:

## 1. Business Implications
- What do these numbers mean for the business?
- How does this impact the company's financial position?
- What are the immediate business consequences?

## 2. Strategic Recommendations  
- Specific actions to take based on the data
- Short-term and long-term strategic moves
- Resource allocation recommendations

## 3. Risk Assessment
- Potential risks identified from the data
- Financial vulnerabilities or concerns
- Risk mitigation strategies

## 4. Growth Opportunities
- Areas showing positive trends for investment
- Market opportunities revealed by the data
- Revenue expansion possibilities

## 5. Executive Summary
- Key takeaways for leadership
- Critical decisions that need to be made
- Priority actions and next steps

Write in executive-friendly language with specific, actionable insights backed by the data."""
        
        response = self.llm.invoke([{"role": "user", "content": bi_prompt}])
        
        # Create final response message
        final_response = f"""## Financial Analysis Results

### 📊 Data Analysis
{state.get('analysis', '')}

### 💼 Business Intelligence Insights
{response.content}

### 📈 Summary
- **Query Processed**: {state.get('user_query', '')}
- **Records Analyzed**: Based on financial database query results
- **Analysis Completeness**: Multi-dimensional financial analysis with statistical insights and business recommendations

---
*Analysis completed by TextLayer AI Financial Assistant*"""
        
        return {
            "messages": [AIMessage(content=final_response)],
            "business_insights": response.content,
            "current_step": "complete"
        }
    
    async def _judge_agent(self, state: AgentState) -> Dict:
        """Judge Agent: Evaluates and potentially improves the response"""
        logger.info("👨‍⚖️ Judge Agent: Evaluating response quality")
        
        # Extract the generated SQL query from tool messages
        sql_query = ""
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                try:
                    sql_query = msg.content
                    break
                except:
                    continue
        
        # Default evaluation response
        default_evaluation = {
            "query_score": 0,
            "analysis_score": 0,
            "insights_score": 0,
            "needs_improvement": False,
            "improved_response": "",
            "explanation": "Judge evaluation failed."
        }
        
        try:
            # Get evaluation from judge with proper error handling
            evaluation = await self.judge.evaluate_response(
                user_query=state.get("user_query", ""),
                sql_query=sql_query,
                sql_results=state.get("sql_results", ""),
                analysis=state.get("analysis", ""),
                business_insights=state.get("business_insights", "")
            )
            
            # Ensure we have a valid evaluation dictionary
            if not evaluation or not isinstance(evaluation, dict):
                logger.error("Judge returned invalid evaluation format")
                evaluation = default_evaluation.copy()
                evaluation["explanation"] = "Judge returned invalid response format"
            
            # Get the original response if available
            original_response = ""
            for msg in reversed(state.get("messages", [])):
                if isinstance(msg, AIMessage):
                    original_response = msg.content
                    break
            
            # Use improved response only if we're confident it's better
            final_response = original_response
            if (evaluation.get("needs_improvement") and 
                evaluation.get("improved_response") and 
                isinstance(evaluation.get("improved_response"), str)):
                final_response = evaluation["improved_response"]
            
            # Ensure we have valid numeric scores
            scores = []
            for score_key in ['query_score', 'analysis_score', 'insights_score']:
                try:
                    score = float(evaluation.get(score_key, 0))
                    scores.append(min(max(score, 0), 10))  # Clamp between 0 and 10
                except (ValueError, TypeError):
                    scores.append(0)
                    logger.warning(f"Invalid {score_key}: {evaluation.get(score_key)}")
            
            average_score = sum(scores) / len(scores) if scores else 0
            
        except Exception as e:
            logger.error(f"Error in judge evaluation: {e}")
            evaluation = default_evaluation.copy()
            evaluation["explanation"] = f"Judge evaluation failed: {str(e)}"
            average_score = 0
            final_response = state.get("messages", [])[-1].content if state.get("messages") else "Analysis failed."
        
        # Format the final message with proper error handling
        try:
            # Extract the original detailed analysis response
            original_analysis_response = ""
            for msg in reversed(state.get("messages", [])):
                if isinstance(msg, AIMessage) and "## Financial Analysis Results" in msg.content:
                    original_analysis_response = msg.content
                    break
            
            # If we don't have the original response, use what we have
            if not original_analysis_response:
                original_analysis_response = final_response
            
            # Create judge summary to prepend to the original response
            judge_summary = f"""## Financial Analysis Results

{'🌟 HIGH QUALITY RESPONSE 🌟' if average_score >= 8 else '📊 Analysis Results'}

### Quality Assessment
- SQL Query Score: {evaluation.get('query_score', 0)}/10
- Analysis Score: {evaluation.get('analysis_score', 0)}/10
- Business Insights Score: {evaluation.get('insights_score', 0)}/10
- Overall Score: {average_score:.1f}/10

### Judge's Feedback
{evaluation.get('explanation', 'No feedback provided.')}

---"""

            # Extract just the data analysis and business intelligence sections from the original response
            clean_original = original_analysis_response
            
            # Remove the header if present
            if clean_original.startswith("## Financial Analysis Results"):
                lines = clean_original.split('\n')
                # Find the first content line after the header
                content_start = 1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() and not line.startswith('#'):
                        content_start = i
                        break
                clean_original = '\n'.join(lines[content_start:])
            
            # Ensure we keep the complete analysis and business insights
            if "### 📊 Data Analysis" in clean_original and "### 💼 Business Intelligence Insights" in clean_original:
                # We have the full structured response, use it as is
                judge_message = f"{judge_summary}\n{clean_original}"
            else:
                # Fallback: reconstruct from state components
                analysis_section = f"### 📊 Data Analysis\n{state.get('analysis', 'Analysis not available')}"
                bi_section = f"### 💼 Business Intelligence Insights\n{state.get('business_insights', 'Business insights not available')}"
                summary_section = f"""### 📈 Summary
- **Query Processed**: {state.get('user_query', '')}
- **Records Analyzed**: Based on financial database query results
- **Analysis Completeness**: Multi-dimensional financial analysis with statistical insights and business recommendations

---
*Analysis completed by TextLayer AI Financial Assistant*"""
                
                judge_message = f"{judge_summary}\n{analysis_section}\n\n{bi_section}\n\n{summary_section}"
            
        except Exception as e:
            logger.error(f"Error formatting judge message: {e}")
            # Fallback to original response if formatting fails
            judge_message = final_response
        
        return {
            "messages": [AIMessage(content=judge_message)],
            "current_step": "judged"
        }
    
    async def process_query(self, user_query: str) -> str:
        """Process a user query through the multi-agent system"""
        logger.info(f"🚀 Starting multi-agent financial analysis for: {user_query}")
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "user_query": user_query,
            "current_step": "started",
            "retry_count": 0,
            "data_quality_check": "unknown"
        }
        
        try:
            # Run the graph
            result = await self.graph.ainvoke(initial_state)
            
            # Extract the final response
            final_message = result["messages"][-1]
            return final_message.content
            
        except Exception as e:
            logger.error(f"Error in multi-agent processing: {e}")
            return f"I encountered an error while processing your financial query: {str(e)}"


# Factory function for easy usage
def create_financial_analysis_agent() -> FinancialAnalysisAgent:
    """Create and return a configured FinancialAnalysisAgent"""
    return FinancialAnalysisAgent()
