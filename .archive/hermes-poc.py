"""
In the notebook, we have to clone the source repository:
!git clone https://github.com/svallory/crossover-hermes.git hermes
%cd hermes
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
from langgraph.graph import StateGraph, END
from pinecone import Pinecone as PineconeClient, ServerlessSpec

#region: Environment Variables / Notebook Parameters

# --- OpenAI Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<OPENAI API KEY: Use one provided by Crossover or your own>")
OPENAI_BASE_URL = 'https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/'
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Pinecone Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "<YOUR PINECONE API KEY>")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "<YOUR PINECONE ENVIRONMENT>")
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
AGENTS = {
    "categorizer": "01-classification-signal-extraction-agent.md",
    "inventory_manager": "02-product-matcher-agent.md", 
    "fulfiller": "03-order-processing-agent.md",
    "representative": "04-inquiry-processing-agent.md",
    "composer": "05-response-composer-agent.md"
}

# --- Other Constants ---
MAX_RETRIES_LLM = 3

#endregion: Environment Variables / Notebook Parameters

#region: --- Client Initializations ---
chat_model = None
embedding_model = None
pinecone_index = None

if OPENAI_API_KEY != "<OPENAI API KEY: Use one provided by Crossover or your own>":
    try:
        chat_model = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.2,
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

#region: --- Data Loading ---
def convert_gsheet_to_data_frame(document_id, sheet_name):
    """Reads a sheet from a Google Spreadsheet into a pandas DataFrame."""
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
with open(os.path.join(DOCS_DIR, SALES_GUIDE_FILENAME), 'r') as f:
    sales_guide_content = f.read()

def load_prompt_template(prompt_filename, dynamic_values=None):
    """Loads a prompt template from a file and injects dynamic values and included files."""
    global sales_guide_content
    with open(os.path.join(PROMPTS_DIR, prompt_filename), 'r') as f:
        template = f.read()
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
#endregion: --- Data Loading ---


#region: --- Pydantic Models for Structured LLM Outputs ---
class LLMError(BaseModel):
    error: str
    raw_content: Optional[str] = None

class SignalDetail(BaseModel):
    product_identification: List[str] = Field(default_factory=list, description="List of product IDs or specific names mentioned.")
    customer_sentiment: Optional[str] = Field(default=None)
    key_phrases_or_questions: List[str] = Field(default_factory=list)

class ClassificationAgentOutput(BaseModel):
    category: str 
    confidence: float
    signals: SignalDetail
    reasoning: Optional[str] = None

class ProductItemDetail(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    original_mention: str
    quantity: Optional[int] = 1
    questions: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    match_method: Optional[str] = None

class UnmatchedMentionDetail(BaseModel):
    original_mention: str
    reason_for_no_match: Optional[str] = None

class ProductMatcherAgentOutput(BaseModel):
    order_items: List[ProductItemDetail] = Field(default_factory=list)
    inquiry_items: List[ProductItemDetail] = Field(default_factory=list)
    unmatched_mentions: List[UnmatchedMentionDetail] = Field(default_factory=list)

class ProcessedOrderItem(BaseModel):
    product_id: str
    original_mention: str
    requested_quantity: int
    fulfilled_quantity: int
    status: str 
    reason: Optional[str] = None
    suggested_alternative_ids: List[str] = Field(default_factory=list)

class OrderProcessingAgentOutput(BaseModel):
    processed_items: List[ProcessedOrderItem] = Field(default_factory=list)

class InquiryResponseItem(BaseModel):
    original_mention: str
    product_id_inquired: Optional[str] = None
    response_text: str

class AlternativeSuggestionItem(BaseModel):
    original_mention_or_unfulfilled_item: str
    suggested_product_id: str
    suggested_product_name: str
    reason_for_suggestion: str

class UpsellOpportunityItem(BaseModel):
    related_to_mention_or_product_id: Optional[str] = None
    upsell_product_id: str
    upsell_product_name: str
    reason_for_upsell: str

class InquiryProcessingAgentOutput(BaseModel):
    inquiry_responses: List[InquiryResponseItem] = Field(default_factory=list)
    alternative_suggestions: List[AlternativeSuggestionItem] = Field(default_factory=list)
    upsell_opportunities: List[UpsellOpportunityItem] = Field(default_factory=list)

class ComposedEmailOutput(BaseModel):
    subject: str
    greeting: str
    body: str
    signature: str
#endregion: --- Pydantic Models for Structured LLM Outputs ---

#region: --- LangChain & LLM Helper ---
def call_llm_with_structured_output(
    prompt_content: str,
    pydantic_schema: Optional[type(BaseModel)] = None,
    temperature: float = 0.2
):
    if not chat_model:
        print("**Error:** LangChain ChatModel (chat_model) is not initialized.")
        return LLMError(error="ChatModel not initialized") if pydantic_schema else None

    prompt_template = ChatPromptTemplate.from_messages([("user", prompt_content)])
    
    current_model_for_call = chat_model
    if temperature != chat_model.temperature:
        try:
            current_model_for_call = ChatOpenAI(
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                temperature=temperature,
                max_retries=MAX_RETRIES_LLM
            )
        except Exception as e:
            print(f"**Error creating temporary ChatOpenAI instance for temperature {temperature}: {e}**")
            return LLMError(error=f"Failed to create temp model: {e}") if pydantic_schema else None

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
        print(f"**Error calling LangChain ChatModel:** {e}")
        raw_output_details = "No raw output retrievable from LangChain exception."
        return LLMError(error=error_message, raw_content=raw_output_details) if pydantic_schema else error_message

def get_langchain_embeddings(texts_list: List[str]) -> List[List[float]]:
    if not embedding_model:
        print("**Error:** LangChain EmbeddingModel (embedding_model) is not initialized.")
        return []
    if not texts_list: return []
    try:
        texts_list_cleaned = [str(text).replace("\n", " ") for text in texts_list]
        return embedding_model.embed_documents(texts_list_cleaned)
    except Exception as e:
        print(f"**Error getting embeddings via LangChain:** {e}")
        return []

def prepare_embedding_text_for_product(product_row_dict: Dict[str, Any]) -> str:
    return (
        f"Product: {str(product_row_dict.get('name', ''))}\n"
        f"Description: {str(product_row_dict.get('description', ''))}\n"
        f"Category: {str(product_row_dict.get('category', ''))}\n"
        f"Season: {str(product_row_dict.get('season', ''))}"
    )
#endregion: --- LangChain & LLM Helper ---

#region: --- Pinecone Initialization and Helpers ---
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
            stock = int(inventory_df.loc[prod_id_str, 'stock'] if inventory_df is not None and prod_id_str in inventory_df.index else prod_dict.get('stock', 0))
            metadata = {
                "product_id": prod_id_str, "name": str(prod_dict.get('name', '')),
                "description": str(prod_dict.get('description', '')), "category": str(prod_dict.get('category', '')),
                "season": str(prod_dict.get('season', '')), "price": float(prod_dict.get('price', 0.0)),
                "stock": stock }
            vectors_to_upsert.append({"id": prod_id_str, "values": embeddings[j], "metadata": metadata})
        if vectors_to_upsert: target_index.upsert(vectors=vectors_to_upsert)
    print("Product embedding and upsertion complete.")
    
def initialize_pinecone():
    global pinecone_index
    # Access global variables needed for population check
    global products_df, embedding_model, inventory_df

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
            wait_time = 0; max_wait_time = 300
            while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                time.sleep(10); wait_time += 10
                if wait_time >= max_wait_time:
                    print("**Error:** Pinecone index did not become ready in time.")
                    return None
            print(f"Index '{PINECONE_INDEX_NAME}' created and ready.")
        else:
            pass # Index already exists
        
        current_pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        print(f"Pinecone index '{current_pinecone_index.name}' object retrieved.")

        try:
            stats = current_pinecone_index.describe_index_stats()
            # Ensure stats and total_vector_count are valid before checking
            if hasattr(stats, 'total_vector_count') and stats.total_vector_count == 0:
                print(f"Pinecone index '{current_pinecone_index.name}' is empty. Attempting to populate...")
                # Check prerequisites for population
                if products_df is not None and not products_df.empty and embedding_model is not None and inventory_df is not None:
                    print("**Starting Pinecone population process (within initialize_pinecone)...**")
                    populate_pinecone(products_df, current_pinecone_index)
                else:
                    missing_prereqs = []
                    if products_df is None or products_df.empty: missing_prereqs.append("products_df")
                    if embedding_model is None: missing_prereqs.append("embedding_model")
                    if inventory_df is None: missing_prereqs.append("inventory_df")
                    print(f"Skipping Pinecone population during initialization: Required data not ready ({', '.join(missing_prereqs)}).")
            elif hasattr(stats, 'total_vector_count'):
                print(f"Pinecone index '{current_pinecone_index.name}' already contains {stats.total_vector_count} vectors. Skipping population.")
            else:
                print(f"**Warning (Pinecone Stats):** Could not determine vector count for '{current_pinecone_index.name}'. Population status unknown.")
        except Exception as e_stats:
            print(f"**Warning (Pinecone Stats):** Could not get index stats for '{current_pinecone_index.name}': {e_stats}. Population status unknown.")
        
        # Assign to global after all operations including potential population
        pinecone_index = current_pinecone_index
        print("Pinecone initialization complete.")
        return pinecone_index
    except Exception as e:
        print(f"**Error initializing Pinecone:** {e}. Check API key, environment, and index config.")
        pinecone_index = None # Ensure global is None on failure
        return None

pinecone_index = initialize_pinecone()

def query_pinecone_for_products(query_text: str, top_k=3, index_to_query=None) -> List[Dict[str, Any]]:
    effective_index = index_to_query if index_to_query else pinecone_index
    if effective_index is None:
        print("**Warning (Query Pinecone):** Pinecone index not available. Returning no results.")
        return []
    if not query_text or not str(query_text).strip(): return []
    if not embedding_model: 
        print("**Error (Query Pinecone):** EmbeddingModel not initialized."); return []
    try:
        query_embedding = embedding_model.embed_query(str(query_text))
        if not query_embedding: raise ValueError("Embedding generation failed")
        results = effective_index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        return results.get('matches', [])
    except Exception as e:
        print(f"**Error (Query Pinecone):** Failed for query '{str(query_text)[:50]}...': {e}")
        return []
#endregion: --- Pinecone Initialization and Helpers ---


#region: --- LangGraph State Definition ---
class EmailData(TypedDict):
    email_id: str
    subject: str
    message: str

class AgentGraphState(TypedDict):
    original_email: EmailData
    classification_output: Optional[ClassificationAgentOutput]
    product_match_output: Optional[ProductMatcherAgentOutput]
    order_processing_output: Optional[OrderProcessingAgentOutput]
    inquiry_processing_output: Optional[InquiryProcessingAgentOutput]
    final_composed_response: Optional[str]
    error_messages: List[str]
#endregion: --- LangGraph State Definition ---

#region: --- LangGraph Nodes ---
def classification_signal_extraction_node(state: AgentGraphState) -> Dict[str, Any]:
    print(f"**Node 1 (Classification) processing Email ID: {state['original_email']['email_id']}**")
    email_data = state['original_email']
    prompt_filename = AGENTS["categorizer"]
    dynamic_prompt_values = {"email.email_id": email_data['email_id'], "email.subject": str(email_data['subject']), "email.message": str(email_data['message'])}
    complete_prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    if not complete_prompt_content:
        error_msg = f"Prompt load error for {prompt_filename}"; print(f"**{error_msg}**")
        return {"error_messages": state.get("error_messages", []) + [error_msg], "classification_output": None}
    llm_response = call_llm_with_structured_output(complete_prompt_content, pydantic_schema=ClassificationAgentOutput)
    if isinstance(llm_response, ClassificationAgentOutput):
        return {"classification_output": llm_response, "error_messages": state.get("error_messages", [])}
    error_msg = f"Node 1 Error: {llm_response.error if isinstance(llm_response, LLMError) else 'Malformed output'}. Raw: {getattr(llm_response, 'raw_content', str(llm_response)[:100])}"
    print(f"**{error_msg}**")
    return {"error_messages": state.get("error_messages", []) + [error_msg], "classification_output": None}

def product_matcher_node(state: AgentGraphState) -> Dict[str, Any]:
    print(f"**Node 2 (Product Matcher) for Email ID: {state['original_email']['email_id']}**")
    email_data, classification_results = state['original_email'], state.get('classification_output')
    if not (classification_results and isinstance(classification_results, ClassificationAgentOutput)):
        error_msg = "Node 2: Missing/invalid classification output."; print(f"**{error_msg}**")
        return {"error_messages": state.get("error_messages", []) + [error_msg], "product_match_output": None}
    prompt_filename = AGENTS["inventory_manager"]
    catalog_lines = ["Product_ID,Name,Category,Description (first 50 chars),Stock"]
    if not products_df.empty:
        for _, row in products_df.head(15).iterrows():
            stock = inventory_df.loc[row['product_id'], 'stock'] if inventory_df is not None and row['product_id'] in inventory_df.index else row.get('stock',0)
            catalog_lines.append(f"{row.get('product_id')},{row.get('name')},{row.get('category')},{str(row.get('description',''))[:50].replace('\n',' ')}...,{stock}")
    else: catalog_lines.append("No product catalog data available.")
    dynamic_prompt_values = {
        "classification_results": classification_results.dict(),
        "product_catalog": "\n".join(catalog_lines),
        "vector_embeddings_of_product_descriptions": "(Vector search can be used for descriptive phrases if direct matching fails.)"
    }
    complete_prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    llm_response = call_llm_with_structured_output(complete_prompt_content, pydantic_schema=ProductMatcherAgentOutput)
    if isinstance(llm_response, ProductMatcherAgentOutput):
        return {"product_match_output": llm_response, "error_messages": state.get("error_messages", [])}
    error_msg = f"Node 2 Error: {llm_response.error if isinstance(llm_response, LLMError) else 'Malformed output'}. Raw: {getattr(llm_response, 'raw_content', str(llm_response)[:100])}"
    print(f"**{error_msg}**")
    return {"error_messages": state.get("error_messages", []) + [error_msg], "product_match_output": None}

def order_processing_node(state: AgentGraphState) -> Dict[str, Any]:
    email_data, p_match_results = state['original_email'], state.get("product_match_output")
    print(f"**Node 3 (Order Processing) for Email ID: {email_data['email_id']}**")
    if not (p_match_results and isinstance(p_match_results, ProductMatcherAgentOutput) and p_match_results.order_items):
        return {"order_processing_output": OrderProcessingAgentOutput(), "error_messages": state.get("error_messages", [])}
    prompt_filename = AGENTS["fulfiller"]
    inventory_status_lines, catalog_alt_lines = ["Product_ID,Name,Current_Stock"], ["Product_ID,Name,Category,Price,Current_Stock"]
    for item in p_match_results.order_items:
        if item.product_id and inventory_df is not None and item.product_id in inventory_df.index:
            name = products_df.loc[products_df['product_id'] == item.product_id, 'name'].iloc[0] if not products_df.empty else "Unknown"
            inventory_status_lines.append(f"{item.product_id},{name},{inventory_df.loc[item.product_id, 'stock']}")
    if not products_df.empty:
        for _, row in products_df.sample(min(30, len(products_df)), random_state=42).iterrows():
            stock = inventory_df.loc[row['product_id'], 'stock'] if inventory_df is not None and row['product_id'] in inventory_df.index else 0
            catalog_alt_lines.append(f"{row.get('product_id')},{row.get('name')},{row.get('category')},{row.get('price')},{stock}")
    dynamic_prompt_values = {
        "product_matcher_results": {"order_items": [item.dict() for item in p_match_results.order_items]},
        "current_inventory_status": "\n".join(inventory_status_lines),
        "product_catalog_for_alternatives": "\n".join(catalog_alt_lines)
    }
    complete_prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    llm_response = call_llm_with_structured_output(complete_prompt_content, pydantic_schema=OrderProcessingAgentOutput)
    if isinstance(llm_response, OrderProcessingAgentOutput):
        return {"order_processing_output": llm_response, "error_messages": state.get("error_messages", [])}
    error_msg = f"Node 3 Error: {llm_response.error if isinstance(llm_response, LLMError) else 'Malformed output'}. Raw: {getattr(llm_response, 'raw_content', str(llm_response)[:100])}"
    print(f"**{error_msg}**")
    return {"error_messages": state.get("error_messages", []) + [error_msg], "order_processing_output": None}

def inquiry_processing_node(state: AgentGraphState) -> Dict[str, Any]:
    email_data = state['original_email']
    print(f"**Node 4 (Inquiry Processing) for Email ID: {email_data['email_id']}**")
    class_res, p_match_res, o_proc_res = state.get("classification_output"), state.get("product_match_output"), state.get("order_processing_output")
    
    inquiry_items = p_match_res.inquiry_items if p_match_res and isinstance(p_match_res, ProductMatcherAgentOutput) else []
    needs_oos_handling = o_proc_res and isinstance(o_proc_res, OrderProcessingAgentOutput) and any(item.status != 'created' for item in o_proc_res.processed_items)
    if not inquiry_items and not needs_oos_handling:
        return {"inquiry_processing_output": InquiryProcessingAgentOutput(), "error_messages": state.get("error_messages", [])}

    prompt_filename = AGENTS["representative"]
    rag_context_list = []
    for item in inquiry_items:
        query = item.original_mention + (" " + " ".join(item.questions) if item.questions else "")
        if query.strip() and pinecone_index:
            for match in query_pinecone_for_products(query.strip(), top_k=2, index_to_query=pinecone_index):
                md = match.get('metadata', {})
                rag_context_list.append({"query_mention_or_product": item.original_mention, "retrieved_info": f"VectorSim (Score {match.get('score',0):.2f}): ID '{match.get('id')}', Name '{md.get('name')}', Desc: {str(md.get('description',''))[:75]}..."})
        if item.product_id and not products_df.empty and item.product_id in products_df['product_id'].values:
            exact_prod = products_df.loc[products_df['product_id'] == item.product_id].iloc[0]
            rag_context_list.append({"query_mention_or_product": item.original_mention, "retrieved_info": f"Exact Match: ID '{item.product_id}', Name '{exact_prod.get('name')}': {prepare_embedding_text_for_product(exact_prod.to_dict())}"})
    
    catalog_lines = ["Product_ID,Name,Category,Price,Current_Stock"]
    if not products_df.empty:
        for _, row in products_df.sample(min(20, len(products_df)), random_state=101).iterrows():
            stock = inventory_df.loc[row['product_id'], 'stock'] if inventory_df is not None and row['product_id'] in inventory_df.index else 0
            catalog_lines.append(f"{row.get('product_id')},{row.get('name')},{row.get('category')},{row.get('price')},{stock}")

    dynamic_prompt_values = {
        "classification_results": class_res.dict() if class_res else {},
        "product_matcher_results": p_match_res.dict() if p_match_res else {},
        "order_processing_results": o_proc_res.dict() if o_proc_res else {},
        "product_catalog_with_detailed_descriptions": "\n".join(catalog_lines),
        "retrieved_rag_context": rag_context_list
    }
    complete_prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    llm_response = call_llm_with_structured_output(complete_prompt_content, pydantic_schema=InquiryProcessingAgentOutput)
    if isinstance(llm_response, InquiryProcessingAgentOutput):
        return {"inquiry_processing_output": llm_response, "error_messages": state.get("error_messages", [])}
    error_msg = f"Node 4 Error: {llm_response.error if isinstance(llm_response, LLMError) else 'Malformed output'}. Raw: {getattr(llm_response, 'raw_content', str(llm_response)[:100])}"
    print(f"**{error_msg}**")
    return {"error_messages": state.get("error_messages", []) + [error_msg], "inquiry_processing_output": None}

def response_composer_node(state: AgentGraphState) -> Dict[str, Any]:
    email_data = state['original_email']
    print(f"**Node 5 (Response Composer) for Email ID: {email_data['email_id']}**")
    prompt_filename = AGENTS["composer"]
    cr = state.get("classification_output"); pmr = state.get("product_match_output"); 
    opr = state.get("order_processing_output"); ipr = state.get("inquiry_processing_output")
    dynamic_prompt_values = {
        "email.email_id": email_data['email_id'], "email.subject": str(email_data['subject']), "email.message": str(email_data['message']),
        "classification_results": cr.dict() if isinstance(cr, ClassificationAgentOutput) else {"error": "Classification results missing"},
        "product_matcher_results": pmr.dict() if isinstance(pmr, ProductMatcherAgentOutput) else {"error": "Product matcher results missing"},
        "order_processing_results": opr.dict() if isinstance(opr, OrderProcessingAgentOutput) else {},
        "inquiry_processing_results": ipr.dict() if isinstance(ipr, InquiryProcessingAgentOutput) else {}
    }
    complete_prompt_content = load_prompt_template(prompt_filename, dynamic_prompt_values)
    llm_response = call_llm_with_structured_output(complete_prompt_content, pydantic_schema=ComposedEmailOutput, temperature=0.4)
    final_resp_str, current_errors = "Error: Composition failed.", state.get("error_messages", [])
    if isinstance(llm_response, ComposedEmailOutput):
        final_resp_str = f"Subject: {llm_response.subject}\n\n{llm_response.greeting}\n\n{llm_response.body}\n\n{llm_response.signature}"
        return {"final_composed_response": final_resp_str, "error_messages": current_errors}
    error_msg = f"Node 5 Error: {llm_response.error if isinstance(llm_response, LLMError) else 'Malformed output'}. Raw: {getattr(llm_response, 'raw_content', str(llm_response)[:100])}"
    print(f"**{error_msg}**")
    final_resp_str = f"Error composing response (Node 5): {error_msg}"
    return {"final_composed_response": final_resp_str, "error_messages": current_errors + [error_msg]}

#endregion: --- LangGraph Nodes ---

#region: --- Inventory Update Logic (called from main loop after graph) ---
def apply_inventory_updates_from_llm_decision(
    order_processing_output: Optional[OrderProcessingAgentOutput],
    live_inventory_df_ref: Optional[pd.DataFrame]
):
    if not order_processing_output or not isinstance(order_processing_output, OrderProcessingAgentOutput) or not order_processing_output.processed_items:
        return [] 
    if live_inventory_df_ref is None: print("Apply Inventory: Live inventory_df is None. Cannot apply updates."); return []
        
    actual_applied_changes = []
    for item_data in order_processing_output.processed_items:
        pid = str(item_data.product_id)
        if not pid or pid not in live_inventory_df_ref.index:
            continue
        current_stock = live_inventory_df_ref.loc[pid, 'stock']
        qty_to_deduct = 0
        if item_data.status in ['created', 'partial_fulfillment']:
            qty_to_deduct = item_data.fulfilled_quantity
        
        if qty_to_deduct > 0:
            if qty_to_deduct > current_stock:
                print(f"**Critical Warning (Apply Inventory):** For '{pid}', to fulfill {qty_to_deduct}, but only {current_stock} available. Deducting {current_stock}.")
                qty_to_deduct = current_stock
            new_stock = current_stock - qty_to_deduct
            live_inventory_df_ref.loc[pid, 'stock'] = new_stock
            actual_applied_changes.append({"product_id": pid, "qty_deducted": qty_to_deduct, "stock_before": current_stock, "stock_after": new_stock, "llm_item_status": item_data.status})
    return actual_applied_changes
#endregion: --- Inventory Update Logic (called from main loop after graph) ---

#region: --- LangGraph Workflow Definition ---
workflow = StateGraph(AgentGraphState)
workflow.add_node("classify_email", classification_signal_extraction_node)
workflow.add_node("product_matcher", product_matcher_node)
workflow.add_node("order_processor", order_processing_node)
workflow.add_node("inquiry_processor", inquiry_processing_node)
workflow.add_node("response_composer", response_composer_node)

def decide_after_classification(state: AgentGraphState) -> str:
    if state.get("error_messages") and "Node 1 (Classification)" in state["error_messages"][-1]: return "response_composer"
    output = state.get("classification_output")
    if output and isinstance(output, ClassificationAgentOutput):
        if output.category == 'order request': return "product_matcher"
        if output.category == 'product inquiry': return "product_matcher"
    return "response_composer"

def decide_after_product_matching(state: AgentGraphState) -> str:
    if state.get("error_messages") and "Node 2 (Product Matcher)" in state["error_messages"][-1]: return "response_composer"
    class_output = state.get("classification_output")
    if class_output and isinstance(class_output, ClassificationAgentOutput):
        if class_output.category == 'order request': return "order_processor"
        if class_output.category == 'product inquiry': return "inquiry_processor"
    return "response_composer"

def decide_after_order_processing(state: AgentGraphState) -> str:
    if state.get("error_messages") and "Node 3 (Order Processing)" in state["error_messages"][-1]: return "response_composer"
    p_match_out = state.get("product_match_output")
    o_proc_out = state.get("order_processing_output")
    needs_inquiry = (p_match_out and isinstance(p_match_out, ProductMatcherAgentOutput) and p_match_out.inquiry_items) or \
                    (o_proc_out and isinstance(o_proc_out, OrderProcessingAgentOutput) and any(item.status not in ['created', 'error_processing'] for item in o_proc_out.processed_items))
    return "inquiry_processor" if needs_inquiry else "response_composer"

workflow.set_entry_point("classify_email")
workflow.add_conditional_edges("classify_email", decide_after_classification, {"product_matcher": "product_matcher", "response_composer": "response_composer"})
workflow.add_conditional_edges("product_matcher", decide_after_product_matching, {"order_processor": "order_processor", "inquiry_processor": "inquiry_processor", "response_composer": "response_composer"})
workflow.add_conditional_edges("order_processor", decide_after_order_processing, {"inquiry_processor": "inquiry_processor", "response_composer": "response_composer"})
workflow.add_edge("inquiry_processor", "response_composer")
workflow.add_edge("response_composer", END)

pipeline = workflow.compile()

# --- Main Processing Loop (Using LangGraph) ---
email_classification_output_list = []
order_status_output_list = []
order_response_output_list = []
inquiry_response_output_list = []
processing_errors_summary_list = []

MAX_EMAILS_TO_PROCESS = 0
INDIVIDUAL_EMAIL_DELAY_SECONDS = 1.0

emails_for_loop_df = emails_df.copy()
if MAX_EMAILS_TO_PROCESS > 0:
    emails_for_loop_df = emails_df.head(MAX_EMAILS_TO_PROCESS)
    print(f"**Starting email processing loop for a maximum of {MAX_EMAILS_TO_PROCESS} emails.**")

for _, current_email_row in emails_for_loop_df.iterrows():
    current_email_id = str(current_email_row['email_id'])
    current_email_subject = str(current_email_row.get('subject', ''))
    current_email_body = str(current_email_row.get('message', ''))

    print(f"\n---⚙️--- Processing Email ID: {current_email_id} ---⚙️---")

    initial_state_dict: AgentGraphState = {
        "original_email": EmailData(email_id=current_email_id, subject=current_email_subject, message=current_email_body),
        "classification_output": None, "product_match_output": None, "order_processing_output": None,
        "inquiry_processing_output": None, "final_composed_response": "Error: Graph error.", "error_messages": []
    }

    final_graph_state: Optional[AgentGraphState] = None
    try:
        final_graph_state = pipeline.invoke(initial_state_dict)
    except Exception as e:
        print(f"**CRITICAL LangGraph Invoke Error for {current_email_id}: {e}**")
        final_graph_state = initial_state_dict
        final_graph_state["error_messages"] = final_graph_state.get("error_messages", []) + [f"InvokeCritical: {str(e)}"]
        final_graph_state["final_composed_response"] = f"Critical error processing email {current_email_id}."
        processing_errors_summary_list.append((current_email_id, "LangGraph Invoke Error", str(e)))
    
    current_email_main_category = 'error_in_processing'
    final_composed_response_text = "Error: Default response due to processing issues."

    if final_graph_state:
        classification_out = final_graph_state.get("classification_output")
        if classification_out and isinstance(classification_out, ClassificationAgentOutput):
            current_email_main_category = classification_out.category
            email_classification_output_list.append({'email ID': current_email_id, 'category': current_email_main_category})
        else:
            email_classification_output_list.append({'email ID': current_email_id, 'category': 'classification_error'})

        order_processing_out = final_graph_state.get("order_processing_output")
        if order_processing_out and isinstance(order_processing_out, OrderProcessingAgentOutput):
            if inventory_df is not None:
                apply_inventory_updates_from_llm_decision(order_processing_out, inventory_df)
            else:
                print(f"**Warning:** Inventory_df is None. Cannot apply updates for {current_email_id}.")
            for item_status in order_processing_out.processed_items:
                order_status_output_list.append({'email ID': current_email_id, 'product ID': str(item_status.product_id), 'quantity': item_status.requested_quantity, 'status': item_status.status})
        
        final_composed_response_text = final_graph_state.get("final_composed_response", final_composed_response_text)
        if current_email_main_category == 'order request':
            order_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})
        elif current_email_main_category == 'product inquiry':
            inquiry_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text})
        else: 
            inquiry_response_output_list.append({'email ID': current_email_id, 'response': final_composed_response_text or f"Default response for category '{current_email_main_category}'."})

        graph_errors = final_graph_state.get("error_messages", [])
        if graph_errors:
            unique_graph_errors_for_summary = set()
            for err_msg in graph_errors:
                print(f"Graph Error for {current_email_id}: {err_msg}")
                if err_msg not in unique_graph_errors_for_summary:
                    processing_errors_summary_list.append((current_email_id, "Graph Node Error", err_msg[:200]))
                    unique_graph_errors_for_summary.add(err_msg)
    else:
        print(f"**CRITICAL:** final_graph_state was None for {current_email_id}.")
        email_classification_output_list.append({'email ID': current_email_id, 'category': 'critical_failure'})
        default_err_resp = "Critical error during automated processing."
        if "order" in current_email_body.lower(): order_response_output_list.append({'email ID': current_email_id, 'response': default_err_resp})
        else: inquiry_response_output_list.append({'email ID': current_email_id, 'response': default_err_resp})
        processing_errors_summary_list.append((current_email_id, "Critical Graph Failure", "final_graph_state was None"))

    print(f"--- Finished processing Email ID: {current_email_id} ---")
    time.sleep(INDIVIDUAL_EMAIL_DELAY_SECONDS)

print(f"\n**Email processing loop finished. Processed {len(emails_for_loop_df)} emails.**")

# --- Output Generation ---
if processing_errors_summary_list:
    print("\n### Processing Errors Summary:")
    for err_id, stage, details in processing_errors_summary_list:
        print(f"- Email ID: {err_id}, Stage: {stage}, Details: {str(details)[:300]}...")
else:
    print("\nNo critical errors logged during the email processing loop.")

print(f"\n### Preparing to write outputs to Excel: `{OUTPUT_SPREADSHEET_NAME}`")
df_email_classification_out = pd.DataFrame(email_classification_output_list)
df_order_status_out = pd.DataFrame(order_status_output_list)
df_order_response_out = pd.DataFrame(order_response_output_list)
df_inquiry_response_out = pd.DataFrame(inquiry_response_output_list)

expected_columns_map = {
    "email-classification": ['email ID', 'category'],
    "order-status": ['email ID', 'product ID', 'quantity', 'status'],
    "order-response": ['email ID', 'response'],
    "inquiry-response": ['email ID', 'response']
}

try:
    with pd.ExcelWriter(OUTPUT_SPREADSHEET_NAME, engine='openpyxl') as writer:
        for sheet_name, df_out in zip(
            expected_columns_map.keys(), 
            [df_email_classification_out, df_order_status_out, df_order_response_out, df_inquiry_response_out]
        ):
            cols = expected_columns_map[sheet_name]
            if not df_out.empty:
                df_out = df_out.reindex(columns=cols)
            else:
                df_out = pd.DataFrame(columns=cols)
            df_out.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"- `{sheet_name}` sheet: {len(df_out)} rows written.")
    print(f"\n**Successfully wrote output sheets to Excel: `{OUTPUT_SPREADSHEET_NAME}`**")
    if inventory_df is not None:
        print("\n### Final Inventory State (First 5 rows):")
        print(inventory_df.head())
except Exception as e:
    print(f"**Error writing to Excel '{OUTPUT_SPREADSHEET_NAME}':** {e}")