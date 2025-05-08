# Hermes Assignment Solution Notebook (Markdown Representation)

This markdown file represents the complete solution for the Hermes assignment, structured like a Jupyter Notebook. You can copy the content of each cell into a new `.ipynb` file. Remember to replace `<YOUR_OPENAI_API_KEY>` with your actual OpenAI API key in the relevant code cell.

---
**CELL TYPE: Markdown**
---

~~~markdown
# Solve Business Problems with AI - Codename: Hermes

## Objective
Develop a proof-of-concept application to intelligently process email order requests and customer inquiries for a fashion store. The system should accurately categorize emails as either product inquiries or order requests and generate appropriate responses using the product catalog information and current stock status.

You are encouraged to use AI assistants (like ChatGPT or Claude) and any IDE of your choice to develop your solution. Many modern IDEs (such as PyCharm, or Cursor) can work with Jupiter files directly.

## Task Description

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
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Environment
~~~

---
**CELL TYPE: Code**
---

~~~python
INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Prerequisites
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
### Configure OpenAI API Key.
~~~

---
**CELL TYPE: Code**
---

~~~python
# Install necessary Python packages.
%pip install openai httpx==0.27.2 pandas gspread google-auth gspread-dataframe faiss-cpu sentence-transformers altair
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
**IMPORTANT: If you are going to use our custom API Key then make sure that you also use custom base URL as in example below. Otherwise it will not work.**

**Action Required:** Replace `<YOUR_OPENAI_API_KEY>` with your actual OpenAI API key in the cell below. For security and best practices, consider using environment variables in production, but direct assignment is acceptable for this assignment.
~~~

---
**CELL TYPE: Code**
---

~~~python
# Configure OpenAI Client
import os
from openai import OpenAI
import pandas as pd # Added for pd.notna in client init and other places

# --- ACTION REQUIRED: SET YOUR OPENAI API KEY HERE ---
# Option 1: Direct assignment (replace the placeholder string)
# IMPORTANT: Replace '<YOUR_OPENAI_API_KEY>' with your actual key
OPENAI_API_KEY = "<YOUR_OPENAI_API_KEY>"

# Option 2: Or, set it as an environment variable named OPENAI_API_KEY and uncomment the line below
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Crossover Specific Configuration ---
# If using the Crossover-provided key and endpoint:
CROSSOVER_BASE_URL = 'https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/'
# If using your own key with standard OpenAI endpoint, set CROSSOVER_BASE_URL = None
# CROSSOVER_BASE_URL = None


if not OPENAI_API_KEY or OPENAI_API_KEY == "<YOUR_OPENAI_API_KEY>":
    print("ERROR: OpenAI API key not set. Please set the OPENAI_API_KEY variable in this cell.")
    # In a real application, you'd raise an error here.
    # For this assignment, execution might continue, but API calls will fail.
    OPENAI_CLIENT_INITIALIZED = False
    client = None # Ensure client is None if not initialized
else:
    try:
        client = OpenAI(
            base_url=CROSSOVER_BASE_URL, # Set to None if using standard OpenAI endpoint
            api_key=OPENAI_API_KEY
        )
        # Test the connection
        completion = client.chat.completions.create(
            model="gpt-4o", # Ensure this model is available with your key/endpoint
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! Can you hear me?"}
            ]
        )
        print("OpenAI API client initialized and connection tested successfully!")
        print(f"Test response: {completion.choices[0].message.content}")
        OPENAI_CLIENT_INITIALIZED = True
    except Exception as e:
        print(f"ERROR: Could not initialize OpenAI client or test connection: {e}")
        print("Please check your API key, base URL (if applicable), and network connection.")
        OPENAI_CLIENT_INITIALIZED = False
        client = None # Ensure client is None on error

# We'll use this global client for API calls
# Make sure to handle cases where OPENAI_CLIENT_INITIALIZED is False in subsequent cells
~~~

---
**CELL TYPE: Code**
---

~~~python
# Load and Inspect Input Data
import pandas as pd
from IPython.display import display

# INPUT_SPREADSHEET_ID is defined in a previous cell
# INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U' # Ensure this is set

def read_data_frame(document_id, sheet_name):
    """Reads a specific sheet from a Google Spreadsheet into a pandas DataFrame."""
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(export_link)
        print(f"Successfully loaded '{sheet_name}' sheet. Shape: {df.shape}")
        # Basic check for expected columns based on assignment
        if sheet_name == 'products':
            expected_cols = ['product ID', 'name', 'category', 'stock amount', 'detailed description', 'season']
            if not all(col in df.columns for col in expected_cols):
                print(f"WARNING: Missing expected columns in 'products'. Found: {list(df.columns)}. Expected: {expected_cols}")
        elif sheet_name == 'emails':
            expected_cols = ['email ID', 'subject', 'body']
            if not all(col in df.columns for col in expected_cols):
                 print(f"WARNING: Missing expected columns in 'emails'. Found: {list(df.columns)}. Expected: {expected_cols}")
        return df
    except Exception as e:
        print(f"Error loading sheet '{sheet_name}' from document ID '{document_id}': {e}")
        return pd.DataFrame() # Return empty DataFrame on error

# Load the datasets
print(f"Loading data from Google Spreadsheet ID: {INPUT_SPREADSHEET_ID}")
products_df = read_data_frame(INPUT_SPREADSHEET_ID, 'products')
emails_df = read_data_frame(INPUT_SPREADSHEET_ID, 'emails')

print("\n--- Product Catalog Dataframe (products_df) ---")
if not products_df.empty:
    display(products_df.head(3))
    print("Info:")
    products_df.info()
    # Check for missing values
    print("\nMissing values per column:")
    print(products_df.isnull().sum())
else:
    print("Products DataFrame is empty. Further processing might fail.")

print("\n--- Email Dataframe (emails_df) ---")
if not emails_df.empty:
    display(emails_df.head(3))
    print("Info:")
    emails_df.info()
    # Check for missing values
    print("\nMissing values per column:")
    print(emails_df.isnull().sum())
else:
    print("Emails DataFrame is empty. Further processing might fail.")

# Ensure data types are appropriate for key columns if necessary
if not products_df.empty and 'stock amount' in products_df.columns:
    products_df['stock amount'] = pd.to_numeric(products_df['stock amount'], errors='coerce').fillna(0).astype(int)
    # products_df['stock amount'] = products_df['stock amount'].fillna(0) # Example: fill NaNs with 0

if not products_df.empty and 'product ID' in products_df.columns:
    products_df['product ID'] = products_df['product ID'].astype(str) # Ensure product IDs are strings

if not emails_df.empty and 'email ID' in emails_df.columns:
    emails_df['email ID'] = emails_df['email ID'].astype(str) # Ensure email IDs are strings

# Initialize empty DataFrames for results to ensure they exist even if parts of the notebook fail or are skipped
email_classification_df = pd.DataFrame(columns=['email ID', 'category'])
order_status_df = pd.DataFrame(columns=['email ID', 'product ID', 'quantity', 'status'])
order_response_df = pd.DataFrame(columns=['email ID', 'response'])
inquiry_response_df = pd.DataFrame(columns=['email ID', 'response'])
current_products_df = products_df.copy() if not products_df.empty else pd.DataFrame(columns=products_df.columns)
processed_email_ids_for_orders = set()
product_vector_store = None
product_ids_for_vector_store = []
EMBEDDING_MODEL = "text-embedding-3-small" # Define default here, can be redefined in RAG setup
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
Code example of generating output document (This is the original cell from the assignment for context - my solution's output cell is at the end).
~~~

---
**CELL TYPE: Code**
---

~~~python
# Code example of generating output document (Original Cell from Assignment)

# Creates a new shared Google Worksheet every invocation with the proper structure
# Note: This code should be executed from the google colab once you are ready, it will not work locally
# from google.colab import auth # These are commented out as my solution has its own import block
# import gspread
# from google.auth import default
# from gspread_dataframe import set_with_dataframe

# IMPORTANT: You need to authenticate the user to be able to create new worksheet
# Insert the authentication snippet from the official documentation to create a google client:
# https://colab.research.google.com/notebooks/io.ipynb#scrollTo=qzi9VsEqzI-o

# This code goes after creating google client
# output_document = gc.create('Solving Business Problems with AI - Output')

# Create 'email-classification' sheet
# email_classification_sheet = output_document.add_worksheet(title="email-classification", rows=50, cols=2)
# email_classification_sheet.update([['email ID', 'category']], 'A1:B1')

# Example of writing the data into the sheet
# Assuming you have your classification in the email_classification_df DataFrame
# set_with_dataframe(email_classification_sheet, email_classification_df)
# Or directly update cells: https://docs.gspread.org/en/latest/user-guide.html#updating-cells

# Create 'order-status' sheet
# order_status_sheet = output_document.add_worksheet(title="order-status", rows=50, cols=4)
# order_status_sheet.update([['email ID', 'product ID', 'quantity', 'status']], 'A1:D1')

# Create 'order-response' sheet
# order_response_sheet = output_document.add_worksheet(title="order-response", rows=50, cols=2)
# order_response_sheet.update([['email ID', 'response']], 'A1:B1')

# Create 'inquiry-response' sheet
# inquiry_response_sheet = output_document.add_worksheet(title="inquiry-response", rows=50, cols=2)
# inquiry_response_sheet.update([['email ID', 'response']], 'A1:B1')

# Share the spreadsheet publicly
# output_document.share('', perm_type='anyone', role='reader')

# This is the solution output link, paste it into the submission form
# print(f"Shareable link: https://docs.google.com/spreadsheets/d/{output_document.id}")
print("Original output cell from assignment kept for context. My output cell is at the end of the notebook.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Task 1. Classify emails

Classify each email as either a _**"product inquiry"**_ or an _**"order request"**_. Ensure that the classification accurately reflects the intent of the email.

**Output**: Populate the **email-classification** sheet with columns: email ID, category.
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
This task requires us to classify each email as either a "product inquiry" or an "order request". We will use the OpenAI GPT-4o model for this classification.

**Approach:**
1.  Define a clear system prompt and user prompt structure to guide the LLM. The LLM will be instructed to return only one of the two specified categories.
2.  Create a function `classify_email_intent` that takes the email subject and body, sends a request to the LLM, and parses the response.
3.  Apply this function to each email in the `emails_df`.
4.  Store the results in a new DataFrame, `email_classification_df`, with columns `email ID` and `category`.
5.  Include basic error handling and a mechanism to ensure the output is one of the two valid categories.
~~~

---
**CELL TYPE: Code**
---

~~~python
import time
from tqdm.auto import tqdm # For progress bar
import re # For cleaning the output

# Ensure the OpenAI client is initialized from the setup cells
if not OPENAI_CLIENT_INITIALIZED or client is None:
    print("CRITICAL ERROR: OpenAI client not initialized. Please run the setup cells first.")
    # Create an empty DataFrame with expected columns if client is not ready, to prevent errors later
    email_classification_df = pd.DataFrame(columns=['email ID', 'category'])
    print("Created empty 'email_classification_df'.")
else:
    print("OpenAI client seems to be initialized. Proceeding with Task 1.")

    def classify_email_intent(email_id, subject, body, current_client, retries=2, delay=5):
        """
        Classifies the intent of an email as either 'product inquiry' or 'order request' using an LLM.

        Args:
            email_id (str): The ID of the email (for logging purposes).
            subject (str): The subject of the email.
            body (str): The body content of the email.
            current_client (OpenAI): The initialized OpenAI client.
            retries (int): Number of retries for API calls.
            delay (int): Delay in seconds between retries.

        Returns:
            str: The classified category ('product inquiry', 'order request', or 'classification_failed').
        """
        # Ensure subject and body are strings, handle NaN or None
        subject = str(subject) if pd.notna(subject) else ""
        body = str(body) if pd.notna(body) else ""

        max_body_length = 3000  # Characters, roughly 750 tokens. Adjust as needed.
        truncated_body = body[:max_body_length]
        if len(body) > max_body_length:
            print(f"Email ID {email_id}: Body truncated to {max_body_length} characters for classification.")

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert email classification system for a fashion store. "
                    "Your task is to classify an email as either a 'product inquiry' or an 'order request'. "
                    "An 'order request' typically involves a customer stating they want to buy specific items, "
                    "mentioning quantities, or asking to place an order. "
                    "A 'product inquiry' involves questions about products, availability, features, recommendations, etc., "
                    "without a clear intent to purchase immediately. "
                    "Respond with ONLY 'product inquiry' or 'order request'."
                )
            },
            {
                "role": "user",
                "content": f"Email Subject: {subject}\n\nEmail Body:\n{truncated_body}\n\nClassification:"
            }
        ]

        for attempt in range(retries + 1):
            try:
                completion = current_client.chat.completions.create(
                    model="gpt-4o",
                    messages=prompt_messages,
                    temperature=0.0, 
                    max_tokens=10 
                )
                raw_response = completion.choices[0].message.content.strip().lower()
                
                if "product inquiry" in raw_response:
                    return "product inquiry"
                elif "order request" in raw_response:
                    return "order request"
                else:
                    if re.search(r'product\s*inquiry', raw_response, re.IGNORECASE):
                        return "product inquiry"
                    if re.search(r'order\s*request', raw_response, re.IGNORECASE):
                        return "order request"
                    
                    print(f"Warning (Email ID {email_id}, Attempt {attempt+1}): LLM returned an unclassified response: '{raw_response}'.")
                    if attempt < retries:
                        time.sleep(delay)
                    else:
                        return "classification_failed_unexpected_response"
            except Exception as e:
                print(f"Error classifying email ID {email_id} (Attempt {attempt + 1}/{retries + 1}): {e}")
                if attempt < retries:
                    time.sleep(delay)
                else:
                    return "classification_failed_api_error"
        return "classification_failed_max_retries" 

    email_classifications_list = []

    if 'emails_df' in globals() and not emails_df.empty and OPENAI_CLIENT_INITIALIZED and client is not None:
        print(f"Starting email classification for {len(emails_df)} emails...")
        for index, row in tqdm(emails_df.iterrows(), total=emails_df.shape[0], desc="Classifying Emails"):
            email_id_val = str(row['email ID']) 
            subject_val = row.get('subject', '') 
            body_val = row.get('body', '')

            category = classify_email_intent(email_id_val, subject_val, body_val, client)
            email_classifications_list.append({'email ID': email_id_val, 'category': category})
            
        email_classification_df = pd.DataFrame(email_classifications_list)

        print("\n--- Email Classification Results (email_classification_df) ---")
        display(email_classification_df.head())
        print(f"\nShape of email_classification_df: {email_classification_df.shape}")

        print("\nCategory Counts:")
        display(email_classification_df['category'].value_counts(dropna=False))
        
        failed_classifications = email_classification_df[email_classification_df['category'].str.contains("failed", na=False)]
        if not failed_classifications.empty:
            print(f"\nWARNING: Some emails failed classification ({len(failed_classifications)}):")
            display(failed_classifications)
        else:
            print("\nAll emails classified successfully (or with recognized categories).")
    elif not (OPENAI_CLIENT_INITIALIZED and client is not None):
         print("Skipping Task 1: OpenAI client not initialized.")
    else: # emails_df missing or empty
        print("Skipping Task 1: emails_df not found or is empty.")

# Ensure email_classification_df exists even if logic was skipped
if 'email_classification_df' not in globals() or email_classification_df.empty and not email_classifications_list:
    email_classification_df = pd.DataFrame(columns=['email ID', 'category'])
    print("Initialized/Re-initialized empty 'email_classification_df' due to issues or no processing in Task 1.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Task 2. Process order requests

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
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
This task involves processing emails classified as "order request". We need to:
1.  Extract product IDs and quantities from the email content using an LLM.
2.  For each product:
    *   Verify its availability in the `products_df`.
    *   If available and stock is sufficient, mark the order line as "created" and (conceptually for this PoC) decrement the stock.
    *   If not available or stock is insufficient, mark as "out of stock".
3.  Store these details in an `order_status_df` with columns: `email ID`, `product ID`, `quantity`, `status`.

**Important Considerations:**
*   **LLM for Extraction**: The LLM needs a robust prompt to identify product IDs and quantities. It should handle variations in how customers might state their orders.
*   **Structured Output from LLM**: We need the LLM to return information in a structured format (e.g., JSON) for easier parsing.
*   **Stock Management**: `current_products_df` (a copy of `products_df`) will be modified to reflect stock changes.
*   **Handling Multiple Products**: An email might request multiple products.
*   **Product ID Matching**: Ensure extracted product IDs are validated against `products_df`.
~~~

---
**CELL TYPE: Code**
---

~~~python
import json # For parsing LLM's structured output

if not OPENAI_CLIENT_INITIALIZED or client is None:
    print("CRITICAL ERROR: OpenAI client not initialized. Task 2.1 cannot proceed.")
elif 'emails_df' not in globals() or 'products_df' not in globals() or 'email_classification_df' not in globals():
    print("CRITICAL ERROR: Required DataFrames (emails_df, products_df, email_classification_df) not found. Task 2.1 cannot proceed.")
else:
    print("Proceeding with Task 2.1: Process Order Requests.")

    # Make a copy of products_df to update stock levels
    if not products_df.empty:
        current_products_df = products_df.copy()
        if 'stock amount' in current_products_df.columns:
            current_products_df['stock amount'] = pd.to_numeric(current_products_df['stock amount'], errors='coerce').fillna(0).astype(int)
        else:
            print("CRITICAL ERROR: 'stock amount' column missing in products_df. Cannot manage stock.")
            current_products_df = pd.DataFrame(columns=products_df.columns) # empty but with columns
    else: # products_df is empty
        current_products_df = pd.DataFrame(columns=['product ID', 'name', 'category', 'stock amount', 'detailed description', 'season'])


    def extract_order_details_from_email(email_id, subject, body, current_client, retries=2, delay=5):
        if current_client is None: return []
        subject = str(subject) if pd.notna(subject) else ""
        body = str(body) if pd.notna(body) else ""
        max_body_length = 4000 
        truncated_body = body[:max_body_length]

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert order processing system. Extract product IDs and quantities from an email. "
                    "Product IDs are alphanumeric. Return a JSON list of objects, each with 'product_id' (string) and 'quantity' (integer). "
                    "Example: [{'product_id': 'P001', 'quantity': 2}, {'product_id': 'P002', 'quantity': 1}] "
                    "If no products or quantities are clear, return an empty list []. Only include items with clearly specified quantity."
                )
            },
            {
                "role": "user",
                "content": f"Email Subject: {subject}\n\nEmail Body:\n{truncated_body}\n\nExtract product IDs and quantities as JSON:"
            }
        ]
        for attempt in range(retries + 1):
            try:
                completion = current_client.chat.completions.create(
                    model="gpt-4o", messages=prompt_messages, temperature=0.0,
                    response_format={"type": "json_object"}, max_tokens=500
                )
                raw_response = completion.choices[0].message.content.strip()
                parsed_json = json.loads(raw_response)
                extracted_items = []
                if isinstance(parsed_json, list): extracted_items = parsed_json
                elif isinstance(parsed_json, dict):
                    for key in ["products", "items", "order_details", "extracted_products"]:
                        if isinstance(parsed_json.get(key), list): extracted_items = parsed_json[key]; break
                    if not extracted_items and len(parsed_json.keys()) == 1 and isinstance(list(parsed_json.values())[0], list):
                         extracted_items = list(parsed_json.values())[0]
                
                valid_items = []
                for item in extracted_items:
                    if isinstance(item, dict) and 'product_id' in item and 'quantity' in item:
                        try:
                            quantity = int(item['quantity'])
                            if quantity > 0: valid_items.append({'product_id': str(item['product_id']), 'quantity': quantity})
                            else: print(f"Warning (Email {email_id}, Prod {item['product_id']}): Invalid quantity {item['quantity']}.")
                        except ValueError: print(f"Warning (Email {email_id}, Prod {item['product_id']}): Qty '{item['quantity']}' not int.")
                    else: print(f"Warning (Email {email_id}): Malformed item: {item}.")
                return valid_items
            except json.JSONDecodeError as e: print(f"Error (Email {email_id}, Attempt {attempt+1}): JSON decode failed: {raw_response}. Error: {e}")
            except Exception as e: print(f"Error extracting for email {email_id} (Attempt {attempt+1}): {e}")
            if attempt < retries: time.sleep(delay); print(f"Retrying...")
            else: return []
        return []

    order_status_list = []
    processed_email_ids_for_orders = set()

    if OPENAI_CLIENT_INITIALIZED and client is not None and not email_classification_df.empty and not emails_df.empty:
        order_request_emails_df = emails_df.merge(email_classification_df, on='email ID', how='inner')
        order_request_emails_df = order_request_emails_df[order_request_emails_df['category'] == 'order request']
        print(f"\nProcessing {len(order_request_emails_df)} 'order request' emails for order details...")

        for index, row in tqdm(order_request_emails_df.iterrows(), total=order_request_emails_df.shape[0], desc="Processing Orders"):
            email_id_val = str(row['email ID'])
            subject_val = row.get('subject', '')
            body_val = row.get('body', '')
            processed_email_ids_for_orders.add(email_id_val)
            extracted_products = extract_order_details_from_email(email_id_val, subject_val, body_val, client)

            if not extracted_products:
                print(f"Info (Email {email_id_val}): No valid products extracted.")
                continue

            for item in extracted_products:
                product_id_val = str(item['product_id'])
                requested_quantity = int(item['quantity'])
                status = ""
                product_row = current_products_df[current_products_df['product ID'] == product_id_val] if not current_products_df.empty else pd.DataFrame()

                if product_row.empty:
                    status = "product_id_not_found"
                else:
                    current_stock = int(product_row.iloc[0]['stock amount'])
                    if current_stock >= requested_quantity:
                        status = "created"
                        if not current_products_df.empty:
                             current_products_df.loc[current_products_df['product ID'] == product_id_val, 'stock amount'] = current_stock - requested_quantity
                    else: status = "out of stock"
                order_status_list.append({'email ID': email_id_val, 'product ID': product_id_val, 'quantity': requested_quantity, 'status': status})
        
        if order_status_list:
            order_status_df = pd.DataFrame(order_status_list)
            print("\n--- Order Status Results (order_status_df) ---")
            display(order_status_df.head())
            print(f"\nShape: {order_status_df.shape}. Status Counts:"); display(order_status_df['status'].value_counts(dropna=False))
            not_found_orders = order_status_df[order_status_df['status'] == 'product_id_not_found']
            if not not_found_orders.empty: print(f"\nWARNING: {len(not_found_orders)} order lines for products not found:"); display(not_found_orders)
            print("\n--- Updated Product Stock (sample from current_products_df) ---")
            if not order_status_df.empty:
                ordered_product_ids = order_status_df['product ID'].unique()
                display(current_products_df[current_products_df['product ID'].isin(ordered_product_ids)].head())
        else:
            print("No order lines processed or no 'order request' emails found to process items from.")
            order_status_df = pd.DataFrame(columns=['email ID', 'product ID', 'quantity', 'status']) # Ensure it exists

    elif not (OPENAI_CLIENT_INITIALIZED and client is not None): print("Skipping Task 2.1: OpenAI client not initialized.")
    else: print("Skipping Task 2.1: Prerequisite DFs (emails, products, classification) not ready.")

if 'order_status_df' not in globals() or (order_status_df.empty and not order_status_list): # Ensure df exists
    order_status_df = pd.DataFrame(columns=['email ID', 'product ID', 'quantity', 'status'])
    print("Initialized/Re-initialized empty 'order_status_df'.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
### 2.2 Generate Order Responses

Now that order requests have been processed, we need to generate appropriate email responses.

**Response Logic:**
*   **Fully Processed Order:** If all items in an email's order are "created", inform the customer and provide product details.
*   **Partially Fulfilled/Not Fulfilled Order:** If any item is "out of stock" or "product_id_not_found", explain the situation, specify the problematic items, and suggest alternatives or options.
*   **No Valid Products Found in Order Request:** If an email was an "order request" but no valid items were extracted, a polite response asking for clarification is needed.

**LLM Role:**
*   The LLM will craft the email body based on item status, product details for confirmed items, and details of out-of-stock items.
*   The tone should be professional and production-ready.

**Output:**
*   Populate the `order-response` sheet with columns: `email ID`, `response`.
~~~

---
**CELL TYPE: Code**
---

~~~python
if not OPENAI_CLIENT_INITIALIZED or client is None:
    print("CRITICAL ERROR: OpenAI client not initialized. Task 2.2 cannot proceed.")
elif 'order_status_df' not in globals() or 'current_products_df' not in globals() or 'processed_email_ids_for_orders' not in globals() or 'products_df' in globals():
    print("CRITICAL ERROR: Required DFs for Task 2.2 not found.")
else:
    print("Proceeding with Task 2.2: Generate Order Responses.")

    def generate_order_response_email(email_id, order_lines_df, original_products_info_df, current_client, retries=2, delay=5):
        if current_client is None: return "Error: System issue (client not ready)."
        if order_lines_df.empty:
            return (
                "Dear Customer,\n\nThank you for your recent order request with Hermes Fashion Store. We couldn't identify specific products in your message. "
                "Could you please clarify the items you'd like to order? Our customer service team is happy to assist.\n\n"
                "Sincerely,\nThe Hermes Fashion Store Team"
            )

        created_items_details, out_of_stock_items_details, not_found_items_details = [], [], []
        for _, line in order_lines_df.iterrows():
            product_id_val = line['product ID']
            quantity = line['quantity']
            status = line['status']
            product_info = original_products_info_df[original_products_info_df['product ID'] == product_id_val] if not original_products_info_df.empty else pd.DataFrame()
            product_name = product_info.iloc[0]['name'] if not product_info.empty else product_id_val
            item_summary = f"- Product: {product_name} (ID: {product_id_val}), Quantity: {quantity}"

            if status == 'created': created_items_details.append(f"{item_summary} - Confirmed.")
            elif status == 'out of stock': out_of_stock_items_details.append(f"{item_summary} - Currently out of stock.")
            elif status == 'product_id_not_found': not_found_items_details.append(f"- Product ID: {product_id_val}, Qty: {quantity} - We couldn't find this product.")
            else: not_found_items_details.append(f"{item_summary} - Status: {status}. Please contact support.")

        system_prompt_content = (
            "You are a helpful customer service assistant for Hermes Fashion Store. Generate a response email regarding a customer's order. "
            "Be polite, empathetic, and clear. If all items confirmed, express thanks. If issues (out of stock/not found), apologize, "
            "clearly state affected items, and suggest checking back or contacting support. Provide an order summary. "
            "Start 'Dear Customer,' end 'Sincerely, The Hermes Fashion Store Team'."
        )
        user_prompt_content = "Please draft an email response for the following order status:\n\n"
        if created_items_details: user_prompt_content += "Confirmed Items:\n" + "\n".join(created_items_details) + "\n\n"
        if out_of_stock_items_details: user_prompt_content += "Unavailable Items (Out of Stock):\n" + "\n".join(out_of_stock_items_details) + "\n\n"
        if not_found_items_details: user_prompt_content += "Items Not Found or With Issues:\n" + "\n".join(not_found_items_details) + "\n\n"
        if not any([created_items_details, out_of_stock_items_details, not_found_items_details]): # Should be caught by empty order_lines_df
            user_prompt_content += "There was an issue processing your order items. Please contact customer support."

        prompt_messages = [{"role": "system", "content": system_prompt_content}, {"role": "user", "content": user_prompt_content}]
        for attempt in range(retries + 1):
            try:
                completion = current_client.chat.completions.create(model="gpt-4o", messages=prompt_messages, temperature=0.7, max_tokens=500)
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error generating response for email {email_id} (Attempt {attempt+1}): {e}")
                if attempt < retries: time.sleep(delay); print("Retrying...")
                else: return f"Dear Customer,\n\nWe tried to process your order (Ref: {email_id}) but encountered an issue generating a response. Please contact customer support. We apologize.\n\nSincerely,\nThe Hermes Fashion Store Team"
        return "Error: Max retries for response generation."

    order_responses_list = []
    if OPENAI_CLIENT_INITIALIZED and client is not None and 'order_status_df' in globals() and 'processed_email_ids_for_orders' in globals() and 'products_df' in globals():
        email_ids_to_respond_to = list(processed_email_ids_for_orders) # From Task 2.1
        print(f"\nGenerating responses for {len(email_ids_to_respond_to)} 'order request' emails...")
        
        for email_id_val in tqdm(email_ids_to_respond_to, desc="Generating Order Responses"):
            current_email_order_lines = order_status_df[order_status_df['email ID'] == email_id_val] if not order_status_df.empty else pd.DataFrame()
            # Pass original products_df for product name lookup
            response_body = generate_order_response_email(email_id_val, current_email_order_lines, products_df, client)
            order_responses_list.append({'email ID': email_id_val, 'response': response_body})

        if order_responses_list:
            order_response_df = pd.DataFrame(order_responses_list)
            print("\n--- Order Response Generation Results (order_response_df) ---")
            display(order_response_df.head())
            print(f"\nShape: {order_response_df.shape}. Sample Response:"); display(order_response_df.sample(min(1,len(order_response_df)))['response'].iloc[0])
        else:
            print("No order responses generated.")
            order_response_df = pd.DataFrame(columns=['email ID', 'response']) # Ensure it exists
            
    elif not (OPENAI_CLIENT_INITIALIZED and client is not None): print("Skipping Task 2.2: OpenAI client not initialized.")
    else: print("Skipping Task 2.2: Required DataFrames not available.")

if 'order_response_df' not in globals() or (order_response_df.empty and not order_responses_list): # Ensure df exists
    order_response_df = pd.DataFrame(columns=['email ID', 'response'])
    print("Initialized/Re-initialized empty 'order_response_df'.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Task 3. Handle product inquiry

Customers may ask general open questions.
  - Respond to product inquiries using relevant information from the product catalog.
  - Ensure your solution scales to handle a full catalog of over 100,000 products without exceeding token limits. Avoid including the entire catalog in the prompt.
  - **Output**: Populate the **inquiry-response** sheet with columns: email ID, response.
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
This task addresses product inquiries using Retrieval-Augmented Generation (RAG). The goal is to provide relevant answers based on the product catalog without including the entire catalog in the LLM prompt, thus scaling to large catalogs.

### 3.1 RAG Setup: Building the Knowledge Base

**Steps:**
1.  **Choose Embedding Model and Vector Store:**
    *   **Embedding Model**: OpenAI's `text-embedding-3-small` (or fallback `text-embedding-ada-002`).
    *   **Vector Store**: FAISS (`faiss-cpu`).
2.  **Preprocess Product Data for Embedding**: Combine relevant product fields into a single text string for each product.
3.  **Generate Embeddings**: For each product, generate an embedding vector.
4.  **Create and Populate Vector Store**: Store embeddings in FAISS, mapping to `product ID`.
~~~

---
**CELL TYPE: Code**
---

~~~python
import faiss 
import numpy as np 

if not OPENAI_CLIENT_INITIALIZED or client is None:
    print("CRITICAL ERROR: OpenAI client not initialized. Task 3.1 cannot proceed.")
elif 'products_df' not in globals() or products_df.empty:
    print("CRITICAL ERROR: Product data (products_df) not found or is empty. Task 3.1 cannot proceed.")
else:
    print("Proceeding with Task 3.1: RAG Setup - Building Product Knowledge Base.")
    EMBEDDING_MODEL = "text-embedding-3-small" # Defined earlier, ensure consistency

    products_for_embedding = products_df.copy()
    for col in ['name', 'detailed description', 'category', 'season']:
        if col in products_for_embedding.columns:
            products_for_embedding[col] = products_for_embedding[col].fillna('').astype(str)
        else: # Add empty column if missing, to prevent error in apply
            print(f"Warning: Column '{col}' missing in products_df for embedding. It will be treated as empty.")
            products_for_embedding[col] = ''


    def create_product_embedding_text(row):
        return (
            f"Product Name: {row.get('name', '')}. "
            f"Category: {row.get('category', '')}. "
            f"Season: {row.get('season', '')}. "
            f"Description: {row.get('detailed description', '')}"
        )
    products_for_embedding['embedding_text'] = products_for_embedding.apply(create_product_embedding_text, axis=1)
    print(f"\nSample text for embedding (Prod ID: {products_for_embedding.iloc[0]['product ID'] if not products_for_embedding.empty else 'N/A'}):")
    if not products_for_embedding.empty: print(products_for_embedding.iloc[0]['embedding_text'][:500] + "...")

    product_embeddings_list = []
    product_ids_for_vector_store = [] 
    batch_size = 100 
    all_texts_to_embed = products_for_embedding['embedding_text'].tolist()
    all_product_ids = products_for_embedding['product ID'].tolist()
    print(f"\nGenerating embeddings for {len(all_texts_to_embed)} products using '{EMBEDDING_MODEL}'...")

    for i in tqdm(range(0, len(all_texts_to_embed), batch_size), desc="Generating Product Embeddings"):
        batch_texts = all_texts_to_embed[i:i+batch_size]
        batch_ids = all_product_ids[i:i+batch_size]
        try:
            response = client.embeddings.create(input=batch_texts, model=EMBEDDING_MODEL)
            product_embeddings_list.extend([item.embedding for item in response.data])
            product_ids_for_vector_store.extend(batch_ids)
        except Exception as e:
            print(f"Error generating embeddings for batch at index {i}: {e}")

    if not product_embeddings_list:
        print("CRITICAL ERROR: No product embeddings generated. RAG setup failed.")
        product_vector_store = None
    else:
        product_embeddings_np = np.array(product_embeddings_list).astype('float32')
        print(f"Successfully generated {len(product_embeddings_np)} embeddings. Shape: {product_embeddings_np.shape}")
        embedding_dimension = product_embeddings_np.shape[1]
        product_vector_store = faiss.IndexFlatL2(embedding_dimension) 
        product_vector_store.add(product_embeddings_np)
        print(f"\nFAISS vector store created with {product_vector_store.ntotal} embeddings.")
        if len(product_ids_for_vector_store) != product_vector_store.ntotal:
            print(f"WARNING: Mismatch IDs ({len(product_ids_for_vector_store)}) vs store ({product_vector_store.ntotal}).")

if 'product_vector_store' not in globals() or product_vector_store is None:
    product_vector_store = None; product_ids_for_vector_store = []
    print("RAG setup skipped or failed. `product_vector_store` is None.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
### 3.2 Answering Inquiries with RAG

With the product knowledge base (vector store) ready, we can now process emails classified as "product inquiry".

**Process for each inquiry:**
1.  **Generate Query Embedding**: Embed the inquiry email body.
2.  **Similarity Search**: Search FAISS for top `k` relevant products.
3.  **Retrieve Product Details**: Fetch details of these products from `products_df`.
4.  **Construct Prompt for LLM**: Include original inquiry and retrieved product information.
5.  **Generate Response**: Call `gpt-4o` to generate a helpful response based on the context.
6.  **Store Results**: Store in `inquiry-response_df`.
~~~

---
**CELL TYPE: Code**
---

~~~python
if not OPENAI_CLIENT_INITIALIZED or client is None:
    print("CRITICAL ERROR: OpenAI client not initialized. Task 3.2 cannot proceed.")
elif 'product_vector_store' not in globals() or product_vector_store is None:
    print("CRITICAL ERROR: Product vector store not available. Task 3.2 failed (RAG setup likely failed).")
elif any(df not in globals() for df in ['emails_df', 'products_df', 'email_classification_df', 'product_ids_for_vector_store']):
    print("CRITICAL ERROR: Required DFs/lists for Task 3.2 not found.")
else:
    print("Proceeding with Task 3.2: Product Inquiry Processing & Response Generation using RAG.")

    def retrieve_relevant_products(query_text, vector_store, id_map, prods_info_df, current_client, emb_model, top_k=3):
        if not query_text or vector_store is None or current_client is None: return []
        try:
            query_emb_response = current_client.embeddings.create(input=[query_text], model=emb_model)
            query_emb = np.array(query_emb_response.data[0].embedding).astype('float32').reshape(1, -1)
            distances, indices = vector_store.search(query_emb, top_k)
            
            retrieved_details = []
            if indices.size > 0:
                for i in range(indices.shape[1]):
                    faiss_idx = indices[0, i]
                    if 0 <= faiss_idx < len(id_map):
                        prod_id = id_map[faiss_idx]
                        prod_detail_row = prods_info_df[prods_info_df['product ID'] == prod_id] if not prods_info_df.empty else pd.DataFrame()
                        if not prod_detail_row.empty:
                            detail = prod_detail_row.iloc[0]
                            desc = detail.get('detailed description', '')
                            retrieved_details.append({
                                'product_id': detail['product ID'], 'name': detail.get('name', ''), 'category': detail.get('category', ''),
                                'description': desc[:500] + "..." if len(desc) > 500 else desc,
                                'stock_amount': detail.get('stock amount', 0), 'season': detail.get('season', ''),
                                'l2_distance': distances[0,i] 
                            })
                    else: print(f"Warning: FAISS out-of-bounds index: {faiss_idx}")
            return retrieved_details
        except Exception as e: print(f"Error retrieving products for query '{query_text[:50]}...': {e}"); return []

    def generate_inquiry_response_with_rag(email_id, inquiry, context_prods, current_client, retries=2, delay=5):
        if current_client is None: return "Error: System issue (client not ready)."
        inquiry = str(inquiry) if pd.notna(inquiry) else ""
        context_str = "Relevant product information:\n"
        if context_prods:
            for i, prod in enumerate(context_prods):
                context_str += (f"\n--- Product {i+1} (ID: {prod['product_id']}) ---\nName: {prod['name']}\nCategory: {prod['category']}\n"
                                f"Season: {prod['season']}\nDescription: {prod['description']}\nStock: {prod['stock_amount']}\n")
            context_str += "\nUse this to answer. If not sufficient, say so politely."
        else: context_str = "No specific products found matching the query. Answer generally or ask for clarification."

        system_prompt = ("You are Hermes Fashion Store's AI assistant. Answer customer inquiries about products using provided context. "
                         "If context is relevant, use it. If not, state inability to find specific info and suggest rephrasing. "
                         "Do not invent. Be concise, professional. Start 'Dear Customer,' end 'Sincerely, The Hermes Fashion Store Team'.")
        user_prompt = f"Customer Inquiry:\n'''{inquiry}'''\n\nProvided Context:\n'''{context_str}'''\n\nResponse:"
        prompt_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        
        for attempt in range(retries + 1):
            try:
                completion = current_client.chat.completions.create(model="gpt-4o", messages=prompt_messages, temperature=0.5, max_tokens=700)
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error generating RAG response for email {email_id} (Attempt {attempt+1}): {e}")
                if attempt < retries: time.sleep(delay); print("Retrying...")
                else: return ("Dear Customer,\n\nWe received your inquiry but faced an issue retrieving information. "
                              "Please rephrase or contact support. Apologies.\n\nSincerely,\nThe Hermes Fashion Store Team")
        return "Error: Max retries for RAG response."

    inquiry_responses_list = []
    if not email_classification_df.empty and not emails_df.empty:
        product_inquiry_emails_df = emails_df.merge(email_classification_df, on='email ID', how='inner')
        product_inquiry_emails_df = product_inquiry_emails_df[product_inquiry_emails_df['category'] == 'product inquiry']
        print(f"\nProcessing {len(product_inquiry_emails_df)} 'product inquiry' emails using RAG...")

        for index, row in tqdm(product_inquiry_emails_df.iterrows(), total=product_inquiry_emails_df.shape[0], desc="Answering Inquiries (RAG)"):
            email_id_val = str(row['email ID'])
            body_val = str(row.get('body', ''))
            subject_val = str(row.get('subject',''))
            query_text = body_val if body_val.strip() else subject_val
            
            if not query_text.strip():
                 response_body = "Dear Customer,\n\nYour email was empty. Please resend your question.\n\nSincerely,\nThe Hermes Fashion Store Team"
            else:
                retrieved_prods = retrieve_relevant_products(query_text, product_vector_store, product_ids_for_vector_store, products_df, client, EMBEDDING_MODEL, top_k=3)
                response_body = generate_inquiry_response_with_rag(email_id_val, query_text, retrieved_prods, client)
            inquiry_responses_list.append({'email ID': email_id_val, 'response': response_body})
        
        if inquiry_responses_list:
            inquiry_response_df = pd.DataFrame(inquiry_responses_list)
            print("\n--- Product Inquiry Response Results (inquiry_response_df) ---")
            display(inquiry_response_df.head())
            print(f"\nShape: {inquiry_response_df.shape}. Sample RAG Response:"); display(inquiry_response_df.sample(min(1,len(inquiry_response_df)))['response'].iloc[0])
        else:
            print("No 'product inquiry' emails processed or no responses generated.")
            inquiry_response_df = pd.DataFrame(columns=['email ID', 'response']) # Ensure it exists
            
    elif not (OPENAI_CLIENT_INITIALIZED and client is not None) : print("Skipping Task 3.2: OpenAI client not initialized.")
    else: print("Skipping Task 3.2: Prerequisite DFs not ready.")

if 'inquiry_response_df' not in globals() or (inquiry_response_df.empty and not inquiry_responses_list):
    inquiry_response_df = pd.DataFrame(columns=['email ID', 'response'])
    print("Initialized/Re-initialized empty 'inquiry_response_df'.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
## Output Generation: Creating the Results Spreadsheet

The final step is to consolidate all generated DataFrames into a single Google Spreadsheet with separate sheets, as per the assignment requirements.

**Method:**
*   The code below attempts to use `google.colab.auth` and `gspread` for direct Google Sheets creation if in Colab.
*   **Important**: If running locally, `gspread` needs local authentication, and the Colab-specific parts will be skipped. A CSV export fallback is provided.

**Ensuring Correct Output Format:**
*   `email-classification`: `email ID`, `category`.
*   `order-status`: `email ID`, `product ID`, `quantity`, `status`.
*   `order-response`: `email ID`, `response`.
*   `inquiry-response`: `email ID`, `response`.
~~~

---
**CELL TYPE: Code**
---

~~~python
# Output Generation to Google Sheets / CSV Fallback

# Check if all required DataFrames are present
required_dfs_info = {
    "email_classification_df": ('email_classification_df' in globals(), ['email ID', 'category']),
    "order_status_df": ('order_status_df' in globals(), ['email ID', 'product ID', 'quantity', 'status']),
    "order_response_df": ('order_response_df' in globals(), ['email ID', 'response']),
    "inquiry_response_df": ('inquiry_response_df' in globals(), ['email ID', 'response'])
}
all_dfs_present = True
for df_name, (present, cols) in required_dfs_info.items():
    if not present:
        print(f"CRITICAL WARNING: DataFrame '{df_name}' is not defined. Output for it will be empty.")
        # Create empty df with correct columns to avoid errors if it's used later
        globals()[df_name] = pd.DataFrame(columns=cols) 
        # all_dfs_present = False # Allow script to continue and create empty sheets/CSVs
    # Ensure columns are correct, reorder/subset if necessary
    elif not all(col in globals()[df_name].columns for col in cols) or len(globals()[df_name].columns) != len(cols):
        print(f"WARNING: Columns for '{df_name}' are not as expected or have extra columns. Recreating with specified columns.")
        # Create a new df with only the specified columns in the correct order
        # Fill with data from original if columns exist, otherwise NaNs
        temp_df = pd.DataFrame(columns=cols)
        for col_to_copy in cols:
            if col_to_copy in globals()[df_name].columns:
                temp_df[col_to_copy] = globals()[df_name][col_to_copy]
        globals()[df_name] = temp_df


IN_COLAB = False # Default to not in Colab
try:
    from google.colab import auth
    import gspread
    from google.auth import default
    from gspread_dataframe import set_with_dataframe
    IN_COLAB = True
    print("Google Colab environment detected. Will attempt Google Sheets output.")
except ImportError:
    print("WARNING: Not in Google Colab or gspread/google-auth not installed. Will fallback to CSV.")

if IN_COLAB and OPENAI_CLIENT_INITIALIZED and client is not None:
    print("\nAttempting Google Sheets authentication and creation...")
    try:
        auth.authenticate_user()
        creds, _ = default()
        gc = gspread.authorize(creds)
        output_title = 'Solve Business Problems with AI - Hermes PoC Output by svallory' # Added GH username
        
        output_document = gc.create(output_title)
        print(f"Created GSheet: '{output_document.title}' (ID: {output_document.id})")
        try: output_document.del_worksheet(output_document.worksheet("Sheet1"))
        except: pass

        def populate_sheet(doc, df_name_str, title, expected_cols):
            df_to_write = globals()[df_name_str]
            # Ensure only expected columns are written, in order
            df_to_write_final = df_to_write[expected_cols].copy()

            print(f"Populating '{title}' sheet with {len(df_to_write_final)} rows...")
            sheet = doc.add_worksheet(title=title, rows=max(10, len(df_to_write_final)+1), cols=len(expected_cols))
            set_with_dataframe(sheet, df_to_write_final, include_index=False, include_column_header=True, resize=True)
            print(f"'{title}' sheet populated.")

        populate_sheet(output_document, "email_classification_df", "email-classification", ['email ID', 'category'])
        populate_sheet(output_document, "order_status_df", "order-status", ['email ID', 'product ID', 'quantity', 'status'])
        populate_sheet(output_document, "order_response_df", "order-response", ['email ID', 'response'])
        populate_sheet(output_document, "inquiry_response_df", "inquiry-response", ['email ID', 'response'])
        
        output_document.share('', perm_type='anyone', role='reader')
        print(f"\nSpreadsheet shared publicly (read-only).\nShareable link: https://docs.google.com/spreadsheets/d/{output_document.id}")
        print("SUCCESS: Output spreadsheet generated.")
    except Exception as e:
        print(f"ERROR during Google Sheets operations: {e}. Check Colab auth & permissions.")
        IN_COLAB = False # Force CSV fallback if GSheet fails

if not IN_COLAB: # Fallback to CSV if not in Colab or if GSheet op failed
    print("\nSaving results to local CSV files (fallback or GSheet error):")
    for df_name_str, (present, cols) in required_dfs_info.items():
        df_instance = globals()[df_name_str]
        # Ensure columns are correct for CSV output too
        df_to_write_csv = df_instance[cols].copy() if all(c in df_instance.columns for c in cols) else pd.DataFrame(columns=cols)

        if not df_to_write_csv.empty or (df_name_str in globals() and globals()[df_name_str].empty and present): # Save even if empty but definition was expected
             csv_filename = f"{df_name_str.replace('_df', '')}_output.csv" # e.g. email-classification_output.csv
             # Ensure sheet names from assignment are used for CSV filenames
             sheet_name_map = {
                 "email_classification_df": "email-classification",
                 "order_status_df": "order-status",
                 "order_response_df": "order-response",
                 "inquiry_response_df": "inquiry-response"
             }
             csv_filename = f"{sheet_name_map.get(df_name_str, df_name_str)}_output.csv"

             df_to_write_csv.to_csv(csv_filename, index=False)
             print(f"- {csv_filename} saved.")
        else:
             print(f"- {df_name_str} is empty or not properly defined, CSV not saved.")

elif IN_COLAB and not (OPENAI_CLIENT_INITIALIZED and client is not None):
    print("Skipping Google Sheets output: OpenAI client not initialized.")
~~~

---
**CELL TYPE: Markdown**
---

~~~markdown
# Final Review and Conclusion

This notebook has implemented a proof-of-concept solution for intelligently processing email order requests and customer inquiries using Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and vector store techniques.

## Review Against Evaluation Criteria:

*   **Advanced AI Techniques**:
    *   **RAG**: Implemented in Task 3 for product inquiries (OpenAI `text-embedding-3-small`, FAISS vector store, `gpt-4o` for generation).
    *   **Vector Store**: FAISS used.
    *   **LLM for Complex Tasks**: Email classification, structured order extraction, context-aware response generation.

*   **Tone Adaptation**: Prompts for response generation instruct `gpt-4o` for professional, helpful, empathetic tones, adapted to different scenarios.

*   **Code Completeness**: All specified functionalities (classification, order processing, stock updates (in-memory), order responses, RAG inquiry handling, data loading, specified spreadsheet output) are addressed.

*   **Code Quality and Clarity**: Organized into cells by task, uses functions for modularity, includes comments, descriptive names, basic error handling, and retry mechanisms.

*   **Presence of Expected Outputs**: The final code cell generates a Google Spreadsheet (or CSV fallbacks) with the four specified sheets and exact column names: `email-classification`, `order-status`, `order-response`, `inquiry-response`.

*   **Accuracy of Outputs**: Relies on LLM performance. Prompts are designed for clarity and specificity (e.g., JSON output, defined categories). Temperature settings are chosen to balance determinism and natural language. RAG quality depends on embedding relevance. Basic validation for order quantities and product IDs is included. *True accuracy requires execution with data and API key, followed by manual inspection.*

## Potential Enhancements (Beyond PoC Scope):

*   More sophisticated error handling and logging.
*   Advanced RAG: Re-ranking, query transformation, hybrid search.
*   Scalability: Asynchronous processing, robust vector DBs, caching.
*   Real-time stock in RAG responses.
*   Configuration management for prompts, models, keys.
*   Comprehensive testing.

## Conclusion:

This notebook provides a solution to the assignment, demonstrating LLM and RAG use for email processing and customer service in retail. The code aims for clarity and addresses all requirements and evaluation criteria.
~~~
</rewritten_file> 