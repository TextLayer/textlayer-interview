# Textlayer Core

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-42%25-yellow.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Maintained](https://img.shields.io/badge/maintained-yes-green.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

</div>

**Textlayer Core** is a comprehensive Flask application template for building AI-powered services. It provides a structured foundation with built-in integrations for AI services, search capabilities, and observability—designed to help teams quickly leverage Large Language Models (LLMs) while maintaining consistent architecture patterns.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
  - [Application Flow](#application-flow)
  - [Langfuse Integration](#langfuse-integration)
  - [LiteLLM Integration](#litellm-integration)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## 🔍 Overview

Textlayer Core is a powerful template for building AI-powered applications and services within organizations. It provides a structured foundation with built-in integrations for AI services, search capabilities, and comprehensive observability. Designed as an AI enablement layer, it helps teams quickly integrate and leverage Large Language Models (LLMs) in their applications while maintaining a consistent architecture and deployment pattern.

### Key Use Cases

This repository serves as a starting point for:
- **Building internal AI tools and services** with a consistent architecture
- **Creating LLM-powered APIs** for your organization with built-in observability
- **Implementing consistent patterns** for AI-enabled applications across teams
- **Establishing robust monitoring** for AI components in production environments

## ✨ Features

Textlayer Core comes with a rich set of features to accelerate your AI application development:

| Feature | Description |
|---------|-------------|
| **Modular Flask Structure** | Well-organized application structure following best practices |
| **LiteLLM Integration** | Unified interface to access multiple LLM providers (OpenAI, Anthropic, etc.) |
| **Search Capabilities** | Built-in OpenSearch integration for vector, keyword and hybrid search |
| **AWS Integration** | Ready-to-use cloud deployment configurations |
| **Langfuse Observability** | Comprehensive prompt management and AI observability |
| **Docker Deployment** | Containerized deployment for consistent environments |
| **Environment Config** | Flexible configuration management for different environments |
| **Command Pattern** | Clean separation of business logic from request handling |

## 🏛️ Architecture

### Application Flow

The Textlayer Core template implements a clean, modular architecture for AI applications:

1. **Request Handling**: 
   - Controllers receive and process incoming API requests
   - Validation through schema definitions

2. **Command Processing**:
   - Business logic is organized in command handlers
   - Separation of concerns with distinct command modules

3. **Service Integration**:
   - External services wrapped in service modules
   - Modular design for extensibility

4. **Response Handling**:
   - Structured API responses
   - Error handling with custom error types

### Langfuse Integration

[Langfuse](https://langfuse.com/docs) is integrated throughout the application to provide prompt management and observability:

1. **Prompt Management**:
   - Centralized storage and versioning of prompts
   - A/B testing of different prompt variants
   - Prompt templates with variable substitution
   - Prompt performance analytics

2. **Observability with Trace Logging**:
   - Process flows create Langfuse traces
   - Key processing steps are tagged with observe markers
   - Spans capture duration and metadata for performance analysis
   - Scores and feedback can be logged for quality assessment

Example trace tags implementation:

```python
# use the @observe tag for logging traces
@observe()
def add_numbers(a: int, b: int) -> int:
    """
    Example function demonstrating Langfuse trace logging.
    
    Args:
        a: First number to add
        b: Second number to add
        
    Returns:
        Sum of the two numbers
    """
    return a + b
```

The trace logging enables detailed analytics on:
- End-to-end processing time
- LLM response latency
- Error rates and types
- Prompt effectiveness
- User feedback correlation

For more information on Langfuse integration, see the [Langfuse Documentation](https://langfuse.com/docs/sdk/python).

### LiteLLM Integration

The application uses [LiteLLM](https://docs.litellm.ai/) in the `services/llm` module to provide a unified interface for multiple LLM providers:

1. **Provider Agnostic Interface**:
   - Single interface to access multiple LLM providers (OpenAI, Anthropic, etc.)
   - Simplified model switching and fallback mechanisms
   - Standardized input/output formats

2. **Features Utilized**:
   - Model routing
   - Cost tracking and budget management
   - Caching and rate limiting
   - Automatic retries and error handling

3. **Dynamic Model Registry**:
   - Automatically updated model registry from LiteLLM
   - Stores token limits and embedding dimensions
   - Provides consistent access to available models
   - Simple CLI commands for management

Example LiteLLM usage:

```python
from litellm import completion

response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Analyze this content..."}],
    temperature=0.7,
    max_tokens=2000
)
```

LiteLLM allows the application to easily switch between different LLM providers without changing the codebase, enabling model experimentation and fallback strategies.

For more information on LiteLLM integration, see the [LiteLLM Documentation](https://docs.litellm.ai/).

### Model Registry

The application includes a dynamic model registry system that provides access to the latest available LLM models:

1. **Automated Updates**:
   - Automatically retrieves model information from LiteLLM
   - Regular updates via scheduled GitHub Actions workflow
   - Manual updates available through CLI commands

2. **Registry Features**:
   - Stores model metadata (token limits, embedding dimensions)
   - Separates chat models and embedding models
   - Provides fallback mechanism for missing models
   - Environment variable configuration for defaults

3. **CLI Commands**:
   - `flask update_models`: Update the model registry from LiteLLM
   - `flask list_models`: Display available models in the registry
   - `make update-models`: Makefile command for easy updates

Example model registry usage:

```python
from app.services.llm.session import LLMSession

# Initialize with specific models (or use defaults from config)
session = LLMSession(
    chat_model="gpt-4o",
    embedding_model="text-embedding-3-large"
)

# Session automatically validates models against registry
```

## 📋 Prerequisites

- Python 3.12
- [Docker](https://docs.docker.com/engine/install/) (for building and testing the container)
- [Doppler](https://dashboard.doppler.com/register) account & [Doppler CLI](https://docs.doppler.com/docs/install-cli) (recommended for secrets management)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (if deploying to AWS)
- Access to LLM providers (OpenAI, Anthropic, etc.)
- Langfuse account for prompt management and observability

## 🚀 Installation

### Local Development

1. Clone the repository

```bash
git clone https://github.com/Textlayer/textlayer-core.git
cd textlayer-core
```

2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Set up environment variables

```bash
cp .env.example .env  # Create from example if available
# Edit .env with your configuration
```

### Using `uv` for Dependency Management

This project supports the use of the `uv` Python package manager for managing dependencies:

- Install `uv` globally using `pipx`:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install pipx
   pipx install uv
   ```

- Install dependencies using `uv`:

   ```bash
   # Install all dependencies including dev dependencies
   # This will install the dependencies on your system which should be the dev container
   # -e flag installs the package in editable mode which is useful for development
   uv pip install -e .[dev] --system

   # Install only production dependencies
   uv pip install . --system --no-cache-dir
   ```

## 🚀 Quick Start Guide

Getting up and running with Textlayer Core is straightforward:

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Textlayer/textlayer-core.git
cd textlayer-core

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (choose one)
pip install -r requirements.txt  # Standard installation
# OR
make dev  # Install development dependencies using Makefile
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with these essential variables:

```ini
# Flask Configuration
FLASK_CONFIG=DEV
FLASK_APP=application.py

# LLM Configuration (choose your provider)
LLM_API_KEY=your_api_key_here

# For Langfuse integration (optional but recommended)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Run the Application

```bash
# Start the development server
flask run

# Or with Doppler for secrets management (recommended)
doppler run -- flask run
```

### 4. Verify Setup

```bash
# Run tests to verify your setup
make test

# Check code formatting
make lint
```

### 5. Create Your First AI Endpoint

1. Create a new command in `app/commands/` directory:

```python
# app/commands/content/my_llm_command.py
from app.core.commands import ReadCommand
from app.services.llm.session import LLMSession

class GenerateContentCommand(ReadCommand):
    def __init__(self, prompt):
        self.prompt = prompt
        self.llm_session = LLMSession(
            chat_model=current_app.config['CHAT_MODEL'],
            embedding_model=current_app.config['EMBEDDING_MODEL']
        )
        
    def execute(self):
        response = self.llm_session.chat(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": self.prompt}]
        )
        return response
```

2. Create a controller to handle the command:

```python
# app/controllers/content_controller.py
from app.commands.content.my_llm_command import GenerateContentCommand
from app.controllers.controller import Controller

class ContentController(Controller):
    def generate_content(self, prompt: str) -> str:
        return self.executor.execute_read(GenerateContentCommand(prompt))
```

3. Register the controller and routes in `app/routes/content_routes.py`
```python
# app/routes/content_routes.py
from flask import Blueprint, request
from app.controllers.content_controller import ContentController
from app.decorators import handle_exceptions
from app.utils.response import Response

content_routes = Blueprint("content_routes", __name__)
content_controller = ContentController()

@content_routes.route('/generate', methods=['POST'])
@handle_exceptions
def generate_content():
    data = request.get_json()
    prompt = data.get('prompt', '')
    result = content_controller.generate_content(prompt)
    return Response.make(result, Response.HTTP_SUCCESS)
```

4. Register the routes in `app/routes/routes.py`

```python
# Add to the init_routes function
from app.routes import content_routes

# ... Other imports and code ...add()

blueprints = {
   "content_routes": content_routes,
   # ... other blueprints ...
}

# The blueprints are then registered in the init_routes function
def init_routes(app):
    app.wsgi_app = DispatcherMiddleware(stop, {'/v1': app.wsgi_app})

    app.before_request(get_current_user)
    app.before_request(log_request_info)
    app.after_request(log_response_info)

    for path in blueprints:
        app.register_blueprint(blueprints[path], url_prefix=path)

```

4. Test your endpoint:

```bash
curl -X POST http://localhost:5000/v1/content/generate \ 
    -H "Content-Type: application/json" \
    -d '{"prompt": "Explain artificial intelligence in simple terms"}'
```

### Development with Docker

You can also use Docker for local development (recommended):

```bash
# Build and run the development Docker container
docker build -t textlayer-core -f Dockerfile .
docker run -p 5000:5000 textlayer-core
```

## 🛠️ Development Commands

Here are the most common commands you'll use during development:

```bash
# Run the application locally
make run

# Run tests
make test

# Run linting checks
make lint

# Format code
make format

# Update the model registry
make update-models
```

## ⚙️ GitHub Actions

This project includes several GitHub Actions workflows for automation:

1. **Model Registry Updates**: 
   - Automatically updates the models.json registry weekly
   - Fetches latest model data from LiteLLM
   - Creates a commit with the updated registry
   - Can be manually triggered via GitHub Actions UI

To create the GitHub Actions workflow for model updates, add the following file in your repository:

`.github/workflows/update-models.yml`:
```yaml
name: Update LLM Model Registry

on:
  schedule:
    # Run once a week on Monday at 2:00 AM UTC
    - cron: '0 2 * * 1'
  workflow_dispatch:
    # Allow manual triggering

jobs:
  update-models:
    runs-on: ubuntu-latest
    name: Update LLM model registry
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          ref: ${{ github.head_ref }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install requests
      
      - name: Update model registry
        run: flask update_models --force
        env:
          FLASK_APP: application.py
          FLASK_CONFIG: DEV
      
      - name: Commit changes if model registry updated
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add models.json
          git diff --staged --quiet || git commit -m "Update model registry [automated]"
      
      - name: Push changes
        uses: ad-m/github-push-action@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          branch: ${{ github.ref }}
```

## ⚙️ Configuration

Textlayer Core uses a hierarchical configuration system based on environment variables:

- **Base Configuration**: Defined in the `Config` class in `config.py`
- **Environment-specific Configuration**: Development, Testing, Staging, and Production configurations extend the base config

### Environment Variables

| Category | Environment Variables | Description |
|----------|----------------------|-------------|
| **Flask** | `FLASK_CONFIG` | Environment configuration (DEV, TEST, STAGING, PROD) |
| | `FLASK_APP` | Application entry point (default: application.py) |
| **AWS** | `ACCESS_KEY_ID` | AWS access key |
| | `SECRET_ACCESS_KEY` | AWS secret key |
| | `REGION` | AWS region (e.g., us-east-1) |
| **Opensearch** | `OPENSEARCH_HOST` | URL of your OpenSearch instance |
| | `OPENSEARCH_USER` | Username for OpenSearch |
| | `OPENSEARCH_PASSWORD` | Password for OpenSearch |
| **Langfuse** | `LANGFUSE_PUBLIC_KEY` | Public key for Langfuse integration |
| | `LANGFUSE_SECRET_KEY` | Secret key for Langfuse integration |
| | `LANGFUSE_HOST` | Langfuse API host (default: https://cloud.langfuse.com) |
| **LLM** | `LLM_API_KEY` | Generic API key for LLM providers |
| | `OPENAI_API_KEY` | Specific API key for OpenAI (if using) |
| | `ANTHROPIC_API_KEY` | Specific API key for Anthropic (if using) |

### Using Doppler for Secrets Management (recommended)

1. Make a [Doppler](https://doppler.com) account
2. Download the [Doppler CLI](https://docs.doppler.com/docs/install-cli)
3. Run `doppler login`
4. Run `doppler setup` and select your environment
5. Start the application with automated secrets injection: `doppler run -- flask run`

## 📝 Usage

### Running Locally

```bash
# With regular environment variables
flask run

# Or with Doppler (recommended)
doppler run -- flask run
```

### CLI Commands

The application provides CLI commands for maintenance and testing:

```bash
# Run tests
flask test

# Run tests with coverage
flask test --coverage
```

#### Test Coverage Report

When running tests with coverage, a detailed HTML report is generated in the `app/cli/tmp/coverage` directory. You can view this report by opening `app/cli/tmp/coverage/index.html` in your browser.

```bash
# Run tests with specific test names
flask test test_app.py test_config.py

# View coverage report location
flask test --coverage
# Output includes: HTML version: file://[path]/app/cli/tmp/coverage/index.html
```

### Dataset Testing with Langfuse

Textlayer Core provides built-in testing capabilities through Langfuse integration. This allows you to validate your LLM application's performance against curated datasets and use LLM-as-judge for automated evals.

#### Running Dataset Tests

The `run-dataset-test` command allows you to test your application against datasets stored in Langfuse:

```bash
# Run tests on a single dataset
flask run-dataset-test my_dataset

# Run tests on multiple datasets
flask run-dataset-test dataset1 dataset2 dataset3

# Use datasets configured in app config (TEST_DATASETS)
flask run-dataset-test --use-config

# Add a version tag to identify this test run
flask run-dataset-test my_dataset --run-version=v1.0
```

#### Configuration

To use dataset testing:

1. Configure Langfuse in your environment variables:
   ```
   LANGFUSE_PUBLIC_KEY=your_public_key
   LANGFUSE_SECRET_KEY=your_secret_key
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

2. To use datasets from configuration, add to your environment:
   ```
   TEST_DATASETS=dataset1,dataset2,dataset3
   ```

#### Setting Up Datasets in Langfuse

1. Create a dataset in Langfuse with test cases
2. Each test case should include:
   - `input`: The user query or prompt to test
   - `expected_output`: The expected model response (optional)
   - `metadata`: Additional context or parameters for the test

#### Using LLM as Judge for Evaluation

Langfuse supports using LLMs to automatically evaluate your application's responses:

1. **Create a Dataset in Langfuse**:
   - Go to Langfuse UI → Datasets → New Dataset
   - Add test cases with inputs, expected outputs and metadata

2. Create an Evaluation Model in Langfuse:
   - Go to Langfuse UI → Evaluation → LLM-as-a-Judge
   - Create Evaluator
   - Create or Select an existing Template
   - Configure your evaluation prompt and criteria
   - Ensure that the evaluator filters for "TEST" tags

3. **Run your application against this dataset using `flask run-dataset-test`
    - Traces are automatically logged to Langfuse
    - Using the evaluator filters for "TEST" tags, the LLM will score responses based on your criteria
    - The LLM will also provide feedback on the responses

4. **Analyze Results**:
   - View scores and feedback in the Langfuse dashboard
   - Compare different runs and versions
   - Identify areas for improvement

#### Example Evaluation Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Test Dataset   │────▶│ run-dataset-test│────▶│  LLM Responses  │
│  in Langfuse    │     │     Command     │     │  (Traces)       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Performance   │◀────│   Evaluation    │◀────│   LLM Judge     │
│    Insights     │     │    Results      │     │  Evaluation     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

For more information on Langfuse evaluation capabilities, see the [Langfuse Evaluation Documentation](https://langfuse.com/docs/scores/overview).

### Makefile Commands

The project includes a Makefile with helpful commands for development tasks:

```bash
# View all available commands
make help

# Run linting checks with Ruff
make lint

# Format code with Ruff
make format

# Run all tests
make test

# Run tests with coverage report
make coverage

# Clean up build artifacts
make clean

# Install production dependencies
make install

# Install development dependencies
make dev
```

These commands simplify common development tasks and ensure consistent execution of linting, testing, and other operations across development environments.

## 🚢 Deployment

This template supports deployment as a containerized application.

### Building the Docker Image

```bash
docker build -t textlayer-app -f Dockerfile .
```

### Deploying to AWS

For AWS deployment, the template includes support for:
- Amazon ECR for container registry
- AWS Lambda for serverless deployment
- Amazon ECS for container orchestration

Specific deployment instructions depend on your chosen AWS service.

## 🧩 Common AI Integration Patterns

Textlayer Core supports several common patterns for AI-enabled applications:

### 1. Prompt Engineering and Management

Leverage the `@prompt` decorator for dynamic prompt management:

```python
from app.services.llm.prompts import prompt

@prompt(name="summarize_text")
def summarization_prompt(text):
    """
    Summarize the following text in a concise way:
    
    {{text}}
    """
    return f"Summarize the following text in a concise way:\n\n{text}"
```

### 2. Retrieval Augmented Generation (RAG)

Combine search and generation capabilities:

```python
from app.services.search import opensearch_session
from app.services.llm.session import LLMSession

session = LLMSession(
    chat_model=current_app.config['CHAT_MODEL'],
    embedding_model=current_app.config['EMBEDDING_MODEL']
)

# Retrieve relevant information
es = opensearch_session()
results = es.search(
    index="knowledge_base",
    body={"query": {"match": {"content": query}}}
)

# Extract context from search results
context = "\n".join([doc["_source"]["content"] for doc in results["hits"]["hits"]])

# Generate response with context
prompt = f"Based on this information:\n\n{context}\n\nAnswer: {query}"
response = session.chat(model="gpt-4", messages=[{"role": "user", "content": prompt}])
```

### 3. Observability and Tracing

Use Langfuse traces to monitor your AI application:

```python
from langfuse.decorators import observe

@observe()
def process_document(document):
    # Processing steps will be logged as spans in Langfuse
    extracted_data = extract_information(document)
    analysis = analyze_data(extracted_data)
    return generate_report(analysis)
```

## 📁 Project Structure

```
textlayer-core/
├── app/                        # Main application code
│   ├── commands/               # Command handlers for business logic
│   ├── controllers/            # Logic controllers
│   ├── core/                   # Core application functionality
│   ├── errors/                 # Error handling
│   ├── middlewares/            # HTTP middleware
│   ├── routes/                 # API route definitions
│   ├── schemas/                # Data validation schemas
│   ├── services/               # External service integrations
│   │   ├── aws/                # AWS integration
│   │   ├── llm/                # LiteLLM integration
│   │   └── search/             # Search service integration
│   ├── utils/                  # Utility functions
│   ├── aws_triggers/           # AWS Lambda triggers
│   ├── cli/                    # Command-line interface tools
│   ├── decorators.py           # Decorators
│   ├── extensions.py           # Flask extensions
│   ├── log.py                  # Logging configuration
│   └── __init__.py             # Application initialization
├── application.py              # Application entry point
├── config.py                   # Configuration management
├── Dockerfile                  # Docker configuration
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore file
└── README.md                   # This documentation
```

## 🏗️ Understanding the Command Pattern

Textlayer Core implements the Command Pattern to separate business logic from request handling:

### Core Components

- **Commands** (`app/core/commands.py`): Abstract base classes for read and write operations
  - `ReadCommand`: For operations that retrieve data
  - `WriteCommand`: For operations that modify data

- **Executor** (`app/core/executor.py`): Singleton class that executes commands

- **Controller** (`app/controllers/controller.py`): Uses the Executor to run commands

### Example Implementation

1. Define a command:

```python
from app.core.commands import ReadCommand

class GetUserCommand(ReadCommand):
    def __init__(self, user_id):
        self.user_id = user_id
        
    def execute(self):
        # Implementation to fetch user from database
        return {"id": self.user_id, "name": "Example User"}
```

2. Use the command in a controller:

```python
from app.controllers.controller import Controller

class UserController(Controller):
    def get_user(self, user_id: str) -> dict:
        return self.executor.execute_read(GetUserCommand(user_id))
```

3. Register the controller and routes in `app/routes/user_routes.py`

```python
from app.routes.user_routes import user_routes

@user_routes.route('/users/<user_id>', methods=['GET'])
@handle_exceptions
def get_user(user_id):
    controller = UserController()
    user = controller.get_user(user_id)
    return Response.make(user, Response.HTTP_SUCCESS)
```

4. Register the routes in `app/routes/routes.py`

```python
from app.routes import user_routes

# ... Other imports and code ...

blueprints = {
   "user_routes": user_routes,
   # ... other blueprints ...
}

```

This pattern provides several benefits:
- Separation of concerns
- Testability of business logic
- Reusability of commands across different interfaces
- Easier to maintain and extend the application

### Thread Processing Implementation

Textlayer Core includes a complete implementation of thread processing using the command pattern. This real-world example demonstrates how to build an LLM-powered chat endpoint:

1. **Command** (`app/commands/threads/process_chat_message.py`):
   ```python
   class ProcessChatMessageCommand(ReadCommand):
       """Process a user message in a chat conversation using LLM."""
       
       def __init__(self, chat_messages: List[Dict[str, Any]]) -> None:
           self.chat_messages = chat_messages
           self.llm_session = LLMSession(
               chat_model=current_app.config.get("CHAT_MODEL"),
               embedding_model=current_app.config.get("EMBEDDING_MODEL"),
           )
           self.toolkit = Toolkit()
           self.toolkit.add_tools()
       
       def validate(self) -> bool:
           if not self.chat_messages:
               raise ValidationException("Chat messages are required.")
           return True
       
       def execute(self) -> List[Dict[str, Any]]:
           # 1. Validate input
           self.validate()
           
           # 2. Get response from LLM
           response = self._get_llm_response()
           
           # 3. Process response and any tool calls
           new_messages = self._process_llm_response(response)
           
           # 4. Add new messages to conversation history
           self.chat_messages.extend(new_messages)
           
           return self.chat_messages
   ```

2. **Controller** (`app/controllers/thread_controller.py`):
   ```python
   class ThreadController(Controller):
       """A controller for threads."""
       
       def process_chat_message(self, chat_messages: list) -> list:
           return self.executor.execute_write(ProcessChatMessageCommand(chat_messages))
   ```

3. **Route** (`app/routes/thread_routes.py`):
   ```python
   thread_routes = Blueprint("thread_routes", __name__)
   thread_controller = ThreadController()
   
   @thread_routes.post("/chat")
   @handle_exceptions
   def chat():
       validated_request_data = chat_messages_schema.load(request.get_json())
       messages = thread_controller.process_chat_message(validated_request_data.get("messages"))
       return Response.make(messages, Response.HTTP_SUCCESS)
   ```

4. **Testing the Chat Endpoint**:
   ```bash
   curl -X POST http://localhost:5000/v1/thread_routes/chat \
       -H "Content-Type: application/json" \
       -d '{
           "messages": [
               {"role": "user", "content": "Tell me about artificial intelligence"}
           ]
       }'
   ```

This implementation showcases several advanced features:
- **LLM Integration**: Uses LiteLLM to communicate with language models
- **Tool Calling**: Supports LLM tool calls with the Vaul toolkit
- **Observability**: Includes Langfuse tracing with `@observe()` decorators
- **Validation**: Implements input validation with clear error messages
- **Error Handling**: Uses the `@handle_exceptions` decorator for consistent error responses

By following this pattern, you can easily extend the application with new AI capabilities while maintaining a clean, testable architecture.

## 👥 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request                                                                                                                                                                                                                                                                                                                                                                                                                                                                
