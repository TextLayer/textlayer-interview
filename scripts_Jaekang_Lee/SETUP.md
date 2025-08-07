# Simple TextLayer Text-to-SQL System Setup Guide

## Please check out *`scripts/README.txt`* first!

This guide will help you set up and run the TextLayer text-to-SQL system locally. Note that you will require gemini api key but in case you don't have access to google api key, I recorded example runs. 

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

## Quick Start

### 1. Clone and Navigate to Project
```bash
git clone <repository-url>
cd textlayer-interview-0.1.3
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root

### 4. Start Database
```bash
# Start PostgreSQL with Docker Compose
docker-compose up -d
```

### 5. Run the Application
```bash
# Start the Flask application
python application.py
```

The application will be available at `http://localhost:5000`

## Testing the System

### Option 1: Interactive Testing Script
```bash
python scripts/test_chat.py
```

This script will prompt you to enter queries interactively.

### Option 2: Direct API Testing

You can test the API directly using curl or any HTTP client:

```bash
curl -X POST http://localhost:5000/v1/threads/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "how many tables are there in the database?"}'
```

## Demo Output (No API Key Required)

If you don't have a Gemini API key, here are the expected outputs for the test queries:

### Test 1: "hello how are you?"
```json
{
  "correlation_id": "6781c9bf-382e-46cb-807b-22107c6e921f",
  "payload": [
    {
      "content": "hello how are you?",
      "role": "user"
    },
    {
      "content": "Hello! I am an AI, so I don't have feelings, but I am ready to help you. How can I assist you today?",
      "decision": "response",
      "final_response": {
        "decision": "response",
        "response": "Hello! I am an AI, so I don't have feelings, but I am ready to help you. How can I assist you today?",
        "status": "direct_response"
      },
      "finish_reason": "stop",
      "id": "c674ce49-086d-4480-99b3-90534ca211e9",
      "reasoning": "The user query is a greeting and does not require tool usage. According to the guidelines, greetings should be handled by responding directly.",
      "role": "assistant",
      "timestamp": ["2025-08-06 23:36:46.689837048"]
    }
  ],
  "status": 200
}
```

### Test 2: "how many tables and columns are there in the database?"
```json
{
  "correlation_id": "cee3fa6a-226f-66ad-966e-191b01ceaa4c",
  "payload": [
    {
      "content": "how many tables and columns are there in the database?",
      "role": "user"
    },
    {
      "content": "I found the answer to your question! Here are the results:\n\n|   table_count |   column_count |\n|--------------:|---------------:|\n|          7.00 |          60.00 |\n\nQuery executed successfully in 36.82ms, returning 1 row(s).",
      "decision": "use_tool",
      "final_response": {
        "decision": "use_tool",
        "execution_time_ms": 36.8196964263916,
        "query": "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')) AS table_count, (SELECT count(*) FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog', 'information_schema')) AS column_count;",
        "result": "|   table_count |   column_count |\n|--------------:|---------------:|\n|          7.00 |          60.00 |",
        "row_count": 1,
        "status": "success",
        "tool": "execute_sql_tool",
        "tool_parameters": {
          "explanation": "Counts the total number of tables and columns in the database by querying the information_schema, excluding system tables.",
          "sql": "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')) AS table_count, (SELECT count(*) FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog', 'information_schema')) AS column_count;"
        }
      },
      "finish_reason": "stop",
      "id": "bbee3961-926e-4c4e-91e5-d74885a1a7c0",
      "reasoning": "The user is asking for a count of tables and columns, which requires querying database metadata. The `execute_sql_tool` is appropriate for this data query.",
      "role": "assistant",
      "timestamp": ["2025-08-06 23:38:25.812054565"]
    }
  ],
  "status": 200
}
```

### Test 3: "how many customers are there?" (Expected Failure)
```json
{
  "correlation_id": "fd799074-5039-406c-ba05-b6d1f4aab2f2",
  "payload": [
    {
      "content": "how many customers are there?",
      "role": "user"
    },
    {
      "content": "I'm sorry, I encountered an issue while trying to retrieve the data. Please try again later.",
      "decision": "response",
      "final_response": {
        "decision": "response",
        "response": "I'm sorry, I encountered an issue while trying to retrieve the data. Please try again later.",
        "status": "direct_response"
      },
      "finish_reason": "stop",
      "id": "c28f5c6c-ea5c-4126-b2c1-221b73bf7767",
      "reasoning": "Tool execution failed: SQL execution failed after 4 attempts. Last error: Catalog Error: Table with name customers does not exist!\nDid you mean \"customer\"?\n\nLINE 1: SELECT COUNT(*) FROM customers;\n                             ^",
      "role": "assistant",
      "timestamp": ["2025-08-06 23:30:28.257878727"]
    }
  ],
  "status": 200
}
```

## Test Results Summary

✅ **Test 1**: "hello how are you?" - **SUCCESS**
- Properly routes non-SQL queries to direct response
- Shows decision logic working correctly

✅ **Test 2**: "how many tables and columns are there?" - **SUCCESS** 
- Generates correct information_schema query
- Returns accurate result: 7 tables, 60 columns
- Execution time: 36.82ms

❌ **Test 3**: "how many customers are there?" - **FAILED**
- Demonstrates table name resolution challenge
- Generated `customers` instead of correct `customer` table
- Shows error recovery system in action

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  Decision Agent  │───▶│   SQL Tool      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Direct Response  │    │   Database      │
                       └──────────────────┘    └─────────────────┘
```

## Development

### 📁 Project Structure

```
textlayer-interview-0.1.3/
├── app/                                    # Main application code
│   ├── commands/                           # Command handlers
│   │   └── threads/                        # Thread management
│   │       └── process_chat_message.py     # Chat message processing
│   ├── services/                          # External services integration
│   │   └── llm/                           # LLM service layer
│   │       ├── tools/                     # LLM tools (SQL execution, etc.)
│   │       │   └── text_to_sql.py         # Text-to-SQL tool implementation
│   │       └── structured_outputs/        # Structured response schemas
│   │           └── text_to_sql.py         # Text-to-SQL response format
├── scripts/                               # 🔧 Development & Testing Scripts
│   ├── README.txt                         # 📖 Technical deep-dive & for interviewer
│   ├── test_chat.py                       # 🧪 api testing script
│   ├── generate_schema.py                 # 🏗️ Database schema extraction
│   ├── connect_db.py                      # 🔗 Database connection utilities
│   ├── database_schema.json              # 📊 Extracted schema (JSON format)
│   ├── database_schema_prompt.txt         # 📝 Schema for LLM prompts
│   ├── docker_command.md                  # ignore
├── tests/                                 # Test cases
├── application.py                         # Application entry point
├── config.py                             # Configuration settings
├── requirements.txt                       # Dependencies
├── Dockerfile                            # Container definition
├── docker-compose.yml                    # Multi-container setup
├── DATABASE_EDA.md                        # Database analysis documentation
├── SETUP.md                              # Setup and run guide (this file)
└── .env.example                          # Environment variable template
```

### 📋 Scripts Directory Details

| File | Purpose | Usage |
|------|---------|-------|
| `README.txt` | **Interview Discussion Guide** | Comprehensive technical analysis and enterprise considerations |
| `test_chat.py` | **Interactive Testing** | `python scripts/test_chat.py` - Test chat API with custom queries |
| `generate_schema.py` | **Schema Extraction** | Extracts database schema into JSON and prompt formats |
| `connect_db.py` | **Database Utilities** | Database connection and query utilities |
| `database_schema.json` | **Structured Schema** | Machine-readable database schema |
| `database_schema_prompt.txt` | **LLM Context** | Human-readable schema for LLM prompts |
| `text_to_sql_test_results_*.csv` | **Test Results** | Execution logs and performance metrics |
| `docker_command.md` | **Docker Reference** | Quick Docker setup commands |
| `advanced_text_to_sql_engineering_guide.md` | **Engineering Guide** | Detailed implementation strategies |

### Adding New Tools
1. Create tool in `app/services/llm/tools/`
2. Register in tool registry
3. Add structured output schema if needed
4. Test with `scripts/test_chat.py`

---

*For detailed technical discussion and enterprise considerations, see `scripts/README.txt`*
