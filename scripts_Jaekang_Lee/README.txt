Jaekang Lee TextLayer Tech Take Home Assignment Document

I divided the sections into 
1.Engineering (more covered in - textlayer-interview-0.1.3\INSTRUCTIONS.md) 
2.text to sql in depth (how to improve response for enterprise)

# 1. ENGINEERING

Notes:
- I am using gemini api. I integrated with existing litellm Abstraction. I just happen to have Gemini API key available. Reason for not using Doppler - I wanted to use gemini model that I am most familiar with. Also I wanted to explore litellm because litellm was new to me (I mainly used Langgraph for model abstraction layers)
- I modifed apps/commands/threads/process_chat_message.py to better align with my previous agentic experience. (Better structured output for scaling with tool callings)
- Added tool scripts for AI to be aware of possible tools, how to use it with parameters (apps/services/tools)
- The API app simply takes "content": ex."hello how are you?" in the payload and outputs .json response with 
```
content: final response (unstructured)
decision: use_tool vs response
final_response: hardcoded (since it only supports one iteration of decision)
decision: just description of final_response
response: just description of final_response
status: just description of final_response
finish_reason: hardcoded always 'stop'
id: uuid for messsage level
reasoning: helpful for debugging
role
timestamp
```

## High-Level Implementation Steps

### 1. Data Analysis
- Examined the provided database schema
- Identified 7 tables with 60 total columns
- Understood the hierarchical financial structure (accounts, customers, products, time dimensions)

### 2. Schema Processing
- Created a simple script to process table and column schema
- Generated `database_schema_prompt.txt` with structured schema documentation
- Integrated schema directly into prompts (manageable size for this dataset)

### 3. Initial Testing
Tested with three simple queries to validate basic functionality:

**Test 1: "hello how are you?"**
- Status: ✅ SUCCESS
- Result: Proper greeting response without unnecessary SQL execution
- Shows decision logic working correctly (respond vs use_tool)

**Test 2: "how many tables and columns are there in the database?"**
- Status: ✅ SUCCESS  
- Result: 7 tables, 60 columns
- Generated appropriate information_schema query
- Execution time: 36.82ms

**Test 3: "how many customers are there?"**
- Status: ❌ FAILED
- Error: Generated `SELECT COUNT(*) FROM customers;` instead of `customer`
- Demonstrates critical table name resolution challenge

### Results: 2/3 Success Rate


# 2. TEXT TO SQL (Let's talk more about text to SQL)

Now I stopped here because the above showcases API, docker, llm integrations, agents, text to sql, coding practices, data processing, vibe coding and considering the time expected on the assignment is 1 hour, I figured I wanted to address the followings with more weight. There are so many topics to talk about because I have experience building real agentic workflow text to sql, [Woody](https://jaekangai.netlify.app/posts/2506_text_to_sql/2025-06-25-text_to_sql.html).

Let's answer 'Your task will be to improve the quality of the generated responses using techniques such as prompt engineering, LLM-as-a-Judge, RAG, or anything else you can think of.'. 

## Key Enterprise Text-to-SQL Challenges (Based on Woody Experience)

### 1. Table Name Resolution
- **Problem**: Agent wrote 'customers' instead of correct 'customer' table name
- **Solution Approaches**: RAG, ground truth sql example or giving agent tool to get correct table name or columns name (get_table_and_column_names_tool())

### 2. Keywords
- **Scenario**: Finding 'Jason' in the database. We want to find out which table and column 'Jason' is from.
- **Solution**: RAG (lexical search for faster search, okbm25) 

### 3. Keyword + context
- **Scenario**: Finding 'Jason' in the 'User.name' AND 'Account.name'. What do you do?
- **Solution**: RAG (semantic search), require domain context and ground truth examples. 

### 3. SQL Execution Recovery
- **Scenario**: Basic retry mechanism with error memory
- **Woody Implementation**: Keep error in memory to prevent trying same error repeatedly, implement conversation overseer every 3 agentic step to make sure we are making progress. Otherwise, this might hint human in the loop required.

### 4. Conversational Context Management
- **Example**: "How much sold in Canada and US?" followed by "What about France?"
- **Challenge**: What do you put into the RAG? Remember, RAG works by finding best similar match so inserting entire conversation is ineffective.
- **Solution**: RAG system for conversation history and user intention recognition

### 5. Two Primary Text-to-SQL Approaches

**Approach 1: Free-style SQL Generation**
- Pros: Flexible, handles novel queries
- Cons: Unreliable for complex business logic
- Woody Experience: 200+ line SQL queries couldn't be trusted to AI. Free style dominates early prototype but predefined sql dominates as we gather more data, find more patterns.

**Approach 2: Predefined SQL Tools with Parameters**
- Pros: Reliable, tested business logic
- Cons: Limited to predefined patterns
- Woody Implementation: Hybrid approach with both methods

### 6. Large Result Set Management
- **Problem**: SQL returns massive datasets, decision agent needs to read all
- **Solutions**: Instead of returning entire sql executed result back to the agent, automatically store it in memory with pointers. A real example was user asked a question that required first finding matching list of ids and then running a complicated predefined sql function with all the ids to get result. For example asking about total volume about 2 years.

### 7. LLM Judges Evaluation
- **Challenge**: "How much sold today?" with ground truth sql will be different from today vs tomorrow. So if we run a test in the future, value may be different.
- **Solution**: LLM as judge, giving good example of good evaluations and bad evaluations, explaining the context such as time sensitive data and how to compare ground truth sql vs generated sql for correctness if values are different.

### 8. Multi-SQL Agentic Workflows
- **Simple**: "How much sold today?" → Single SQL
- **Medium**: "Sales each day this week?" → Multiple SQL sequence
- **Complex**: "How is salesperson A doing?" → Multi-report generation
- **Strategic**: "How can I make customers happy?" → Advanced analytics pipeline

### 9. Time sensitive jargons
- **Situation**: User asks 'how much sold' + past week vs last week. Including weekdays vs weekends
- **Solution**: Give ground truth examples. Hardcode matching timezone current time in the prompt.


# 3. Technical Implementation Details

### LLM Integration
- **Choice**: Gemini API (available API key)
- **Modifications**: Updated `llm/session.py`, `llm/structured_outputs`, `text_to_sql.py`
- **Abstraction**: Maintained LiteLLM for provider flexibility

### Decision Architecture
Modified text-to-SQL flow for intelligent routing:

**Structured Response Format:**
```python
{
    "decision": "response" | "use_tool",
    "response": "Direct response text",
    "tool": "Tool name",
    "tool_parameters": "Tool parameters",
    "tool_result": "Tool execution result",
    "reasoning": "LLM decision explanation",
    "success": Boolean,
    "error": "Error message if applicable"
}
```

### Tool Framework
- **Design**: Extensible tool system in `llm/tools`
- **Current**: `execute_sql_tool`
- **Future**: `rag_tool`, `calculator_tool`, `predefined_sql_tool`, `schema_check_tool`

## Evaluation Strategy (Woody experience)

### Offline Metrics
- **Manual Labeling**: Started with 100 hand-labeled queries
- **Auto-generation**: Created variants (name swapping, etc.) once base cases worked
- **Human Verification**: All ground truth required human validation
- **Data Separation**: Strict separation of human vs AI-generated test data

### Online Metrics
- **User Engagement**: Interaction duration and frequency
- **Agentic Performance**: Steps taken, latency per step
- **Business Impact**: Query success rate, user satisfaction

## Latency Considerations
- **Primary Bottleneck**: LLM inference time (API calls)

## Recommended Further Reading
https://jaekangai.netlify.app/posts/2506_text_to_sql/2025-06-25-text_to_sql.html


