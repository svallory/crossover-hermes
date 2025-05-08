# Hermes Reference Solution Specification

This document maps each architectural decision to the concrete project structure. For each moving part, it specifies:
- Where to place the code
- Implementation pattern (class/function/other)
- Library and specific classes/functions to use
- Any other relevant details for a lean, best-practice LangChain/LangGraph solution

---

## 1. Configuration
- **Location:** `src/config.py`
- **Pattern:** Pydantic `BaseModel` class (e.g., `HermesConfig`)
- **Library:** `pydantic.BaseModel`
- **Details:**
  - All runtime and model parameters (model name, temperature, vector store config, etc)
  - Use a `from_runnable_config` classmethod for LangChain compatibility

---

## 2. State Schema
- **Location:** `src/state.py`
- **Pattern:** `dataclass` with `Annotated` fields (following agent examples)
- **Library:** `dataclasses`, `typing.Annotated`
- **Details:**
  - One state class for the whole pipeline (e.g., `HermesState`)
  - Fields for each processing stage (email, classification, order, inquiry, response, etc)
  - Use annotated fields with reducer functions (e.g., `messages: Annotated[List[BaseMessage], add_messages]`)
  - Consider subclassing `MessagesState` as the base for simpler implementation

---

## 3. Agents (Nodes)
- **Location:** `src/agents/`
  - `email_classifier.py`
  - `order_processor.py`
  - `response_generator.py`
  - `supervisor.py` (if needed)
- **Pattern:** Each agent as a function (or class with a `__call__` method if stateful)
- **Library:**
  - `langgraph.StateGraph` for pipeline
  - `langchain_core.messages` (`AIMessage`, `HumanMessage`, `ToolMessage`)
  - `langchain_core.runnables` for node composition
- **Details:**
  - Each agent receives and returns a state dict
  - Use `@tool` for tool-calling nodes if needed

---

## 4. Prompts
- **Location:** `src/prompts/`
  - One Python file per agent (e.g., `email_classifier.py`, `order_processor.py`, etc)
- **Pattern:** Exported variables (e.g., `EMAIL_CLASSIFIER_PROMPT: ChatPromptTemplate`)
- **Library:**
  - `langchain.prompts.ChatPromptTemplate`, `SystemMessagePromptTemplate`, `HumanMessagePromptTemplate`
- **Details:**
  - Use `ChatPromptTemplate` for all prompts
  - Store few-shot examples as variables in the same file
  - No markdown prompt files; all prompts as Python variables for type safety and IDE support

---

## 5. Tools (for Tool Calling)
- **Location:** `src/tools/`
  - Grouped by agent responsibility (e.g., `catalog_tools.py`, `order_tools.py`, `response_tools.py`)
- **Pattern:** Functions decorated with `@tool`
- **Library:**
  - `langchain_core.tools.tool`
  - Use `InjectedToolArg` and `InjectedState` for dependency injection
- **Details:**
  - Each tool is a function with type annotations
  - Tools are registered and passed to agents as needed

---

## 6. Vector Store & Embeddings
- **Location:** `src/vectorstore.py`
- **Pattern:** Functions or a simple class for setup and retrieval
- **Library:**
  - `langchain_community.vectorstores.Chroma`
  - `langchain_openai.OpenAIEmbeddings`
- **Details:**
  - One function to initialize the vector store and add product documents
  - Use metadata filtering for category-based pre-filtering
  - Note that category is not the only possible filter. A client may looking for a gift "whithin a price range"

---

## 7. Pipeline/Workflow Configuration
- **Location:** `src/pipeline.py`
- **Pattern:**
  - Define the main `StateGraph` pipeline
  - Add nodes for each agent
  - Use conditional routing for classification
- **Library:**
  - `langgraph.StateGraph`, `langgraph.types.Command`
- **Details:**
  - Compose the pipeline in a single file for clarity
  - Use subgraphs if needed for complex agent teams

---

## 8. Output/Integration
- **Location:** `src/output.py`
- **Pattern:** Functions for writing results to Google Sheets
- **Library:**
  - `gspread`, `gspread_dataframe`, `google.auth`
- **Details:**
  - Functions to create and update sheets as per assignment requirements

---

## 9. Testing & Validation
- **Location:** `src/tests/`
- **Pattern:** Pytest functions for each agent and the full pipeline
- **Library:** `pytest`
- **Details:**
  - Include sample emails and expected outputs
  - Focus on edge cases (multi-language, mixed intent, vague references)

---

## 10. Documentation
- **Location:** `README.md`, `docs/notes/`
- **Pattern:** Markdown files
- **Details:**
  - Overview, setup instructions, architecture diagram, and decision rationale

---

## 11. Memory & Checkpointing (Optional/Advanced)
- **Location:** `src/memory.py` (if needed)
- **Pattern:** Use LangGraph checkpointers for state persistence
- **Library:** `langgraph.checkpointers`
- **Details:**
  - Only if long-term memory or recovery is required

---

# Summary Table

| Part                | Location                | Pattern         | Library/Classes/Functions                      |
|---------------------|------------------------|-----------------|-----------------------------------------------|
| Config              | src/config.py           | Pydantic class  | pydantic.BaseModel                            |
| State               | src/state.py            | Dataclass       | dataclasses, typing.Annotated                 |
| Agents              | src/agents/            | Function/class  | langgraph.StateGraph, langchain_core.messages |
| Prompts             | src/prompts/           | Python vars     | langchain.prompts.ChatPromptTemplate          |
| Tools               | src/tools/             | @tool function  | langchain_core.tools.tool                     |
| Vector Store        | src/vectorstore.py      | Function/class  | Chroma, OpenAIEmbeddings                      |
| Pipeline            | src/pipeline.py         | StateGraph      | langgraph.StateGraph, Command                 |
| Output              | src/output.py           | Function        | gspread, gspread_dataframe                    |
| Testing             | src/tests/              | pytest          | pytest                                       |
| Docs                | README.md, docs/notes/  | Markdown       | -                                             |
| Memory (optional)   | src/memory.py           | Function/class  | langgraph.checkpointers                       |

---

This spec defines the skeleton for a lean, robust, and maintainable Hermes reference solution using LangChain and LangGraph best practices. 