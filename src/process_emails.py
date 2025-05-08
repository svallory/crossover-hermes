""" {cell}
## Main Processing Script

This script orchestrates the entire Hermes email processing pipeline. It demonstrates
how to:
1. Load necessary data (product catalog and sample emails).
2. Initialize the configuration, vector store, and workflow.
3. Process a batch of emails using the Hermes workflow.
4. Collect and format the results.
5. Trigger the output process (writing to Google Sheets).

This script serves as the main entry point for running the Hermes system.
"""
import pandas as pd
import asyncio
from typing import List, Dict, Any, Optional

# Import necessary components from our solution
from .config import HermesConfig
from .state import HermesState
from .vectorstore import (
    create_product_vectorstore_batched, 
    load_product_vectorstore
)
from .pipeline import create_hermes_workflow
from .output import format_and_write_final_outputs

async def process_emails_batch(emails_data: List[Dict[str, str]], 
                             product_catalog_df: pd.DataFrame, 
                             config: Optional[HermesConfig] = None) -> List[Dict[str, Any]]:
    """
    Process a batch of emails using the Hermes workflow.
    
    Args:
        emails_data: List of dictionaries, each containing email data ('id', 'subject', 'body').
        product_catalog_df: DataFrame containing the product catalog.
        config: Optional HermesConfig instance.
        
    Returns:
        A list of final state dictionaries for each processed email.
    """
    if config is None:
        config = HermesConfig()
        
    # 1. Setup Vector Store
    # Check if vector store exists, otherwise create it
    try:
        print("Loading existing vector store...")
        vector_store = load_product_vectorstore(
            chroma_persist_directory=config.vector_store_path,
            collection_name=config.chroma_collection_name,
            embedding_model_name=config.embedding_model_name
        )
        print("Vector store loaded successfully.")
    except Exception as e:
        print(f"Failed to load vector store: {e}. Creating a new one...")
        vector_store = create_product_vectorstore_batched(
            product_catalog_df=product_catalog_df,
            embedding_model_name=config.embedding_model_name,
            chroma_persist_directory=config.vector_store_path,
            collection_name=config.chroma_collection_name
        )
        print("New vector store created.")
        
    # 2. Create the workflow
    # Pass the configuration to the workflow
    runnable_config = {
        "configurable": {
            "hermes_config": config
        }
    }
    workflow = create_hermes_workflow(config=runnable_config)
    
    # 3. Prepare initial states for each email
    initial_states = []
    for email in emails_data:
        initial_state = HermesState(
            email_id=email.get('id', 'unknown'),
            email_subject=email.get('subject', ''),
            email_body=email.get('body', ''),
            # Inject shared resources into metadata for agents/tools to access
            metadata={
                "product_catalog_df": product_catalog_df,
                "vector_store": vector_store
            }
        )
        initial_states.append(initial_state)
    
    # 4. Process emails in parallel using asyncio
    print(f"Processing {len(emails_data)} emails...")
    
    # Define the function to process a single email
    async def process_single_email(initial_state):
        final_state = await workflow.ainvoke(initial_state.__dict__, config=runnable_config)
        return final_state

    # Run processing tasks concurrently
    tasks = [process_single_email(state) for state in initial_states]
    processed_states = await asyncio.gather(*tasks)
    
    print("Finished processing all emails.")
    return processed_states

""" {cell}
# Example Usage

# --- 1. Load Data --- 

# Load Product Catalog (replace with actual loading logic)
# Example: Load from a CSV file
try:
    product_catalog_df = pd.read_csv("sample-data/fashion_catalog.csv")
    print(f"Loaded product catalog with {len(product_catalog_df)} items.")
except FileNotFoundError:
    print("Error: Product catalog file 'sample-data/fashion_catalog.csv' not found.")
    # Create a dummy DataFrame for demonstration if file is missing
    product_catalog_df = pd.DataFrame({
        'product ID': ['DUMMY001'], 
        'name': ['Dummy Product'], 
        'category': ['Dummies'], 
        'stock amount': [10], 
        'description': ['This is a dummy product for testing.'],
        'price': [99.99]
    })

# Sample Emails Data (replace with actual loading logic, e.g., from Google Sheets or a list)
sample_emails = [
    {
        "id": "email_001",
        "subject": "Order Request - LTH0976 Jacket",
        "body": "Hi team, I'd like to order the brown leather jacket, product ID LTH0976, in size Large. Please confirm availability. Thanks!"
    },
    {
        "id": "email_002",
        "subject": "Question about cashmere scarves",
        "body": "Hello, I'm interested in your cashmere scarves. Can you tell me if the CSH1098 model is 100% cashmere? Also, what colors does it come in?"
    },
    {
        "id": "email_003",
        "subject": "Urgent: Need summer dress for wedding!",
        "body": "Help! I need a beautiful dress for a summer wedding next weekend. Looking for something floral, maybe knee-length? Do you have anything suitable? I'm a size Medium."
    },
    {
        "id": "email_004",
        "subject": "Order TSH5678 and inquiry",
        "body": "I want to order the basic white T-shirt (TSH5678), quantity 2, size Small. Also, do you have any recommendations for casual jeans to go with it?"
    }
]

# --- 2. Setup Configuration --- 

# Initialize configuration (can customize parameters here)
hermes_config = HermesConfig(
    llm_model_name="gpt-4o", # Specify desired model
    # llm_api_key="YOUR_API_KEY", # Optional: set if not using environment variables
    debug_mode=False
)

# --- 3. Run Processing --- 

async def main():
    # Run the batch processing
    final_states = await process_emails_batch(
        emails_data=sample_emails,
        product_catalog_df=product_catalog_df,
        config=hermes_config
    )
    
    # --- 4. Output Results --- 
    
    # Format and write results to Google Sheets
    # Note: This requires Google Colab environment or appropriate local auth setup
    try:
        format_and_write_final_outputs(
            processed_states=final_states,
            spreadsheet_name=hermes_config.output_spreadsheet_name
        )
    except Exception as output_error:
        print(f"Could not write to Google Sheets: {output_error}")
        print("Displaying final states instead:")
        # Optionally print results if sheet writing fails
        # for i, state in enumerate(final_states):
        #     print(f"--- Result for Email {i+1} ---")
        #     print(state)

# Execute the main function (using asyncio.run in a notebook/script environment)
# In a notebook cell, you might need `await main()` if running in an async context
if __name__ == "__main__" or __name__ == "__mp_main__": # Check for script execution
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Handle case where asyncio event loop is already running (e.g., in Jupyter)
        if "cannot run event loop while another loop is running" in str(e):
            print("Asyncio loop already running. Trying nested loop...")
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.run(main())
        else:
            raise
"""

""" {cell}
### Main Processing Script Implementation Notes

This script brings together all the components of the Hermes system to process a batch of emails:

1. **Data Loading**: It demonstrates loading the product catalog (e.g., from CSV) and defines sample email data. In a real application, this would be replaced with actual data sources.

2. **Configuration**: Initializes `HermesConfig` which centralizes settings like LLM model names, API keys, and paths.

3. **Resource Initialization**: Handles the creation or loading of the `vector_store`, ensuring it's available for the RAG process.

4. **Workflow Invocation**: 
   - Creates the compiled LangGraph `workflow`.
   - Prepares the initial `HermesState` for each email, injecting shared resources like the product catalog DataFrame and vector store via the `metadata` field.
   - Uses `asyncio.gather` to process emails concurrently for efficiency.

5. **State Management**: Passes the state dictionary through the workflow, allowing each agent node to read inputs and write outputs.

6. **Output Handling**: Calls `format_and_write_final_outputs` to write the collected final states to Google Sheets, fulfilling the assignment requirement.

7. **Asynchronous Execution**: Leverages `asyncio` for parallel processing of emails, significantly speeding up execution for larger batches.

This script serves as the entry point for running the reference solution and demonstrates the end-to-end flow from data loading to result output.
""" 