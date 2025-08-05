from typing import List, Dict, Optional, Tuple
import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import faiss
import logging

from app import logger


@dataclass
class KnowledgeItem:
    """A single item in the financial knowledge base."""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    relevance_score: float = 0.0


class FinancialKnowledgeBase:
    """
    Advanced RAG knowledge base using FAISS vector database with sentence transformers
    for semantic search of financial concepts, definitions, and best practices.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = "app/data/rag_cache"):
        """
        Initialize FAISS-based knowledge base with sentence transformer embeddings.
        
        Args:
            model_name: Sentence transformer model for embeddings
            cache_dir: Directory to cache embeddings and FAISS index
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.embeddings_file = os.path.join(cache_dir, "embeddings.pkl")
        self.index_file = os.path.join(cache_dir, "faiss.index")
        self.knowledge_file = os.path.join(cache_dir, "knowledge_items.pkl")
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize sentence transformer model
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.encoder = SentenceTransformer(model_name)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        # Initialize FAISS index and knowledge items
        self.faiss_index = None
        self.knowledge_items: List[KnowledgeItem] = []
        
        # Load or create knowledge base
        self._initialize_knowledge_base()
    
    def __init__(self, knowledge_file: Optional[str] = None):
        self.knowledge_items: List[KnowledgeItem] = []
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.knowledge_vectors = None
        self.is_initialized = False
        
        # Load knowledge base
        if knowledge_file and os.path.exists(knowledge_file):
            self.load_knowledge_base(knowledge_file)
        else:
            self._create_default_knowledge_base()
        
        self._build_search_index()
    
    def _create_default_knowledge_base(self):
        """Create a default financial knowledge base with common concepts."""
        
        default_knowledge = [
            {
                "id": "financial_ratios_overview",
                "title": "Financial Ratios Overview",
                "content": """Financial ratios are quantitative measures used to evaluate a company's financial performance and health. Key categories include:

1. **Liquidity Ratios**: Measure ability to meet short-term obligations
   - Current Ratio = Current Assets / Current Liabilities
   - Quick Ratio = (Current Assets - Inventory) / Current Liabilities
   - Cash Ratio = Cash and Cash Equivalents / Current Liabilities

2. **Profitability Ratios**: Measure ability to generate profits
   - Gross Profit Margin = (Revenue - COGS) / Revenue
   - Net Profit Margin = Net Income / Revenue
   - Return on Assets (ROA) = Net Income / Total Assets
   - Return on Equity (ROE) = Net Income / Shareholders' Equity

3. **Leverage Ratios**: Measure debt levels and financial risk
   - Debt-to-Equity = Total Debt / Total Equity
   - Debt-to-Assets = Total Debt / Total Assets
   - Interest Coverage = EBIT / Interest Expense

4. **Efficiency Ratios**: Measure how effectively assets are used
   - Asset Turnover = Revenue / Average Total Assets
   - Inventory Turnover = COGS / Average Inventory
   - Receivables Turnover = Revenue / Average Accounts Receivable""",
                "category": "financial_analysis",
                "tags": ["ratios", "financial_analysis", "performance", "metrics"]
            },
            {
                "id": "time_series_analysis",
                "title": "Financial Time Series Analysis",
                "content": """Time series analysis in finance involves examining financial data points collected over time to identify trends, patterns, and seasonality.

**Key Concepts:**
- **Trend**: Long-term movement in data (upward, downward, or sideways)
- **Seasonality**: Regular patterns that repeat over specific periods
- **Cyclical Patterns**: Longer-term fluctuations related to business cycles
- **Volatility**: Measure of price fluctuations over time

**Common Techniques:**
1. **Moving Averages**: Smooth out short-term fluctuations
   - Simple Moving Average (SMA)
   - Exponential Moving Average (EMA)
   - Weighted Moving Average (WMA)

2. **Trend Analysis**: Identify direction and strength of trends
   - Linear regression
   - Polynomial fitting
   - Seasonal decomposition

3. **Volatility Measures**: Assess risk and uncertainty
   - Standard deviation
   - Variance
   - Value at Risk (VaR)

**Best Practices:**
- Always consider the time period and frequency of data
- Account for market conditions and external factors
- Use multiple indicators for comprehensive analysis
- Be aware of survivorship bias and data quality issues""",
                "category": "data_analysis",
                "tags": ["time_series", "trends", "volatility", "analysis", "patterns"]
            },
            {
                "id": "risk_management",
                "title": "Financial Risk Management",
                "content": """Risk management is the process of identifying, assessing, and controlling financial risks that could impact investment returns or business operations.

**Types of Financial Risk:**

1. **Market Risk**: Risk from changes in market prices
   - Equity risk (stock price changes)
   - Interest rate risk (bond price changes)
   - Currency risk (exchange rate fluctuations)
   - Commodity risk (commodity price changes)

2. **Credit Risk**: Risk of counterparty default
   - Default risk (failure to pay)
   - Concentration risk (over-exposure to single entity)
   - Settlement risk (payment processing failures)

3. **Liquidity Risk**: Risk of inability to convert assets to cash
   - Market liquidity risk (cannot sell at fair price)
   - Funding liquidity risk (cannot meet cash obligations)

4. **Operational Risk**: Risk from internal processes, systems, or events
   - Technology failures
   - Human error
   - Fraud and security breaches

**Risk Measures:**
- **Value at Risk (VaR)**: Maximum expected loss over specific time period
- **Conditional VaR (CVaR)**: Expected loss beyond VaR threshold
- **Beta**: Measure of systematic risk relative to market
- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline

**Risk Management Strategies:**
- Diversification across assets, sectors, and geographies
- Hedging using derivatives (options, futures, swaps)
- Position sizing and portfolio allocation limits
- Regular monitoring and stress testing""",
                "category": "risk_management",
                "tags": ["risk", "management", "VaR", "diversification", "hedging"]
            },
            {
                "id": "portfolio_optimization",
                "title": "Portfolio Optimization and Asset Allocation",
                "content": """Portfolio optimization involves selecting the optimal mix of assets to maximize returns for a given level of risk or minimize risk for a target return.

**Modern Portfolio Theory (MPT):**
- Developed by Harry Markowitz
- Focuses on risk-return tradeoff
- Efficient frontier represents optimal portfolios
- Assumes investors are risk-averse and rational

**Key Concepts:**
1. **Expected Return**: Weighted average of individual asset returns
2. **Portfolio Variance**: Measure of portfolio risk considering correlations
3. **Correlation**: How assets move relative to each other
4. **Diversification Benefit**: Risk reduction through uncorrelated assets

**Optimization Approaches:**

1. **Mean-Variance Optimization**:
   - Maximize: E(R) - λ * Var(R)
   - Where λ is risk aversion parameter

2. **Risk Parity**:
   - Equal risk contribution from each asset
   - Weights inversely proportional to volatility

3. **Black-Litterman Model**:
   - Incorporates investor views
   - Addresses estimation error in expected returns

4. **Factor-Based Allocation**:
   - Allocate based on risk factors
   - Value, growth, momentum, quality factors

**Practical Considerations:**
- Transaction costs and liquidity constraints
- Tax implications and rebalancing frequency
- Benchmark tracking and active vs passive management
- Dynamic allocation based on market conditions
- Alternative assets (REITs, commodities, private equity)

**Performance Evaluation:**
- Sharpe Ratio: (Return - Risk-free rate) / Standard deviation
- Information Ratio: Active return / Tracking error
- Alpha: Excess return vs benchmark
- Maximum drawdown and recovery time""",
                "category": "portfolio_management",
                "tags": ["portfolio", "optimization", "allocation", "MPT", "diversification"]
            },
            {
                "id": "financial_statements",
                "title": "Financial Statement Analysis",
                "content": """Financial statements provide a structured representation of a company's financial position and performance.

**Three Main Financial Statements:**

1. **Income Statement (P&L)**:
   - Revenue/Sales
   - Cost of Goods Sold (COGS)
   - Gross Profit = Revenue - COGS
   - Operating Expenses (SG&A, R&D, Depreciation)
   - Operating Income (EBIT)
   - Interest Expense
   - Pre-tax Income
   - Tax Expense
   - Net Income

2. **Balance Sheet**:
   - **Assets**: Current (cash, inventory, receivables) + Non-current (PPE, intangibles)
   - **Liabilities**: Current (payables, short-term debt) + Long-term (bonds, loans)
   - **Equity**: Share capital + Retained earnings
   - Fundamental equation: Assets = Liabilities + Equity

3. **Cash Flow Statement**:
   - **Operating Cash Flow**: Cash from core business operations
   - **Investing Cash Flow**: Cash from asset purchases/sales
   - **Financing Cash Flow**: Cash from debt/equity transactions
   - Net change in cash position

**Key Analysis Techniques:**

1. **Horizontal Analysis**: Compare across time periods
   - Year-over-year growth rates
   - Trend analysis over multiple periods

2. **Vertical Analysis**: Express items as percentage of base
   - Common-size statements
   - Percentage of revenue or total assets

3. **Ratio Analysis**: Calculate financial ratios
   - Profitability, liquidity, leverage, efficiency ratios

4. **DuPont Analysis**: Break down ROE components
   - ROE = Net Margin × Asset Turnover × Equity Multiplier

**Red Flags to Watch:**
- Declining gross margins
- Increasing days sales outstanding (DSO)
- Growing inventory relative to sales
- High debt levels and interest coverage issues
- Significant one-time charges or adjustments
- Discrepancies between net income and cash flow""",
                "category": "financial_analysis",
                "tags": ["financial_statements", "analysis", "income_statement", "balance_sheet", "cash_flow"]
            }
        ]
        
        for item_data in default_knowledge:
            knowledge_item = KnowledgeItem(
                id=item_data["id"],
                title=item_data["title"],
                content=item_data["content"],
                category=item_data["category"],
                tags=item_data["tags"]
            )
            self.knowledge_items.append(knowledge_item)
        
        logger.info(f"Created default knowledge base with {len(self.knowledge_items)} items")
    
    def _build_search_index(self):
        """Build TF-IDF search index for knowledge retrieval."""
        
        if not self.knowledge_items:
            logger.warning("No knowledge items to index")
            return
        
        # Combine title and content for indexing
        documents = []
        for item in self.knowledge_items:
            doc_text = f"{item.title} {item.content} {' '.join(item.tags)}"
            documents.append(doc_text)
        
        try:
            self.knowledge_vectors = self.vectorizer.fit_transform(documents)
            self.is_initialized = True
            logger.info(f"Built search index for {len(documents)} knowledge items")
        except Exception as e:
            logger.error(f"Error building search index: {e}")
    
    def search_knowledge(self, query: str, top_k: int = 3) -> List[KnowledgeItem]:
        """
        Search the knowledge base for relevant items.
        
        Args:
            query: Search query
            top_k: Number of top results to return
        
        Returns:
            List of relevant KnowledgeItem objects with relevance scores
        """
        
        if not self.is_initialized:
            logger.warning("Knowledge base not initialized")
            return []
        
        try:
            # Vectorize the query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(query_vector, self.knowledge_vectors).flatten()
            
            # Get top-k most similar items
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum relevance threshold
                    item = self.knowledge_items[idx]
                    item.relevance_score = float(similarities[idx])
                    results.append(item)
            
            logger.info(f"Found {len(results)} relevant knowledge items for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def get_contextual_knowledge(self, user_query: str, sql_query: Optional[str] = None) -> str:
        """
        Get contextual knowledge relevant to a user query and SQL operation.
        
        Args:
            user_query: The user's natural language question
            sql_query: The SQL query being executed (if any)
        
        Returns:
            Formatted contextual knowledge string
        """
        
        # Search for relevant knowledge
        search_query = user_query
        if sql_query:
            # Extract key terms from SQL query
            sql_terms = self._extract_sql_concepts(sql_query)
            search_query += " " + " ".join(sql_terms)
        
        relevant_items = self.search_knowledge(search_query, top_k=2)
        
        if not relevant_items:
            return ""
        
        context = "## Relevant Financial Context:\n\n"
        
        for item in relevant_items:
            context += f"### {item.title}\n"
            # Include first paragraph or first 300 characters
            content_preview = item.content.split('\n\n')[0]
            if len(content_preview) > 300:
                content_preview = content_preview[:300] + "..."
            context += f"{content_preview}\n\n"
        
        return context
    
    def get_contextual_knowledge_with_sources(self, question: str, sql_query: str = "") -> Tuple[str, List[Dict]]:
        """
        Get contextual knowledge along with source references for RAG citations.
        
        Args:
            question: User's question
            sql_query: Optional SQL query for additional context
            
        Returns:
            Tuple of (contextual_knowledge, list_of_sources)
        """
        # Get the regular contextual knowledge
        knowledge = self.get_contextual_knowledge(question, sql_query)
        
        # Get the relevant items to create source references
        search_query = question
        if sql_query:
            sql_terms = self._extract_sql_concepts(sql_query)
            search_query += " " + " ".join(sql_terms)
        
        relevant_items = self.search_knowledge(search_query, top_k=2)
        
        # Create source references from relevant items
        sources = []
        for item in relevant_items:
            source = {
                'title': item.title,
                'description': f'{item.category} - {item.content[:100]}...',
                'url': f'#knowledge-{item.id}'  # Internal reference
            }
            sources.append(source)
        
        return knowledge, sources
    
    def _extract_sql_concepts(self, sql_query: str) -> List[str]:
        """Extract financial concepts from SQL query."""
        
        sql_lower = sql_query.lower()
        concepts = []
        
        # Financial terms mapping
        financial_terms = {
            'revenue': ['revenue', 'sales', 'income'],
            'profit': ['profit', 'margin', 'earnings'],
            'ratio': ['ratio', 'percentage', 'rate'],
            'trend': ['trend', 'growth', 'change'],
            'risk': ['risk', 'volatility', 'variance'],
            'return': ['return', 'yield', 'performance']
        }
        
        for concept, terms in financial_terms.items():
            if any(term in sql_lower for term in terms):
                concepts.append(concept)
        
        # SQL aggregation functions suggest statistical analysis
        if any(func in sql_lower for func in ['avg', 'sum', 'count', 'max', 'min']):
            concepts.append('analysis')
        
        # Time-based queries suggest trend analysis
        if any(term in sql_lower for term in ['date', 'month', 'year', 'quarter']):
            concepts.append('time_series')
        
        return concepts
    
    def load_knowledge_base(self, file_path: str):
        """Load knowledge base from JSON file."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.knowledge_items = []
            for item_data in data.get('knowledge_items', []):
                knowledge_item = KnowledgeItem(
                    id=item_data['id'],
                    title=item_data['title'],
                    content=item_data['content'],
                    category=item_data['category'],
                    tags=item_data['tags']
                )
                self.knowledge_items.append(knowledge_item)
            
            logger.info(f"Loaded {len(self.knowledge_items)} knowledge items from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading knowledge base from {file_path}: {e}")
            self._create_default_knowledge_base()
    
    def save_knowledge_base(self, file_path: str):
        """Save knowledge base to JSON file."""
        
        try:
            data = {
                'knowledge_items': [
                    {
                        'id': item.id,
                        'title': item.title,
                        'content': item.content,
                        'category': item.category,
                        'tags': item.tags
                    }
                    for item in self.knowledge_items
                ],
                'created_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved knowledge base to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving knowledge base to {file_path}: {e}")


# Global knowledge base instance
_knowledge_base = None

def get_financial_knowledge_base() -> FinancialKnowledgeBase:
    """Get or create the global financial knowledge base instance."""
    global _knowledge_base
    
    if _knowledge_base is None:
        _knowledge_base = FinancialKnowledgeBase()
    
    return _knowledge_base
