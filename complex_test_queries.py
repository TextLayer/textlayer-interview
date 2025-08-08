#!/usr/bin/env python3
"""
Complex Financial Analysis Test Queries
=======================================

These queries test various aspects of the multi-agent financial analysis system:
- SQL generation capabilities
- Data analysis depth
- Business intelligence insights
- Judge evaluation accuracy
- Error handling and recovery

Run these through the Flask API endpoint: POST /v1/threads/chat/agentic
"""

# =============================================================================
# LEVEL 1: FOUNDATIONAL QUERIES (Should work perfectly now)
# =============================================================================

LEVEL_1_QUERIES = [
    # 1.1 Basic Revenue Analysis
    "Show me total revenue by product category for 2018",
    
    # 1.2 Time-based Analysis  
    "What was the quarterly revenue breakdown for 2018?",
    
    # 1.3 Channel Analysis
    "Compare revenue performance across different customer channels in 2018",
    
    # 1.4 Product Performance
    "Which product categories generated the most revenue in 2018 and by how much?",
    
    # 1.5 Account Hierarchy
    "Break down all revenue streams (Gross Revenue, Product Revenue, Service Revenue, Other Revenue) for 2018"
]

# =============================================================================
# LEVEL 2: INTERMEDIATE COMPLEXITY
# =============================================================================

LEVEL_2_QUERIES = [
    # 2.1 Quarterly Comparisons
    "Compare Q1 vs Q4 2018 revenue performance by product category. Which categories showed the biggest differences?",
    
    # 2.2 Channel-Product Matrix
    "Show me a matrix of revenue by product category and customer channel for 2018. Identify the top 5 combinations.",
    
    # 2.3 Monthly Trends
    "What are the monthly revenue trends for the top 3 product categories in 2018?",
    
    # 2.4 Market Share Analysis
    "Calculate the market share of each product category within total revenue for 2018",
    
    # 2.5 Performance Benchmarking
    "Which customer channels are performing above and below average revenue per product category?"
]

# =============================================================================
# LEVEL 3: ADVANCED ANALYTICAL QUERIES
# =============================================================================

LEVEL_3_QUERIES = [
    # 3.1 Growth Rate Analysis (Modified for 2018 data)
    "Calculate quarter-over-quarter growth rates for each product category in 2018. Which showed the most consistent growth?",
    
    # 3.2 Customer-Product Correlation
    "Analyze the relationship between customer channel and product mix. Which channels prefer which product categories?",
    
    # 3.3 Revenue Concentration
    "Perform a revenue concentration analysis - what percentage of total revenue comes from the top 20% of product-channel combinations?",
    
    # 3.4 Seasonal Pattern Analysis
    "Identify seasonal patterns in revenue by analyzing monthly fluctuations across product categories in 2018",
    
    # 3.5 Portfolio Diversification
    "Assess our revenue portfolio diversification - calculate variance and standard deviation across product categories and channels"
]

# =============================================================================
# LEVEL 4: COMPLEX BUSINESS INTELLIGENCE QUERIES
# =============================================================================

LEVEL_4_QUERIES = [
    # 4.1 Multi-dimensional Performance Analysis
    "Create a comprehensive performance dashboard showing revenue by product category, customer channel, and quarter. Include rankings and percentage contributions.",
    
    # 4.2 Risk Assessment Query
    "Identify revenue risk factors by analyzing which product-channel combinations have the highest volatility and concentration.",
    
    # 4.3 Cross-functional Business Analysis
    "Compare service revenue vs product revenue across different customer channels. What does this tell us about our go-to-market effectiveness?",
    
    # 4.4 Market Opportunity Analysis
    "Based on 2018 performance, identify underperforming product-channel combinations that represent growth opportunities.",
    
    # 5.5 Financial Health Assessment
    "Provide a comprehensive financial health assessment including revenue diversification, customer concentration, and growth stability metrics."
]

# =============================================================================
# LEVEL 5: STRESS TESTS & EDGE CASES
# =============================================================================

LEVEL_5_QUERIES = [
    # 5.1 Complex Multi-step Analysis
    "Calculate the Gini coefficient for revenue distribution across product categories and customer channels to measure inequality.",
    
    # 5.2 Advanced Statistical Analysis
    "Perform a statistical analysis of revenue including mean, median, standard deviation, and quartiles by product category. Identify outliers.",
    
    # 5.3 Predictive Insights
    "Based on 2018 quarterly trends, what patterns suggest potential risks or opportunities for revenue performance?",
    
    # 5.4 Competitive Market Analysis
    "Analyze market dynamics by comparing the performance patterns of our different product lines against their respective channels.",
    
    # 5.5 Executive Summary Query
    "Generate an executive summary of 2018 financial performance including key metrics, trends, risks, and strategic recommendations."
]

# =============================================================================
# TESTING FRAMEWORK
# =============================================================================

def create_test_scenarios():
    """Create structured test scenarios for systematic testing"""
    
    scenarios = {
        "foundation": {
            "description": "Tests basic SQL generation and data retrieval",
            "queries": LEVEL_1_QUERIES,
            "expected_sql_score": "8-10",
            "expected_features": ["Basic JOINs", "Simple aggregations", "Time filtering"]
        },
        
        "intermediate": {
            "description": "Tests multi-dimensional analysis and comparisons", 
            "queries": LEVEL_2_QUERIES,
            "expected_sql_score": "7-9",
            "expected_features": ["Multi-table JOINs", "Complex WHERE clauses", "Ranking functions"]
        },
        
        "advanced": {
            "description": "Tests statistical analysis and growth calculations",
            "queries": LEVEL_3_QUERIES, 
            "expected_sql_score": "6-8",
            "expected_features": ["Window functions", "CTEs", "Statistical calculations"]
        },
        
        "business_intelligence": {
            "description": "Tests complex business analysis and insights",
            "queries": LEVEL_4_QUERIES,
            "expected_sql_score": "5-8", 
            "expected_features": ["Complex CTEs", "Multiple window functions", "Business logic"]
        },
        
        "stress_tests": {
            "description": "Tests system limits and edge cases",
            "queries": LEVEL_5_QUERIES,
            "expected_sql_score": "4-7",
            "expected_features": ["Advanced statistics", "Multi-step analysis", "Complex business logic"]
        }
    }
    
    return scenarios

# =============================================================================
# SPECIFIC SQL TESTING QUERIES (For Direct Database Testing)
# =============================================================================

SQL_TEST_QUERIES = [
    # Test 1: Basic functionality
    """
    -- Test: Basic revenue by product (should work)
    SELECT p.Name as product_category, SUM(fd.amount) as total_revenue
    FROM financial_data fd
    JOIN product p ON fd.product_key = p.Key
    JOIN account a ON fd.account_key = a.Key
    JOIN time t ON fd.time_period = t.Month
    WHERE a.AccountType = '1'
      AND CAST(t.Year AS INTEGER) = 2018
    GROUP BY p.Name
    ORDER BY total_revenue DESC;
    """,
    
    # Test 2: Quarter-over-quarter growth
    """
    -- Test: Q-o-Q growth rates (complex window functions)
    WITH quarterly_data AS (
        SELECT 
            p.Name as product_category,
            t.Quarter,
            SUM(fd.amount) as revenue
        FROM financial_data fd
        JOIN product p ON fd.product_key = p.Key
        JOIN time t ON fd.time_period = t.Month
        JOIN account a ON fd.account_key = a.Key
        WHERE a.AccountType = '1'
          AND CAST(t.Year AS INTEGER) = 2018
        GROUP BY p.Name, t.Quarter
    )
    SELECT 
        product_category,
        Quarter,
        revenue,
        LAG(revenue) OVER (PARTITION BY product_category ORDER BY Quarter) as prev_quarter,
        ROUND(
            (revenue - LAG(revenue) OVER (PARTITION BY product_category ORDER BY Quarter))
            / NULLIF(LAG(revenue) OVER (PARTITION BY product_category ORDER BY Quarter), 0) * 100, 2
        ) as growth_rate_pct
    FROM quarterly_data
    ORDER BY product_category, Quarter;
    """,
    
    # Test 3: Market share analysis
    """
    -- Test: Market share calculations
    WITH total_revenue AS (
        SELECT SUM(fd.amount) as total
        FROM financial_data fd
        JOIN account a ON fd.account_key = a.Key
        JOIN time t ON fd.time_period = t.Month
        WHERE a.AccountType = '1'
          AND CAST(t.Year AS INTEGER) = 2018
    ),
    category_revenue AS (
        SELECT 
            p.Name as product_category,
            SUM(fd.amount) as category_revenue
        FROM financial_data fd
        JOIN product p ON fd.product_key = p.Key
        JOIN account a ON fd.account_key = a.Key
        JOIN time t ON fd.time_period = t.Month
        WHERE a.AccountType = '1'
          AND CAST(t.Year AS INTEGER) = 2018
        GROUP BY p.Name
    )
    SELECT 
        cr.product_category,
        cr.category_revenue,
        tr.total as total_revenue,
        ROUND((cr.category_revenue / tr.total) * 100, 2) as market_share_pct
    FROM category_revenue cr
    CROSS JOIN total_revenue tr
    ORDER BY market_share_pct DESC;
    """
]

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    print("🧪 COMPLEX FINANCIAL ANALYSIS TEST QUERIES")
    print("=" * 50)
    
    scenarios = create_test_scenarios()
    
    for level, config in scenarios.items():
        print(f"\n📋 {level.upper()}: {config['description']}")
        print(f"Expected SQL Score: {config['expected_sql_score']}")
        print(f"Features: {', '.join(config['expected_features'])}")
        print("-" * 30)
        
        for i, query in enumerate(config['queries'], 1):
            print(f"{i}. {query}")
    
    print(f"\n🎯 TESTING INSTRUCTIONS:")
    print("1. Start with Level 1 queries to verify basic functionality")
    print("2. Progress through levels as system proves stable") 
    print("3. Monitor SQL scores and overall response quality")
    print("4. Test edge cases with Level 5 queries")
    print("5. Use SQL test queries for direct database validation")
