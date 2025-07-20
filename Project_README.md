# Text-to-SQL Chat Agent

This project implements a tool-augmented conversational agent that transforms natural language queries into executable SQL against a DuckDB database. It leverages OpenAI's GPT-4o for classification, schema understanding, and SQL generation, and integrates structured outputs, tool calling, and schema analyzers for robust functionality.



##  Project Goal

To create an LLM-powered assistant that can:

- Classify user queries.
- Determine if a question is related to data (triage).
- Decide if a query is already SQL or needs translation.
- Perform schema analysis (via LLM or embedding).
- Generate SQL and execute it on DuckDB.
- Return structured, human-readable responses.



##  Features Completed

### 1. **Query Classification**
- Used `LLMPromptBuilder.triage_prompt` to classify queries as:
  - `DATA_QUESTION`
  - `OUT_OF_SCOPE`
- Only `DATA_QUESTION`s are forwarded to further steps.

### 2. **LLM SQL Detection (Removed)**
- Initially checked if the input was already SQL using string prefixes like `SELECT`, `WITH`, `SHOW`.
- Replaced with LLM-based classification via `sql_or_nl_prompt`.
- Later **removed this step** and relied solely on LLM tool-calling behavior.

### 3. **Tool Calling with Function Signatures**
- Used OpenAI function calling (`tool_call`) to link the query to the `text_to_sql()` tool.
- If tool calling was not triggered, returned the LLM message as-is.

### 4. **Schema Analysis**
- Dual-path analysis using:
  - **GPT-based** schema grounding (`SchemaAnalyzerTool`)
  - **Embedding-based** fallback (`EmbeddingSchemaAnalyzer`)
- Extracts relevant tables and fields before query generation.

### 5. **SQL Generation**
- Used the `generate_sql_from_prompt()` function with a schema-aware prompt.
- Output includes SQL and explanation in a structured JSON format.

### 6. **Execution and Output Formatting**
- SQL is executed against `DuckDBDatastore("app/data/data.db")`.
- Response returned with:
  - `sql_query`
  - `result_markdown`
  - `natural_language_answer`



##  Design Decisions

- **LLM-only flow**: No heuristic checks (like `.startswith("SELECT")`). Everything is handled via GPT.
- **Observability**: Langfuse decorators like `@observe()` are used to trace tool and model performance.
- **Fallbacks**: Always fall back to safe assistant responses on failure.
- **Modular tool design**: The tool is decoupled and invoked via OpenAI tool calling.
- **Structured prompt building**: Prompt engineering isolated in `LLMPromptBuilder`.


##  Prompt Engineering

### Triage Prompt
Classifies the intent of the question.

```json
{
  "queryType": "DATA_QUESTION" | "OUT_OF_SCOPE"
}
```


### SQL Generation Prompt
Uses schema + user query to output:

```json
{
  "query": "SELECT ...",
  "explanation": "This query does ..."
}
```


##  Dependencies

- `openai`
- `duckdb`
- `langfuse`
- `vaul`
- `pandas`


##  Configuration

Environment variables (`.env`):

```env
FLASK_CONFIG=DEV
OPENAI_API_KEY=sk-xxx
CHAT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```


##  Schema JSON Construction

To power semantic search and SQL generation, I built structured schema representations of our database.

### 1. Raw Schema JSON (Tables & Fields)

I parsed the database (e.g., DuckDB) to extract:
- Table names
- Column (field) names for each table

```json
{
  "tables": ["product", "customer", "order"],
  "fields": {
    "product": ["Key", "Name", "Price"],
    "customer": ["ID", "Name", "Email"]
  }
}
```

#### Preprocessing

The `preprocessing/` folder contains the script used to generate a JSON schema file listing the database tables, their fields, and corresponding descriptions. This structured schema is essential for enabling accurate SQL generation from natural language queries. The output files are saved in the `models/` folder.


### 2. Schema Summaries

To improve the LLM's understanding of the database structure and semantics, I optionally generated **natural language summaries** (field descriptions) for each column. These were used as grounding context for both the **LLM-based** and **embedding-based** schema analyzers.

####  Methods Used to Create Summaries:
- **Heuristics** based on column names  
  _(e.g., a column named `Price` is likely numeric and represents cost)_
- **Sample values** from the database  
  _(e.g., recognizing that `product.Key` follows an alphanumeric pattern)_
- **LLM assistance** to generate descriptions automatically when needed

####  Example `field_descriptions` JSON:
```json
{
  "product.Key": "Unique product identifier",
  "product.Name": "Name of the product",
  "product.Price": "Selling price of the product"
}
```

These summaries make it easier for the system to infer meaning, especially when users ask abstract or ambiguous questions. They play a crucial role in both semantic similarity (embedding search) and prompt grounding (LLM tools).

### LLM vs. Embedding Schema Analysis

Our system uses two complementary methods for identifying relevant tables and fields:
 **LLM-based schema analysis** and **embedding-based search**. 
 The LLM-based approach uses prompt engineering to directly ask a language model which parts of the schema are relevant to a user's query. This method excels at complex reasoning and understanding vague or abstract questions. In contrast, the embedding-based method uses vector similarity between the user query and precomputed embeddings of schema elements. It is lightweight, fast, and robust to minor variations in phrasing. By combining both, I balance **precision and speed**—using LLMs for deeper contextual understanding, and embeddings for quick, scalable relevance filtering.

###  Key Components

- `schema_summarizer`: Extracts concise descriptions of tables and fields from database content using an LLM.
- `llm_prompt_builder`: Constructs structured prompts for LLMs to classify and process user queries intelligently.
- `embedding_schema_analyzer`: Uses vector embeddings to match user queries with relevant tables and fields.
- `sql_generator`: Converts natural language queries and schema information into executable SQL queries.
- `schema_analysis`: Uses LLMs to determine whether a query is in scope and to identify relevant tables and fields.


## Future Work
While the core functionality of converting natural language to SQL and executing queries works reliably, there are several areas identified for future improvement:

- Improve error recovery for failed SQL executions (e.g., re-ask user or regenerate).
- Add metadata logging for each query execution.
- Extend schema analysis to handle relationships and joins.
- Include field-level summaries (e.g., datatypes, value ranges).
- Add more flexible output formats (e.g., chart, table download).
- Enable structured output parsing via `StructuredOutput` class pattern.
- I created a set of test cases for different types of user queries—simple column lookups, joins, aggregations, edge cases (e.g., ambiguous fields), and out-of-scope questions. These cases have been useful in manual validation, but automated testing and CI integration remain to be implemented.
- I initially planned to use OpenAI's function-calling tools to handle structured outputs for tool calls in a more reliable and typed manner. However, due to time constraints, this part wasn't fully implemented. Right now, responses are parsed manually from raw JSON output. Adding structured tool definitions and integrating a validation layer (e.g., using Pydantic) will significantly increase robustness and reduce parsing errors.
- Though the system already uses both LLM and embedding-based analyzers, I could further improve LLM prompts for multi-table joins, implicit aggregations, and default filters. Adding feedback loops (e.g., reranking based on results) is another avenue to explore.
- Adding a lightweight UI for testing, viewing SQL logs, and tracking usage would make the tool easier to maintain and extend. Capturing metrics (e.g., query success rate, fallback frequency) would also help identify where to fine-tune performance.
- Currently, the query processing flow is static, and each input is handled once through classification, schema analysis, and SQL generation. In future iterations, I plan to adopt an agentic approach where the LLM actively evaluates the generated SQL and its results. If the output is ambiguous, incorrect, or insufficient, the agent will iteratively refine the query or schema context, enabling a more dynamic and self-correcting pipeline.
- Several enhancements can be made to improve maintainability and user experience. First, system prompts should be moved to separate configuration or template files instead of being regenerated in code, allowing easier updates and experimentation. Second, incorporating chat memory would enable the system to maintain context across multiple turns, supporting more natural, conversational interactions with users over time—essential for a true chat experience.
- A small test set has been created to evaluate the model using real-world queries. The evaluation will check SQL accuracy, syntax validity, and the clarity of the natural language explanations. LLM-as-a-Judge methods can be used to assess correctness and relevance.




## Running the App

1. Set environment variables.
2. Launch the FastAPI or Flask server.
3. Send a POST request to `/v1/threads/chat` with your query.

Example:

```json
{
  "messages": [{"role": "user", "content": "Show 5 keys from the product table"}]
}
```
