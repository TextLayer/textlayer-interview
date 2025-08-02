from typing import List, Dict


def column_filter_prompt(**kwargs) -> List[Dict[str, str]]:
    """
    This prompt is used to judge whether a column contains domain values.
    """
    return [
        {
            "role": "system",
            "content": """You are analyzing database columns to identify business domain terms for text-to-SQL queries.

            TASK: Determine if a column contains searchable business domain terms.

            KEEP (Business Domain Terms - Based on Actual FPA Database):
            
            FINANCIAL TERMS (account.Name):
            - "Gross Margin", "Other Revenue", "Manufacturing Overhead"
            - "Average Selling Price", "Cost of Sales %", "Direct Labor %"
            - "Bookings", "Churn", "Unearned Revenue", "Volume"
            - "Net New Customers", "Customers Acquired"
            
            GEOGRAPHIC LOCATIONS (customer.Location):
            - "US-CA", "US-TX", "CA-BC", "CA-AB", "FR", "AU", "BR", "SE", "ZA", "FI"
            
            PRODUCT LINES (product."Product Line"):
            - "Product Line A", "Product Line B", "Product Line C", "Product Line D"
            
            VERSION NAMES (version.Name - business-friendly):
            - "Prior Quarter Actual", "6+6 Forecast", "Scenario C", "Actual"
            - "Prior Year Variance", "PY Var (%)", "Scenario B Variance"
            
            TIME PERIODS (time.Name, time.Year):
            - Month names: "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
            - Years: "2018", "2019", "2020", "2021", "2022", "2023", "2024"

            REJECT (System Codes - Based on Actual FPA Database):
            
            VERSION KEYS (version.Key - all technical codes):
            - "PQVAR_PCT", "Q1FOR_C", "SCN_LOW", "BUD02", "PYACT", "SCN_A"
            - "PYVAR_PCT", "VAR_SCNA", "ACT", "Q1FOR", "BUD01", "PQACT"
            - "Q1FOR_B", "VAR_SCNC", "PYVAR", "SCN_B", "SCN_C"
            - Any Key column with underscores, abbreviations, or mixed case
            
            NUMERIC CODES (account.AccountType, etc.):
            - Simple numbers: "1", "2", "3", "4", "0"
            - No business meaning to users
            
            SYSTEM IDENTIFIERS:
            - Any "Key", "ParentId" column values
            - Technical abbreviations with underscores
            - Mixed alphanumeric codes without clear business meaning
            
            CRITICAL DECISION RULES:
            
            **AUTOMATIC REJECT** - No analysis needed:
            1. **Column name contains "Key"**: ALWAYS REJECT (system identifiers)
            2. **Column name contains "ParentId"**: ALWAYS REJECT (hierarchy codes)
            3. **Column name contains "Id"**: REJECT (likely system codes)
            4. **Sample values are mostly codes like "Q1FOR_C", "PYVAR_PCT"**: REJECT
            5. **Sample values are simple numbers "1", "2", "3"**: REJECT (type codes)
            6. **Technical field names**: calculationmethod, tcmethod, versiontype, status, etc. → REJECT
            
            **AUTOMATIC KEEP** - Clear business value:
            1. **Column name "Name" with readable values**: KEEP
            2. **Column name "Location" with geographic codes**: KEEP  
            3. **Month names, years, business terms**: KEEP
            4. **Product lines, account names, customer info**: KEEP
            
            **BE VERY CONSERVATIVE**: When in doubt about technical vs business terms, REJECT.
            Users search for "Gross Margin", "US-CA", "Product Line A" - not "Q1FOR_C".
            
            **PERFORMANCE RULE**: Only approve columns with HIGH business value.
            Better to miss some edge cases than flood the vector DB with low-value data.
            
            **QUALITY OVER QUANTITY**: We want 100-500 high-quality business terms, 
            not 10,000+ mixed technical/business values.
            
            CONTEXT: Financial/BI database. Users search for account types, customer segments, product categories, time periods, and business metrics.

            Focus on terms users would naturally search for, not internal system identifiers.""",
        }
    ]
