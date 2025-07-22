# TextLayer - Universal Text-to-SQL Analytics Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Database](https://img.shields.io/badge/Database-Universal-purple.svg)

**🚀 Enterprise-grade text-to-SQL interface with universal database support, streaming responses, and intelligent query optimization.**

</div>

TextLayer transforms natural language questions into precise SQL queries across **any database type** - from local DuckDB files to enterprise PostgreSQL clusters. Built for analysts, developers, and business users who need instant data insights without writing SQL.

## ✨ Key Features

### 🌐 Universal Database Support
- **Multi-Database Compatibility**: DuckDB, PostgreSQL, MySQL, SQLite, and more
- **Automatic Detection**: Smart connection string parsing and database type detection
- **SQL Dialect Intelligence**: Automatic query optimization for each database engine
- **Zero Configuration**: Works out-of-the-box with any supported database

### 🎯 Advanced Analytics
- **Natural Language Processing**: Convert plain English to optimized SQL
- **LLM-as-a-Judge**: Automatic response quality evaluation and improvement
- **Context-Aware Analysis**: Database-specific insights and recommendations

### 🏗️ Enterprise Architecture
- **Hybrid API Mode**: Seamless local/remote processing with intelligent fallback
- **Schema Intelligence**: Dynamic schema introspection and optimization
- **Connection Pooling**: Efficient database connection management
- **Error Handling**: Database-specific error messages and troubleshooting

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd textlayer-interview

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
```

### Basic Configuration

```bash
# .env file - Choose your database
DATABASE_TYPE=auto                    # Auto-detect database type
DATABASE_PATH=data/financial_data.db  # Local database file

# OR use direct connection string
DATABASE_URL=postgresql://user:pass@localhost:5432/analytics
```

### Start the Application

```bash
# Development server
export FLASK_APP=application.py
flask run --port=5000

# Production
python application.py
```

Visit `http://localhost:5000` and start asking questions about your data!

## 🗄️ Database Configuration

### Supported Databases

| Database | Status | Connection String | Features |
|----------|--------|-------------------|----------|
| **DuckDB** | ✅ Full Support | `data/database.duckdb` | Advanced analytics, PIVOT/UNPIVOT, fast columnar processing |
| **PostgreSQL** | ✅ Full Support | `postgresql://user:pass@host:5432/db` | ACID compliance, JSON support, full-text search |
| **MySQL** | ✅ Full Support | `mysql://user:pass@host:3306/db` | Window functions, CTEs (8.0+), high concurrency |
| **SQLite** | ✅ Via DuckDB | `data/database.sqlite` | File-based, cross-platform compatibility |

### Configuration Methods

#### Method 1: Environment Variables
```bash
# Option A: Auto-detection (recommended)
DATABASE_PATH=data/financial_data.db
DATABASE_TYPE=auto

# Option B: Direct connection string
DATABASE_URL=postgresql://user:password@localhost:5432/database

# Option C: Component-based
DATABASE_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics
DB_USER=postgres
DB_PASSWORD=secure_password
```

#### Method 2: Runtime Switching
```python
# Switch databases without code changes
from app.services.datastore import create_datastore

# Test different databases
datastore = create_datastore("postgresql://user:pass@host:5432/db")
print(f"Connected to: {datastore.dialect}")
```

## 📊 Current Database Schema

The system includes a comprehensive financial analytics database:

```
📋 Database Tables Overview
├── customer (26,112 records) - Customer master data with segments
├── product (20,428 records) - Product catalog with hierarchies
├── time (360 records) - Time dimension with fiscal calendar
├── account (79 records) - Chart of accounts definitions
├── version (27 records) - Actual vs budget scenarios
├── time_perspective (2 records) - Calculation perspectives
└── other (31 records) - Miscellaneous dimension data
```

### Key Data Dimensions
- **Customer Segments**: Channel, Industry, Location hierarchies
- **Product Lines**: Comprehensive product categorization
- **Time Periods**: Monthly/quarterly/yearly financial calendars
- **Account Types**: Financial account structure and definitions

## 🎯 Usage Examples

### Basic Analysis
```
"How many customers are in each segment?"
"What are the different product categories?"
"Show me the time periods available in the database"
```

### Advanced Queries
```
"Which customer segments have the most customers by industry?"
"Break down product distribution by category and subcategory"
"Show me the account hierarchy and types available"
```

### Business Intelligence
```
"What's the customer distribution across different channels?"
"Which industries have the highest customer concentration?"
"Show me the product mix across different customer segments"
```

## 🏗️ Technical Architecture

### Core Components

#### Universal Database Layer
```
app/services/datastore/
├── base_datastore.py        # Abstract database interface
├── connection_factory.py    # Auto-detection and connection management
├── duckdb_datastore.py     # DuckDB implementation
├── postgresql_datastore.py # PostgreSQL implementation
├── mysql_datastore.py      # MySQL implementation
└── sql_dialect_manager.py  # SQL syntax adaptation
```

#### Intelligence Layer
```
app/services/
├── schema_service.py        # Dynamic schema introspection
├── sql_executor.py          # Universal query execution
└── llm_session.py          # AI-powered query generation
```

#### API Layer
```
app/routes/
├── thread_routes.py         # Chat and streaming endpoints
├── frontend_routes.py       # Web interface
└── routes.py               # Core routing
```

### Database Abstraction Flow

```mermaid
graph TB
    A[Natural Language Query] --> B[LLM Processing]
    B --> C[Schema Service]
    C --> D[Connection Factory]
    D --> E[Database Detection]
    E --> F[SQL Dialect Manager]
    F --> G[Query Optimization]
    G --> H[Database Execution]
    H --> I[Result Formatting]
    I --> J[Streaming Response]
```

## 🔧 Advanced Features

### Streaming Responses
Real-time query processing with live progress indicators:

```javascript
// Frontend automatically handles streaming
fetch('/v1/threads/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
        messages: [{ role: 'user', content: 'Your question' }]
    })
})
```

### LLM-as-a-Judge
Automatic response quality evaluation:

- **Quality Scoring**: 1-10 scale across 5 criteria (Accuracy, Completeness, Clarity, SQL Quality, Data Presentation)
- **Automatic Improvement**: Low-quality responses get enhanced
- **Feedback Integration**: Continuous learning from interactions

### Hybrid API Architecture
Seamless local/remote processing:

```bash
# Local processing (default)
API_MODE=LOCAL

# Remote TextLayer API
API_MODE=REMOTE
TEXTLAYER_API_BASE=https://core.dev.textlayer.ai/v1
```

### Schema Intelligence
Dynamic database introspection and optimization:

- **Auto-Schema Detection**: Discovers tables, columns, and relationships
- **Sample Data Analysis**: Provides context for better query generation
- **Performance Optimization**: Database-specific query tuning

## 🎨 User Interface

### Modern Chat Interface
- **Real-time Streaming**: Live response generation with status indicators
- **SQL Code Blocks**: Syntax-highlighted queries with copy/export options
- **Table Visualizations**: Excel-style data presentation with popup views
- **Action Buttons**: Quick access to common operations

### Table Features
- **Responsive Design**: Works on desktop and mobile
- **Popup Views**: Full-screen table exploration for tables >5 rows
- **Export Options**: CSV, JSON, and clipboard support
- **Search and Filter**: Interactive data exploration

## 📚 API Reference

### Chat Endpoints
```bash
# Standard chat
POST /v1/threads/chat
Content-Type: application/json
{
  "messages": [
    {"role": "user", "content": "Your question"}
  ]
}

# Streaming chat
POST /v1/threads/chat/stream
Content-Type: application/json
{
  "messages": [
    {"role": "user", "content": "Your question"}
  ]
}
```

### Status Endpoints
```bash
# API status
GET /v1/threads/status

# Health check
GET /v1/health

# Database info
GET /v1/database/info
```

## ⚙️ Configuration

The application is configured through environment variables in the `.env` file:

### Core Configuration
```bash
# Flask Configuration
FLASK_CONFIG=DEV  # Options: DEV, TEST, STAGING, PROD
ENVIRONMENT=development

# Database Configuration (Universal)
DATABASE_TYPE=auto                    # auto, duckdb, postgresql, mysql
DATABASE_PATH=data/financial_data.db  # Local file path
DATABASE_URL=                         # Direct connection string

# PostgreSQL/MySQL specific
DB_HOST=localhost
DB_PORT=5432
DB_NAME=textlayer
DB_USER=postgres
DB_PASSWORD=
```

### AI Configuration
```bash
# LLM Configuration
ANTHROPIC_API_KEY=your-anthropic-key
CHAT_MODEL=claude-3-5-sonnet-20241022
EMBEDDING_MODEL=text-embedding-3-small

# Langfuse Configuration (for observability)
LANGFUSE_PUBLIC_KEY=pk-your-public-key
LANGFUSE_SECRET_KEY=sk-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### API Mode Configuration
```bash
# API Mode (LOCAL or REMOTE)
API_MODE=LOCAL

# Remote API settings
TEXTLAYER_API_BASE=https://core.dev.textlayer.ai/v1
TEXTLAYER_API_KEY=your-api-key
```

## 🔧 Development

### Local Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install

# Start development server
flask run --debug --port=5000
```

### Using Make (Recommended)
```bash
# Initialize the project (creates venv, installs dependencies, sets up .env)
make init

# Start the Flask server
make run

# For help with available commands
make help
```

### Using Docker
```bash
# Build the Docker image
docker build -t textlayer-interview .

# Run the container
docker run -p 5000:5000 textlayer-interview

# With environment variables
docker run -p 5000:5000 \
  -v $(pwd):/app \
  --env-file .env \
  textlayer-interview
```

### Environment Configuration
```bash
# Development
ENVIRONMENT=development
DATABASE_PATH=data/dev_data.duckdb

# Staging
ENVIRONMENT=staging
DATABASE_URL=postgresql://staging_user:pass@staging-db:5432/staging

# Production
ENVIRONMENT=production
DATABASE_URL=postgresql://prod_user:pass@prod-db:5432/production
```

## 📁 Project Structure

```
textlayer-interview/
├── app/                          # Application package
│   ├── commands/                 # Command handlers (business logic)
│   ├── controllers/              # API controllers
│   ├── services/                 # Core services
│   │   ├── datastore/           # Universal database layer
│   │   │   ├── base_datastore.py
│   │   │   ├── connection_factory.py
│   │   │   ├── duckdb_datastore.py
│   │   │   ├── postgresql_datastore.py
│   │   │   └── mysql_datastore.py
│   │   ├── schema_service.py    # Schema introspection
│   │   ├── sql_executor.py      # Query execution
│   │   └── llm_session.py       # AI processing
│   ├── routes/                  # API routes
│   ├── middlewares/             # HTTP middlewares
│   ├── utils/                   # Utility functions
│   ├── static/                  # Frontend assets
│   └── prompts/                 # LLM prompts
├── data/                        # Database files
├── application.py               # Application entry point
├── config.py                    # Configuration settings
├── requirements.txt             # Dependencies
├── Dockerfile                   # Container definition
├── Makefile                     # Build automation
├── DATABASE_SETUP.md           # Database setup guide
└── .env.example                # Environment template
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database server status
systemctl status postgresql  # PostgreSQL
systemctl status mysql      # MySQL

# Test connection
ping your-database-host
telnet your-database-host 5432  # PostgreSQL
telnet your-database-host 3306  # MySQL
```

#### Missing Dependencies
```bash
# PostgreSQL
pip install psycopg2-binary sqlalchemy

# MySQL
pip install pymysql sqlalchemy

# All databases
pip install -r requirements.txt
```

#### Configuration Issues
```bash
# Debug mode
export LOG_LEVEL=DEBUG
export DATABASE_DEBUG=true

# Verify configuration
python -c "from config import Config; print(Config.get_database_info())"
```

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
export DATABASE_DEBUG=true
export FLASK_DEBUG=true
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app

# Run tests from the CLI
flask test

# Run tests with code coverage report
flask test --coverage
```

### Test Database Abstraction
```python
# Quick test script
from app.services.datastore import create_datastore, ConnectionFactory
from app.services.schema_service import schema_service
from app.services.sql_executor import Executor

# Test connection factory
connection_string = "data/financial_data.db"
datastore = create_datastore(connection_string)
print(f"✅ Connected to {datastore.dialect}")

# Test schema service
schema_service.initialize()
tables = schema_service.get_table_names()
print(f"📊 Found {len(tables)} tables")

# Test SQL executor
executor = Executor.getInstance()
result = executor.execute("SELECT COUNT(*) as total FROM customer")
print(f"🔍 Query result: {result['data'].values[0][0]} customers")
```


## 🎯 Key Implementation Features

### Universal Database Abstraction
- **BaseDatastore Interface**: Abstract class defining common database operations
- **ConnectionFactory**: Smart detection and instantiation of database connections
- **SQL Dialect Manager**: Database-specific SQL syntax and function mapping
- **Automatic Fallback**: Graceful handling of unsupported features

### LLM-as-a-Judge System
- **Quality Evaluation**: Automatic assessment of response quality across 5 criteria
- **Response Improvement**: Automatic enhancement of low-quality responses
- **Visual Indicators**: Quality scores and improvement status in UI

### Hybrid Architecture
- **Local/Remote Processing**: Seamless switching between local and remote API processing
- **Intelligent Fallback**: Automatic fallback to local processing if remote fails
- **Zero-impact Design**: Same API endpoints work in both modes

---