# Plan: Jupyter Notebook to Python Project (Hermes)

This plan outlines the steps to convert the `hermes.ipynb` notebook into a structured Python project within the `notebooks/hermes/` directory, using `uv` for environment management.

## 1. Final Project Structure

```
notebooks/hermes/
├── src/
│   └── hermes/
│       ├── __init__.py
│       ├── config.py             # HermesConfig, environment variable loading from .env
│       ├── common_models.py      # EmailType, OrderStatus, Product, CustomerSignal, ToneAnalysis, etc.
│       ├── prompts.py            # Prompt definitions (PROMPTS dict, create_prompt)
│       ├── agents/
│       │   ├── __init__.py
│       │   └── email_analyzer.py # EmailAnalysisOutput model, analyze_email, verify_email_analysis functions
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── gsheet.py           # read_data_from_gsheet function
│       │   └── llm_client.py       # get_llm_client function
│       ├── main.py               # Main application workflow (data loading, email processing, output writing)
│       └── state.py              # HermesState dataclass definition
├── .env.example                  # Example environment variables
├── .python-version               # (already exists)
├── pyproject.toml                # (already exists, will be updated with dependencies)
├── README.md                     # Project overview, setup, and run instructions
└── uv.lock                       # (already exists)
```

## 2. Migration Steps

### Step 2.1: Setup Project Files and Directories
- Create the directory structure outlined above.
- Create empty `__init__.py` files in `src/hermes/`, `src/hermes/agents/`, and `src/hermes/utils/`.

### Step 2.2: Environment Variables & Configuration (`.env.example`, `src/hermes/config.py`)
- **`.env.example`**:
    - Create this file based on the "Environment Variables" cell in the notebook.
    - List all variables: `LLM_PROVIDER`, `EMBEDDING_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `INPUT_SPREADSHEET_ID`, `OUTPUT_SPREADSHEET_NAME`, `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `LANGSMITH_PROJECT`.
- **`src/hermes/config.py`**:
    - Define a function `load_dotenv_vars()` to load variables from a `.env` file using `python-dotenv`. Call this at the module level.
    - Transfer the `HermesConfig` Pydantic model.
    - Modify `HermesConfig` fields to primarily fetch values from environment variables loaded by `dotenv`.
    - Default values from the notebook (like model names, `INPUT_SPREADSHEET_ID`, `OUTPUT_SPREADSHEET_NAME`) can remain as Pydantic field defaults if not found in the environment.
    - The `os.environ` calls in the "Environment Variables" cell related to LangSmith should be part of `load_dotenv_vars` or a specific setup function in `config.py` that's called early in `main.py`.

### Step 2.3: Update `pyproject.toml` with Dependencies
- Extract all package names from the "Packages" cell (`%pip install ...`).
- Add these to the `dependencies` list in `pyproject.toml`.
  Packages: `pandas`, `openai`, `gspread`, `gspread-dataframe`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `pydantic`, `langchain`, `langchain-openai`, `python-dotenv`, `nest-asyncio`, `langchain_google_genai`, `langgraph`, `langsmith`, `pydrive2`, `oauth2client`.

### Step 2.4: Common Imports & Setup (Distribute as needed)
- The "Import Common Packages and Setup Libraries" cell:
    - `typing` imports, `traceable`, `BaseModel`, `Field` go into relevant modules.
    - `IPython.display` is for notebooks and should be removed or replaced with standard logging/printing.
    - `nest_asyncio.apply()`: Include this at the beginning of `src/hermes/main.py` if `asyncio.run` is directly used in a script context that might run in an environment where an event loop is already present (less common for simple scripts, more for frameworks). It's safer to include it for now.
    - `markdown = str` type hint can be removed or kept if preferred.

### Step 2.5: Utilities (`src/hermes/utils/`)
- **`src/hermes/utils/gsheet.py`**:
    - Move the `read_data_from_gsheet` function.
    - Add necessary imports: `pandas as pd`.
- **`src/hermes/utils/llm_client.py`**:
    - Move the `get_llm_client` function.
    - Add necessary imports: `ChatOpenAI`, `ChatGoogleGenerativeAI`, `BaseChatModel` from LangChain, `HermesConfig` (from `..config`).

### Step 2.6: Data Models (`src/hermes/common_models.py`)
- Transfer content from "Common Models and Enums" cell (Enums like `EmailType`, `OrderStatus`, `ReferenceType`, `SignalCategory`).
- Transfer content from "Product" cell (`ProductBase`, `Product`, `ProductReference`, `ProductNotFound`).
- Transfer content from "Sentiment Analysis" cell (`CustomerSignal`, `ToneAnalysis`).
- Ensure all Pydantic and typing imports are present.

### Step 2.7: State Definition (`src/hermes/state.py`)
- Transfer the `HermesState` dataclass definition.
- Add necessary imports: `dataclasses`, `typing`, `BaseMessage` from `langchain_core.messages`, `add_messages` from `langgraph.graph.message`, `pandas as pd`.

### Step 2.8: Prompts (`src/hermes/prompts.py`)
- Transfer the `PROMPTS` dictionary and `create_prompt` function.
- Transfer the `email_analyzer_prompt` string and the call `create_prompt('email_analyzer', email_analyzer_prompt)`.
- Transfer the `email_analysis_verification_prompt` string and its `create_prompt` call.
- Add imports: `Dict` from `typing`, `PromptTemplate` from `langchain_core.prompts`. `markdown = str` can be removed.

### Step 2.9: Agents (`src/hermes/agents/email_analyzer.py`)
- Define the `EmailAnalysisOutput` Pydantic model.
- Transfer the `analyze_email` function.
- Transfer the `verify_email_analysis` function.
- Add necessary imports: `traceable` from `langsmith`, Pydantic models, `HermesConfig`, `HermesState`, `PROMPTS`, `get_llm_client`, `BaseChatModel`, `EmailType`, `ToneAnalysis`, `ProductReference`, `CustomerSignal`. Adjust import paths (e.g., `from ..common_models import ...`, `from ..config import HermesConfig`).

### Step 2.10: Main Workflow (`src/hermes/main.py`)
- **Initialization**:
    - Import and call `load_dotenv_vars()` from `hermes.config`.
    - Instantiate `HermesConfig`.
    - Apply `nest_asyncio.apply()` at the beginning.
- **Data Loading**:
    - Adapt the "Load Input Data" cell. Use `read_data_from_gsheet` from `utils.gsheet`.
    - `INPUT_SPREADSHEET_ID` should come from the `HermesConfig` instance.
    - Remove `display()` calls; use `print()` or logging.
- **Email Processing**:
    - Adapt the "Process Emails with Analyzer Agent" cell. This will be the main part of an `async def main():` function.
    - `run_email_analysis` will become the core logic within `async def main()`.
    - Ensure `HermesState` and `EmailAnalysisOutput` are correctly used.
    - `PRODUCTS` global from notebook will be loaded locally in `main`.
- **Output Handling**:
    - Adapt "Prepare Output Data for Google Sheets" cell.
    - Adapt "Write Results to Google Sheets" cell. The functions `authenticate_and_get_gspread_client` and `write_df_to_gsheet` should be moved, perhaps to `src/hermes/utils/gsheet.py` or kept in `main.py` if specific to this workflow.
    - Imports for `gspread`, `gspread_dataframe`, `google.colab.auth`, `google.auth` need to be handled. `google.colab.auth` is Colab-specific. For local execution, standard Google Cloud authentication (e.g., `gcloud auth application-default login`) or service account keys would be used. The `authenticate_and_get_gspread_client` function needs to be adapted or clearly documented for non-Colab environments. For now, I will try to use `google-auth` to get default credentials.
- **Execution**:
    - The script should be runnable with `if __name__ == "__main__": asyncio.run(main())`.

### Step 2.11: `README.md`
- Create `README.md` with:
    - Project description.
    - Instructions on setting up a `.env` file from `.env.example`.
    - How to install dependencies: `uv venv venv_name` (if not already done by user), `uv pip sync -p python_version_from_toml pyproject.toml`.
    - How to run: `python src/hermes/main.py`.

## 3. Iteration and Refinement
- Create directories and files one by one.
- Copy code from cells to the appropriate files.
- Add `__init__.py` files to make directories importable as packages.
- Adjust imports: use relative imports within the `hermes` package (e.g., `from .config import HermesConfig`, `from ..utils.gsheet import read_data_from_gsheet`).
- Remove Jupyter-specific code (`display`, `%pip`, etc.).
- Test by trying to run `python src/hermes/main.py`. Debug import errors and other issues.

This plan provides a clear path to refactor the notebook into a maintainable Python project. 