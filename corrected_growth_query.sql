-- CORRECTED VERSION of the problematic query
-- Original issues fixed:
-- 1. p."Product Line" -> p.Name (correct column name)
-- 2. Missing proper JOINs to time table
-- 3. Incomplete growth rate calculation
-- 4. Missing time filtering for "past 2 years"
-- 5. Missing account type filtering for revenue

WITH quarterly_revenue AS (
    -- Step 1: Get base quarterly data with proper JOINs
    SELECT 
        p.Name as product_category,
        c.Channel,
        t.Year,
        t.Quarter,
        CONCAT(t.Year, '-Q', t.Quarter) as quarter_label,
        SUM(fd.amount) as total_revenue
    FROM financial_data fd
    JOIN product p ON fd.product_key = p.Key
    JOIN customer c ON fd.customer_key = c.Key  
    JOIN time t ON fd.time_period = t.Key        -- Fixed: proper time JOIN
    JOIN account a ON fd.account_key = a.Key
    WHERE a.AccountType = 'Revenue'              -- Fixed: filter for revenue only
      AND t.Year >= (SELECT MAX(Year) - 1 FROM time)  -- Fixed: past 2 years filter
    GROUP BY p.Name, c.Channel, t.Year, t.Quarter
),
growth_calculations AS (
    -- Step 2: Calculate growth rates with proper window functions
    SELECT 
        product_category,
        Channel,
        Year,
        Quarter,
        quarter_label,
        total_revenue,
        LAG(total_revenue) OVER (
            PARTITION BY product_category, Channel 
            ORDER BY Year, Quarter                   -- Fixed: proper ORDER BY
        ) as previous_quarter_revenue,
        CASE 
            WHEN LAG(total_revenue) OVER (
                PARTITION BY product_category, Channel 
                ORDER BY Year, Quarter
            ) IS NOT NULL AND LAG(total_revenue) OVER (
                PARTITION BY product_category, Channel 
                ORDER BY Year, Quarter
            ) > 0
            THEN ROUND(
                ((total_revenue - LAG(total_revenue) OVER (
                    PARTITION BY product_category, Channel 
                    ORDER BY Year, Quarter
                )) / NULLIF(LAG(total_revenue) OVER (  -- Fixed: complete NULLIF syntax
                    PARTITION BY product_category, Channel 
                    ORDER BY Year, Quarter
                ), 0)) * 100, 2
            )
            ELSE NULL
        END as growth_rate_pct
    FROM quarterly_revenue
),
ranked_growth AS (
    -- Step 3: Rank combinations by growth rate
    SELECT 
        *,
        RANK() OVER (
            PARTITION BY quarter_label 
            ORDER BY growth_rate_pct DESC NULLS LAST
        ) as growth_rank
    FROM growth_calculations
    WHERE growth_rate_pct IS NOT NULL  -- Only include records with calculable growth
)
-- Final output with highest growth combinations highlighted
SELECT 
    product_category,
    Channel,
    quarter_label,
    total_revenue,
    previous_quarter_revenue,
    growth_rate_pct,
    growth_rank,
    CASE 
        WHEN growth_rank <= 3 THEN '🏆 TOP PERFORMER'
        WHEN growth_rate_pct >= 10 THEN '📈 HIGH GROWTH'
        WHEN growth_rate_pct < 0 THEN '📉 DECLINING'
        ELSE '➡️ STABLE'
    END as performance_indicator
FROM ranked_growth
ORDER BY quarter_label, growth_rank, product_category, Channel;

/* 
QUERY EXPLANATION:
==================
1. Uses CTEs for clear, step-by-step logic
2. Properly joins all dimension tables
3. Filters for revenue accounts only
4. Includes past 2 years time filtering
5. Uses correct column names (p.Name not p."Product Line")
6. Complete growth rate calculations with NULLIF
7. Ranks combinations by growth performance
8. Adds performance indicators for business insight

KEY FIXES FROM ORIGINAL:
========================
❌ p."Product Line" -> ✅ p.Name
❌ Missing time JOIN -> ✅ JOIN time t ON fd.time_period = t.Key
❌ Incomplete NULLIF -> ✅ Complete division with null handling
❌ No time filtering -> ✅ WHERE t.Year >= (past 2 years)
❌ No account filtering -> ✅ WHERE a.AccountType = 'Revenue'
❌ Basic query -> ✅ Multi-step CTE with ranking and insights
*/
