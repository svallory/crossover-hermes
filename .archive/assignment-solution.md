# Solve Business Problems with AI - Codename: Hermes

## Objective
Develop a proof-of-concept application to intelligently process email order requests and customer inquiries for a fashion store. The system should accurately categorize emails as either product inquiries or order requests and generate appropriate responses using the product catalog information and current stock status.

This notebook implements the solution based on the provided design documents, leveraging Large Language Models (LLMs) for complex tasks like email classification, signal extraction, and response generation, and Retrieval-Augmented Generation (RAG) for handling product inquiries.

# 0. Project Overview & Requirements

This section reiterates the core tasks and deliverables as outlined in the original assignment description.

### Inputs

Google Spreadsheet **[Document](https://docs.google.com/spreadsheets/d/14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U)** containing:

- **Products**: List of products with fields including product ID, name, category, stock amount, detailed description, and season.

- **Emails**: Sequential list of emails with fields such as email ID, subject, and body.

### Instructions

- Implement all requirements using advanced Large Language Models (LLMs) to handle complex tasks, process extensive data, and generate accurate outputs effectively.
- Use Retrieval-Augmented Generation (RAG) and vector store techniques where applicable to retrieve relevant information and generate responses.
- You are provided with a temporary OpenAI API key granting access to GPT-4o, which has a token quota. Use it wisely or use your own key if preferred.
- Address the requirements in the order listed. Review them in advance to develop a general implementation plan before starting.
- Your deliverables should include:
   - Code developed within this notebook.
   - A single spreadsheet containing results, organized across separate sheets.
   - Comments detailing your thought process.
- You may use additional libraries (e.g., langchain) to streamline the solution. Use libraries appropriately to align with best practices for AI and LLM tools.
- Use the most suitable AI techniques for each task. Note that solving tasks with traditional programming methods will not earn points, as this assessment evaluates your knowledge of LLM tools and best practices.

### Requirements

#### 1. Classify emails
    
Classify each email as either a _**"product inquiry"**_ or an _**"order request"**_. Ensure that the classification accurately reflects the intent of the email.

**Output**: Populate the **email-classification** sheet with columns: email ID, category.

#### 2. Process order requests
1.   Process orders
  - For each order request, verify product availability in stock.
  - If the order can be fulfilled, create a new order line with the status "created".
  - If the order cannot be fulfilled due to insufficient stock, create a line with the status "out of stock" and include the requested quantity.
  - Update stock levels after processing each order.
  - Record each product request from the email.
  - **Output**: Populate the **order-status** sheet with columns: email ID, product ID, quantity, status (**_"created"_**, **_"out of stock"_**).

2.   Generate responses
  - Create response emails based on the order processing results:
      - If the order is fully processed, inform the customer and provide product details.
      - If the order cannot be fulfilled or is only partially fulfilled, explain the situation, specify the out-of-stock items, and suggest alternatives or options (e.g., waiting for restock).
  - Ensure the email tone is professional and production-ready.
  - **Output**: Populate the **order-response** sheet with columns: email ID, response.

#### 3. Handle product inquiry

Customers may ask general open questions.
  - Respond to product inquiries using relevant information from the product catalog.
  - Ensure your solution scales to handle a full catalog of over 100,000 products without exceeding token limits. Avoid including the entire catalog in the prompt.
  - **Output**: Populate the **inquiry-response** sheet with columns: email ID, response.

## Evaluation Criteria
- **Advanced AI Techniques**: The system should use Retrieval-Augmented Generation (RAG) and vector store techniques to retrieve relevant information from data sources and use it to respond to customer inquiries.
- **Tone Adaptation**: The AI should adapt its tone appropriately based on the context of the customer's inquiry. Responses should be informative and enhance the customer experience.
- **Code Completeness**: All functionalities outlined in the requirements must be fully implemented and operational as described.
- **Code Quality and Clarity**: The code should be well-organized, with clear logic and a structured approach. It should be easy to understand and maintain.
- **Presence of Expected Outputs**: All specified outputs must be correctly generated and saved in the appropriate sheets of the output spreadsheet. Ensure the format of each output matches the requirements—do not add extra columns or sheets.
- **Accuracy of Outputs**: The accuracy of the generated outputs is crucial and will significantly impact the evaluation of your submission.

We look forward to seeing your solution and your approach to solving real-world problems with AI technologies.

# 1. Environment Setup

This section handles the installation of necessary libraries, import of modules, and configuration of API keys and other constants.

### 1.1 Install Dependencies

```python
%pip install openai httpx==0.27.2 pandas pinecone-client thefuzz python-Levenshtein openpyxl
```

### 1.2 Import Libraries

```python
import os
import json
import time
import pandas as pd
from openai import OpenAI
import pinecone
from thefuzz import process as fuzz_process
from IPython.display import display, Markdown
```

### 1.3 Configure API Keys and Constants


```python
# --- OpenAI Configuration ---
OPENAI_API_KEY = "<OPENAI API KEY: Use one provided by Crossover or your own>"
OPENAI_BASE_URL = 'https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/'
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Pinecone Configuration ---
PINECONE_API_KEY = "<YOUR PINECONE API KEY>"
PINECONE_ENVIRONMENT = "<YOUR PINECONE ENVIRONMENT>"
PINECONE_INDEX_NAME = "hermes-products"
PINECONE_EMBEDDING_DIMENSION = 1536
PINECONE_METRIC = "cosine"

# --- Data Configuration ---
INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'
OUTPUT_SPREADSHEET_NAME = 'hermes_assignment_output.xlsx'

# --- Prompt Files Configuration ---
PROMPTS_DIR = "prompts/"
DOCS_DIR = "docs/"
SALES_GUIDE_FILENAME = "sales-email-intelligence-guide.md"

# --- Other Constants ---
FUZZY_MATCH_THRESHOLD = 80
MAX_RETRIES_LLM = 3
RETRY_DELAY_LLM = 5
```

### 1.4 Initialize OpenAI Client

```python
client = None
if OPENAI_API_KEY != "<OPENAI API KEY: Use one provided by Crossover or your own>":
    try:
        client = OpenAI(
            base_url=OPENAI_BASE_URL, # Comment out or remove if using your own key directly with OpenAI's API
            api_key=OPENAI_API_KEY
        )
        display(Markdown("OpenAI client initialized successfully."))
    except Exception as e:
        display(Markdown(f"**Error initializing OpenAI client:** {e}. Please check your API key and base URL."))
else:
    display(Markdown("**OpenAI API Key not configured.** Please set your API key in section 1.3."))
```

# 2. Data Loading and Preparation

This section includes functions to load the product catalog and email data from the specified Google Spreadsheet, and prepare them for processing.

```python
def read_data_frame(document_id, sheet_name):
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(export_link)
        # display(Markdown(f"Successfully loaded `{sheet_name}` (Shape: {df.shape}).")) # Removed for conciseness
        return df
    except Exception as e:
        display(Markdown(f"**Error loading sheet `{sheet_name}`:** {e}"))
        return pd.DataFrame()

products_df = read_data_frame(INPUT_SPREADSHEET_ID, 'products')
emails_df = read_data_frame(INPUT_SPREADSHEET_ID, 'emails')

# Display first few rows to verify loading - Removed for conciseness
# if not products_df.empty:
#     display(Markdown("**Products Data (First 3 rows):**"))
#     display(products_df.head(3))
# if not emails_df.empty:
#     display(Markdown("**Emails Data (First 3 rows):**"))
#     display(emails_df.head(3))
```

### 2.1 Data Cleaning and Preparation

Perform any necessary data cleaning or type conversions. For instance, ensuring product IDs are strings, stock is integer, price is float. Also, create a mutable copy of the inventory for processing.

```python
if not products_df.empty:
    products_df['product_id'] = products_df['product_id'].astype(str)
    products_df['stock'] = pd.to_numeric(products_df['stock'], errors='coerce').fillna(0).astype(int)
    products_df['price'] = pd.to_numeric(products_df['price'], errors='coerce').fillna(0.0).astype(float)
    # Ensure other text fields are strings and handle NaNs
    for col in ['name', 'category', 'description', 'season']:
        if col in products_df.columns:
            products_df[col] = products_df[col].astype(str).fillna('')
    # display(Markdown("Product data types processed.")) # Removed for conciseness
    # products_df.info() # For debugging types

if not emails_df.empty:
    emails_df['email_id'] = emails_df['email_id'].astype(str)
    # Ensure other text fields are strings and handle NaNs
    for col in ['subject', 'message_body']:
        if col in emails_df.columns:
             emails_df[col] = emails_df[col].astype(str).fillna('')
    # display(Markdown("Email data types processed.")) # Removed for conciseness
    # emails_df.info() # For debugging types
    
# Create a mutable copy of inventory for processing
inventory_df = None
if not products_df.empty:
    inventory_df = products_df[['product_id', 'stock']].copy()
    inventory_df.set_index('product_id', inplace=True)
    # display(Markdown("Initial inventory DataFrame created.")) # Removed for conciseness
    # display(inventory_df.head()) # For debugging
```

# 3. Utility Functions and Core Components

This section defines helper functions for loading prompt templates, interacting with LLMs, managing the Pinecone vector store, and other core logic required by the agent pipeline.

### 3.1 Prompt Engineering Utilities

Functions to load prompt templates from files, inject dynamic values (like email content or prior agent results), and include content from other files (e.g., `sales-email-intelligence-guide.md`).

```python
sales_guide_content = ""
try:
    # Adjust path if your notebook is not at the root of the hermes directory structure
    with open(os.path.join(DOCS_DIR, SALES_GUIDE_FILENAME), 'r') as f:
        sales_guide_content = f.read()
    display(Markdown(f"Successfully loaded `{SALES_GUIDE_FILENAME}` from `{DOCS_DIR}`."))
except FileNotFoundError:
    display(Markdown(f"**Warning:** `{SALES_GUIDE_FILENAME}` not found in `{DOCS_DIR}`. Prompts requiring it may fail or be incomplete."))
except Exception as e:
    display(Markdown(f"**Error loading `{SALES_GUIDE_FILENAME}`:** {e}"))

def load_prompt_template(prompt_filename, dynamic_values=None):
    """Loads a prompt template from a file and injects dynamic values and included files."""
    global sales_guide_content # Access the globally loaded sales guide
    try:
        # Adjust path if your notebook is not at the root of the hermes directory structure
        with open(os.path.join(PROMPTS_DIR, prompt_filename), 'r') as f:
            template = f.read()
    except FileNotFoundError:
        display(Markdown(f"**Error:** Prompt file `{prompt_filename}` not found in `{PROMPTS_DIR}`."))
        return None
    except Exception as e:
        display(Markdown(f"**Error reading prompt file `{prompt_filename}`:** {e}"))
        return None

    # Handle << include: sales-email-intelligence-guide.md >> directives
    if "<< include: sales-email-intelligence-guide.md >>" in template:
        if sales_guide_content:
            template = template.replace("<< include: sales-email-intelligence-guide.md >>", sales_guide_content)
        else:
            display(Markdown(f"**Warning:** Prompt `{prompt_filename}` requests `{SALES_GUIDE_FILENAME}`, but it was not loaded. Substitution skipped."))
    
    # Add more general file includes here if needed based on `<< include: filename >>` pattern
    # Example: For including other .md files from DOCS_DIR or PROMPTS_DIR
    # Note: This is a simple replace. More robust parsing for multiple includes might be needed.
    # For now, only the sales guide is explicitly handled.

    # Substitute other dynamic values like << include: email.subject >> or << classification_results >>
    if dynamic_values:
        for key, value in dynamic_values.items():
            # Ensure values that are dicts/lists are converted to JSON strings for inclusion in prompts
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, indent=2) # Pretty print JSON for readability
            else:
                value_str = str(value)
            template = template.replace(f"<< include: {key} >>", value_str) # For keys like 'email.subject'
            template = template.replace(f"<< {key} >>", value_str)       # For simple keys like 'classification_results'
            
    return template
```

### 3.2 LLM Interaction Utilities

A robust function to call the OpenAI Chat Completion API, including error handling, retries, and optional JSON output parsing.

```python
def call_openai_chat_completion(prompt_content, model=OPENAI_MODEL, temperature=0.2, is_json_output=True):
    """Calls the OpenAI Chat Completion API and returns the message content, optionally parsing JSON."""
    if not client:
        display(Markdown("**Error:** OpenAI client is not initialized. Cannot make API call."))
        return {"error": "OpenAI client not initialized"} if is_json_output else None # Return error dict if JSON expected

    messages = [{"role": "user", "content": prompt_content}]
    
    for attempt in range(MAX_RETRIES_LLM):
        try:
            response_format_arg = {"type": "json_object"} if is_json_output else None
            
            # Ensure response_format is only passed if not None, to avoid issues with models not supporting it or when not expecting JSON
            completion_args = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            if response_format_arg: # Only add if we want JSON and it's configured
                completion_args["response_format"] = response_format_arg
                
            completion = client.chat.completions.create(**completion_args)
            content = completion.choices[0].message.content
            
            if is_json_output:
                try:
                    # Attempt to strip markdown code block fences if present before parsing JSON
                    if content.strip().startswith("```json\n") and content.strip().endswith("\n```"):
                        content_for_json = content.strip()[7:-3].strip()
                    elif content.strip().startswith("```\n") and content.strip().endswith("\n```"):
                         content_for_json = content.strip()[3:-3].strip()
                    else:
                        content_for_json = content
                    return json.loads(content_for_json)
                except json.JSONDecodeError as e:
                    display(Markdown(f"**Warning:** LLM output was not valid JSON (attempt {attempt + 1}): {e}. Raw content (first 200 chars): ```{content[:200]}...```"))
                    if attempt < MAX_RETRIES_LLM - 1:
                        time.sleep(RETRY_DELAY_LLM)
                        continue # Retry if JSON parsing failed
                    return {"error": "JSONDecodeError after retries", "raw_content": content} # Final attempt failed
            return content # Return raw content if not expecting JSON
        except Exception as e:
            display(Markdown(f"**Error calling OpenAI API (attempt {attempt + 1}/{MAX_RETRIES_LLM}):** {e}"))
            if attempt < MAX_RETRIES_LLM - 1:
                time.sleep(RETRY_DELAY_LLM)
            else:
                display(Markdown("Max retries reached for OpenAI API call."))
                return {"error": str(e)} if is_json_output else None # Return error dict if JSON expected
    return {"error": "Max retries reached and call failed consistently"} if is_json_output else None
```

### 3.3 Pinecone Vector Store Utilities

Functions for initializing Pinecone, creating an index if it doesn't exist, embedding product data (text preparation and batch upsertion), and querying the index for Retrieval-Augmented Generation (RAG).

```python
pinecone_index = None # Global variable for the Pinecone index object

def initialize_pinecone():
    """Initializes Pinecone connection and returns the index object."""
    global pinecone_index
    if PINECONE_API_KEY == "<YOUR PINECONE API KEY>" or PINECONE_ENVIRONMENT == "<YOUR PINECONE ENVIRONMENT>":
        display(Markdown("**Pinecone API Key or Environment not configured.** Pinecone features will be disabled."))
        return None
    try:
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        if PINECONE_INDEX_NAME not in pinecone.list_indexes():
            display(Markdown(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'..."))
            pinecone.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=PINECONE_EMBEDDING_DIMENSION,
                metric=PINECONE_METRIC,
                # pod_type='p1.x1' 
            )
            # Wait for index to be ready
            wait_time = 0
            max_wait_time = 300 # 5 minutes
            while not pinecone.describe_index(PINECONE_INDEX_NAME).status['ready']:
                display(Markdown("Waiting for Pinecone index to be ready... (elapsed: {wait_time}s)"))
                time.sleep(10)
                wait_time += 10
                if wait_time >= max_wait_time:
                    display(Markdown("**Error:** Pinecone index did not become ready in time."))
                    return None
            display(Markdown(f"Index '{PINECONE_INDEX_NAME}' created and ready."))
        else:
            display(Markdown(f"Pinecone index '{PINECONE_INDEX_NAME}' already exists."))
        pinecone_index = pinecone.Index(PINECONE_INDEX_NAME)
        display(Markdown("Pinecone initialized and index object retrieved."))
        # display(pinecone_index.describe_index_stats())
        return pinecone_index
    except Exception as e:
        display(Markdown(f"**Error initializing Pinecone:** {e}. Check API key, environment, and index name/configuration."))
        pinecone_index = None
        return None

def get_openai_embeddings(texts_list, model=OPENAI_EMBEDDING_MODEL):
    """Generates embeddings for a list of texts using OpenAI."""
    if not client:
        display(Markdown("**Error:** OpenAI client not initialized for embeddings."))
        return []
    if not texts_list: # Handle empty list input to avoid API error
        return []
    try:
        # Replace newlines, as recommended by OpenAI for their embedding models to improve performance
        texts_list_cleaned = [str(text).replace("\n", " ") for text in texts_list]
        response = client.embeddings.create(input=texts_list_cleaned, model=model)
        return [item.embedding for item in response.data]
    except Exception as e:
        display(Markdown(f"**Error getting OpenAI embeddings:** {e}"))
        return []

def prepare_embedding_text_for_product(product_row_dict):
    """Prepares a concise text representation of a product for embedding, based on ITD-007."""
    # Ensure all parts are strings to avoid errors with NoneTypes during join/format
    name = str(product_row_dict.get('name', ''))
    description = str(product_row_dict.get('description', ''))
    category = str(product_row_dict.get('category', ''))
    season = str(product_row_dict.get('season', ''))
    return (
        f"Product: {name}\n"
        f"Description: {description}\n"
        f"Category: {category}\n"
        f"Season: {season}"
    )

def embed_and_upsert_products(products_df_to_embed, target_index, batch_size=50):
    """Embeds product data and upserts it into the Pinecone index."""
    if target_index is None or products_df_to_embed.empty:
        display(Markdown("**Error (Embed/Upsert):** Pinecone index not initialized or products DataFrame is empty. Cannot upsert."))
        return
    
    display(Markdown(f"Starting embedding and upsertion of {len(products_df_to_embed)} products to '{target_index.name}'... This may take a while."))
    for i in range(0, len(products_df_to_embed), batch_size):
        batch_df = products_df_to_embed.iloc[i:i+batch_size]
        # Use itertuples for efficiency and convert to dict for prepare_embedding_text_for_product
        texts_to_embed = [prepare_embedding_text_for_product(row._asdict()) for row in batch_df.itertuples(index=False)]
        
        if not texts_to_embed:
            display(Markdown(f"Skipping empty batch at index {i}."))
            continue
            
        embeddings = get_openai_embeddings(texts_to_embed)
        if not embeddings or len(embeddings) != len(batch_df):
            display(Markdown(f"**Warning (Embed/Upsert):** Embedding failed or mismatch for batch starting at index {i}. Expected {len(batch_df)}, got {len(embeddings)}. Skipping batch."))
            continue

        vectors_to_upsert = []
        for j, product_tuple in enumerate(batch_df.itertuples(index=False)):
            product_row_dict = product_tuple._asdict() # Convert NamedTuple to dict
            product_id_str = str(product_row_dict['product_id']) # Ensure ID is string for Pinecone
            
            # Get current stock from the operational inventory_df for metadata
            current_stock = 0 # Default if not found
            if inventory_df is not None and product_id_str in inventory_df.index:
                current_stock = int(inventory_df.loc[product_id_str, 'stock'])
            else:
                current_stock = int(product_row_dict.get('stock', 0)) # Fallback to original stock from products_df
                
            metadata_dict = {
                "product_id": product_id_str,
                "name": str(product_row_dict.get('name', '')),
                "description": str(product_row_dict.get('description', '')),
                "category": str(product_row_dict.get('category', '')),
                "season": str(product_row_dict.get('season', '')),
                "price": float(product_row_dict.get('price', 0.0)),
                "stock": current_stock 
            }
            vectors_to_upsert.append({
                "id": product_id_str, 
                "values": embeddings[j],
                "metadata": metadata_dict
            })
        
        if vectors_to_upsert:
            try:
                target_index.upsert(vectors=vectors_to_upsert)
                num_total_batches = (len(products_df_to_embed) + batch_size - 1) // batch_size
                # display(Markdown(f"Upserted batch {i//batch_size + 1}/{num_total_batches} to Pinecone.")) # Reduced verbosity
                if (i//batch_size + 1) % 5 == 0 or (i//batch_size + 1) == num_total_batches: # Display every 5 batches or on the last batch
                     display(Markdown(f"Pinecone upsert progress: Batch {i//batch_size + 1}/{num_total_batches} processed."))
            except Exception as e:
                display(Markdown(f"**Error (Embed/Upsert):** Failed upserting batch to Pinecone: {e}"))
        time.sleep(1)
    display(Markdown("Product embedding and upsertion complete."))

def query_pinecone_for_products(query_text, top_k=3, index_to_query=None):
    """Embeds a query and searches the Pinecone index."""
    if index_to_query is None:
        display(Markdown("**Error (Query Pinecone):** Pinecone index not available for querying."))
        return []
    if not query_text or not str(query_text).strip(): # Check for empty or whitespace-only query
        display(Markdown("**Warning (Query Pinecone):** Empty query text provided. Returning no results."))
        return []
            
    query_embedding_list = get_openai_embeddings([str(query_text)]) # Ensure query_text is string
    if not query_embedding_list or not query_embedding_list[0]:
        display(Markdown("**Error (Query Pinecone):** Failed to generate embedding for query text: '{str(query_text)[:100]}...'"))
        return []
    
    try:
        results = index_to_query.query(
            vector=query_embedding_list[0],
            top_k=top_k,
            include_metadata=True
        )
        return results.get('matches', [])
    except Exception as e:
        display(Markdown(f"**Error (Query Pinecone):** Failed during Pinecone query: {e}"))
        return []

# Initialize Pinecone (attempt once per session)
pinecone_index = initialize_pinecone()

# Populate Pinecone index with product data 
# This is a potentially long and costly operation. 
# Set RUN_PINECONE_POPULATION to True ONLY if you need to populate or re-populate the index. 
# For subsequent runs, if the index is already populated, this step will be skipped if the below flag is False.
RUN_PINECONE_POPULATION = False # <-- IMPORTANT: Default to False. Set to True only if you intend to (re)populate.

if RUN_PINECONE_POPULATION:
    if pinecone_index and not products_df.empty:
        display(Markdown("**Starting Pinecone population process (RUN_PINECONE_POPULATION is True)...**"))
        # Optional: Logic to delete and re-create index if a completely fresh population is always desired.
        # For now, it will upsert, which overwrites existing vectors with the same ID or adds new ones.
        embed_and_upsert_products(products_df, pinecone_index)
    else:
        display(Markdown("Skipping Pinecone population: RUN_PINECONE_POPULATION is True, but Pinecone index or product data is missing/unavailable."))
elif pinecone_index: # If not running population, but index exists, optionally show stats.
    display(Markdown("RUN_PINECONE_POPULATION is False. Assuming Pinecone index is already populated or population is not intended for this run."))
    # try:
    #    stats = pinecone_index.describe_index_stats()
    #    display(Markdown(f"Existing Pinecone index '{pinecone_index.name}' stats: {stats}"))
    # except Exception as e:
    #    display(Markdown(f"Could not fetch stats for existing index '{pinecone_index.name}': {e}"))
else:
    display(Markdown("RUN_PINECONE_POPULATION is False, and Pinecone index is not initialized (e.g. API key missing). RAG features will not work."))
```

### 3.4 Product Matching Utilities (Fuzzy Matching)

Based on ITD-003 (Product Name/ID Mapping Strategy) and ITD-006 (Product Matching Implementation Strategy), this uses fuzzy string matching (e.g., using `thefuzz` library) to map textual product mentions to product IDs from the catalog. This is an algorithmic approach that can supplement or be used by the LLM-based Product Matcher Agent.

```python
def resolve_product_mention_fuzzy(mention_text, product_names_list_for_fuzz, product_id_map_for_fuzz, score_threshold=FUZZY_MATCH_THRESHOLD):
    """
    Resolves a product mention using fuzzy matching against product names.
    Returns a dictionary with 'product_id', 'product_name', 'confidence', 'match_method' or None.
    product_id_map_for_fuzz: A dictionary mapping product names to product_ids for quick lookup after match.
    """
    if not mention_text or not product_names_list_for_fuzz:
        return None
    
    # Using extractOne which finds the best match above a certain score_cutoff
    match_details = fuzz_process.extractOne(str(mention_text), product_names_list_for_fuzz, score_cutoff=score_threshold)
    
    if match_details:
        matched_name_str, score_val = match_details
        # Retrieve the product_id using the matched name
        # This assumes product_name_to_id_map is {name: id}
        p_id = product_id_map_for_fuzz.get(matched_name_str)
        if p_id:
            return {
                "product_id": str(p_id), # Ensure product_id is string
                "product_name": matched_name_str,
                # Quantity is often part of the order extraction by LLM, not simple name matching. 
                # Defaulting to 1 or omitting it here, to be filled by a later stage if it's an order item.
                # "quantity": 1, 
                "confidence": score_val / 100.0, # Normalize score to 0.0 - 1.0
                "original_mention": str(mention_text),
                "match_method": "fuzzy_name_match"
            }
        else:
            # This case should be rare if product_id_map_for_fuzz is built correctly from the same source as product_names_list_for_fuzz
            display(Markdown(f"**Fuzzy match warning:** Matched name '{matched_name_str}' (from mention '{mention_text}') not found in product_id_map."))
    return None

# Prepare product names and a map from name to ID for efficient fuzzy matching
product_names_for_fuzzy_matching = []
product_name_to_id_dict = {}
if not products_df.empty:
    product_names_for_fuzzy_matching = products_df['name'].unique().tolist()
    product_name_to_id_dict = pd.Series(products_df.product_id.values, index=products_df.name).to_dict()
    # display(Markdown(f"Product name list ({len(product_names_for_fuzzy_matching)} unique) and name-to-ID map ({len(product_name_to_id_dict)}) prepared for fuzzy matching.")) # Removed
# else: # Assuming products_df is never empty as per user clarification
    # display(Markdown("Products DataFrame is empty. Fuzzy matching utilities will not be effective."))
```

# 4. Email Processing Pipeline Agents

This section defines the functions that represent each agent in the pipeline, as outlined in ITD-005 (Agent Architecture). Each agent function will typically:
1. Load its specific prompt template from the `/prompts` directory.
2. Populate the template with dynamic data (e.g., email content, outputs from previous agents, RAG context).
3. Call the LLM (via `call_openai_chat_completion`).
4. Parse the structured JSON output from the LLM and return it.

Error handling and data validation will be incorporated within each agent and in the main loop.

### 4.1 Agent 1: Classification & Signal Extraction Agent

**Purpose**: Analyzes incoming emails to determine primary intent (order or inquiry) and extract all relevant customer signals (product mentions, emotional cues, etc.) based on `prompts/01-classification-signal-extraction-agent.md` and the `sales-email-intelligence-guide.md`.

```python
def classification_signal_extraction_agent(email_id_val, email_subject_val, email_message_val):
    """Processes an email for classification and signal extraction using an LLM."""
    display(Markdown(f"**Agent 1 (Classification) processing Email ID: {email_id_val}**"))
    prompt_template_filename = "01-classification-signal-extraction-agent.md"
    dynamic_prompt_values = {
        "email.email_id": email_id_val,
        "email.subject": str(email_subject_val),
        "email.message": str(email_message_val)
    }
    complete_prompt_content = load_prompt_template(prompt_template_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        return {"error": f"Failed to load prompt for Agent 1: {prompt_template_filename}"}
    
    llm_response = call_openai_chat_completion(complete_prompt_content, is_json_output=True)
    
    # Validate basic structure of LLM response for this agent
    if isinstance(llm_response, dict) and 'category' in llm_response and 'confidence' in llm_response and 'signals' in llm_response:
        display(Markdown(f"Agent 1: Classification for {email_id_val}: **{llm_response.get('category', 'N/A')}** (Confidence: {llm_response.get('confidence', 0):.2f})"))
    elif isinstance(llm_response, dict) and 'error' in llm_response:
        display(Markdown(f"**Error in Agent 1 output for {email_id_val}:** {llm_response['error']}. Raw: {llm_response.get('raw_content','empty')[:200]}..."))
    else:
        display(Markdown(f"**Agent 1 failed or returned malformed JSON for Email ID: {email_id_val}. Output (first 300 chars): {str(llm_response)[:300]}**"))
        return {"error": "Agent 1 failed or returned malformed JSON", "raw_output": str(llm_response)[:500]}
    return llm_response
```

### 4.2 Agent 2: Product Matcher Agent

**Purpose**: Identifies specific products mentioned in the email, distinguishing between order items and inquiry items. It leverages signals from Agent 1 and uses a combination of matching strategies (exact ID, fuzzy name, vector similarity for descriptions if prompted). Relies on `prompts/02-product-matcher-agent.md`. 
The current implementation primarily tasks the LLM with this based on catalog snippets and signals. Algorithmic fuzzy matching (from 3.4) can be used as a pre-processing step or fallback if the LLM struggles, but the primary path here is LLM-driven matching guided by context.

```python
def product_matcher_agent(email_id_val, classification_agent_results, products_catalog_df_ref, pinecone_index_ref):
    """Identifies specific products mentioned in the email using LLM, guided by catalog data and signals."""
    display(Markdown(f"**Agent 2 (Product Matcher) processing Email ID: {email_id_val}**"))
    prompt_template_filename = "02-product-matcher-agent.md"

    if not isinstance(classification_agent_results, dict) or 'signals' not in classification_agent_results:
        display(Markdown("**Error (Agent 2):** Classification results are missing or invalid for product matching."))
        return {"error": "Missing or invalid classification_results for Agent 2"}

    # Prepare a snippet of the product catalog to provide context to the LLM
    product_catalog_context_str = "Product_ID,Name,Category,Description (first 50 chars),Stock\n" # Added Stock
    if not products_catalog_df_ref.empty:
        # Try to provide a more relevant snippet if product_identification signals exist
        identified_mentions = classification_agent_results.get('signals', {}).get('product_identification', [])
        candidate_products_for_snippet_df = pd.DataFrame()
        
        # 1. Exact ID matches from mentions
        if identified_mentions:
            exact_id_matches_df = products_catalog_df_ref[products_catalog_df_ref['product_id'].isin(identified_mentions)]
            if not exact_id_matches_df.empty:
                candidate_products_for_snippet_df = pd.concat([candidate_products_for_snippet_df, exact_id_matches_df])

        # 2. Fuzzy name matches for remaining mentions (if any)
        #    This is illustrative; a full fuzzy pre-match could be complex here. LLM will use raw mentions.

        # 3. If few specific candidates, add some general catalog items for broader context
        num_specific_candidates = len(candidate_products_for_snippet_df)
        num_general_needed = max(0, 10 - num_specific_candidates) # Aim for around 10-15 total for snippet
        
        if num_general_needed > 0 and len(products_catalog_df_ref) > num_specific_candidates:
            # Exclude already selected candidates from sampling general ones
            remaining_products_df = products_catalog_df_ref[~products_catalog_df_ref['product_id'].isin(candidate_products_for_snippet_df['product_id'])]
            if not remaining_products_df.empty:
                 sample_size = min(num_general_needed, len(remaining_products_df))
                 general_sample_df = remaining_products_df.sample(sample_size, random_state=1) # random_state for reproducibility
                 candidate_products_for_snippet_df = pd.concat([candidate_products_for_snippet_df, general_sample_df])
        
        df_for_snippet = candidate_products_for_snippet_df.drop_duplicates(subset=['product_id']).head(15) # Limit total snippet size
        
        if df_for_snippet.empty and not products_catalog_df_ref.empty: # Fallback if no candidates found
            df_for_snippet = products_catalog_df_ref.head(10)

        for _, row_data in df_for_snippet.iterrows():
            desc_snip = str(row_data.get('description', ''))[:50].replace('\n', ' ') + "..."
            # Get current stock from live inventory_df for the snippet
            stock_val = 0
            if inventory_df is not None and row_data['product_id'] in inventory_df.index:
                stock_val = inventory_df.loc[row_data['product_id'], 'stock']
            else:
                stock_val = row_data.get('stock',0) # Fallback to original if not in live inventory
            product_catalog_context_str += f"{row_data.get('product_id')},{row_data.get('name')},{row_data.get('category')},{desc_snip},{stock_val}\n"
    else:
        product_catalog_context_str += "No product catalog data available.\n"

    # Vector similarity search is mentioned in the prompt's instructions to the LLM.
    # The LLM is expected to use descriptive phrases if it identifies them from the email signals.
    # For this PoC, we don't have a separate Python step for vector search *within* this agent call based on LLM identifying a phrase.
    # The RAG in Agent 4 (Inquiry Processing) is more direct for vector search against user queries.
    vector_search_info_for_prompt = "(Vector similarity search can be used for descriptive phrases if such are identified from email signals. Currently, prioritize matches from the provided catalog snippet and direct mentions. If a descriptive phrase seems key, note it for potential later vector search if direct matching fails.)"

    dynamic_prompt_values = {
        "classification_results": classification_agent_results, # Full JSON output from Agent 1
        "product_catalog": product_catalog_context_str,
        "vector_embeddings_of_product_descriptions": vector_search_info_for_prompt 
    }
    complete_prompt_content = load_prompt_template(prompt_template_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        return {"error": f"Failed to load prompt for Agent 2: {prompt_template_filename}"}
    
    llm_response = call_openai_chat_completion(complete_prompt_content, is_json_output=True)

    if isinstance(llm_response, dict) and 'order_items' in llm_response and 'inquiry_items' in llm_response : # Check for key fields
        display(Markdown(f"Agent 2: Product matching for {email_id_val} completed. Order items found: {len(llm_response.get('order_items',[]))}, Inquiry items found: {len(llm_response.get('inquiry_items',[]))}, Unmatched: {len(llm_response.get('unmatched_mentions',[]))}"))
    elif isinstance(llm_response, dict) and 'error' in llm_response:
        display(Markdown(f"**Error in Agent 2 (Product Matcher) output for {email_id_val}:** {llm_response['error']}. Raw: {llm_response.get('raw_content','empty')[:200]}..."))
    else:
        display(Markdown(f"**Agent 2 (Product Matcher) failed or returned unexpected/malformed JSON for Email ID: {email_id_val}. Output: {str(llm_response)[:300]}**"))
        return {"error": "Agent 2 failed or returned malformed JSON", "raw_output": str(llm_response)[:500]}
    return llm_response
```

### 4.3 Agent 3: Order Processing Agent

**Purpose**: Processes confirmed order items (from Agent 2). Checks inventory (live `inventory_df` snapshot provided in the prompt), determines fulfillment status (created, out_of_stock, partial), suggests alternatives for out-of-stock items, and outputs LLM-generated `inventory_updates` instructions (which Python code then validates and applies to the live `inventory_df`). Based on `prompts/03-order-processing-agent.md`.

```python
def order_processing_agent(email_id_val, product_matcher_agent_results, current_inventory_snapshot_df, main_products_catalog_df):
    """Processes order items, checks stock, and suggests alternatives using an LLM."""
    display(Markdown(f"**Agent 3 (Order Processing) processing Email ID: {email_id_val}**"))
    prompt_template_filename = "03-order-processing-agent.md"
    
    # Ensure product_matcher_results is a dict, even if it failed or was empty, to avoid errors in .get()
    order_items_list_to_process = product_matcher_agent_results.get('order_items', []) if isinstance(product_matcher_agent_results, dict) else []
    
    if not order_items_list_to_process:
        display(Markdown(f"Agent 3: No order items to process for {email_id_val} based on Product Matcher output."))
        return { "processed_items": [], "unfulfilled_items_for_inquiry": [], "inventory_updates": [] } # Return valid empty structure

    # Prepare current inventory status string for ONLY the items in the order for the LLM's primary focus
    inventory_status_for_prompt_str = "Product_ID,Name,Current_Stock\n"
    # Get unique product IDs from the order items to avoid redundant lookups
    ordered_product_ids = list(set(item['product_id'] for item in order_items_list_to_process if 'product_id' in item and item['product_id']))

    for pid_str in ordered_product_ids:
        stock_level = 0 # Default if not found
        product_name_val = "Unknown Product"
        if pid_str in current_inventory_snapshot_df.index:
            stock_level = current_inventory_snapshot_df.loc[pid_str, 'stock']
            # Get product name for better context in prompt
            if pid_str in main_products_catalog_df['product_id'].values:
                 product_name_val = main_products_catalog_df.loc[main_products_catalog_df['product_id'] == pid_str, 'name'].iloc[0]
        inventory_status_for_prompt_str += f"{pid_str},{product_name_val},{stock_level}\n"
                
    # Provide a broader catalog snippet for the LLM to find alternatives for out-of-stock items
    # This helps LLM suggest relevant alternatives beyond just the ordered items.
    product_catalog_for_alternatives_str = "Product_ID,Name,Category,Price,Current_Stock\n"
    if not main_products_catalog_df.empty:
         # Sample some products, prioritizing those in stock, potentially from similar categories if an item is OOS
         # For PoC, using a larger sample of the catalog for LLM to pick from. Max 30-40 items.
         sample_size = min(30, len(main_products_catalog_df))
         df_for_alt_snippet = main_products_catalog_df.sample(sample_size, random_state=42) if len(main_products_catalog_df) > sample_size else main_products_catalog_df

         for _, row_data in df_for_alt_snippet.iterrows():
            # Get current stock for these potential alternatives from live inventory
            stock_level_alt = 0
            if row_data['product_id'] in current_inventory_snapshot_df.index:
                stock_level_alt = current_inventory_snapshot_df.loc[row_data['product_id'], 'stock']
            product_catalog_for_alternatives_str += f"{row_data.get('product_id')},{row_data.get('name')},{row_data.get('category')},{row_data.get('price')},{stock_level_alt}\n"

    dynamic_prompt_values = {
        # Agent 03 prompt expects `product_matcher_results` which should contain `order_items` array
        "product_matcher_results": {"order_items": order_items_list_to_process}, 
        "current_inventory_status": inventory_status_for_prompt_str, # Stock for items in order
        "product_catalog_for_alternatives": product_catalog_for_alternatives_str # Broader catalog for suggesting alts
    }
    complete_prompt_content = load_prompt_template(prompt_template_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        return {"error": f"Failed to load prompt for Agent 3: {prompt_template_filename}"}
    
    llm_response = call_openai_chat_completion(complete_prompt_content, is_json_output=True)

    # Validate basic structure of LLM response for this agent
    if isinstance(llm_response, dict) and 'processed_items' in llm_response: # Key field for this agent
        display(Markdown(f"Agent 3: Order processing for {email_id_val} completed by LLM. Items LLM decided on: {len(llm_response.get('processed_items',[]))}"))
    elif isinstance(llm_response, dict) and 'error' in llm_response:
        display(Markdown(f"**Error in Agent 3 (Order Processing) output for {email_id_val}:** {llm_response['error']}. Raw: {llm_response.get('raw_content','empty')[:200]}..."))
    else:
        display(Markdown(f"**Agent 3 (Order Processing) failed or returned unexpected/malformed JSON for Email ID: {email_id_val}. Output: {str(llm_response)[:300]}**"))
        return {"error": "Agent 3 failed or returned malformed JSON", "raw_output": str(llm_response)[:500]}
    return llm_response

def apply_inventory_updates_from_llm_decision(order_processing_llm_results, live_inventory_df_ref):
    """
    Applies inventory updates to the `live_inventory_df_ref` based on the LLM's order processing output.
    This function interprets the `processed_items` from the LLM to determine actual stock deductions.
    It modifies `live_inventory_df_ref` in place.
    Returns a list of dictionaries, where each dict describes an actual update applied.
    """
    if not isinstance(order_processing_llm_results, dict) or 'processed_items' not in order_processing_llm_results:
        display(Markdown("Apply Inventory: Invalid or missing 'processed_items' in LLM results. No updates applied."))
        return [] 
    
    if live_inventory_df_ref is None:
        display(Markdown("Apply Inventory: Live inventory DataFrame is None. Cannot apply updates."))
        return []
        
    actual_applied_inventory_changes_list = []
    llm_processed_items_list = order_processing_llm_results.get('processed_items', [])
    
    for item_data_dict in llm_processed_items_list:
        pid_str = str(item_data_dict.get('product_id', '')) # Ensure string ID
        status_str = item_data_dict.get('status')
        # 'quantity' in processed_items is the original requested quantity by customer for that item
        original_requested_qty = int(item_data_dict.get('quantity', 0)) 
        
        if not pid_str:
            display(Markdown(f"Apply Inventory: Missing product_id in processed item data: {item_data_dict}"))
            continue
            
        if pid_str not in live_inventory_df_ref.index:
            display(Markdown(f"**Warning (Apply Inventory):** Product ID '{pid_str}' from order results not found in live inventory. Cannot apply update."))
            continue
            
        current_stock_on_record = live_inventory_df_ref.loc[pid_str, 'stock']
        quantity_to_deduct_from_stock = 0

        if status_str == 'created':
            # LLM confirmed full order for original_requested_qty based on stock it was shown. Deduct that original requested quantity.
            quantity_to_deduct_from_stock = original_requested_qty
        elif status_str == 'partial_fulfillment':
            # LLM decided on partial fulfillment. It should output 'available_quantity' for what was actually fulfilled.
            # This 'available_quantity' from LLM is the amount it believes can be fulfilled and thus deducted.
            quantity_to_deduct_from_stock = int(item_data_dict.get('available_quantity', 0))
            if quantity_to_deduct_from_stock == 0 and original_requested_qty > 0:
                display(Markdown(f"**Warning (Apply Inventory):** Partial fulfillment for '{pid_str}' but LLM's 'available_quantity' is 0 or missing. No stock deducted for this item based on this status logic."))
        elif status_str == 'out_of_stock':
            quantity_to_deduct_from_stock = 0 # No stock deducted for OOS items
        else:
            display(Markdown(f"**Warning (Apply Inventory):** Unknown status '{status_str}' for product '{pid_str}'. No stock deducted."))
            continue # Skip to next item if status is unclear
            
        if quantity_to_deduct_from_stock > 0:
            if quantity_to_deduct_from_stock > current_stock_on_record:
                display(Markdown(f"**Critical Warning (Apply Inventory):** For product '{pid_str}', LLM/logic determined to fulfill {quantity_to_deduct_from_stock}, but only {current_stock_on_record} is actually available in live inventory. Deducting only the available stock ({current_stock_on_record}). This indicates a potential discrepancy or race condition if multiple processes update stock."))
                quantity_to_deduct_from_stock = current_stock_on_record # Safety: never deduct more than currently available
            
            new_stock_level = current_stock_on_record - quantity_to_deduct_from_stock
            live_inventory_df_ref.loc[pid_str, 'stock'] = new_stock_level # Modify live inventory DataFrame
            
            applied_change_info = {
                "product_id": pid_str,
                "quantity_fulfilled_and_deducted": quantity_to_deduct_from_stock,
                "stock_before_update": current_stock_on_record,
                "stock_after_update": new_stock_level,
                "llm_item_status": status_str
            }
            actual_applied_inventory_changes_list.append(applied_change_info)
            display(Markdown(f"Inventory update for '{pid_str}': {current_stock_on_record} -> {new_stock_level} (deducted: {quantity_to_deduct_from_stock}) based on LLM status '{status_str}'."))
            
    return actual_applied_inventory_changes_list
```

### 4.4 Agent 4: Inquiry Processing Agent

**Purpose**: Handles product inquiries. Python code first performs RAG by embedding the inquiry and querying Pinecone (using utilities from 3.3) to fetch relevant product context. This context, along with signals (Agent 1), matched inquiry items (Agent 2), and any unfulfilled order items needing alternatives (Agent 3), is then fed to the LLM (using `prompts/04-inquiry-processing-agent.md`) to structure answers, suggest alternatives, and identify upsell opportunities.

```python
def inquiry_processing_agent(email_id_val, classification_agent_results, product_matcher_agent_results, order_proc_results_for_unfulfilled, main_products_catalog_df, pinecone_idx_ref):
    """Handles product inquiries using RAG (Python-driven) and LLM for structured responses."""
    display(Markdown(f"**Agent 4 (Inquiry Processing) processing Email ID: {email_id_val}**"))
    prompt_template_filename = "04-inquiry-processing-agent.md"

    # Ensure inputs are dicts, even if prior steps failed or had no relevant items, to prevent .get() errors
    product_matcher_data = product_matcher_agent_results if isinstance(product_matcher_agent_results, dict) else {}
    classification_data = classification_agent_results if isinstance(classification_agent_results, dict) else {}
    order_processing_unfulfilled_data = order_proc_results_for_unfulfilled if isinstance(order_proc_results_for_unfulfilled, dict) else {}
    
    inquiry_items_from_matcher_list = product_matcher_data.get('inquiry_items', [])
    # Items from order processing that were unfulfilled and now need to be treated as inquiries for alternatives
    unfulfilled_order_items_now_inquiries = order_processing_unfulfilled_data.get('unfulfilled_items_for_inquiry', [])

    if not inquiry_items_from_matcher_list and not unfulfilled_order_items_now_inquiries:
        display(Markdown(f"Agent 4: No direct inquiry items or unfulfilled order items needing alternatives for {email_id_val}."))
        return { "inquiry_responses": [], "alternative_suggestions": [], "upsell_opportunities": [] } # Valid empty structure
    
    # --- RAG Component: Fetch context for inquiry items from Pinecone --- 
    rag_context_for_llm_prompt_list = []
    # Process direct inquiry items first
    if inquiry_items_from_matcher_list:
        for item_data_dict in inquiry_items_from_matcher_list:
            item_product_id_str = str(item_data_dict.get('product_id', ''))
            item_questions_list = item_data_dict.get('questions', []) # List of questions about this item
            item_original_mention_str = str(item_data_dict.get('original_mention', ''))
            
            # Formulate a query for Pinecone based on questions or original mention
            query_text_for_pinecone_search = item_original_mention_str
            if item_questions_list: # Append questions to the query for better context
                query_text_for_pinecone_search += " " + " ".join(item_questions_list)
            
            pinecone_search_results_list = []
            if query_text_for_pinecone_search.strip(): # Only query if there's meaningful text
                pinecone_search_results_list = query_pinecone_for_products(query_text_for_pinecone_search.strip(), top_k=3, index_to_query=pinecone_idx_ref)
            
            # If a specific product ID is known for the inquiry, fetch its direct details to ensure it's in context
            if item_product_id_str and not main_products_catalog_df.empty and item_product_id_str in main_products_catalog_df['product_id'].values:
                # .loc might return a DataFrame, so use .iloc[0] to get the Series, then .to_dict()
                exact_product_series = main_products_catalog_df.loc[main_products_catalog_df['product_id'] == item_product_id_str].iloc[0]
                exact_product_text_for_rag = prepare_embedding_text_for_product(exact_product_series.to_dict())
                rag_context_for_llm_prompt_list.append({
                    "query_mention_or_product": f"{item_original_mention_str} (specific product inquiry: {item_product_id_str})",
                    "retrieved_info": f"Details for Product ID '{item_product_id_str}' (Name: '{exact_product_series.get('name')}'): {exact_product_text_for_rag}"
                })
            elif not item_product_id_str and item_original_mention_str: # General mention, rely on Pinecone search
                 display(Markdown(f"Agent 4: Inquiry item '{item_original_mention_str}' has no specific product ID. Relying on RAG search for context."))

            if pinecone_search_results_list:
                for match_item_dict in pinecone_search_results_list:
                    metadata = match_item_dict.get('metadata', {})
                    rag_context_for_llm_prompt_list.append({
                        "query_mention_or_product": item_original_mention_str, # The original customer mention that triggered this RAG search
                        "retrieved_info": f"Retrieved via similarity search (score: {match_item_dict.get('score',0):.2f}): Product ID '{match_item_dict.get('id')}', Name: '{metadata.get('name')}', Description: {str(metadata.get('description',''))[:150]}... Category: {metadata.get('category')}, Price: ${metadata.get('price', 0.0):.2f}, Stock: {metadata.get('stock',0)}"
                    })
    # --- End RAG Component ---

    # Provide a general product catalog snippet for LLM context (e.g., for upsells not directly from RAG, or if RAG yields little)
    general_product_catalog_snippet_str = "Product_ID,Name,Category,Price,Current_Stock\n"
    if not main_products_catalog_df.empty:
        # Sample some products for general context, ensuring stock info is from live inventory_df
        sample_size_catalog = min(20, len(main_products_catalog_df))
        df_for_general_snippet = main_products_catalog_df.sample(sample_size_catalog, random_state=101) if len(main_products_catalog_df) > sample_size_catalog else main_products_catalog_df
        for _, row_data_dict in df_for_general_snippet.iterrows():
             stock_val = 0
             if inventory_df is not None and row_data_dict['product_id'] in inventory_df.index:
                stock_val = inventory_df.loc[row_data_dict['product_id'], 'stock']
             else:
                stock_val = row_data_dict.get('stock', 0)
             general_product_catalog_snippet_str += f"{row_data_dict.get('product_id')},{row_data_dict.get('name')},{row_data_dict.get('category')},{row_data_dict.get('price')},{stock_val}\n"

    dynamic_prompt_values = {
        "product_matcher_results": product_matcher_data, # Contains original inquiry_items from Agent 2
        "unfulfilled_order_items": unfulfilled_order_items_now_inquiries, # From Agent 3, items that need alternative suggestions
        "product_catalog_with_detailed_descriptions": general_product_catalog_snippet_str, # General catalog context for LLM
        "signals_from_classification": classification_data.get('signals', {}), # Signals from Agent 1
        "retrieved_rag_context": rag_context_for_llm_prompt_list # Specific context from Pinecone RAG search
    }
    complete_prompt_content = load_prompt_template(prompt_template_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        return {"error": f"Failed to load prompt for Agent 4: {prompt_template_filename}"}

    llm_response = call_openai_chat_completion(complete_prompt_content, is_json_output=True)

    if isinstance(llm_response, dict) and 'inquiry_responses' in llm_response: # Check for a key field
        display(Markdown(f"Agent 4: Inquiry processing for {email_id_val} completed by LLM. Responses generated: {len(llm_response.get('inquiry_responses',[]))}, Alt suggestions: {len(llm_response.get('alternative_suggestions',[]))}, Upsells: {len(llm_response.get('upsell_opportunities',[]))}"))
    elif isinstance(llm_response, dict) and 'error' in llm_response:
        display(Markdown(f"**Error in Agent 4 (Inquiry Processing) output for {email_id_val}:** {llm_response['error']}. Raw: {llm_response.get('raw_content','empty')[:200]}..."))
    else:
        display(Markdown(f"**Agent 4 (Inquiry Processing) failed or returned unexpected/malformed JSON for Email ID: {email_id_val}. Output: {str(llm_response)[:300]}**"))
        return {"error": "Agent 4 failed or returned malformed JSON", "raw_output": str(llm_response)[:500]}
    return llm_response
```

### 4.5 Agent 5: Response Composer Agent

**Purpose**: The final agent in the pipeline. It synthesizes all information gathered and processed by the previous agents (classification, product matches, order status, inquiry answers, RAG context) into a single, cohesive, personalized email response formatted as JSON (subject, greeting, body, signature). Based on `prompts/05-response-composer-agent.md`.

```python
def response_composer_agent(email_id_val, original_email_subj, original_email_msg, 
                            class_results, prod_match_results, 
                            order_proc_results, inquiry_proc_results):
    """Composes the final email response using an LLM, based on all prior processing steps."""
    display(Markdown(f"**Agent 5 (Response Composer) processing Email ID: {email_id_val}**"))
    prompt_template_filename = "05-response-composer-agent.md"

    # Ensure all inputs to the prompt are dicts, even if empty or failed from previous steps, to prevent template errors.
    # The prompt expects these keys, so provide empty dicts if results are None or not dicts.
    cr = class_results if isinstance(class_results, dict) else {"error": "Classification results missing or invalid"}
    pmr = prod_match_results if isinstance(prod_match_results, dict) else {"error": "Product matcher results missing or invalid"}
    # Order processing might be None if it was a pure inquiry email
    opr = order_proc_results if isinstance(order_proc_results, dict) else {}
    # Inquiry processing might be None if it was a pure order with no unfulfilled items/questions
    ipr = inquiry_proc_results if isinstance(inquiry_proc_results, dict) else {}
    
    dynamic_prompt_values = {
        "email.email_id": email_id_val,
        "email.subject": str(original_email_subj),
        "email.message": str(original_email_msg),
        "classification_results": cr,
        "product_matcher_results": pmr, 
        "order_processing_results": opr, 
        "inquiry_processing_results": ipr 
    }
    complete_prompt_content = load_prompt_template(prompt_template_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        error_msg = f"Failed to load prompt for Agent 5: {prompt_template_filename}"
        display(Markdown(f"**{error_msg} for Email ID: {email_id_val}**"))
        return f"Error in Response Composer: {error_msg}" # Return a string for the output sheet
    
    # Temperature might be slightly higher for more natural responses
    llm_response_json = call_openai_chat_completion(complete_prompt_content, is_json_output=True, temperature=0.4)

    # Validate the expected JSON structure from the LLM for the response
    if isinstance(llm_response_json, dict) and 'body' in llm_response_json and 'subject' in llm_response_json: # Check for key fields
        display(Markdown(f"Agent 5: Response composed for {email_id_val}. Subject: '{llm_response_json.get('subject', 'N/A')}'"))
        # Combine the parts into a single string for the output sheet, as per assignment requirement for a single 'response' column.
        full_response_str = (
            f"Subject: {llm_response_json.get('subject', '(No Subject Provided)')}\n\n"
            f"{llm_response_json.get('greeting', '')}\n\n"
            f"{llm_response_json.get('body', '(No Body Content Provided)')}\n\n"
            f"{llm_response_json.get('signature', '(No Signature Provided)')}"
        )
        return full_response_str
    elif isinstance(llm_response_json, dict) and 'error' in llm_response_json:
        error_detail = llm_response_json['error']
        raw_content_snip = str(llm_response_json.get('raw_content','empty'))[:200] + "..."
        display(Markdown(f"**Error in Agent 5 (Response Composer) output for {email_id_val}:** {error_detail}. Raw: {raw_content_snip}"))
        return f"Error composing response via Agent 5: {error_detail}. Raw LLM output snippet: {raw_content_snip}"
    else:
        # This case handles if llm_response_json is None or not a dict, or a dict missing key fields
        malformed_output_str = str(llm_response_json)[:300]
        display(Markdown(f"**Agent 5 (Response Composer) failed, returned unexpected or malformed/incomplete JSON for Email ID: {email_id_val}. Output: {malformed_output_str}**"))
        return f"Failed to compose response: Agent 5 returned malformed or incomplete JSON. Output: {malformed_output_str}"
```

# 5. Main Email Processing Loop

This section iterates through each email from the `emails_df` DataFrame, passes it through the defined agent pipeline, and collects all the results (classifications, order statuses, generated responses) into lists. These lists will then be used to populate the output DataFrames for the final spreadsheet.

```python
# Lists to store outputs for each sheet
email_classification_output_list = []
order_status_output_list = []         # For order-status sheet
order_response_output_list = []       # For order-response sheet
inquiry_response_output_list = []      # For inquiry-response sheet

# --- Configuration for Processing --- 
# Set MAX_EMAILS_TO_PROCESS to a small number (e.g., 1, 2, 5) for quick testing.
# Set to 0 or a large number to process all emails (or up to length of emails_df).
MAX_EMAILS_TO_PROCESS = 0 # 0 means process all emails in the loaded dataframe
# Delay between processing each email to be polite to APIs and manage rate limits
INDIVIDUAL_EMAIL_DELAY_SECONDS = 1.5 # Increased slightly

# For collecting any critical errors during the loop that prevent full processing of an email
processing_errors_summary_list = []

# --- Pre-flight checks for critical components ---
CAN_PROCEED_PROCESSING = True
# Removed checks for emails_df.empty, products_df.empty, inventory_df is None as per user request, assuming data is defined.
# if emails_df.empty:
#     display(Markdown("**CRITICAL ERROR: `emails_df` is empty. Cannot proceed.**"))
#     CAN_PROCEED_PROCESSING = False
# if products_df.empty:
#     display(Markdown("**CRITICAL ERROR: `products_df` is empty. Cannot proceed.**"))
#     CAN_PROCEED_PROCESSING = False
# if inventory_df is None and not products_df.empty: # inventory_df relies on products_df
#     display(Markdown("**CRITICAL ERROR: `inventory_df` is not initialized.**"))
#     CAN_PROCEED_PROCESSING = False

if client is None:
    display(Markdown("**CRITICAL ERROR: OpenAI client (`client`) is not initialized.** Check API key (Section 1.3) and client init (Section 1.4)."))
    CAN_PROCEED_PROCESSING = False
if PINECONE_API_KEY != "<YOUR PINECONE API KEY>" and PINECONE_API_KEY != "" and PINECONE_API_KEY is not None and pinecone_index is None: # Check if key is set but index failed
    display(Markdown("**CRITICAL ERROR: Pinecone API key provided, but `pinecone_index` is not initialized.** Check Pinecone init (Section 3.3). RAG will fail."))
    CAN_PROCEED_PROCESSING = False

# --- Main Processing Loop --- 
if CAN_PROCEED_PROCESSING:
    emails_for_loop_df = emails_df.copy() # Work on a copy
    if MAX_EMAILS_TO_PROCESS > 0:
        emails_for_loop_df = emails_df.head(MAX_EMAILS_TO_PROCESS)
        display(Markdown(f"**Starting email processing loop for a maximum of {MAX_EMAILS_TO_PROCESS} emails.**"))
    else:
        display(Markdown(f"**Starting email processing loop for all {len(emails_df)} emails.**"))

    for _, current_email_row in emails_for_loop_df.iterrows():
        current_email_id = str(current_email_row['email_id'])
        current_email_subject = str(current_email_row.get('subject', '')) # Use .get for safety
        current_email_body = str(current_email_row.get('message_body', '')) # Ensure this matches your column name

        display(Markdown(f"\n---⚙️--- Processing Email ID: **{current_email_id}** ---⚙️---"))

        # Initialize per-email agent results storage to ensure they are always defined for the composer
        agent1_class_signals_results = None
        agent2_product_match_results = None
        agent3_order_proc_results = None # For order-specific processing steps
        agent4_inquiry_proc_results = None # For inquiry-specific processing steps
        final_composed_response_text = "Error: Response composition pipeline encountered a critical failure before completion."

        # --- Agent 1: Classification & Signal Extraction --- 
        agent1_class_signals_results = classification_signal_extraction_agent(current_email_id, current_email_subject, current_email_body)
        if not isinstance(agent1_class_signals_results, dict) or 'category' not in agent1_class_signals_results:
            error_detail_msg = f"Agent 1 (Classification) critically failed or returned invalid/incomplete data for {current_email_id}. Output: {str(agent1_class_signals_results)[:250]}"
            display(Markdown(f"**{error_detail_msg}**"))
            processing_errors_summary_list.append((current_email_id, "Agent 1 Critical Error", error_detail_msg))
            email_classification_output_list.append({'email ID': current_email_id, 'category': 'classification_pipeline_error'})
            # Attempt to compose a generic error response if classification fails badly
            final_composed_response_text = response_composer_agent(current_email_id, current_email_subject, current_email_body, agent1_class_signals_results or {}, {}, {}, {})
            # Decide if this error means it's an order or inquiry for sheet population purposes
            # Heuristic: if it mentions common order words, maybe put error in order_response, else inquiry_response
            if "order" in current_email_body.lower() or "buy" in current_email_body.lower():
                 order_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})
            else:
                 inquiry_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})
            time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS)
            continue # Skip to next email if classification critically fails
        
        email_classification_output_list.append({
            'email ID': current_email_id, 
            'category': agent1_class_signals_results.get('category', 'error_category_missing_post_validation')
        })
        current_email_main_category = agent1_class_signals_results.get('category')

        # --- Agent 2: Product Matcher --- 
        agent2_product_match_results = product_matcher_agent(current_email_id, agent1_class_signals_results, products_df, pinecone_index)
        if not isinstance(agent2_product_match_results, dict): 
            error_detail_msg = f"Agent 2 (Product Matcher) critically failed or returned non-dict data for {current_email_id}. Output: {str(agent2_product_match_results)[:250]}"
            display(Markdown(f"**{error_detail_msg}**"))
            processing_errors_summary_list.append((current_email_id, "Agent 2 Critical Error", error_detail_msg))
            agent2_product_match_results = {"error": error_detail_msg} # Ensure it's a dict for subsequent agents
            # Don't necessarily skip here, let composer try to make a response based on Agent 1 + this error

        # --- Conditional Processing based on Email Category --- 
        if current_email_main_category == 'order request':
            # --- Agent 3: Order Processing (only if it's an order request) --- 
            if inventory_df is not None:
                agent3_order_proc_results = order_processing_agent(current_email_id, agent2_product_match_results, inventory_df, products_df)
                if isinstance(agent3_order_proc_results, dict) and 'error' not in agent3_order_proc_results:
                    actual_inventory_updates_list = apply_inventory_updates_from_llm_decision(agent3_order_proc_results, inventory_df) # Modifies inventory_df in place
                    agent3_order_proc_results['actual_inventory_updates_applied_by_python'] = actual_inventory_updates_list # Store Python-verified updates
                    for item_status_dict in agent3_order_proc_results.get('processed_items', []):
                        order_status_output_list.append({
                            'email ID': current_email_id,
                            'product ID': str(item_status_dict.get('product_id','N/A')),
                            'quantity': item_status_dict.get('quantity'), # This should be originally requested quantity
                            'status': item_status_dict.get('status')
                        })
                else: # Agent 3 failed or returned an error structure
                    error_detail_msg = f"Agent 3 (Order Processing) failed or returned an error for {current_email_id}. Output: {str(agent3_order_proc_results)[:250]}"
                    display(Markdown(f"**{error_detail_msg}**"))
                    processing_errors_summary_list.append((current_email_id, "Agent 3 Error", error_detail_msg))
                    agent3_order_proc_results = {"error": error_detail_msg} if not isinstance(agent3_order_proc_results, dict) else agent3_order_proc_results
            else:
                no_inventory_err = "Agent 3 (Order Processing) skipped for {current_email_id} as inventory_df is not available."
                display(Markdown(f"**{no_inventory_err}**"))
                agent3_order_proc_results = {"error": no_inventory_err}

            # --- Check for and Run Agent 4 (Inquiry) if this order email ALSO has inquiry aspects --- 
            has_explicit_inquiries_in_classification = agent1_class_signals_results and agent1_class_signals_results.get('inquiries')
            has_inquiry_items_from_matcher = agent2_product_match_results and isinstance(agent2_product_match_results, dict) and agent2_product_match_results.get('inquiry_items')
            has_unfulfilled_items_needing_alternatives = agent3_order_proc_results and isinstance(agent3_order_proc_results, dict) and agent3_order_proc_results.get('unfulfilled_items_for_inquiry')
            
            if has_explicit_inquiries_in_classification or has_inquiry_items_from_matcher or has_unfulfilled_items_needing_alternatives:
                display(Markdown(f"Order email {current_email_id} also contains inquiry elements. Running Agent 4 (Inquiry Processing)."))
                agent4_inquiry_proc_results = inquiry_processing_agent(current_email_id, agent1_class_signals_results, agent2_product_match_results, agent3_order_proc_results, products_df, pinecone_index)
                if not isinstance(agent4_inquiry_proc_results, dict):
                    error_detail_msg = f"Agent 4 (Inquiry for Order) failed or returned invalid data for {current_email_id}. Output: {str(agent4_inquiry_proc_results)[:250]}"
                    display(Markdown(f"**{error_detail_msg}**"))
                    processing_errors_summary_list.append((current_email_id, "Agent 4 (Order-Inquiry) Error", error_detail_msg))
                    agent4_inquiry_proc_results = {"error": error_detail_msg} # Ensure dict for composer
            
            # --- Agent 5: Response Composer for Order (potentially with inquiry parts) --- 
            final_composed_response_text = response_composer_agent(current_email_id, current_email_subject, current_email_body, 
                                                            agent1_class_signals_results, agent2_product_match_results, 
                                                            agent3_order_proc_results, agent4_inquiry_proc_results) # agent4_inquiry_proc_results might be None or error dict
            order_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})

        elif current_email_main_category == 'product inquiry':
            # --- Agent 4: Inquiry Processing (for pure inquiries) --- 
            agent4_inquiry_proc_results = inquiry_processing_agent(current_email_id, agent1_class_signals_results, agent2_product_match_results, None, products_df, pinecone_index)
            if not isinstance(agent4_inquiry_proc_results, dict):
                error_detail_msg = f"Agent 4 (Inquiry) failed or returned invalid data for {current_email_id}. Output: {str(agent4_inquiry_proc_results)[:250]}"
                display(Markdown(f"**{error_detail_msg}**"))
                processing_errors_summary_list.append((current_email_id, "Agent 4 Error", error_detail_msg))
                agent4_inquiry_proc_results = {"error": error_detail_msg} # Ensure dict for composer
            
            # --- Agent 5: Response Composer for Inquiry --- 
            final_composed_response_text = response_composer_agent(current_email_id, current_email_subject, current_email_body, 
                                                            agent1_class_signals_results, agent2_product_match_results, 
                                                            None, agent4_inquiry_proc_results) # No order processing results for pure inquiry
            inquiry_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})
        
        else: # Category was not 'order request' or 'product inquiry' (e.g., due to classification error or unknown category)
            error_detail_msg = f"Email {current_email_id} has an unhandled category: '{current_email_main_category}'. Cannot determine specific processing path after Agent 1."
            display(Markdown(f"**{error_detail_msg}**"))
            processing_errors_summary_list.append((current_email_id, "Unhandled Category Error", error_detail_msg))
            # Attempt to compose a generic response acknowledging the issue
            final_composed_response_text = response_composer_agent(current_email_id, current_email_subject, current_email_body, 
                                                               agent1_class_signals_results, agent2_product_match_results, 
                                                               None, None) # Pass what we have to composer
            # Decide which sheet to put this generic/error response into. 
            # If original category from Agent 1 was an error, it won't fit neatly.
            # For now, if it wasn't order/inquiry, let's add to inquiry_response as a fallback for any response.
            inquiry_response_output_list.append({'email ID': current_email_id, 'response': f"Could not fully process email due to unhandled category '{current_email_main_category}'. Fallback response: {final_composed_response_text}"}) 

        display(Markdown(f"--- Finished processing Email ID: {current_email_id} ---"))
        time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS) # API Rate Limiting / Polite Delay
    
    display(Markdown(f"\n**Email processing loop finished. Processed {len(emails_for_loop_df)} emails.**"))

else: # CAN_PROCEED_PROCESSING was False
    display(Markdown("**Main email processing loop was not started due to critical pre-flight check failures.** Please review error messages above."))

# Display summary of any errors encountered during the loop
if processing_errors_summary_list:
    display(Markdown("### Processing Errors Encountered During Loop:"))
    for err_id, err_agent_stage, err_details_str in processing_errors_summary_list:
        display(Markdown(f"- **Email ID:** {err_id}, **Stage/Agent:** {err_agent_stage}, **Details:** {str(err_details_str)[:350]}..."))
else:
    if CAN_PROCEED_PROCESSING:
        display(Markdown("No critical errors logged during the email processing loop."))
```

# 6. Output Generation

This section compiles all the collected results from the processing loop into pandas DataFrames and then saves them to a single Excel spreadsheet (`hermes_assignment_output.xlsx`) with four separate sheets as required by the assignment: `email-classification`, `order-status`, `order-response`, and `inquiry-response`.

```python
display(Markdown(f"### Preparing to write all outputs to Excel file: `{OUTPUT_SPREADSHEET_NAME}`"))

# Create DataFrames from the output lists collected during the loop
df_email_classification_out = pd.DataFrame(email_classification_output_list)
df_order_status_out = pd.DataFrame(order_status_output_list)
df_order_response_out = pd.DataFrame(order_response_output_list)
df_inquiry_response_out = pd.DataFrame(inquiry_response_output_list)

# Define expected columns for each sheet to ensure headers are present even if DataFrames are empty
expected_columns_map = {
    "email-classification": ['email ID', 'category'],
    "order-status": ['email ID', 'product ID', 'quantity', 'status'],
    "order-response": ['email ID', 'response'],
    "inquiry-response": ['email ID', 'response']
}

try:
    with pd.ExcelWriter(OUTPUT_SPREADSHEET_NAME, engine='openpyxl') as writer:
        # Email Classification Sheet
        sheet_name_ec = 'email-classification'
        if not df_email_classification_out.empty:
            # Ensure only expected columns are written, in the correct order
            df_email_classification_out = df_email_classification_out.reindex(columns=expected_columns_map[sheet_name_ec])
            df_email_classification_out.to_excel(writer, sheet_name=sheet_name_ec, index=False)
        else:
            pd.DataFrame(columns=expected_columns_map[sheet_name_ec]).to_excel(writer, sheet_name=sheet_name_ec, index=False)
        display(Markdown(f"- `{sheet_name_ec}` sheet: {len(df_email_classification_out)} rows written."))

        # Order Status Sheet
        sheet_name_os = 'order-status'
        if not df_order_status_out.empty:
            df_order_status_out = df_order_status_out.reindex(columns=expected_columns_map[sheet_name_os])
            df_order_status_out.to_excel(writer, sheet_name=sheet_name_os, index=False)
        else:
            pd.DataFrame(columns=expected_columns_map[sheet_name_os]).to_excel(writer, sheet_name=sheet_name_os, index=False)
        display(Markdown(f"- `{sheet_name_os}` sheet: {len(df_order_status_out)} rows written."))

        # Order Response Sheet
        sheet_name_or = 'order-response'
        if not df_order_response_out.empty:
            df_order_response_out = df_order_response_out.reindex(columns=expected_columns_map[sheet_name_or])
            df_order_response_out.to_excel(writer, sheet_name=sheet_name_or, index=False)
        else:
            pd.DataFrame(columns=expected_columns_map[sheet_name_or]).to_excel(writer, sheet_name=sheet_name_or, index=False)
        display(Markdown(f"- `{sheet_name_or}` sheet: {len(df_order_response_out)} rows written."))

        # Inquiry Response Sheet
        sheet_name_ir = 'inquiry-response'
        if not df_inquiry_response_out.empty:
            df_inquiry_response_out = df_inquiry_response_out.reindex(columns=expected_columns_map[sheet_name_ir])
            df_inquiry_response_out.to_excel(writer, sheet_name=sheet_name_ir, index=False)
        else:
            pd.DataFrame(columns=expected_columns_map[sheet_name_ir]).to_excel(writer, sheet_name=sheet_name_ir, index=False)
        display(Markdown(f"- `{sheet_name_ir}` sheet: {len(df_inquiry_response_out)} rows written."))
            
    display(Markdown(f"\n**Successfully wrote all output sheets to Excel file: `{OUTPUT_SPREADSHEET_NAME}`**"))
    
    # Display final state of inventory for review
    display(Markdown("### Final Inventory State (First 5 rows after all processing):"))
    if inventory_df is not None:
        display(inventory_df.head())
    else:
        display(Markdown("(Inventory DataFrame (`inventory_df`) was not available or not modified during this run.)"))

except Exception as e:
    display(Markdown(f"**Error writing output to Excel file '{OUTPUT_SPREADSHEET_NAME}':** {e}"))
    display(Markdown("Please ensure 'openpyxl' is installed (`%pip install openpyxl`) and the file is not locked or in use."))

# Note on Google Sheets output (from original notebook):
# The original assignment notebook included code for creating a Google Spreadsheet directly using gspread.
# That functionality requires being in a Google Colab environment, authenticating the user, and having the gspread library.
# For broader compatibility (local Jupyter, other IDEs), this implementation defaults to saving to an Excel file.
# If Google Sheets output is strictly required and you are in Colab, the gspread code (commented out in a later cell) would need to be adapted and run.
```

# 7. Conclusion and Next Steps

This notebook has implemented an AI-powered email processing pipeline for Project Hermes. It classifies emails, processes orders (updating inventory), handles inquiries using RAG with a vector store, and generates personalized responses, adhering to the specified agent architecture and design documents.

**Key functionalities demonstrated:**
- LLM-based multi-agent system for sequential email processing.
- Dynamic prompt engineering, loading templates and including external guide content from markdown files.
- Integration of Pinecone vector store for RAG in product inquiries (including setup, data embedding/upsertion, and querying).
- Algorithmic product matching (fuzzy search) as a utility function.
- Stateful inventory management, with the inventory DataFrame being modified based on processed orders.
- Generation of four structured output sheets in a single Excel file as per assignment requirements.
- Modularity in agent design, allowing for individual testing and progressive improvements.
- Basic error handling and reporting throughout the pipeline.

**Potential Next Steps & Enhancements:**
- **Advanced Error Handling & Resilience**: Implement more sophisticated error recovery for LLM API calls (e.g., retries with slightly modified prompts for malformed JSON), and more robust parsing of LLM outputs, possibly with schema validation (e.g., using Pydantic).
- **Refined Product Matching**: Enhance the Product Matcher Agent. For instance, if the LLM identifies a highly descriptive phrase but fails to match it to the catalog snippet, this phrase could be used by Python code to perform a vector search, with results fed back to the LLM for a second-pass decision. More complex logic for disambiguating multiple potential matches (e.g., using confidence scores, stock levels, or even prompting the LLM to formulate a clarifying question for the user).
- **Context Window Management**: For very long email threads or extremely complex inquiries, implement more advanced techniques for managing the LLM's context window (e.g., summarization of earlier parts of the conversation, more selective inclusion of catalog data in prompts).
- **Scalability & Performance**: For high-volume email processing, explore asynchronous operations for LLM calls and batching of API requests where appropriate. Optimize Pinecone queries and embedding generation.
- **Comprehensive Evaluation Framework**: Develop a rigorous evaluation framework to measure the accuracy and effectiveness of each agent (e.g., classification accuracy, F1 scores for signal extraction) and the end-to-end pipeline (e.g., order fulfillment correctness, quality of generated responses, RAG relevance metrics).
- **Stateful Service Deployment**: If this were to be deployed as a continuously running service, a more robust database solution for inventory, processed email states, and conversation history would be necessary instead of in-memory pandas DataFrames.
- **Cost Optimization & Model Selection**: Experiment with smaller/cheaper LLM models for certain less complex tasks (e.g., some signal extraction, simple formatting) if performance is acceptable. Further optimize prompt token counts across all agents.
- **Fine-tuning Models**: For highly specialized fashion retail language, unique brand voice, or very specific types of customer inquiries, consider fine-tuning an LLM on proprietary (anonymized) data.
- **User Feedback Loop & Human-in-the-Loop**: Incorporate a mechanism to gather feedback on generated responses (e.g., from CS agents) to continually improve the system. For ambiguous cases, implement a human-in-the-loop escalation path.
- **Security and PII Handling**: For production, ensure robust PII (Personally Identifiable Information) detection and redaction before sending email content to LLMs, and handle API keys and sensitive data securely (e.g., using environment variables or secret management services).

```python
# This cell is retained from the original notebook to show the Google Colab gspread output example.
# It is NOT executed in the current local/Excel-based output flow of this Markdown version.

# from google.colab import auth
# import gspread
# from google.auth import default
# from gspread_dataframe import set_with_dataframe
# 
# # IMPORTANT: You need to authenticate the user to be able to create new worksheet in Colab
# # auth.authenticate_user()
# # creds, _ = default()
# # gc = gspread.authorize(creds)
# 
# # This code goes after creating google client (gc)
# # try:
# #     output_document_title = 'Solving Business Problems with AI - Hermes Output (YourNameHere)' # Personalize title
# #     output_document = gc.create(output_document_title)
# #     print(f"Created Google Sheet: {output_document_title}")
# # 
# #     # Define a helper function for writing DataFrames to sheets
# #     def write_df_to_gsheet(worksheet_title, df_to_write, expected_cols_list):
# #         if not df_to_write.empty:
# #             # Ensure correct columns and order
# #             df_final_for_sheet = df_to_write.reindex(columns=expected_cols_list)
# #             # Pad with empty rows if df is shorter than a minimum (e.g., 50), or adjust rows param
# #             num_rows = max(50, len(df_final_for_sheet) + 1)
# #             num_cols = max(len(expected_cols_list), df_final_for_sheet.shape[1] if not df_final_for_sheet.empty else len(expected_cols_list))
# #             sheet = output_document.add_worksheet(title=worksheet_title, rows=num_rows, cols=num_cols)
# #             sheet.update([expected_cols_list], 'A1') # Write headers
# #             set_with_dataframe(sheet, df_final_for_sheet, row=2, include_index=False, include_column_header=False)
# #         else:
# #             sheet = output_document.add_worksheet(title=worksheet_title, rows=50, cols=len(expected_cols_list))
# #             sheet.update([expected_cols_list], 'A1') # Write headers for empty sheet
# #         print(f"- Wrote '{worksheet_title}' to Google Sheet ({len(df_to_write)} data rows).")
# # 
# #     write_df_to_gsheet('email-classification', df_email_classification_out, expected_columns_map['email-classification'])
# #     write_df_to_gsheet('order-status', df_order_status_out, expected_columns_map['order-status'])
# #     write_df_to_gsheet('order-response', df_order_response_out, expected_columns_map['order-response'])
# #     write_df_to_gsheet('inquiry-response', df_inquiry_response_out, expected_columns_map['inquiry-response'])
# # 
# #     # Share the spreadsheet publicly
# #     output_document.share('', perm_type='anyone', role='reader')
# #     print(f"Google Sheet shared publicly (read-only).")
# # 
# #     # This is the solution output link, paste it into the submission form
# #     print(f"Shareable link: https://docs.google.com/spreadsheets/d/{output_document.id}")
# # except Exception as e_gspread:
# #    print(f"Error creating or updating Google Sheet: {e_gspread}")
# #    print("Ensure you have authenticated in Colab, gspread is installed, and the necessary Drive/Sheets API permissions are enabled.")
```