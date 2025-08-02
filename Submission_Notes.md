## Weaviate Setup:
- Please use the `weaviate-indexer.zip` file to setup weaviate
- It requires `docker` instaled and running
- after unzipping, please run the main.py and if your docker is running it will create schema, row and column indexes from the duckdb local database file. 

## Project features Added
- Implemented a full workflow for text-to-SQL generation.
- The main logic can be found in:  
  `app/services/llm/workflows/text_to_sql_workflow.py`
- The workflow follows these steps:
    1. **Vectorize Query**: vectorizes the user query using OpenAI
    2. **Retrieve Tables Schema (Vector Search)**: uses Weaviate and cosine similarity to retrieve relevant tables and their schema
        - A tables context string is generated from the table schemas
    3. **Row Retrieval (Vector Search)**: Uses the retrieved tables and retrieves samples rows from the row indexes in Weaviate
        - Rows context string is generated from the retrieved rows. 
    4. **Identifying Relevant Columns**: LLM is used to pick the most important columns based on the table schemas retrieved in step 2.
        - Tables context generated in step two will be injected into a prompt together with user query so LLM can select the right columns
    5. **Column Retrieval**: LLMs response from the previous step is used to retireve top-k column data from the columns suggested by the LLM.
        - Columns context string is generated from the retrieved table column values.
    6. **Context Generation**: A comprehensive context is generated from the retrieved tables, rows and columns.
    7. **SQL Generation (LLM Call)**: the comprehensive context from the previous step together with the user query is injected in a SQL generation prompt and LLM is asked to generate the most appropriate prompt to answer the question.
        - The results is syntactically checked to make sure it is a real SQL query.
    8. **Query Rewrite**: In this step, LLM is provided with all the information again includig the generated SQL query and asked to review the query and refine it if needed. 
        - This process can be adjusted so multiple rewrites can be had.
    9. **Final Answer Generation**: The SQL results are returned to the LLM for final answer generation


## Known Limitations and Potential Enhancements
- workflow timeout
- LLM call timeout
- Final Answer Rewrite: Allowing LLM to review its answer and refine it.
- Irrelevant Questions (Edge Case)
- Paraphrasing: generating more questions from the original query
- Subquery generation: I prompted the LLM to generate subqueries at the begining but I think within the tool could also be helpful