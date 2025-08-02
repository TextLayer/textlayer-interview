# TextLayer.ai Interview - Text-to-SQL Agent

An intelligent system that converts natural language questions into SQL queries for financial data analysis. Built with **agentic error recovery**, **RAG**, and **knowledge graphs**.

## 🚀 Quick Start

### Run with Docker Compose (Recommended)

```bash
# Start all services
DOPPLER_TOKEN=your_token_here make start

# Stop all services
make stop

# Ingest the database (first time only)
curl -X POST "http://localhost:5001/v1/threads/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source": "app/data/fpa_dev.db"}'
```

**Access the app:**
- 🌐 **Chat UI**: http://localhost:8501 (with direct links to other services)
- 🔧 **API**: http://localhost:5001  
- 🗃️ **Vector DB Dashboard**: http://localhost:6333/dashboard

### Local Development

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Install dependencies  
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run Flask API
FLASK_APP=application.py python -m flask run --port=5001

# Run Streamlit UI (separate terminal)
streamlit run streamlit_app.py --server.port=8501
```

## ✨ What I Built

### 🧠 **Agentic Architecture**
- **Self-correcting system** that learns from SQL execution errors
- **Automatic retry** with error context for smarter second attempts
- **Graceful failure** when queries can't be resolved

### 🔍 **Advanced RAG**  
- **Three-phase data pipeline**: Schema extraction → Column filtering with LLMs → Vector embedding
- **Multi-layer filtering system**:
  - **Pre-filtering**: Regex patterns skip `Key`, `Id`, `ParentId` columns automatically
  - **LLM-as-a-judge**: Analyzes sample values to distinguish business vs technical data
- **Intelligent sample analysis**: LLM analyzes 15 sample values per column for filtering decisions
- **Massive noise reduction**: 479 → 13 batches (97.5% reduction) through smart filtering
- **Qdrant integration**: 1,536-dimensional embeddings with cosine similarity search
- **Batch processing**: 100 embeddings per batch with threading control (`time.sleep(0.1)`)
- **Rich metadata**: Each vector includes table, column, data type, and location context

### 🕸️ **Knowledge Graphs**
- **NetworkX implementation**: Graph-based schema representation with nodes and edges
- **Hierarchical structure**: Schema → Tables → Columns with typed relationships
- **Node metadata**: Each node includes type, name, data_type attributes
- **Serialization**: Graphs saved as pickle files (`fpa_dev_schema.pkl`) for fast startup
- **Context injection**: Rich schema context provided to LLM for informed SQL generation
- **Relationship mapping**: `has_table` and `has_column` edge relationships

### 🎯 **Prompt Engineering**
- **Agentic chat prompt**: Comprehensive prompt handling schema context, domain values, and error history
- **DuckDB syntax optimization**: Specific guidance for DuckDB SQL patterns (`SHOW TABLES;`, `DESCRIBE table;`)
- **Error recovery examples**: Prompt includes examples of how to learn from SQL execution errors
- **Column filtering prompt**: Specialized LLM-as-a-judge prompt with explicit KEEP/REJECT rules
- **Business vs technical classification**: Detailed examples of business terms vs system codes
- **Conservative filtering approach**: "When in doubt, reject" philosophy for high-quality data
- **Context-aware prompts**: Dynamic prompts that adapt based on available schema and domain data

## 🏗️ Architecture

### Request Flow
```
                   ┌─ RAG Context (Domain Values) ──┐
User Question ──── ┤                                ├─ LLM Tool Call → SQL Execution
                   └─ Knowledge Graph (Schema) ─────┘                         ↓
                                                                        DuckDB Query
                                                                              ↓
                                                                      Success/Error
                                                                              ↓
                                                             Error Recovery Loop (Append & Retry)
```


### Ingestion Flow
```
                          ┌─ Schema Extraction ──→ Knowledge Graph (NetworkX)
Data Source (DuckDB) ──── ┤                                    
                          └─ Column Analysis ────→ Domain Values ──→ Embedding ──→ Vector DB
                                    ↓
                              LLM Filtering (LLM-as-a-judge)
                           (Business vs Technical)
```

### Services
- **Flask API** (Port 5001): 
  - Agentic chat processing with error recovery
  - DuckDB SQL execution engine
  - RAG context orchestration
  - Knowledge graph loading
- **Qdrant Vector DB** (Port 6333): 
  - 1,216 business domain value embeddings
  - Cosine similarity semantic search
  - Persistent vector storage with metadata
- **Streamlit UI** (Port 8501): 
  - Real-time streaming chat interface
  - Structured response display (SQL + Results + Errors)
  - Query examples and history management

## 🛡️ Technology Stack

### **Core AI/ML**
- **LiteLLM**: Unified interface for multiple LLM providers (OpenAI, Anthropic, AWS Bedrock)
- **OpenAI Embeddings**: `text-embedding-3-small` for 1,536-dimensional vectors
- **Toolkit**: LLM tool calling and structured outputs with Pydantic
- **Qdrant**: High-performance vector database for semantic search

### **Backend & Data**
- **Flask**: RESTful API with modular architecture (controllers, services, commands)
- **DuckDB**: In-memory/file-based SQL analytics database for financial data
- **NetworkX**: Graph library for schema knowledge representation
- **Pandas**: DataFrame processing for batch operations and SQL results

### **Infrastructure & DevOps**
- **Docker Compose**: Multi-service orchestration with persistent volumes
- **Streamlit**: Interactive web UI with real-time chat components
- **Doppler**: Secure secret management for API keys and configuration
- **Langfuse**: LLM observability, prompt management, and request tracing

---