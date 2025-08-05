import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from app import logger

# Try to import FAISS and sentence transformers with fallback
try:
    import faiss
    logger.info("FAISS successfully imported")
    try:
        from sentence_transformers import SentenceTransformer
        FAISS_AVAILABLE = True
        logger.info("FAISS and sentence-transformers successfully imported")
    except ImportError as e:
        logger.warning(f"SentenceTransformers not available: {e}")
        logger.warning("This is likely due to huggingface_hub compatibility issue")
        logger.warning("Falling back to basic knowledge base without vector search")
        FAISS_AVAILABLE = False
except ImportError as e:
    logger.warning(f"FAISS not available: {e}")
    logger.warning("Falling back to basic knowledge base without vector search")
    FAISS_AVAILABLE = False
    # Create dummy classes for type hints
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, *args, **kwargs):
            return np.random.rand(1, 384)  # Dummy embedding
        def get_sentence_embedding_dimension(self):
            return 384
    
    class faiss:
        @staticmethod
        def IndexFlatIP(*args): 
            return None
        @staticmethod
        def normalize_L2(*args): 
            pass
        @staticmethod
        def read_index(*args): 
            return None
        @staticmethod
        def write_index(*args): 
            pass

@dataclass
class KnowledgeChunk:
    """A chunk of knowledge with metadata for better retrieval."""
    id: str
    parent_id: str  # Original knowledge item ID
    title: str
    content: str
    category: str
    tags: List[str]
    chunk_index: int
    total_chunks: int
    relevance_score: float = 0.0


@dataclass
class KnowledgeItem:
    """A single item in the financial knowledge base."""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    relevance_score: float = 0.0


class FAISSFinancialKnowledgeBase:
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
        if FAISS_AVAILABLE:
            logger.info(f"Loading sentence transformer model: {model_name}")
            self.encoder = SentenceTransformer(model_name)
            self.embedding_dim = self.encoder.get_sentence_embedding_dimension()
        else:
            logger.warning("FAISS not available, using fallback mode")
            self.encoder = SentenceTransformer()  # Dummy encoder
            self.embedding_dim = 384
        
        # Initialize FAISS index and knowledge items
        self.faiss_index = None
        self.knowledge_items: List[KnowledgeItem] = []
        
        # Load or create knowledge base
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base by loading cached data or creating new."""
        try:
            if self._load_cached_data():
                logger.info("Loaded cached FAISS knowledge base")
            else:
                logger.info("Creating new FAISS knowledge base")
                self._create_default_knowledge_base()
                self._build_faiss_index()
                self._save_cached_data()
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            # Fallback to creating new knowledge base
            self._create_default_knowledge_base()
            self._build_faiss_index()
    
    def _load_cached_data(self) -> bool:
        """Load cached embeddings and FAISS index."""
        try:
            if not all(os.path.exists(f) for f in [self.knowledge_file, self.index_file]):
                return False
            
            # Load knowledge items
            with open(self.knowledge_file, 'rb') as f:
                self.knowledge_items = pickle.load(f)
            
            # Load FAISS index
            self.faiss_index = faiss.read_index(self.index_file)
            
            logger.info(f"Loaded {len(self.knowledge_items)} knowledge items from cache")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load cached data: {e}")
            return False
    
    def _save_cached_data(self):
        """Save embeddings and FAISS index to cache."""
        try:
            # Save knowledge items
            with open(self.knowledge_file, 'wb') as f:
                pickle.dump(self.knowledge_items, f)
            
            # Save FAISS index
            faiss.write_index(self.faiss_index, self.index_file)
            
            logger.info("Saved FAISS knowledge base to cache")
            
        except Exception as e:
            logger.error(f"Failed to save cached data: {e}")
    
    def _create_default_knowledge_base(self):
        """Create a comprehensive financial knowledge base."""
        
        default_knowledge = [
            {
                "id": "financial_ratios_overview",
                "title": "Financial Ratios Overview",
                "content": """Financial ratios are quantitative measures used to evaluate a company's financial performance and health. They provide insights into profitability, liquidity, efficiency, and leverage.

**Key Categories with Formulas:**

1. **Profitability Ratios**:
   - **ROE (Return on Equity)** = Net Income / Shareholders' Equity
     * Good ROE: 15-20% for most industries
     * Excellent ROE: >20%
   - **ROA (Return on Assets)** = Net Income / Total Assets
     * Good ROA: 5-10% depending on industry
   - **Gross Profit Margin** = (Revenue - COGS) / Revenue × 100
     * Retail: 20-40%, Software: 70-85%
   - **Net Profit Margin** = Net Income / Revenue × 100
     * Good margin: 10-20%, Excellent: >20%

2. **Liquidity Ratios**:
   - **Current Ratio** = Current Assets / Current Liabilities
     * Healthy range: 1.5-3.0
     * Below 1.0 indicates potential liquidity problems
   - **Quick Ratio** = (Current Assets - Inventory) / Current Liabilities
     * Good range: 1.0-1.5
   - **Cash Ratio** = Cash + Cash Equivalents / Current Liabilities
     * Minimum acceptable: 0.2-0.3

3. **Efficiency Ratios**:
   - **Asset Turnover** = Revenue / Average Total Assets
     * Higher is better, varies by industry
   - **Inventory Turnover** = COGS / Average Inventory
     * Retail: 6-12 times/year, Manufacturing: 4-8 times/year
   - **Receivables Turnover** = Revenue / Average Accounts Receivable
     * Good range: 6-12 times/year

4. **Leverage Ratios**:
   - **Debt-to-Equity** = Total Debt / Total Equity
     * Conservative: <0.3, Moderate: 0.3-0.6, Aggressive: >0.6
   - **Interest Coverage** = EBIT / Interest Expense
     * Safe minimum: 2.5, Good: >5.0
   - **Debt Service Coverage** = Operating Income / Total Debt Service
     * Minimum acceptable: 1.2, Good: >1.5

**Industry Benchmarks:**
- **Technology**: High margins (70%+ gross), low asset turnover
- **Retail**: Low margins (20-40% gross), high inventory turnover
- **Manufacturing**: Moderate margins (40-60% gross), moderate turnover
- **Utilities**: Low ROE (8-12%), high debt ratios, stable cash flows

**Best Practices:**
- Compare ratios over 3-5 year periods for trends
- Use industry-specific benchmarks (S&P 500 averages)
- Consider seasonal variations in quarterly ratios
- Analyze ratios in context of business cycle and economic conditions""",
                "category": "financial_analysis",
                "tags": ["ratios", "profitability", "liquidity", "efficiency", "leverage", "ROE", "ROA", "margins"]
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
1. **Market Risk**: Risk of losses due to market movements
   - Equity risk, interest rate risk, currency risk, commodity risk

2. **Credit Risk**: Risk of counterparty default
   - Default risk, concentration risk, settlement risk

3. **Operational Risk**: Risk from internal processes, systems, or events
   - Technology failures, fraud, regulatory changes

4. **Liquidity Risk**: Risk of inability to meet short-term obligations
   - Funding liquidity risk, market liquidity risk

**Risk Management Strategies:**
- Diversification across assets, sectors, and geographies
- Hedging using derivatives (options, futures, swaps)
- Position sizing and portfolio allocation limits
- Regular monitoring and stress testing

**Key Metrics:**
- **Value at Risk (VaR)**: Maximum potential loss over a specific time period
- **Conditional VaR (CVaR)**: Expected loss beyond VaR threshold
- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline""",
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
- Treynor Ratio: (Return - Risk-free rate) / Beta
- Jensen's Alpha: Excess return over CAPM prediction""",
                "category": "portfolio_management",
                "tags": ["portfolio", "optimization", "allocation", "MPT", "diversification"]
            },
            {
                "id": "customer_segmentation",
                "title": "Customer Segmentation and Analysis",
                "content": """Customer segmentation is the practice of dividing customers into groups based on shared characteristics to enable targeted marketing and service strategies.

**Segmentation Approaches with Examples:**

1. **Demographic Segmentation**:
   - **Age Groups**: Gen Z (18-25), Millennials (26-41), Gen X (42-57), Boomers (58+)
   - **Income Brackets**: Low (<$35K), Middle ($35K-$75K), High ($75K-$150K), Premium (>$150K)
   - **Geographic**: Urban (60% of customers), Suburban (30%), Rural (10%)
   - **Education**: High School (25%), Bachelor's (45%), Graduate (30%)

2. **Behavioral Segmentation**:
   - **Purchase Frequency**: Heavy users (>10 purchases/year), Medium (4-10), Light (1-3)
   - **Spending Patterns**: High-value ($500+ avg order), Medium ($100-500), Low (<$100)
   - **Channel Preference**: Online-only (40%), Omnichannel (45%), Store-only (15%)
   - **Loyalty Status**: Champions (NPS 9-10), Passives (7-8), Detractors (0-6)

3. **Value-Based Segmentation**:
   - **Customer Lifetime Value (CLV)**:
     * Platinum: CLV >$5,000 (top 5% of customers)
     * Gold: CLV $2,000-$5,000 (next 15%)
     * Silver: CLV $500-$2,000 (next 30%)
     * Bronze: CLV <$500 (remaining 50%)

**Key Metrics with Benchmarks:**

- **Customer Acquisition Cost (CAC)**:
  * E-commerce average: $45-$200
  * SaaS average: $205-$415
  * Formula: Total Marketing Spend / New Customers Acquired

- **Customer Lifetime Value (CLV)**:
  * Formula: (Average Order Value × Purchase Frequency × Gross Margin) × Customer Lifespan
  * Good CLV:CAC ratio: 3:1 or higher
  * Excellent CLV:CAC ratio: 5:1 or higher

- **Churn Rate**:
  * SaaS monthly churn: 5-7% (good), <5% (excellent)
  * E-commerce annual churn: 20-30% (typical)
  * Formula: Customers Lost / Total Customers at Start × 100

- **Net Promoter Score (NPS)**:
  * Excellent: >70, Good: 50-70, Average: 30-50, Poor: <30
  * Formula: % Promoters (9-10) - % Detractors (0-6)

**RFM Analysis Scoring:**
- **Recency**: Last purchase within 30 days (5), 31-60 days (4), 61-90 days (3), 91-180 days (2), >180 days (1)
- **Frequency**: >10 purchases (5), 7-10 (4), 4-6 (3), 2-3 (2), 1 purchase (1)
- **Monetary**: >$1000 spent (5), $500-1000 (4), $200-500 (3), $50-200 (2), <$50 (1)

**Customer Segment Examples:**
- **Champions** (RFM: 5-5-5): 5% of customers, 35% of revenue
- **Loyal Customers** (RFM: 4-5-4): 15% of customers, 25% of revenue
- **At Risk** (RFM: 2-3-4): 10% of customers, need retention campaigns
- **Lost Customers** (RFM: 1-1-2): 20% of customers, win-back opportunities

**Industry Benchmarks:**
- **Retail**: 80/20 rule - 20% of customers generate 80% of revenue
- **SaaS**: Top 10% of customers typically have 5x higher CLV
- **E-commerce**: Average customer makes 2.3 purchases per year
- **Financial Services**: Customer retention improvement of 5% can increase profits by 25-95%

**Analysis Techniques:**
- **K-means Clustering**: Optimal clusters typically 3-7 segments
- **Cohort Analysis**: Track monthly/quarterly retention rates
- **Predictive Modeling**: Churn prediction accuracy >85% considered good
- **A/B Testing**: Segment-specific campaigns show 15-25% improvement over mass marketing""",
                "category": "customer_analysis",
                "tags": ["segmentation", "customers", "CLV", "churn", "targeting", "RFM", "NPS", "CAC"]
            },
            {
                "id": "statistical_analysis",
                "title": "Statistical Analysis in Finance",
                "content": """Statistical analysis provides the foundation for data-driven financial decision making through descriptive statistics, hypothesis testing, and predictive modeling.

**Descriptive Statistics with Examples:**

1. **Central Tendency**:
   - **Mean**: Sum of all values / Number of observations
     * Example: Stock returns [5%, 3%, -2%, 8%, 1%] → Mean = 3%
     * Sensitive to outliers (one extreme value can skew results)
   - **Median**: Middle value when data is sorted
     * Example: Customer ages [22, 25, 28, 35, 67] → Median = 28
     * Robust to outliers, better for skewed distributions
   - **Mode**: Most frequently occurring value
     * Example: Purchase amounts [100, 150, 100, 200, 100] → Mode = 100

2. **Dispersion Measures**:
   - **Standard Deviation**: √(Variance)
     * Low volatility stock: σ = 15-20%
     * High volatility stock: σ = 30-50%
     * Formula: σ = √[Σ(xi - μ)² / N]
   - **Variance**: Average of squared deviations from mean
   - **Range**: Max - Min value
   - **Interquartile Range (IQR)**: Q3 - Q1 (middle 50% of data)

3. **Distribution Shape**:
   - **Skewness**: Measure of asymmetry
     * Normal distribution: Skewness ≈ 0
     * Right-skewed (positive): Skewness > 0 (income distributions)
     * Left-skewed (negative): Skewness < 0
   - **Kurtosis**: Measure of tail heaviness
     * Normal distribution: Kurtosis = 3
     * High kurtosis: More extreme outliers (financial crises)

**Key Statistical Measures with Benchmarks:**

- **Correlation Coefficient (r)**:
  * Strong positive: r > 0.7 (e.g., stock price and trading volume)
  * Moderate: 0.3 < r < 0.7
  * Weak: 0.1 < r < 0.3
  * No correlation: r ≈ 0
  * Strong negative: r < -0.7

- **R-squared (R²)**:
  * Excellent model: R² > 0.9 (explains >90% of variance)
  * Good model: 0.7 < R² < 0.9
  * Moderate: 0.5 < R² < 0.7
  * Weak: R² < 0.5

- **P-values and Significance**:
  * Highly significant: p < 0.01 (99% confidence)
  * Significant: p < 0.05 (95% confidence)
  * Marginally significant: p < 0.10 (90% confidence)
  * Not significant: p ≥ 0.10

**Hypothesis Testing Examples:**

- **T-test**: Compare means between two groups
  * Example: Average customer spend before vs. after campaign
  * H₀: μ₁ = μ₂ (no difference), H₁: μ₁ ≠ μ₂ (significant difference)

- **Chi-square Test**: Test independence between categorical variables
  * Example: Customer segment vs. product preference
  * Degrees of freedom = (rows-1) × (columns-1)

- **ANOVA**: Compare means across multiple groups
  * Example: Revenue performance across different sales channels
  * F-statistic determines if group means are significantly different

**Financial Benchmarks and Rules of Thumb:**

- **Sample Size Requirements**:
  * Minimum for t-test: n ≥ 30 per group
  * For proportions: np ≥ 5 and n(1-p) ≥ 5
  * For regression: n ≥ 10 × number of variables

- **Confidence Intervals**:
  * 95% CI: Mean ± 1.96 × (σ/√n) for large samples
  * 99% CI: Mean ± 2.58 × (σ/√n)

- **Effect Size Interpretation**:
  * Small effect: Cohen's d = 0.2
  * Medium effect: Cohen's d = 0.5
  * Large effect: Cohen's d = 0.8

**Common Statistical Distributions in Finance:**

- **Normal Distribution**: Stock returns (approximately)
  * 68% of data within 1σ, 95% within 2σ, 99.7% within 3σ

- **Log-normal Distribution**: Stock prices, asset values
  * Cannot be negative, right-skewed

- **Poisson Distribution**: Rare events (defaults, system failures)
  * Example: Number of customer complaints per day

**Best Practices with Specific Guidelines:**
- **Data Quality**: Aim for <5% missing values, check for outliers beyond 3σ
- **Sample Size**: Use power analysis to determine minimum n for desired effect size
- **Multiple Testing**: Apply Bonferroni correction when testing multiple hypotheses
- **Cross-validation**: Use 80/20 or 70/30 train/test splits for model validation
- **Business Context**: Statistical significance ≠ practical significance (consider effect size)""",
                "category": "statistical_analysis",
                "tags": ["statistics", "mean", "median", "correlation", "hypothesis", "t-test", "ANOVA", "p-values"]
            }
        ]
        
        # Convert to KnowledgeItem objects
        self.knowledge_items = []
        for item_data in default_knowledge:
            item = KnowledgeItem(
                id=item_data["id"],
                title=item_data["title"],
                content=item_data["content"],
                category=item_data["category"],
                tags=item_data["tags"]
            )
            self.knowledge_items.append(item)
        
        logger.info(f"Created {len(self.knowledge_items)} default knowledge items")
    
    def _chunk_text(self, text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
        """
        Chunk text into overlapping segments for better semantic retrieval.
        
        Args:
            text: Text to chunk
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks with overlap
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + chunk_size
            
            # If we're not at the end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for paragraph breaks
                    para_break = text.rfind('\n\n', start, end)
                    if para_break > start:
                        end = para_break + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            
            # Prevent infinite loop
            if start >= len(text):
                break
                
        return chunks
    
    def _create_knowledge_chunks(self, knowledge_items: List[KnowledgeItem]) -> List[KnowledgeChunk]:
        """
        Create chunks from knowledge items with proper overlap and metadata.
        
        Args:
            knowledge_items: List of knowledge items to chunk
            
        Returns:
            List of knowledge chunks
        """
        all_chunks = []
        
        for item in knowledge_items:
            # Combine title and content for chunking
            full_text = f"{item.title}\n\n{item.content}"
            
            # Create chunks with overlap
            text_chunks = self._chunk_text(full_text, chunk_size=400, overlap=80)
            
            # Create KnowledgeChunk objects
            for i, chunk_text in enumerate(text_chunks):
                chunk = KnowledgeChunk(
                    id=f"{item.id}_chunk_{i}",
                    parent_id=item.id,
                    title=item.title,
                    content=chunk_text,
                    category=item.category,
                    tags=item.tags,
                    chunk_index=i,
                    total_chunks=len(text_chunks)
                )
                all_chunks.append(chunk)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(knowledge_items)} knowledge items")
        return all_chunks

    def _build_faiss_index(self):
        """Build FAISS index from knowledge items."""
        if not self.knowledge_items:
            logger.warning("No knowledge items to index")
            return
        
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available, skipping index building")
            return
        
        # Create text for embedding (title + content)
        texts = []
        for item in self.knowledge_items:
            text = f"{item.title}. {item.content}"
            texts.append(text)
        
        logger.info(f"Generating embeddings for {len(texts)} knowledge items...")
        
        try:
            # Generate embeddings
            embeddings = self.encoder.encode(texts, show_progress_bar=True)
            embeddings = np.array(embeddings).astype('float32')
            
            # Create FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add embeddings to index
            self.faiss_index.add(embeddings)
            
            logger.info(f"Built FAISS index with {self.faiss_index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error building FAISS index: {e}")
            self.faiss_index = None

    def search_knowledge(self, query: str, top_k: int = 5) -> List[KnowledgeItem]:
        """
        Search knowledge base using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of relevant KnowledgeItem objects with relevance scores
        """
        if not FAISS_AVAILABLE or not self.faiss_index or not self.knowledge_items:
            logger.warning("FAISS search not available, using fallback text search")
            return self._fallback_search(query, top_k)
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding, min(top_k, len(self.knowledge_items)))
            
            # Create results with relevance scores
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.knowledge_items):  # Valid index
                    item = self.knowledge_items[idx]
                    item.relevance_score = float(score)
                    results.append(item)
            
            logger.info(f"Found {len(results)} relevant knowledge items for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return self._fallback_search(query, top_k)
    
    def _fallback_search(self, query: str, top_k: int = 5) -> List[KnowledgeItem]:
        """Fallback search using simple text matching when FAISS is not available."""
        query_lower = query.lower()
        results = []
        
        logger.info(f"Fallback search for query: '{query}'")
        
        # Split query into individual words for better matching
        query_words = [word.strip() for word in query_lower.split() if len(word.strip()) > 2]
        logger.info(f"Search words: {query_words}")
        
        for item in self.knowledge_items:
            # Enhanced text matching with individual words
            title_matches = any(word in item.title.lower() for word in query_words)
            content_matches = any(word in item.content.lower() for word in query_words)
            tag_matches = any(any(word in tag.lower() for word in query_words) for tag in item.tags)
            
            # Also check for exact phrase matches
            exact_title_match = query_lower in item.title.lower()
            exact_content_match = query_lower in item.content.lower()
            exact_tag_match = any(query_lower in tag.lower() for tag in item.tags)
            
            if title_matches or content_matches or tag_matches or exact_title_match or exact_content_match or exact_tag_match:
                # Enhanced scoring based on matches
                score = 0.0
                if exact_title_match:
                    score += 1.0
                elif title_matches:
                    score += 0.5
                if exact_content_match:
                    score += 0.8
                elif content_matches:
                    score += 0.3
                if exact_tag_match:
                    score += 0.6
                elif tag_matches:
                    score += 0.2
                
                item.relevance_score = score
                results.append(item)
                logger.info(f"Match found: '{item.title}' (score: {score:.2f})")
        
        # Sort by relevance score and return top_k
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    def get_contextual_knowledge(self, question: str, sql_query: str = "") -> str:
        """
        Get contextual knowledge for a question and optional SQL query.
        
        Args:
            question: User's question
            sql_query: Optional SQL query for additional context
            
        Returns:
            Formatted contextual knowledge string
        """
        # Create search query
        search_query = question
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
                'url': f'#knowledge-{item.id}',  # Internal reference
                'relevance_score': item.relevance_score
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
            'return': ['return', 'yield', 'performance'],
            'customer': ['customer', 'client', 'segment'],
            'product': ['product', 'item', 'category'],
            'account': ['account', 'financial', 'balance']
        }
        
        for concept, terms in financial_terms.items():
            if any(term in sql_lower for term in terms):
                concepts.append(concept)
        
        # SQL aggregation functions suggest statistical analysis
        if any(func in sql_lower for func in ['avg', 'sum', 'count', 'max', 'min']):
            concepts.append('statistics')
        
        # Time-based queries suggest trend analysis
        if any(term in sql_lower for term in ['date', 'month', 'year', 'quarter']):
            concepts.append('time_series')
        
        return concepts
    
    def add_knowledge_item(self, item: KnowledgeItem):
        """Add a new knowledge item and rebuild index."""
        self.knowledge_items.append(item)
        self._build_faiss_index()
        self._save_cached_data()
        logger.info(f"Added knowledge item: {item.title}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        categories = {}
        for item in self.knowledge_items:
            categories[item.category] = categories.get(item.category, 0) + 1
        
        return {
            "total_items": len(self.knowledge_items),
            "categories": categories,
            "embedding_dimension": self.embedding_dim,
            "model_name": self.model_name,
            "index_size": self.faiss_index.ntotal if self.faiss_index else 0
        }


# Global instance
_faiss_knowledge_base = None

def get_faiss_financial_knowledge_base() -> FAISSFinancialKnowledgeBase:
    """Get or create the global FAISS financial knowledge base instance."""
    global _faiss_knowledge_base
    if _faiss_knowledge_base is None:
        _faiss_knowledge_base = FAISSFinancialKnowledgeBase()
    return _faiss_knowledge_base
