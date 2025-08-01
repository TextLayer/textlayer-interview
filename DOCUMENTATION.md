📄 Textlayer Technical Assessment – Text-to-SQL Chat Interface

✅ Project Overview
This project implements a chat interface that converts natural language to SQL, executes the query, and streams back results as conversational responses. The system supports structured tool-calling using an LLM and integrates real-time Server-Sent Events (SSE) for streaming outputs.

🧠 Features Implemented
1. Text-to-SQL via Tool Call
Leveraged vaul.StructuredOutput for text_to_sql functionality.
Designed a SqlQuery model to ensure the LLM produces valid SQL wrapped in a tool-callable schema.
Integrated this function into a Toolkit and passed it to the LLM session.

2. Streaming Chat API (/threads/chat/stream)
Implemented SSE response via Flask using a yield generator pattern.
Messages from the LLM response are streamed token-by-token for an interactive user experience.

3. Enhanced Prompting
Created chat_prompt() to provide schema-aware prompting.
Injected table schema dynamically into the LLM system prompt for better SQL accuracy.

4. Error Handling & Logging
Wrapped routes with @handle_exceptions.
Used structured logging and tracing to capture tool calls and LLM responses.

🚀 Endpoints

| Endpoint               | Method | Description                      |
| ---------------------- | ------ | -------------------------------- |
| `/threads/chat`        | POST   | Standard chat with full response |
| `/threads/chat/stream` | POST   | Streaming response with SSE      |

🧪 Testing Notes
The full text-to-SQL flow was verified by sending prompts like:

How many users signed up last week?
Show total revenue by month in 2023.
What is the trend of finance in 2025?

Responses included SQL generation, tool execution, and structured LLM replies.

⚙️ Setup Instructions
# Install dependencies
pip install -r requirements.txt

# Run the app
.venv\Scripts\Actiave
$env:DOPPLER_TOKEN="dp.st.prd.dEyqtHDKSppHXAxBsSEGbzNfZfrouAGXQcC4EnuKxGg"
doppler run -- flask run
