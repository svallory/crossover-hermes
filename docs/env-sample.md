# Hermes Environment Variables Documentation

This document describes the environment variables used by the Hermes system, including how to configure the LLM models and output verification.

## Basic Setup

Copy the example below to a `.env` file at the root of the project and modify as needed:

```
# Hermes Configuration 

# LLM Provider Configuration
# Options: "OpenAI" or "Gemini"
LLM_PROVIDER=OpenAI

# API Keys
OPENAI_API_KEY=your-openai-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here

# Model Configuration
# Strong models (for complex tasks)
OPENAI_STRONG_MODEL=gpt-4.1
GEMINI_STRONG_MODEL=gemini-2.5-flash-preview-04-17

# Weak models (for simpler tasks, faster/cheaper)
OPENAI_WEAK_MODEL=gpt-4o-mini
GEMINI_WEAK_MODEL=gemini-1.5-flash

# LLM Output Verification
# When enabled (true), outputs from weak models are verified using strong models
# This is useful when testing prompts to ensure quality across model tiers
# Can be set to false to save costs during production/batch processing
LLM_OUTPUT_VERIFICATION=true

# LLM API Configuration
OPENAI_BASE_URL=https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/

# Google Sheets Configuration
INPUT_SPREADSHEET_ID=14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U
OUTPUT_SPREADSHEET_NAME=Hermes - Email Analyzer Test Output

# Data Storage Configuration
VECTOR_STORE_PATH=./chroma_db
CHROMA_COLLECTION_NAME=hermes_product_catalog

# Processing Limits
# Use 0 or negative number to process all emails
HERMES_PROCESSING_LIMIT=1

# LangSmith Tracing (set to true to enable tracing)
LANGSMITH_TRACING=false
# LANGCHAIN_API_KEY=your-langchain-api-key
# LANGSMITH_PROJECT=your-langsmith-project
```

## Environment Variables Reference

### LLM Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | The LLM provider to use, either "OpenAI" or "Gemini" | "Gemini" |
| `OPENAI_API_KEY` | API key for OpenAI | (none) |
| `GEMINI_API_KEY` | API key for Google Gemini | (none) |
| `OPENAI_STRONG_MODEL` | OpenAI model name for complex tasks | "gpt-4.1" |
| `OPENAI_WEAK_MODEL` | OpenAI model name for simpler tasks | "gpt-4o-mini" |
| `GEMINI_STRONG_MODEL` | Gemini model name for complex tasks | "gemini-2.5-flash-preview-04-17" |
| `GEMINI_WEAK_MODEL` | Gemini model name for simpler tasks | "gemini-1.5-flash" |
| `LLM_OUTPUT_VERIFICATION` | When enabled, outputs from weak models are verified using strong models | true |
| `OPENAI_BASE_URL` | Base URL for OpenAI API calls | (default proxy URL) |

### Google Sheets Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `INPUT_SPREADSHEET_ID` | ID of the Google Sheet containing input data | (default test sheet) |
| `OUTPUT_SPREADSHEET_NAME` | Name for the output spreadsheet | "Hermes - Email Analyzer Test Output" |

### Data Storage Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_STORE_PATH` | Path to the Chroma vector store | "./chroma_db" |
| `CHROMA_COLLECTION_NAME` | Name of the Chroma collection | "hermes_product_catalog" |

### Processing Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HERMES_PROCESSING_LIMIT` | Maximum number of emails to process (0 or negative for all) | 1 |

### Tracing and Debugging

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGSMITH_TRACING` | Enable LangSmith tracing | false |
| `LANGCHAIN_API_KEY` | API key for LangChain | (none) |
| `LANGSMITH_PROJECT` | Project name for LangSmith | (none) |

## Using the LLM_OUTPUT_VERIFICATION Feature

The `LLM_OUTPUT_VERIFICATION` environment variable enables or disables verification of outputs from weak models using the configured strong model. This is particularly useful when:

1. **Testing Prompts**: Ensures that cheaper/faster models produce results comparable to more expensive/powerful models
2. **Developing New Features**: Provides a validation step to check that your weak model is performing adequately
3. **Quality Assurance**: Adds an extra verification layer for critical applications

For production or batch processing where cost and speed are priorities, you can disable verification by setting `LLM_OUTPUT_VERIFICATION=false`.

Example of use during different phases:

- **Development**: Set `LLM_OUTPUT_VERIFICATION=true` to ensure prompt quality across model tiers
- **Production**: Set `LLM_OUTPUT_VERIFICATION=false` to optimize for cost and speed
- **Critical Applications**: Keep `LLM_OUTPUT_VERIFICATION=true` if accuracy is paramount, even at higher cost

When verification is enabled, the system will use the weak model for initial processing and then use the strong model to verify and potentially correct the results. 