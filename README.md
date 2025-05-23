# Hermes - Humanlike Email Responses for Magically Empathic Sales

This project, codenamed Hermes, analyzes customer emails for a high-end fashion retail store. It classifies emails, extracts product references, identifies customer signals, and analyzes tone using advanced AI agents.

## Project Structure

```
hermes/
├── hermes/
│   ├── __init__.py
│   ├── agents/
│   ├── data_processing/
│   ├── model/
│   ├── tools/
│   └── utils/
├── tests/
│   ├── fixtures/
│   ├── test_catalog_tools.py
│   ├── test_order_tools.py
│   └── test_promotion_tools.py
├── data/
│   └── experiments/
├── docs/
├── notebooks/
├── tools/
│   └── evaluate/
├── .env
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- [poethepoet](https://poethepoet.natn.io/) - Task runner (installed as project dependency)

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd hermes
   ```

2. **Create and activate virtual environment with uv**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Environment Variables**:
   - Copy the `.env.example` file to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit the `.env` file and configure your API keys and settings:
     - `LLM_PROVIDER`: "Gemini" or "OpenAI"
     - `GEMINI_API_KEY`: Your Google AI Studio API key if using Gemini
     - `OPENAI_API_KEY`: Your OpenAI API key if using OpenAI
     - `OPENAI_BASE_URL`: (Optional) Custom base URL for OpenAI
     - `LANGSMITH_API_KEY`: Your LangSmith API key for tracing
     - `INPUT_SPREADSHEET_ID`: Google Sheet ID for input data
     - `OUTPUT_SPREADSHEET_NAME`: Name for the output Google Sheet
     - `GOOGLE_APPLICATION_CREDENTIALS`: (Optional) Path to your Google Cloud service account JSON key file
     - `HERMES_PROCESSING_LIMIT`: (Optional) Number of emails to process

5. **Google Sheets API Access** (if using Google Sheets):
   - **Easiest method for local development**: Use Application Default Credentials (ADC)
     ```bash
     gcloud auth application-default login
     ```
   - **Service Account** (for automated environments):
     1. Create a Google Cloud Project
     2. Enable Google Drive API and Google Sheets API
     3. Create a service account and download JSON key file
     4. Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
     5. Share your Google Sheets with the service account email

## Usage

### Running the Application

```bash
# Run the main email processing workflow
poe run

# Run with LangGraph development server
poe dev-graph

# Run specific workflow
poe run-workflow
```

### Development

#### Code Quality and Formatting

```bash
# Check code quality (lint + test)
poe check

# Lint code with ruff
poe lint

# Format code with ruff
poe format
```

#### Testing

```bash
# Run all tests
poe test

# Run tests with verbose output
poe test -v

# Run specific test file
poe test tests/test_catalog_tools.py
```

For detailed testing documentation, including running specific test classes and methods, see [`tests/README.md`](tests/README.md).

#### Evaluation

```bash
# Run evaluation with dataset
poe evaluate
```

## Available Tasks

The project uses `poethepoet` (poe) for task management. Available tasks defined in `pyproject.toml`:

| Task | Description |
|------|-------------|
| `poe run` | Load environment and run main application |
| `poe dev-graph` | Start LangGraph development server |
| `poe run-workflow` | Load environment and run workflow tools |
| `poe check` | Run linting and tests |
| `poe lint` | Check code with ruff linter |
| `poe format` | Format code with ruff formatter |
| `poe test` | Run all tests with pytest |
| `poe evaluate` | Run evaluation with dataset and auto-upload |

## Testing

The project includes comprehensive tests for all tools and components:

- **Unit Tests**: Located in `tests/` directory
  - `test_catalog_tools.py`: Tests for product catalog search and retrieval
  - `test_order_tools.py`: Tests for order processing and stock management  
  - `test_promotion_tools.py`: Tests for promotion and discount application
- **Test Fixtures**: Mock and test data in `tests/fixtures/`
  - `mock_product_catalog.py`: Mock product data for unit testing
  - `test_product_catalog.py`: Test data helpers using products.csv

Each test file contains two test classes:
1. **Mock Data Tests**: Use synthetic data for isolated unit testing
2. **Test Data Tests**: Use data from CSV files for realistic testing scenarios

See `tests/README.md` for detailed testing documentation.

## Technology Stack

- **Package Management**: uv
- **Task Runner**: poethepoet (poe)
- **Testing**: pytest
- **Code Quality**: ruff (linting and formatting)
- **Type Checking**: mypy
- **AI/ML**: LangChain, LangGraph, OpenAI, Google Gemini
- **Data**: pandas, ChromaDB
- **Google Integration**: gspread, google-auth

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `poe test`
5. Check code quality: `poe check`
6. Submit a pull request

Make sure all tests pass and code follows the project's formatting standards before submitting.
