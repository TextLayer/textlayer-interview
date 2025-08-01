# TextLayer Core

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-42%25-yellow.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Maintained](https://img.shields.io/badge/maintained-yes-green.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
[![Click here for docs](https://img.shields.io/badge/-Click%20Here%20For%20Docs-blue.svg?style=flat-square)](https://docs.textlayer.ai)

</div>

**TextLayer Core** is a comprehensive Flask application template for building AI-powered services. It provides a structured foundation with built-in integrations for AI services, search capabilities, and observability—designed to help teams quickly leverage Large Language Models (LLMs) while maintaining consistent architecture patterns.

---

## 🛠️ Minimal Setup

For a quick start, you'll need:

- Python 3.12 (recommended, as it's the latest version supported by NumPy and pandas)
- Alternatively, you can use the latest version of Python if Python 3.12 is not available.

For detailed setup instructions, visit:
- [Windows Setup Guide](https://docs.textlayer.ai/windows)
- [Unix/Linux/Mac Setup Guide](https://docs.textlayer.ai/unix)

> 💡 **Note:** The `requirements.txt` file has been updated to include additional packages that support enhanced prompt evaluation and LLM feedback mechanisms.

---

## 🌟 What is TextLayer Core?

TextLayer Core is a powerful template for building AI-powered applications and services within organizations. Designed as an AI enablement layer, it helps teams quickly integrate and leverage Large Language Models (LLMs) in their applications while maintaining a consistent architecture and deployment pattern.

### 🎯 Problems It Solves

- **AI Integration Complexity**: Simplifies the integration of LLMs into your applications
- **Inconsistent Architecture**: Provides a standardized structure for AI-powered services
- **Observability Challenges**: Built-in monitoring and tracing for AI components
- **Provider Lock-in**: Unified interface to multiple LLM providers
- **Deployment Friction**: Ready-to-use deployment configurations for various environments
- **Prompt Quality Inconsistency**: Enhanced tooling for refining and scoring prompts using LLM-as-a-Judge mechanism

---

## 🚀 Key Use Cases

- **Building internal AI tools and services** with a consistent architecture
- **Creating LLM-powered APIs** for your organization with built-in observability
- **Implementing consistent patterns** for AI-enabled applications across teams
- **Establishing robust monitoring** for AI components in production environments
- **Evaluating and improving prompt quality** using in-house LLM-based evaluators

---

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| **Modular Flask Structure** | Well-organized application structure following best practices |
| **LiteLLM Integration** | Unified interface to access multiple LLM providers (OpenAI, Anthropic, etc.) |
| **Search Capabilities** | Built-in OpenSearch integration for vector search |
| **AWS Integration** | Ready-to-use cloud deployment configurations |
| **Langfuse Observability** | Comprehensive prompt management and AI observability |
| **LLM-as-a-Judge** | Automated evaluation of prompt responses using a judging LLM |
| **Docker Deployment** | Containerized deployment for consistent environments |
| **Environment Config** | Flexible configuration management for different environments |
| **Command Pattern** | Clean separation of business logic from request handling |

---

## 🏛️ Architecture Overview

TextLayer Core implements a clean, modular architecture for AI applications:

1. **Request Handling**: Controllers receive and process incoming API requests
2. **Command Processing**: Business logic is organized in command handlers
3. **Service Integration**: External services wrapped in service modules
4. **Response Handling**: Structured API responses with error handling
5. **Prompt Evaluation**: Built-in framework for testing, scoring, and refining prompts via LLMs

---

### 🔍 Key Integrations

- **Langfuse**: Integrated throughout the application to provide prompt management and observability
- **LiteLLM**: Provides a unified interface for multiple LLM providers
- **OpenSearch**: Powers vector search capabilities
- **LLM-as-a-Judge**: Used to score and refine prompt quality through comparative evaluations

---

## 📚 Learn More

For comprehensive documentation, visit [docs.textlayer.ai](https://docs.textlayer.ai).
