"""
Simplified Hermes Email Processing Pipeline
"""
import os
import json
import time
import pandas as pd
import pinecone

from typing import TypedDict, List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from pinecone import Pinecone as PineconeClient, ServerlessSpec

#region: Environment Variables / Notebook Parameters (Copied from hermes-poc.py)

# --- OpenAI Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<OPENAI API KEY: Use one provided by Crossover or your own>")
OPENAI_BASE_URL = 'https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/'
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Pinecone Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "<YOUR PINECONE API KEY>")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "<YOUR PINECONE ENVIRONMENT>")
PINECONE_INDEX_NAME = "hermes-products-simplified" # Consider a new index or manage carefully
PINECONE_EMBEDDING_DIMENSION = 1536
PINECONE_METRIC = "cosine"

# --- Data Configuration ---
INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'
OUTPUT_SPREADSHEET_NAME = 'hermes_assignment_output_simplified.xlsx'

# --- Prompt Files Configuration ---
PROMPTS_DIR = "prompts/"
DOCS_DIR = "docs/"
SALES_GUIDE_FILENAME = "sales-email-intelligence-guide.md"

# Placeholder for new simplified prompts
SIMPLIFIED_PROMPTS = {
    "initial_analyzer": "simpl_01_initial_analyzer.md",
    "mega_processor": "simpl_02_mega_processor.md"
}

# --- Other Constants ---
MAX_RETRIES_LLM = 3
MAX_EMAILS_TO_PROCESS = 0 # Set to 0 to process all, or a positive number for testing
INDIVIDUAL_EMAIL_DELAY_SECONDS = 0.5 # Reduced delay for potentially faster simplified flow

#endregion: Environment Variables / Notebook Parameters

#region: --- Client Initializations (Copied from hermes-poc.py) ---

chat_model = None
embedding_model = None
pinecone_index = None

if OPENAI_API_KEY != "<OPENAI API KEY: Use one provided by Crossover or your own>":
    try:
        chat_model = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.2, # Default temperature, can be overridden per call
            max_retries=MAX_RETRIES_LLM
        )
        embedding_model = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )
        print("LangChain ChatModel and EmbeddingModel initialized.")
    except Exception as e:
        print(f"**Error initializing OpenAI components:** {e}. Please check API key and base URL.")
else:
    print("**OpenAI API Key not configured.** Some features will be unavailable.")

#endregion: --- Client Initializations ---

#region: --- Data Loading (Copied from hermes-poc.py, with minor adjustments) ---
def convert_gsheet_to_data_frame(document_id, sheet_name):
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(export_link)
        return df
    except Exception as e:
        print(f"**Error loading sheet `{sheet_name}`:** {e}")
        return pd.DataFrame()

products_df = convert_gsheet_to_data_frame(INPUT_SPREADSHEET_ID, 'products')
emails_df = convert_gsheet_to_data_frame(INPUT_SPREADSHEET_ID, 'emails')

if not products_df.empty:
    products_df['product_id'] = products_df['product_id'].astype(str)
    products_df['stock'] = pd.to_numeric(products_df['stock'], errors='coerce').fillna(0).astype(int)
    products_df['price'] = pd.to_numeric(products_df['price'], errors='coerce').fillna(0.0).astype(float)
    for col in ['name', 'category', 'description', 'season']:
        if col in products_df.columns:
            products_df[col] = products_df[col].astype(str).fillna('')

if not emails_df.empty:
    for col in ['email_id', 'subject', 'message']:
        if col in emails_df.columns:
             emails_df[col] = emails_df[col].astype(str).fillna('')
    
inventory_df = None
if not products_df.empty:
    inventory_df = products_df[['product_id', 'stock']].copy()
    inventory_df.set_index('product_id', inplace=True)

sales_guide_content = ""
try:
    with open(os.path.join(DOCS_DIR, SALES_GUIDE_FILENAME), 'r') as f:
        sales_guide_content = f.read()
    print(f"Sales guide '{SALES_GUIDE_FILENAME}' loaded.")
except Exception as e:
    print(f"**Error loading sales guide '{SALES_GUIDE_FILENAME}':** {e}")

def load_prompt_template(prompt_filename, dynamic_values=None):
    global sales_guide_content # Make sure sales_guide_content is accessible
    try:
        with open(os.path.join(PROMPTS_DIR, prompt_filename), 'r') as f:
            template = f.read()
        # Always include sales guide if the placeholder exists, for simplified prompts
        if "<< include: sales-email-intelligence-guide.md >>" in template:
            template = template.replace("<< include: sales-email-intelligence-guide.md >>", sales_guide_content)
        if dynamic_values:
            for key, value in dynamic_values.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, indent=2)
                else:
                    value_str = str(value)
                template = template.replace(f"<< include: {key} >>", value_str)
                template = template.replace(f"<< {key} >>", value_str)
        return template
    except Exception as e:
        print(f"**Error loading prompt template '{prompt_filename}': {e}**")
        return None
#endregion: --- Data Loading ---

#region: --- Pydantic Models for Simplified LLM Outputs ---
class LLMError(BaseModel):
    error: str
    raw_content: Optional[str] = None

class InitialEmailAnalysis(BaseModel):
    email_id: str
    primary_category: str = Field(description="Primary category of the email (e.g., 'Order Request', 'Product Inquiry', 'Feedback', 'Spam', 'Other').")
    sub_categories: List[str] = Field(default_factory=list, description="More specific categories if applicable.")
    customer_sentiment: Optional[str] = Field(default=None, description="Overall sentiment (e.g., 'Positive', 'Neutral', 'Negative', 'Urgent').")
    key_product_mentions_raw: List[str] = Field(default_factory=list, description="Raw text of product mentions exactly as they appear in the email.")
    key_questions_or_topics: List[str] = Field(default_factory=list, description="Main questions or topics raised by the customer.")
    summary_of_intent: str = Field(description="A brief summary of what the customer wants.")
    suggested_priority: Optional[str] = Field(default='normal', description="Suggested priority for handling (e.g., 'high', 'normal', 'low').")

class IdentifiedProductInfo(BaseModel):
    original_mention: str
    matched_product_id: Optional[str] = None
    matched_product_name: Optional[str] = None
    match_type: Optional[str] = Field(default=None, description="How the product was matched (e.g., 'direct_id', 'name_match', 'vector_search', 'none').")
    quantity_requested: Optional[int] = 1 # Default to 1, LLM might update this in analysis
    current_stock: Optional[int] = None
    price: Optional[float] = None
    confidence_score_if_vector: Optional[float] = None # For vector search matches
    questions_related_to_this_item: List[str] = Field(default_factory=list)

class ProcessedOrderItemSimplified(BaseModel):
    product_id: str
    original_mention: str
    requested_quantity: int
    fulfilled_quantity: int
    status: str = Field(description="e.g., 'fulfilled', 'partially_fulfilled_stock', 'out_of_stock', 'error_processing'")
    reason_if_not_fully_fulfilled: Optional[str] = None
    suggested_alternative_ids: List[str] = Field(default_factory=list)

class InquiryAnswerSimplified(BaseModel):
    original_question_or_topic: str # Could be from InitialEmailAnalysis or a specific product question
    product_id_context: Optional[str] = None # If the question is about a specific product
    answer_text: str
    supporting_product_ids: List[str] = Field(default_factory=list, description="Product IDs mentioned or relevant to the answer.")

class MegaAgentOutput(BaseModel):
    email_id: str
    overall_assessment: str = Field(description="Brief summary of how the email was processed and what actions were taken.")
    processed_order_items: List[ProcessedOrderItemSimplified] = Field(default_factory=list)
    inquiry_answers: List[InquiryAnswerSimplified] = Field(default_factory=list)
    alternative_suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggestions for out-of-stock items or as general alternatives. E.g., {'original_item_mention': str, 'suggested_product_id': str, 'reason': str}")
    upsell_opportunities_identified: List[Dict[str, Any]] = Field(default_factory=list, description="Identified upsell ops. E.g., {'based_on_item_id': str, 'upsell_product_id': str, 'reason': str}")
    composed_subject: str
    composed_greeting: str
    composed_body: str
    composed_signature: str
    errors_encountered_during_processing: List[str] = Field(default_factory=list)
#endregion: --- Pydantic Models for Simplified LLM Outputs ---

#region: --- LangChain Tools ---

# Ensure products_df and inventory_df are accessible, they are global in this script
# If this were part of a class, they'd be passed in or accessible via self.

@tool
def find_product_info_tool(product_mention: str) -> IdentifiedProductInfo:
    """
    Finds detailed information about a product based on a textual mention from an email.
    It tries to match by product ID, then by name, and finally uses a vector search if no direct match is found.
    Use this tool to understand what product the customer is referring to.

    Args:
        product_mention: The raw text from the email that mentions the product.
    """
    global products_df, inventory_df, pinecone_index # Access global resources

    info = IdentifiedProductInfo(original_mention=product_mention)

    if not products_df.empty:
        # Try direct ID match first
        if product_mention in products_df['product_id'].values:
            product_row = products_df[products_df['product_id'] == product_mention].iloc[0]
            info.matched_product_id = product_row['product_id']
            info.matched_product_name = product_row['name']
            info.match_type = 'direct_id'
            info.price = product_row['price']
            info.current_stock = inventory_df.loc[product_row['product_id'], 'stock'] if inventory_df is not None and product_row['product_id'] in inventory_df.index else 0
        else:
            # Try name match (simple exact name match for now, can be fuzzy)
            # Using str.contains for a slightly broader match. For more precision, consider exact match or fuzzywuzzy.
            name_matches = products_df[products_df['name'].str.contains(product_mention, case=False, na=False)]
            if not name_matches.empty:
                product_row = name_matches.iloc[0] # Take the first match
                info.matched_product_id = product_row['product_id']
                info.matched_product_name = product_row['name']
                info.match_type = 'name_match'
                info.price = product_row['price']
                info.current_stock = inventory_df.loc[product_row['product_id'], 'stock'] if inventory_df is not None and product_row['product_id'] in inventory_df.index else 0
            # If no direct/name match, try Pinecone vector search
            elif pinecone_index and product_mention.strip():
                pinecone_results = query_pinecone_for_products(product_mention.strip(), top_k=1)
                if pinecone_results and pinecone_results[0].get('score', 0) > 0.75: # Confidence threshold
                    match_meta = pinecone_results[0].get('metadata', {})
                    info.matched_product_id = match_meta.get('product_id')
                    info.matched_product_name = match_meta.get('name')
                    info.match_type = 'vector_search'
                    info.price = match_meta.get('price')
                    info.current_stock = match_meta.get('stock') # Pinecone metadata should have current stock
                    info.confidence_score_if_vector = pinecone_results[0].get('score')
                else:
                    info.match_type = 'none' # No match found via vector search or below threshold
            else:
                info.match_type = 'none' # No match found and Pinecone not available/applicable
    else:
        print("**Warning (find_product_info_tool):** products_df is empty. Cannot identify products.")
        info.match_type = 'none'
        info.questions_related_to_this_item = [] # Cannot associate if product not found

    # Note: Associating general email questions to items might be better handled by the LLM
    # after it has all product infos and all questions.
    # For now, this tool returns the identified product without associating general questions.
    return info

@tool
def update_stock_tool(product_id: str, quantity_deducted: int, original_mention: str) -> Dict[str, Any]:
    """
    Updates the stock for a given product ID by deducting the specified quantity.
    This should be called AFTER an order item has been confirmed as fulfilled (fully or partially).

    Args:
        product_id: The unique identifier of the product whose stock needs to be updated.
        quantity_deducted: The quantity to deduct from the stock. Should be a positive integer.
        original_mention: The original mention of the item, for logging/reference.
    """
    global inventory_df # Access global inventory DataFrame

    if inventory_df is None:
        msg = f"Inventory_df is None. Cannot update stock for {product_id}."
        print(f"**Error (update_stock_tool):** {msg}")
        return {"product_id": product_id, "status": "error_inventory_unavailable", "message": msg, "stock_after": None}

    if product_id not in inventory_df.index:
        msg = f"Product ID '{product_id}' not found in inventory. Cannot update stock."
        print(f"**Warning (update_stock_tool):** {msg}")
        return {"product_id": product_id, "status": "error_product_not_found", "message": msg, "stock_after": None}

    if quantity_deducted <= 0:
        msg = f"Quantity to deduct for {product_id} must be positive. Was {quantity_deducted}. No update made."
        print(f"**Warning (update_stock_tool):** {msg}")
        return {"product_id": product_id, "status": "error_invalid_quantity", "message": msg, "stock_after": inventory_df.loc[product_id, 'stock']}

    current_stock = inventory_df.loc[product_id, 'stock']
    
    if quantity_deducted > current_stock:
        msg = f"Attempted to deduct {quantity_deducted} for '{product_id}', but only {current_stock} available. Deducting {current_stock}."
        print(f"**Critical Warning (update_stock_tool):** {msg}")
        actual_deduction = current_stock
    else:
        actual_deduction = quantity_deducted
            
    new_stock = current_stock - actual_deduction
    inventory_df.loc[product_id, 'stock'] = new_stock
    
    update_summary = {
        "product_id": product_id,
        "original_mention": original_mention,
        "status": "success",
        "message": f"Stock updated for {product_id}. Deducted {actual_deduction}. Previous: {current_stock}, New: {new_stock}.",
        "quantity_deducted_actual": actual_deduction,
        "stock_before": current_stock,
        "stock_after": new_stock
    }
    print(f"(update_stock_tool): {update_summary['message']}")
    return update_summary

@tool
def process_order_item_tool(product_id: str, product_name: str, current_stock: int, requested_quantity: int, original_mention: str) -> ProcessedOrderItemSimplified:
    """
    Processes a single order item *once its product ID, name, and current stock are known*.
    Determines fulfillment status, quantities, and suggests alternatives if out of stock or partially available.
    Use this tool AFTER identifying the product with 'find_product_info_tool' if the product ID is not directly clear.

    Args:
        product_id: The unique identifier of the product being ordered.
        product_name: The name of the product.
        current_stock: The current available stock for this product.
        requested_quantity: The quantity of the product requested by the customer.
        original_mention: The exact text from the email that refers to this product order.
    """
    global products_df, inventory_df # For suggesting alternatives

    if requested_quantity <= 0: # Should ideally be caught by LLM, but good to have a guard.
        return ProcessedOrderItemSimplified(
            product_id=product_id,
            original_mention=original_mention,
            requested_quantity=requested_quantity,
            fulfilled_quantity=0,
            status='error_invalid_request',
            reason_if_not_fully_fulfilled="Requested quantity must be positive."
        )

    if current_stock >= requested_quantity:
        fulfilled_quantity = requested_quantity
        status = 'fulfilled'
        reason = None
        alternatives = []
    elif current_stock > 0:
        fulfilled_quantity = current_stock
        status = 'partially_fulfilled_stock'
        reason = f"Only {current_stock} of {product_name} (ID: {product_id}) available in stock out of {requested_quantity} requested."
        alternatives = [] # Could suggest ordering the available amount and waiting for restock
    else: # current_stock == 0
        fulfilled_quantity = 0
        status = 'out_of_stock'
        reason = f"{product_name} (ID: {product_id}) is out of stock."
        alternatives = []
        if not products_df.empty and inventory_df is not None: # Ensure inventory_df is available for stock check of alternatives
            try:
                # Find the category of the out-of-stock item
                original_item_category_series = products_df.loc[products_df['product_id'] == product_id, 'category']
                if not original_item_category_series.empty:
                    original_item_category = original_item_category_series.iloc[0]
                    
                    # Find in-stock alternatives from the same category, excluding the original item
                    # Make sure to use .index access for inventory_df since product_id is its index
                    alt_df = products_df[
                        (products_df['product_id'] != product_id) &
                        (products_df['category'] == original_item_category) &
                        (products_df['product_id'].isin(inventory_df.index)) & # Ensure product_id exists in inventory_df
                        (inventory_df.loc[products_df['product_id'].intersection(inventory_df.index), 'stock'] > 0)
                    ].copy() # Use .copy() to avoid SettingWithCopyWarning if you modify alt_df later

                    if not alt_df.empty:
                        # Ensure we are checking stock correctly for these alternatives
                        valid_alternatives = []
                        for alt_pid in alt_df['product_id']:
                            if alt_pid in inventory_df.index and inventory_df.loc[alt_pid, 'stock'] > 0:
                                valid_alternatives.append(alt_pid)
                        alternatives = valid_alternatives[:2] # Take top 2 valid alternatives
            except Exception as e:
                print(f"Error suggesting alternatives for {product_id}: {e}")


    return ProcessedOrderItemSimplified(
        product_id=product_id,
        original_mention=original_mention,
        requested_quantity=requested_quantity,
        fulfilled_quantity=fulfilled_quantity,
        status=status,
        reason_if_not_fully_fulfilled=reason,
        suggested_alternative_ids=alternatives
    )

@tool
def answer_customer_question_tool(question: str, product_id_context: Optional[str] = None, original_email_segment: Optional[str] = None) -> InquiryAnswerSimplified:
    """
    Answers a customer's question, potentially using product information from the catalog
    and general guidance from the sales guide.
    Use this tool for each distinct question or topic raised by the customer that requires an answer.

    Args:
        question: The specific question or topic raised by the customer that needs an answer.
        product_id_context: Optional. If the question is about a specific product, provide its ID.
        original_email_segment: Optional. The segment of the email containing the question, for context.
    """
    global products_df, sales_guide_content # Access global data

    # This tool would ideally use a RAG approach or a focused LLM call with relevant context.
    # For this example, it's a simplified placeholder implementation.
    answer_text = f"Regarding your question: '{question}'"
    supporting_ids = []

    # Incorporate product context if available
    product_info_for_answer = ""
    if product_id_context and not products_df.empty and product_id_context in products_df['product_id'].values:
        product_series = products_df[products_df['product_id'] == product_id_context].iloc[0]
        product_info_for_answer = (
            f"For product '{product_series['name']}' (ID: {product_id_context}): "
            f"Category: {product_series['category']}, Price: ${product_series['price']:.2f}. "
            f"Description: {product_series['description'][:100]}..."
        )
        answer_text += f"\n{product_info_for_answer}"
        supporting_ids.append(product_id_context)

    # Incorporate sales guide context (simple keyword check)
    sales_guide_snippet = ""
    if "return policy" in question.lower():
        # In a real scenario, you'd search sales_guide_content more effectively
        sales_guide_snippet = "Our general return policy allows returns within 30 days with proof of purchase for most items. Please see our website for full details." # Placeholder
        answer_text += f"\nSales Guide Information: {sales_guide_snippet}"
    elif "shipping" in question.lower():
        sales_guide_snippet = "We offer standard and expedited shipping. Costs and times vary by location. More details are on our shipping information page." # Placeholder
        answer_text += f"\nSales Guide Information: {sales_guide_snippet}"
    else:
        answer_text += "\nOur team will provide the best possible information. For detailed product specs, please check the product page on our website."


    # A more sophisticated version would search sales_guide_content and product_df for keywords from the question.
    # It might even use a separate, focused LLM call for complex questions.
    
    return InquiryAnswerSimplified(
        original_question_or_topic=question,
        product_id_context=product_id_context,
        answer_text=answer_text.strip(),
        supporting_product_ids=supporting_ids
    )

#endregion: --- LangChain Tools ---

#region: --- LangChain & LLM Helper (Copied from hermes-poc.py) ---
def call_llm_with_structured_output(
    prompt_content: str,
    pydantic_schema: Optional[type(BaseModel)] = None,
    temperature: float = 0.2 # Default temperature for most calls
):
    if not chat_model:
        error_msg = "ChatModel not initialized"
        print(f"**Error (call_llm):** {error_msg}")
        return LLMError(error=error_msg) if pydantic_schema else error_msg

    prompt_template = ChatPromptTemplate.from_messages([("user", prompt_content)])
    
    current_model_for_call = chat_model
    if temperature != chat_model.temperature: # Create a temporary model if a different temp is needed
        try:
            current_model_for_call = ChatOpenAI(
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                temperature=temperature,
                max_retries=MAX_RETRIES_LLM
            )
        except Exception as e:
            error_msg = f"Failed to create temp model for temperature {temperature}: {e}"
            print(f"**Error (call_llm):** {error_msg}")
            return LLMError(error=error_msg) if pydantic_schema else error_msg

    try:
        if pydantic_schema:
            structured_llm = current_model_for_call.with_structured_output(pydantic_schema)
            chain = prompt_template | structured_llm
            response = chain.invoke({})
            return response
        else:
            chain = prompt_template | current_model_for_call
            response = chain.invoke({})
            return response.content
    except Exception as e:
        error_message = f"LangChain API call failed: {str(e)}"
        raw_output_details = "No raw output retrievable from LangChain exception."
        # Attempt to get raw output if possible, though usually not available directly from invoke on error
        print(f"**Error (call_llm):** {error_message}. Raw output (if any from error): {raw_output_details}")
        return LLMError(error=error_message, raw_content=raw_output_details) if pydantic_schema else error_message

def get_langchain_embeddings(texts_list: List[str]) -> List[List[float]]:
    if not embedding_model:
        print("**Error (get_embeddings):** LangChain EmbeddingModel is not initialized.")
        return []
    # The primary caller (populate_pinecone) ensures texts_list is not empty.
    # If this function were to be used more generally, the `if not texts_list: return []` check would be advisable.
    try:
        texts_list_cleaned = [str(text).replace("\n", " ") for text in texts_list]
        return embedding_model.embed_documents(texts_list_cleaned)
    except Exception as e:
        print(f"**Error (get_embeddings):** {e}")
        return []

def prepare_embedding_text_for_product(product_row_dict: Dict[str, Any]) -> str:
    return (
        f"Product: {str(product_row_dict.get('name', ''))}\n"
        f"Description: {str(product_row_dict.get('description', ''))}\n"
        f"Category: {str(product_row_dict.get('category', ''))}\n"
        f"Season: {str(product_row_dict.get('season', ''))}"
    )
#endregion: --- LangChain & LLM Helper ---

#region: --- Pinecone Initialization and Helpers (Copied from hermes-poc.py, check PINECONE_INDEX_NAME) ---
def populate_pinecone(products_df_to_embed: pd.DataFrame, target_index, batch_size=50):
    if target_index is None or products_df_to_embed.empty:
        print("**Error (Embed/Upsert):** Pinecone index not ready or no products to upsert.")
        return
    print(f"Starting embedding and upsertion of {len(products_df_to_embed)} products to '{target_index.name}'...")
    for i in range(0, len(products_df_to_embed), batch_size):
        batch_df = products_df_to_embed.iloc[i:i+batch_size]
        texts_to_embed = [prepare_embedding_text_for_product(row._asdict()) for row in batch_df.itertuples(index=False)]
        if not texts_to_embed: continue
        embeddings = get_langchain_embeddings(texts_to_embed)
        if not embeddings or len(embeddings) != len(batch_df):
            print(f"**Warning (Embed/Upsert):** Embedding failed/mismatch for batch at index {i}. Skipping.")
            continue
        vectors_to_upsert = []
        for j, product_tuple in enumerate(batch_df.itertuples(index=False)):
            prod_dict = product_tuple._asdict()
            prod_id_str = str(prod_dict['product_id'])
            # Ensure inventory_df is used correctly here for stock
            stock_val = 0
            if inventory_df is not None and prod_id_str in inventory_df.index:
                stock_val = int(inventory_df.loc[prod_id_str, 'stock'])
            else:
                stock_val = int(prod_dict.get('stock', 0)) # Fallback to product_df stock if not in inventory_df
            
            metadata = {
                "product_id": prod_id_str, "name": str(prod_dict.get('name', '')),
                "description": str(prod_dict.get('description', '')), "category": str(prod_dict.get('category', '')),
                "season": str(prod_dict.get('season', '')), "price": float(prod_dict.get('price', 0.0)),
                "stock": stock_val }
            vectors_to_upsert.append({"id": prod_id_str, "values": embeddings[j], "metadata": metadata})
        if vectors_to_upsert: target_index.upsert(vectors=vectors_to_upsert)
    print("Product embedding and upsertion complete.")
    
def initialize_pinecone():
    global pinecone_index, products_df, embedding_model, inventory_df

    if PINECONE_API_KEY == "<YOUR PINECONE API KEY>" or PINECONE_ENVIRONMENT == "<YOUR PINECONE ENVIRONMENT>":
        print("**Pinecone not configured.** RAG features will be limited.")
        return None
    try:
        pc = PineconeClient(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        if PINECONE_INDEX_NAME not in pc.list_indexes().names:
            print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}' (dim: {PINECONE_EMBEDDING_DIMENSION}, metric: {PINECONE_METRIC})...")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=PINECONE_EMBEDDING_DIMENSION,
                metric=PINECONE_METRIC,
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            wait_time = 0; max_wait_time = 300 # 5 minutes
            while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                print(f"Waiting for index '{PINECONE_INDEX_NAME}' to be ready...")
                time.sleep(10); wait_time += 10
                if wait_time >= max_wait_time:
                    print(f"**Error:** Pinecone index '{PINECONE_INDEX_NAME}' did not become ready in time.")
                    return None
            print(f"Index '{PINECONE_INDEX_NAME}' created and ready.")
            # Populate if newly created and prerequisites are met
            if products_df is not None and not products_df.empty and embedding_model is not None and inventory_df is not None:
                print(f"Populating newly created Pinecone index '{PINECONE_INDEX_NAME}'...")
                current_pinecone_index_for_pop = pc.Index(PINECONE_INDEX_NAME)
                populate_pinecone(products_df, current_pinecone_index_for_pop)
            else:
                print(f"Skipping population of new index '{PINECONE_INDEX_NAME}' due to missing prerequisites (products_df, embedding_model, or inventory_df).")
        else:
            print(f"Pinecone index '{PINECONE_INDEX_NAME}' already exists.")
        
        current_pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        print(f"Pinecone index '{current_pinecone_index.name}' object retrieved.")

        # Check if existing index is empty and needs population
        try:
            stats = current_pinecone_index.describe_index_stats()
            if hasattr(stats, 'total_vector_count') and stats.total_vector_count == 0:
                print(f"Pinecone index '{current_pinecone_index.name}' is empty. Attempting to populate...")
                if products_df is not None and not products_df.empty and embedding_model is not None and inventory_df is not None:
                    populate_pinecone(products_df, current_pinecone_index)
                else:
                    print(f"Skipping population of empty index '{current_pinecone_index.name}': Required data not ready.")
            elif hasattr(stats, 'total_vector_count'):
                print(f"Pinecone index '{current_pinecone_index.name}' contains {stats.total_vector_count} vectors.")
            else:
                print(f"**Warning (Pinecone Stats):** Could not determine vector count for '{current_pinecone_index.name}'.")
        except Exception as e_stats:
            print(f"**Warning (Pinecone Stats):** Could not get stats for '{current_pinecone_index.name}': {e_stats}.")
        
        pinecone_index = current_pinecone_index # Assign to global
        print("Pinecone initialization complete.")
        return pinecone_index
    except Exception as e:
        print(f"**Error initializing Pinecone:** {e}.")
        pinecone_index = None
        return None

pinecone_index = initialize_pinecone()

def query_pinecone_for_products(query_text: str, top_k=3, index_to_query=None) -> List[Dict[str, Any]]:
    effective_index = index_to_query if index_to_query else pinecone_index
    if effective_index is None:
        print("**Warning (Query Pinecone):** Pinecone index not available.")
        return []
    if not query_text or not str(query_text).strip(): return []
    if not embedding_model: 
        print("**Error (Query Pinecone):** EmbeddingModel not initialized."); return []
    try:
        query_embedding = embedding_model.embed_query(str(query_text).strip())
        if not query_embedding: raise ValueError("Embedding generation failed for query.")
        results = effective_index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        return results.get('matches', [])
    except Exception as e:
        print(f"**Error (Query Pinecone):** Failed for query '{str(query_text)[:50]}...': {e}")
        return []
#endregion: --- Pinecone Initialization and Helpers ---

#region: --- Simplified Processing Functions ---
def perform_initial_email_analysis(email_id: str, subject: str, message: str) -> Optional[InitialEmailAnalysis]:
    print(f"Step 1: Initial Analysis for Email ID: {email_id}")
    prompt_filename = SIMPLIFIED_PROMPTS["initial_analyzer"]
    # Sales guide might be useful here for nuanced category/sentiment detection
    dynamic_prompt_values = {
        "email.id": email_id,
        "email.subject": subject,
        "email.message": message,
        # "sales_guide_summary": sales_guide_content[:2000] # Optionally pass a summary or key parts
    }
    prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    
    if not prompt_content:
        print(f"**Error:** Could not load prompt for initial analysis.")
        return InitialEmailAnalysis(
            email_id=email_id, 
            primary_category='error_prompt_loading',
            summary_of_intent='Error loading analysis prompt.',
            # Fill other fields as error indications
            key_product_mentions_raw=[],
            key_questions_or_topics=['Prompt loading failed for initial analysis']
        ) # Return a default error object

    llm_response = call_llm_with_structured_output(prompt_content, pydantic_schema=InitialEmailAnalysis)
    
    if isinstance(llm_response, InitialEmailAnalysis):
        return llm_response
    else:
        error_msg = llm_response.error if isinstance(llm_response, LLMError) else "Malformed output from initial analysis LLM."
        raw_c = getattr(llm_response, 'raw_content', str(llm_response)[:100])
        print(f"**Error (Initial Analysis LLM for {email_id}):** {error_msg}. Raw: {raw_c}")
        # Return a structured error to propagate
        return InitialEmailAnalysis(
            email_id=email_id, 
            primary_category='error_llm_analysis',
            summary_of_intent=f'LLM error during initial analysis: {error_msg}',
            key_product_mentions_raw=[],
            key_questions_or_topics=[f'LLM error: {error_msg}']
        )

def run_mega_processor_agent(
    email_id: str, 
    original_subject: str,
    original_message: str, 
    initial_analysis: InitialEmailAnalysis, 
    # identified_products: List[IdentifiedProductInfo] # This is no longer passed in
) -> Optional[MegaAgentOutput]:
    print(f"Step 3: Mega Processor Agent for Email ID: {email_id} (Using Tools)")
    
    if not chat_model:
        error_msg = "ChatModel not initialized for Mega Processor Agent"
        print(f"**Error (Mega Agent - Tools):** {error_msg}")
        return MegaAgentOutput(email_id=email_id, overall_assessment=error_msg, composed_subject='Error', composed_greeting='Error', composed_body='Agent not initialized.', composed_signature='System')

    tools = [find_product_info_tool, process_order_item_tool, answer_customer_question_tool, update_stock_tool]
    llm_with_tools = chat_model.bind_tools(tools)

    # Construct messages for the LLM
    initial_analysis_summary = (
        f"Initial Email Analysis Summary for Email ID {initial_analysis.email_id}:\n"
        f"- Primary Category: {initial_analysis.primary_category}\n"
        f"- Sub Categories: {', '.join(initial_analysis.sub_categories) if initial_analysis.sub_categories else 'N/A'}\n"
        f"- Customer Sentiment: {initial_analysis.customer_sentiment or 'N/A'}\n"
        f"- Summary of Intent: {initial_analysis.summary_of_intent}\n"
        f"- Key Questions/Topics: {'; '.join(initial_analysis.key_questions_or_topics) if initial_analysis.key_questions_or_topics else 'None identified'}\n"
        f"- Raw Product Mentions (use 'find_product_info_tool' for these): {'; '.join(initial_analysis.key_product_mentions_raw) if initial_analysis.key_product_mentions_raw else 'None'}\n"
    )

    # identified_products_context is no longer needed as LLM will use find_product_info_tool

    product_catalog_summary_for_context = "A full product catalog is available. Refer to it for general product information, alternative suggestions, and upsell opportunities if not directly handled by a specific tool."
    if not products_df.empty:
        product_catalog_summary_for_context = products_df.to_string(
            index=False, columns=['product_id', 'name', 'category', 'price', 'description'], 
            max_colwidth=30, max_rows=10 # Brief summary
        )
        product_catalog_summary_for_context = f"Product Catalog Summary (for general context, alternatives, and upsell ideas):\n{product_catalog_summary_for_context}"


    system_prompt = (
        "You are an advanced AI email processing agent. Your goal is to comprehensively understand and act upon customer emails using available tools.\n"
        "Your primary workflow for each email is:\n"
        "1. Review the 'Initial Email Analysis', especially 'Raw Product Mentions' and 'Key Questions/Topics'.\n"
        "2. For each raw product mention that seems to be part of an order or inquiry, use the 'find_product_info_tool' to get its details (ID, name, stock, price). If the mention is clearly a product ID, you might skip this for that mention if confident, but generally prefer to verify.\n"
        "3. Once you have product details (product_id, name, current_stock) and the customer's requested quantity (infer this from the email context and initial analysis summary of intent), use the 'process_order_item_tool' for each item they wish to order. This tool will determine fulfillment status and suggest alternatives if needed.\n"
        "4. Accumulate all results from 'process_order_item_tool' to form the 'processed_order_items' list for the final output.\n"
        "5. For each distinct question or topic from 'Key Questions/Topics' or directly from the email, use the 'answer_customer_question_tool'. If a question relates to a product found in step 2, provide its ID as context to the tool.\n"
        "6. After all order items are processed and you know the 'fulfilled_quantity' for each, for every item where 'fulfilled_quantity' > 0, you MUST call the 'update_stock_tool' to deduct the fulfilled quantity from inventory. Pass the correct product_id, the fulfilled_quantity as quantity_deducted, and the original_mention.\n"
        "7. Synthesize all information: processed orders (including out-of-stock issues and alternatives from tools), answers to questions, and results of stock updates.\n"
        "8. Identify any further alternative product suggestions (beyond what tools provided for OOS items) or upsell opportunities. These should be based on the overall context and catalog summary.\n"
        "9. Finally, compose a polite, professional, and helpful email response and structure the entire result as a single JSON object conforming to the MegaAgentOutput schema. \n"
        "   - The 'overall_assessment' should summarize your actions and the outcome of using tools.\n"
        "   - 'processed_order_items' should contain results from 'process_order_item_tool'.\n"
        "   - 'inquiry_answers' should contain results from 'answer_customer_question_tool'.\n"
        "   - The composed email fields (subject, greeting, body, signature) are critical.\n"
        "   - Include any errors encountered during tool usage in 'errors_encountered_during_processing'. Check the output of 'update_stock_tool' for success/error messages and log them appropriately.\n"
        "IMPORTANT: Always call tools sequentially as needed. For example, call 'find_product_info_tool' before 'process_order_item_tool' if product details are not yet known. Call 'process_order_item_tool' before 'update_stock_tool'. Ensure all required arguments for each tool are correctly inferred and provided."
    )
    
    user_prompt_content = (
        f"Please process the following email based on the initial analysis and available tools:\n\n"
        f"Email ID: {email_id}\n"
        f"Original Subject: {original_subject}\n"
        f"Original Message:\n{original_message}\n\n"
        f"{initial_analysis_summary}\n\n"
        f"Sales Guide Context (use this for tone, policy questions, and general guidance):\n{sales_guide_content[:2000]}...\n\n"
        f"{product_catalog_summary_for_context}\n\n"
        "Follow the workflow outlined in the system prompt. Use tools to find products, process orders, update stock, and answer questions before generating the final MegaAgentOutput JSON."
    )

    messages = [
        HumanMessage(content=system_prompt), # System prompt as first human message for some models
        HumanMessage(content=user_prompt_content)
    ]

    # This is the first call. The response might contain tool calls.
    # A full agent would loop:
    # 1. Get LLM response (ai_msg).
    # 2. If ai_msg.tool_calls:
    #    a. Append ai_msg to messages.
    #    b. For each tool_call in ai_msg.tool_calls:
    #        i. Execute the tool (e.g., process_order_item_tool(...)).
    #       ii. Append ToolMessage(content=tool_output, tool_call_id=tool_call.id) to messages.
    #    c. Call llm_with_tools.invoke(messages) again.
    # 3. Else (no tool calls, LLM provides final response):
    #    a. Parse the final response (expected to be MegaAgentOutput).

    print(f"Invoking LLM with tools for email {email_id}. This may involve multiple steps (tool calls).")
    
    # For this illustrative change, we're showing the setup and first call.
    # The actual processing loop and parsing final MegaAgentOutput is complex and
    # would ideally use something like LangGraph for state management.
    
    # The 'call_llm_with_structured_output' function is designed for direct structured output,
    # not for handling tool calls. We will use the model directly here.
    # The expectation is that the LLM will eventually produce a MegaAgentOutput JSON,
    # possibly after several turns of tool use.
    
    # The `temperature` is set on the `chat_model` itself.
    # If a different temperature is needed here, a new model instance should be configured.
    
    # Forcing structured output for the *final* response after tool interactions.
    # This assumes the LLM is now ready to produce the full MegaAgentOutput.
    # In a real agent, you'd only apply .with_structured_output after the tool call loop.

    final_llm_chain = llm_with_tools.with_structured_output(MegaAgentOutput)

    # --- Simplified Agentic Loop (Conceptual) ---
    # This is a very basic loop. A robust agent needs more error handling,
    # max iterations, and potentially LangGraph.
    
    MAX_AGENT_ITERATIONS = 5 
    current_iteration = 0
    
    while current_iteration < MAX_AGENT_ITERATIONS:
        print(f"Agent Iteration {current_iteration + 1} for email {email_id}")
        ai_response: AIMessage = llm_with_tools.invoke(messages)
        messages.append(ai_response) # Add AI's response to history

        if not ai_response.tool_calls:
            # LLM believes it's done with tools and should provide the final answer
            # (or an intermediate thought process if not constrained by with_structured_output yet)
            print(f"No tool calls from LLM in iteration {current_iteration + 1}. Attempting to get final output.")
            # Now, try to get the structured output. The prompt should guide it to produce MegaAgentOutput.
            # The system prompt already instructs the LLM to output MegaAgentOutput as the final JSON.
            # We need to parse ai_response.content, assuming it's the JSON string for MegaAgentOutput.
            try:
                # If the LLM directly returns the JSON string for MegaAgentOutput
                if isinstance(ai_response.content, str):
                    # Validate if this string is the JSON for MegaAgentOutput
                    # This is tricky; ideally, the LLM is structured to output the JSON directly
                    # when tool_calls are empty *and* it's time for the final schema.
                    # Forcing with_structured_output on the *last* call is more robust.
                    
                    # Let's try to invoke with the schema for the final output generation
                    final_response_structured = final_llm_chain.invoke(messages)
                    if isinstance(final_response_structured, MegaAgentOutput):
                        return final_response_structured
                    else:
                        # This case should ideally not happen if the prompt is clear
                        # and the LLM follows instructions after tool use.
                        error_msg = f"Final LLM response was not the expected MegaAgentOutput structure after tool use. Type: {type(final_response_structured)}"
                        print(f"**Error (Mega Agent - Tools - Final Output):** {error_msg}")
                        return MegaAgentOutput(email_id=email_id, overall_assessment=error_msg, errors_encountered_during_processing=[error_msg], composed_subject="Error", composed_greeting="", composed_body="", composed_signature="")

                elif isinstance(ai_response.content, dict): # LangChain might auto-parse if it's a JSON dict
                     # This path implies the LLM directly outputted a dict matching the schema.
                     # We can try to construct the Pydantic model from it.
                    try:
                        parsed_output = MegaAgentOutput(**ai_response.content)
                        print("Successfully parsed MegaAgentOutput from LLM's direct dict response.")
                        return parsed_output
                    except Exception as e:
                        error_msg = f"LLM output was a dict, but failed to parse into MegaAgentOutput: {e}. Content: {str(ai_response.content)[:500]}"
                        print(f"**Error (Mega Agent - Tools - Dict Parse):** {error_msg}")
                        # Fall through to try with_structured_output again with current messages
                        # This might happen if the dict isn't perfectly matching.
                
                # Fallback: If the content isn't the direct JSON, or parsing failed,
                # try one last time with the explicit structured output chain.
                print("Attempting final structured output generation.")
                final_response_structured = final_llm_chain.invoke(messages)
                if isinstance(final_response_structured, MegaAgentOutput):
                    return final_response_structured
                else:
                    error_msg = "Failed to get valid MegaAgentOutput even after explicit structured output call."
                    print(f"**Error (Mega Agent - Tools - Final Structured):** {error_msg}")
                    return MegaAgentOutput(email_id=email_id, overall_assessment=error_msg, errors_encountered_during_processing=[error_msg], composed_subject="Error", composed_greeting="", composed_body="", composed_signature="")


            except Exception as e:
                error_msg = f"Error parsing final LLM response as MegaAgentOutput: {e}. Response: {str(ai_response.content)[:500]}"
                print(f"**Error (Mega Agent - Tools - Final Parse):** {error_msg}")
                return MegaAgentOutput(email_id=email_id, overall_assessment=error_msg, errors_encountered_during_processing=[error_msg], composed_subject="Error", composed_greeting="", composed_body="", composed_signature="")
        
        # Process tool calls
        print(f"LLM requested {len(ai_response.tool_calls)} tool calls in iteration {current_iteration + 1}.")
        for tool_call in ai_response.tool_calls:
            selected_tool = {t.name: t for t in tools}.get(tool_call["name"])
            if selected_tool:
                tool_output = selected_tool.invoke(tool_call["args"])
                print(f"Tool '{selected_tool.name}' executed with args {tool_call['args']}, output: {str(tool_output)[:200]}...")
                messages.append(ToolMessage(content=json.dumps(tool_output.dict()), tool_call_id=tool_call["id"]))
            else:
                print(f"**Error (Mega Agent - Tools):** Tool '{tool_call['name']}' not found.")
                messages.append(ToolMessage(content=f"Error: Tool '{tool_call['name']}' not found.", tool_call_id=tool_call["id"]))
        
        current_iteration += 1

    # If loop finishes without returning, it means max iterations were hit without final output
    max_iter_error = f"Mega Agent reached max iterations ({MAX_AGENT_ITERATIONS}) without completing for email {email_id}."
    print(f"**Warning (Mega Agent - Tools):** {max_iter_error}")
    return MegaAgentOutput(email_id=email_id, overall_assessment=max_iter_error, errors_encountered_during_processing=[max_iter_error], composed_subject="Processing Incomplete", composed_greeting="", composed_body="Agent timed out.", composed_signature="")

#endregion: --- Simplified Processing Functions ---

#region: --- Inventory Update Logic (Copied from hermes-poc.py, adapted for ProcessedOrderItemSimplified) ---
# def apply_simplified_inventory_updates( # This function will be replaced by the update_stock_tool logic
#     processed_items: List[ProcessedOrderItemSimplified],
#     live_inventory_df_ref: Optional[pd.DataFrame]
# ) -> List[Dict[str, Any]]:
#     if not processed_items:
#         return [] 
#     if live_inventory_df_ref is None: 
#         print(\"**Warning (Apply Inventory):** Live inventory_df is None. Cannot apply updates.\"); return []
        
#     actual_applied_changes = []
#     for item_data in processed_items:
#         pid = str(item_data.product_id)
#         if not pid or pid not in live_inventory_df_ref.index:
#             print(f\"**Warning (Apply Inventory):** Product ID \'{pid}\' not found in inventory. Skipping update for this item.\")
#             continue
        
#         current_stock = live_inventory_df_ref.loc[pid, \'stock\']
#         qty_to_deduct = 0
#         # Check status before deducting. Only deduct for items considered fulfilled or partially.
#         if item_data.status.startswith(\'fulfilled\') or item_data.status.startswith(\'partially_fulfilled\'):
#             qty_to_deduct = item_data.fulfilled_quantity
        
#         if qty_to_deduct > 0:
#             if qty_to_deduct > current_stock:
#                 print(f\"**Critical Warning (Apply Inventory):** For \'{pid}\', LLM decided to fulfill {qty_to_deduct}, but only {current_stock} available. Deducting {current_stock}.\")
#                 qty_to_deduct = current_stock # Cap deduction at available stock
            
#             new_stock = current_stock - qty_to_deduct
#             live_inventory_df_ref.loc[pid, \'stock\'] = new_stock
#             actual_applied_changes.append({
#                 \"product_id\": pid, 
#                 \"original_mention\": item_data.original_mention,
#                 \"qty_deducted\": qty_to_deduct, 
#                 \"stock_before\": current_stock, 
#                 \"stock_after\": new_stock, 
#                 \"llm_item_status\": item_data.status
#             })
#     if actual_applied_changes:
#         print(f\"Inventory updates applied for {len(actual_applied_changes)} items.\")
#     return actual_applied_changes
#endregion: --- Inventory Update Logic ---

#region: --- Main Processing Loop (Simplified) ---
def main():
    global inventory_df # Ensure inventory_df is accessible and updatable

    if emails_df.empty:
        print("No emails to process. Exiting.")
        return

    if products_df.empty:
        print("Product data is empty. Certain functionalities like product matching and inventory will be affected.")
    
    if inventory_df is None and not products_df.empty:
        print("Inventory_df is not initialized from products_df. Re-initializing.")
        temp_inventory_df = products_df[['product_id', 'stock']].copy()
        temp_inventory_df.set_index('product_id', inplace=True)
        inventory_df = temp_inventory_df # Assign to global
    elif inventory_df is None and products_df.empty:
        print("**Critical Warning:** Both products_df and inventory_df are unavailable. Inventory updates will fail.")

    all_results = [] # To store final structured output for each email
    processing_errors_summary = [] # Simplified error tracking

    emails_to_process_df = emails_df.copy()
    if MAX_EMAILS_TO_PROCESS > 0:
        emails_to_process_df = emails_df.head(MAX_EMAILS_TO_PROCESS)
    print(f"**Starting simplified email processing loop for {len(emails_to_process_df)} emails.**")

    for _, email_row in emails_to_process_df.iterrows():
        email_id = str(email_row['email_id'])
        subject = str(email_row.get('subject', ''))
        message = str(email_row.get('message', ''))

        print(f"\n---⚙️--- Processing Email ID: {email_id} (Simplified Flow) ---⚙️---")
        current_email_result = {
            "email_id": email_id,
            "original_subject": subject,
            "initial_analysis": None,
            "identified_products": [],
            "mega_agent_output": None,
            "final_response_text": "Error: Processing did not complete.",
            "errors": []
        }

        try:
            # Step 1: Initial Email Analysis
            analysis_output = perform_initial_email_analysis(email_id, subject, message)
            if not analysis_output or isinstance(analysis_output, LLMError) or analysis_output.primary_category.startswith('error_'):
                error_detail = analysis_output.summary_of_intent if analysis_output else "Analysis output was None"
                current_email_result["errors"].append(f"Initial Analysis Failed: {error_detail}")
                processing_errors_summary.append((email_id, "Initial Analysis", error_detail))
                all_results.append(current_email_result)
                time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS)
                continue # Skip to next email
            current_email_result["initial_analysis"] = analysis_output.dict()

            # Step 2: Product Identification & Enrichment is now part of the Mega Agent
            # identified_products_list = identify_and_enrich_products( # REMOVED
            #     analysis_output.key_product_mentions_raw,
            #     analysis_output.key_questions_or_topics
            # )
            # current_email_result["identified_products"] = [p.dict() for p in identified_products_list] # REMOVED

            # Step 3: Mega Processor Agent
            mega_agent_result = run_mega_processor_agent(
                email_id, subject, message, analysis_output #, identified_products_list # REMOVED
            )
            if not mega_agent_result or isinstance(mega_agent_result, LLMError) or mega_agent_result.overall_assessment.startswith('Error'):
                error_detail = mega_agent_result.overall_assessment if mega_agent_result else "Mega agent output was None"
                current_email_result["errors"].append(f"Mega Agent Failed: {error_detail}")
                if mega_agent_result and mega_agent_result.errors_encountered_during_processing:
                    current_email_result["errors"].extend(mega_agent_result.errors_encountered_during_processing)
                processing_errors_summary.append((email_id, "Mega Agent Processing", error_detail))
                # Still try to get a composed response if available, even if error in assessment
                if mega_agent_result and mega_agent_result.composed_body:
                    current_email_result["final_response_text"] = f"Subject: {mega_agent_result.composed_subject}\n\n{mega_agent_result.composed_greeting}\n\n{mega_agent_result.composed_body}\n\n{mega_agent_result.composed_signature}"
                    current_email_result["mega_agent_output"] = mega_agent_result.dict()
                all_results.append(current_email_result)
                time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS)
                continue # Skip to next email
            
            current_email_result["mega_agent_output"] = mega_agent_result.dict()
            current_email_result["final_response_text"] = f"Subject: {mega_agent_result.composed_subject}\n\n{mega_agent_result.composed_greeting}\n\n{mega_agent_result.composed_body}\n\n{mega_agent_result.composed_signature}"

            # Step 4: Apply Inventory Updates is now part of the Mega Agent via update_stock_tool
            # if mega_agent_result.processed_order_items and inventory_df is not None: # REMOVED
            #     inventory_changes = apply_simplified_inventory_updates(mega_agent_result.processed_order_items, inventory_df) # REMOVED
            #     current_email_result["inventory_changes_applied"] = inventory_changes # REMOVED
            # elif mega_agent_result.processed_order_items and inventory_df is None: # REMOVED
            #     warn_msg = "Inventory_df is None. Cannot apply inventory updates externally (should be handled by agent tool)." # REMOVED
            #     print(f"**Warning for {email_id}:** {warn_msg}") # REMOVED
            #     current_email_result["errors"].append(warn_msg) # REMOVED

            # The agent should log tool errors (including stock update errors) in its own errors_encountered_during_processing field.
            # We can still check that here.
            if mega_agent_result and mega_agent_result.errors_encountered_during_processing:
                current_email_result["errors"].extend(mega_agent_result.errors_encountered_during_processing)
                for err in mega_agent_result.errors_encountered_during_processing:
                     processing_errors_summary.append((email_id, "Mega Agent Internal Tool Error", err))
        except Exception as e:
            err_msg = f"Critical error during processing email {email_id}: {str(e)}"
            print(f"**{err_msg}**")
            current_email_result["errors"].append(err_msg)
            processing_errors_summary.append((email_id, "Main Loop Exception", str(e)))
        
        all_results.append(current_email_result)
        print(f"--- Finished processing Email ID: {email_id} ---")
        time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS)

    print(f"\n**Simplified email processing loop finished. Processed {len(emails_to_process_df)} emails.**")

    # --- Output Generation (Adapted from hermes-poc.py) ---
    if processing_errors_summary:
        print("\n### Simplified Processing Errors Summary:")
        for err_id, stage, details in processing_errors_summary:
            print(f"- Email ID: {err_id}, Stage: {stage}, Details: {str(details)[:300]}...")
    else:
        print("\nNo critical errors logged during the simplified email processing loop.")

    # Prepare DataFrames for Excel output
    # This part needs careful construction based on what you want in each sheet from `all_results`
    email_classification_list = []
    order_status_list = []
    responses_list = [] # Unified responses

    for res in all_results:
        email_id = res['email_id']
        category = 'unknown_error_in_analysis'
        if res.get('initial_analysis') and res['initial_analysis'].get('primary_category'):
            category = res['initial_analysis']['primary_category']
        email_classification_list.append({'email ID': email_id, 'category': category})
        
        responses_list.append({'email ID': email_id, 'response': res.get('final_response_text', 'Error: No response generated')})

        if res.get('mega_agent_output') and res['mega_agent_output'].get('processed_order_items'):
            for item in res['mega_agent_output']['processed_order_items']:
                order_status_list.append({
                    'email ID': email_id, 
                    'product ID': item.get('product_id'), 
                    'original_mention': item.get('original_mention'),
                    'quantity_requested': item.get('requested_quantity'),
                    'quantity_fulfilled': item.get('fulfilled_quantity'),
                    'status': item.get('status')
                })

    df_email_classification_out = pd.DataFrame(email_classification_list)
    df_order_status_out = pd.DataFrame(order_status_list)
    df_responses_out = pd.DataFrame(responses_list)
    # We can add more sheets for inquiry answers, alternatives, upsells if needed by parsing `mega_agent_output` further.

    print(f"\n### Preparing to write outputs to Excel: `{OUTPUT_SPREADSHEET_NAME}`")
    expected_columns_map = {
        "email-classification": ['email ID', 'category'],
        "order-status": ['email ID', 'product ID', 'original_mention', 'quantity_requested', 'quantity_fulfilled', 'status'],
        "email-responses": ['email ID', 'response'] # Simplified from order/inquiry specific
    }

    try:
        with pd.ExcelWriter(OUTPUT_SPREADSHEET_NAME, engine='openpyxl') as writer:
            # Sheet 1: Email Classification
            cols_class = expected_columns_map["email-classification"]
            df_final_class = df_email_classification_out.reindex(columns=cols_class) if not df_email_classification_out.empty else pd.DataFrame(columns=cols_class)
            df_final_class.to_excel(writer, sheet_name="email-classification", index=False)
            print(f"- `email-classification` sheet: {len(df_final_class)} rows written.")

            # Sheet 2: Order Status
            cols_order = expected_columns_map["order-status"]
            df_final_order = df_order_status_out.reindex(columns=cols_order) if not df_order_status_out.empty else pd.DataFrame(columns=cols_order)
            df_final_order.to_excel(writer, sheet_name="order-status", index=False)
            print(f"- `order-status` sheet: {len(df_final_order)} rows written.")

            # Sheet 3: Email Responses
            cols_resp = expected_columns_map["email-responses"]
            df_final_resp = df_responses_out.reindex(columns=cols_resp) if not df_responses_out.empty else pd.DataFrame(columns=cols_resp)
            df_final_resp.to_excel(writer, sheet_name="email-responses", index=False)
            print(f"- `email-responses` sheet: {len(df_final_resp)} rows written.")

        print(f"\n**Successfully wrote output sheets to Excel: `{OUTPUT_SPREADSHEET_NAME}`**")
        if inventory_df is not None:
            print("\n### Final Inventory State (First 5 rows after simplified processing):")
            print(inventory_df.head())
        else:
            print("\nInventory data was not available to display final state.")
            
    except Exception as e:
        print(f"**Error writing to Excel '{OUTPUT_SPREADSHEET_NAME}':** {e}")

if __name__ == '__main__':
    # This allows the script to be run directly.
    # Ensure that any necessary setup (like environment variables for API keys) is done prior to running.
    print("Running simplified Hermes POC script...")
    main()
    print("Simplified Hermes POC script finished.")

#endregion: --- Main Processing Loop (Simplified) --- 