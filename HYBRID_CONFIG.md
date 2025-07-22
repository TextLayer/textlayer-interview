# Hybrid API Configuration Guide

This application now supports both **local processing** and **remote TextLayer API** integration with seamless switching.

## Configuration Options

Add these variables to your `.env` file:

### API Mode Selection
```bash
# Set to "LOCAL" for local processing or "REMOTE" for TextLayer API
API_MODE=LOCAL
```

### Remote TextLayer API Configuration
```bash
# Required for REMOTE mode
TEXTLAYER_API_BASE=https://core.dev.textlayer.ai/v1
TEXTLAYER_API_KEY=your_textlayer_api_key_here
```

### Local Processing Configuration
```bash
# Required for LOCAL mode
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
CHAT_MODEL=claude-3-5-sonnet-20241022
```

### Additional Settings
```bash
# Enable fallback to local if remote fails
ENABLE_LOCAL_FALLBACK=true

# Database configuration
DATABASE_PATH=data/financial_data.duckdb
KNN_EMBEDDING_DIMENSION=1536
```

## How It Works

### Local Mode (`API_MODE=LOCAL`)
- Uses local LLM processing with your API keys
- Includes streaming support
- Includes LLM-as-a-Judge evaluation
- Processes SQL queries against local DuckDB

### Remote Mode (`API_MODE=REMOTE`)
- Forwards requests to TextLayer API at `https://core.dev.textlayer.ai/v1`
- Uses your TextLayer API key for authentication
- Supports both regular and streaming endpoints
- Falls back to local processing if enabled and remote fails

### Hybrid Benefits
- **Zero code changes** required to switch modes
- **Automatic fallback** from remote to local on failures
- **Consistent API** regardless of processing mode
- **Easy testing** between local and remote environments

## API Status Endpoint

Check current configuration:
```bash
GET /v1/threads/status
```

Response:
```json
{
  "mode": "LOCAL",
  "local_available": true,
  "remote_configured": true,
  "remote_base_url": "https://core.dev.textlayer.ai/v1",
  "has_api_key": false
}
```

## Frontend Usage

The frontend automatically detects the mode and works seamlessly with both:

- **Streaming toggle** works in both modes
- **Error handling** with automatic fallback
- **Status indicators** show current processing mode

## Quick Setup

1. **For Local Development:**
   ```bash
   API_MODE=LOCAL
   ANTHROPIC_API_KEY=your_key
   ```

2. **For Production with TextLayer API:**
   ```bash
   API_MODE=REMOTE
   TEXTLAYER_API_KEY=your_textlayer_key
   ```

3. **For Hybrid (Remote with Local Fallback):**
   ```bash
   API_MODE=REMOTE
   TEXTLAYER_API_KEY=your_textlayer_key
   ANTHROPIC_API_KEY=your_local_fallback_key
   ENABLE_LOCAL_FALLBACK=true
   ```