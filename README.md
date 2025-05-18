# Hermes - Email Processing Project

This project, codenamed Hermes, analyzes customer emails for a high-end fashion retail store. It classifies emails, extracts product references, identifies customer signals, and analyzes tone.

This project was converted from a Jupyter Notebook (`hermes.ipynb`) into a structured Python application.

## Project Structure

```
notebooks/hermes/
├── src/
│   └── hermes/
│       ├── __init__.py
│       ├── config.py
│       ├── common_models.py
│       ├── prompts.py
│       ├── agents/
│       │   ├── __init__.py
│       │   └── email_analyzer.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── gsheet.py
│       │   └── llm_client.py
│       ├── main.py
│       └── state.py
├── .env.example
├── .python-version
├── pyproject.toml
├── README.md
└── uv.lock
```

## Setup

1.  **Environment Variables**:
    *   Copy the `.env.example` file to `.env` in the `notebooks/hermes/` directory:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and fill in your API keys and any other necessary configurations:
        *   `LLM_PROVIDER`: "Gemini" or "OpenAI"
        *   `GEMINI_API_KEY`: Your Google AI Studio API key if using Gemini.
        *   `OPENAI_API_KEY`: Your OpenAI API key if using OpenAI.
        *   `OPENAI_BASE_URL`: (Optional) Custom base URL for OpenAI.
        *   `LANGSMITH_API_KEY`: Your LangSmith API key for tracing (if `LANGSMITH_TRACING` is True).
        *   `INPUT_SPREADSHEET_ID`: Google Sheet ID for input data.
        *   `OUTPUT_SPREADSHEET_NAME`: Name for the output Google Sheet.
        *   `GOOGLE_APPLICATION_CREDENTIALS`: (Optional) Path to your Google Cloud service account JSON key file if you want to use a service account for accessing Google Sheets via the API. Otherwise, ensure you are authenticated via `gcloud auth application-default login`.
        *   `HERMES_PROCESSING_LIMIT`: (Optional) Number of emails to process. Set to `1` for a quick test, or `0` (or remove) to process all emails.

2.  **Python Environment and Dependencies (using uv)**:
    *   Ensure you have `uv` installed. (https://github.com/astral-sh/uv)
    *   Navigate to the `notebooks/hermes/` directory.
    *   If you don't have a virtual environment, create one (uv will use the Python version from `.python-version` or `requires-python` in `pyproject.toml`):
        ```bash
        uv venv .venv 
        ```
    *   Activate the virtual environment:
        ```bash
        source .venv/bin/activate
        ```
    *   Install dependencies:
        ```bash
        uv pip sync pyproject.toml
        ```

3.  **Google Sheets API Access (if not using public CSV export for reading/writing)**:
    *   If `read_data_from_gsheet` fails with the public CSV export or if you are writing data back using `write_df_to_gsheet`, you'll need to authenticate with Google APIs.
    *   **Easiest method for local development**: Use Application Default Credentials (ADC).
        Install Google Cloud CLI: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
        Then run:
        ```bash
        gcloud auth application-default login
        ```
        This will open a browser window for you to log in with your Google account. Ensure this account has access to the Google Sheets you intend to read/write.
    *   **Service Account (for automated environments)**:
        1.  Create a Google Cloud Project.
        2.  Enable the Google Drive API and Google Sheets API for your project.
        3.  Create a service account and download its JSON key file.
        4.  Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable in your `.env` file to the path of this JSON key file.
        5.  Share your input and output Google Sheets with the service account's email address, giving it appropriate permissions (Viewer for input, Editor for output).

## Running the Application

Once the setup is complete, you can run the main email processing script from the `notebooks/hermes/` directory:

```bash
python src/hermes/main.py
```

The script will:
1.  Load configuration from `.env` and `src/hermes/config.py`.
2.  Read product data and emails from the Google Sheet specified in `INPUT_SPREADSHEET_ID`.
3.  Process the emails (up to `HERMES_PROCESSING_LIMIT` if set).
4.  Write the classification results to a new Google Sheet (or update an existing one) named according to `OUTPUT_SPREADSHEET_NAME`.

Output logs will be printed to the console.

## Development

This project uses `poethepoet` for task management (defined in `pyproject.toml`). You can use `ruff` for linting and formatting if you have it installed in your environment or globally.

-   Lint: `ruff check .` (or `poe lint`)
-   Format: `ruff format .` (or `poe format`)
