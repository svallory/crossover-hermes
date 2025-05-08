""" {cell}
## Inquiry Responder Agent

This agent handles emails classified as product inquiries. It performs the following key tasks:
1. Resolve product references to specific catalog items
2. Use RAG (Retrieval-Augmented Generation) to find relevant product information
3. Extract and answer customer questions about products
4. Identify related products that might interest the customer
5. Generate comprehensive inquiry response data

The Inquiry Responder leverages vector search to handle inquiries even for large
product catalogs, ensuring accurate and helpful answers to customer questions.
"""
import json
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
import pandas as pd

# Import the new LLM client utility
from ..llm_client import get_llm_client

# Import the product catalog tools
from ..tools.catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    search_products_by_description,
    find_related_products,
    Product,
    ProductNotFound
)

# Import relevant tools
from ..tools.response_tools import extract_questions

# Import order tools
from ..tools.order_tools import extract_promotion, PromotionDetails

# Define the Pydantic models for this agent's outputs
class ProductInformation(BaseModel):
    """Detailed product information relevant to a customer inquiry."""
    product_id: str = Field(description="Product ID")
    product_name: str = Field(description="Product name")
    details: Dict[str, Any] = Field(description="Key product details relevant to the inquiry")
    availability: str = Field(description="Availability status")
    price: Optional[float] = Field(default=None, description="Product price")
    promotions: Optional[str] = Field(default=None, description="Any promotions for this product")

class QuestionAnswer(BaseModel):
    """A customer's question paired with its answer from product information."""
    question: str = Field(description="The customer's question")
    question_excerpt: Optional[str] = Field(default=None, description="Text from the email containing this question")
    answer: str = Field(description="The answer based on product information")
    confidence: float = Field(description="Confidence in the answer (0.0-1.0)")
    relevant_product_ids: List[str] = Field(default_factory=list, description="Product IDs relevant to this answer")

class InquiryResponse(BaseModel):
    """Complete response to a product inquiry."""
    email_id: str = Field(description="Email ID")
    primary_products: List[ProductInformation] = Field(default_factory=list, description="Main products inquired about")
    answered_questions: List[QuestionAnswer] = Field(default_factory=list, description="Questions answered with information")
    related_products: List[ProductInformation] = Field(default_factory=list, description="Related or complementary products")
    response_points: List[str] = Field(description="Key points to include in response")
    unanswered_questions: List[str] = Field(default_factory=list, description="Questions that couldn't be answered")
    unsuccessful_references: List[str] = Field(default_factory=list, description="Product references that couldn't be resolved")

async def process_inquiry_node(state, config=None) -> Dict[str, Any]:
    """
    Process product inquiries, answering customer questions about products.
    
    Args:
        state: Current state from the agent workflow
        config: Configuration dictionary
    
    Returns:
        Updated state with inquiry processing results
    """
    # Extract email details
    if hasattr(state, 'get'):  # It's a dict
        email_id = state.get("email_id", "unknown")
        email_body = state.get("email_body", "")
        email_subject = state.get("email_subject", "")
        email_analysis = state.get("email_analysis", {})
    else:  # It's a state object
        email_id = state.email_id if hasattr(state, 'email_id') else "unknown"
        email_body = state.email_body if hasattr(state, 'email_body') else ""
        email_subject = state.email_subject if hasattr(state, 'email_subject') else ""
        email_analysis = state.email_analysis if hasattr(state, 'email_analysis') else {}
    
    # Ensure configuration exists
    if config and "configurable" in config and "hermes_config" in config["configurable"]:
        hermes_config = config["configurable"]["hermes_config"]
    else:
        from ..config import HermesConfig
        hermes_config = HermesConfig()
    
    # Get LLM client
    llm = get_llm_client(
        config=hermes_config,
        temperature=hermes_config.llm_response_temperature  # Use a valid attribute
    )
    
    # Debug print to understand what's happening
    print(f"Email classification type: {type(email_analysis)}")
    if isinstance(email_analysis, dict):
        print(f"Email classification: {email_analysis.get('classification', 'not found')}")
    else:
        print(f"Email classification: {getattr(email_analysis, 'classification', 'not found')}")
    
    # Verify this is a product inquiry
    if isinstance(email_analysis, dict) and email_analysis.get("classification") != "product_inquiry":
        print(f"Email {email_id} is not classified as a product inquiry. Skipping inquiry processing.")
        # Return a minimal result to keep the workflow going
        empty_result = InquiryResponse(
            email_id=email_id,
            primary_products=[],
            response_points=["This email is not a product inquiry."]
        )
        return {"inquiry_result": empty_result.model_dump()}
    elif not isinstance(email_analysis, dict) and getattr(email_analysis, "classification", "") != "product_inquiry":
        print(f"Email {email_id} is not classified as a product inquiry. Skipping inquiry processing.")
        # Return a minimal result to keep the workflow going
        empty_result = InquiryResponse(
            email_id=email_id,
            primary_products=[],
            response_points=["This email is not a product inquiry."]
        )
        return {"inquiry_result": empty_result.model_dump()}
    
    # Log processing start
    print(f"Processing inquiry for email {email_id}")
    
    # Load resources from state
    if hasattr(state, "product_catalog_df"):
        product_catalog_df = state.product_catalog_df
    elif isinstance(state, dict) and "product_catalog_df" in state:
        product_catalog_df = state["product_catalog_df"]
    else:
        product_catalog_df = None
        
    if hasattr(state, "vector_store"):
        vector_store = state.vector_store
    elif isinstance(state, dict) and "vector_store" in state:
        vector_store = state["vector_store"]
    else:
        vector_store = None

    # Validate resources
    if product_catalog_df is None:
        print(f"Error: Product catalog missing for email {email_id}")
        return {"error": "Missing product catalog data.", "inquiry_result": None}
    if vector_store is None:
         print(f"Warning: Vector store missing for email {email_id}. Semantic search disabled.")
         # Proceed without vector store, but semantic search features will be limited.

    # 1. Extract product references from the email analysis
    product_references_list = []
    if isinstance(email_analysis, dict):
        product_references_list = email_analysis.get("product_references", [])
    else:
        product_references_list = getattr(email_analysis, "product_references", [])
    
    # 2. Extract questions from the email
    try:
        # Try to extract questions using the langchain tool
        questions = extract_questions.invoke(input={"text_to_analyze": email_body})
    except Exception as e:
        print(f"Warning: Failed to extract questions: {e}")
        # If we're in a test scenario, we'll use an empty list
        questions = []
    
    # 3. Process primary products
    primary_products = []
    unsuccessful_references = []
    
    for ref_data in product_references_list:
        # Ensure ref_data is a dictionary before passing to resolve_product_reference
        # which now expects a dict
        if isinstance(ref_data, dict):
            ref_dict = ref_data
        elif hasattr(ref_data, 'model_dump'): # If it's a Pydantic model
            ref_dict = ref_data.model_dump()
        else: # Skip if it's neither
            # processing_notes.append(f"Skipping invalid product reference format: {type(ref_data)}")
            continue # Silently skip invalid refs for now
            
        # Pass the dictionary and resources to resolve_product_reference
        product_info = await resolve_product_reference(ref_dict, product_catalog_df, vector_store, llm)
        
        if isinstance(product_info, ProductNotFound):
            # Track unsuccessful references for later reporting
            unsuccessful_references.append(ref_dict.get('reference_text', 'Unknown reference'))
            continue
        
        # Check availability
        stock_amount = product_info.details.get("stock_amount", 0) if hasattr(product_info, "details") else 0
        availability = "In stock" if stock_amount > 0 else "Out of stock"
        
        # Collect key details
        details = {
            "category": product_info.details.get("category", "Unknown"),
            "description": product_info.details.get("description", "No description available."),
            "stock_amount": product_info.details.get("stock_amount", 0)
        }
        
        # Add optional fields if present
        if hasattr(product_info, "season") and product_info.season:
            details["season"] = product_info.season
        
        # Extract promotions
        promotion_result_dict = extract_promotion.invoke(
            input={
                "product_description": product_info.details.get("description", ""),
                "product_name": product_info.product_name
            }
        )
        # Assuming extract_promotion returns a dict for PromotionDetails
        if isinstance(promotion_result_dict, dict):
            promotion_result = PromotionDetails(**promotion_result_dict) # If PromotionDetails is the pydantic model
        else: # Assuming it's already a PromotionDetails instance
            promotion_result = promotion_result_dict
        
        promotions = promotion_result.promotion_text if promotion_result.has_promotion else None
        
        # Create ProductInformation object
        primary_product = ProductInformation(
            product_id=product_info.product_id,
            product_name=product_info.product_name,
            details=details,
            availability=availability,
            price=product_info.price if hasattr(product_info, "price") else None,
            promotions=promotions
        )
        
        primary_products.append(primary_product)
    
    # 4. Answer customer questions
    answered_questions = []
    unanswered_questions = []
    
    for question_obj in questions:
        question = question_obj.question_text
        
        # Try to answer the question using available product information and RAG
        answer = await answer_product_question(
            question=question,
            primary_products=primary_products,
            product_catalog_df=product_catalog_df,
            vector_store=vector_store,
            llm=llm
        )
        
        if answer and answer.get("is_answered"):
            # Add to answered questions
            answered_questions.append(QuestionAnswer(
                question=question,
                question_excerpt=question_obj.original_excerpt if hasattr(question_obj, "original_excerpt") else None,
                answer=answer.get("answer_text", ""),
                confidence=answer.get("confidence", 0.7),
                relevant_product_ids=answer.get("product_ids", [])
            ))
        else:
            # Add to unanswered questions
            unanswered_questions.append(question)
    
    # 5. Find related products
    related_products = []
    
    # Only suggest related products if we have primary products
    if primary_products:
        # Use the first primary product as the source for related products
        first_product = primary_products[0]
        
        try:
            # Find complementary products
            related_results_data = find_related_products.invoke(
                input={
                    "product_id": first_product.product_id,
                    "product_catalog_df": product_catalog_df,
                    "relationship_type": "complementary"
                }
            )
            
            # Assuming find_related_products returns a list of Product-like dicts or Product objects
            # The tool's own schema would define this.
            processed_related_results = []
            if isinstance(related_results_data, list):
                for item_data in related_results_data:
                    if isinstance(item_data, dict):
                        try:
                            # Convert dict to Product, then to ProductInformation
                            # This assumes Product model has all necessary fields from item_data
                            related_product_obj = Product(**item_data)
                            # You might need to define how to get availability and other details for ProductInformation
                            stock_amount = related_product_obj.details.get("stock_amount", 0) if hasattr(related_product_obj, "details") else 0
                            availability = "In stock" if stock_amount > 0 else "Out of stock"
                            details = {
                                "category": related_product_obj.details.get("category", "Unknown"),
                                "description": related_product_obj.details.get("description", "No description available."),
                                "stock_amount": related_product_obj.details.get("stock_amount", 0)
                            }
                            # Add promotions for related products too if needed
                            promo_dict_related = extract_promotion.invoke(
                                input={"product_description": related_product_obj.details.get("description", ""), "product_name": related_product_obj.product_name}
                            )
                            related_promo = PromotionDetails(**promo_dict_related) if isinstance(promo_dict_related, dict) else promo_dict_related
                            promos_text_related = related_promo.promotion_text if related_promo.has_promotion else None

                            processed_related_results.append(ProductInformation(
                                product_id=related_product_obj.product_id,
                                product_name=related_product_obj.product_name,
                                details=details,
                                availability=availability,
                                price=related_product_obj.price if hasattr(related_product_obj, "price") else None,
                                promotions=promos_text_related
                            ))
                        except Exception as e:
                            # Log any errors with processing
                            print(f"Error processing related product: {e}")
                    elif isinstance(item_data, Product):
                        # Convert Product to ProductInformation
                        stock_amount = item_data.details.get("stock_amount", 0) if hasattr(item_data, "details") else 0
                        availability = "In stock" if stock_amount > 0 else "Out of stock"
                        details = {
                            "category": item_data.details.get("category", "Unknown"),
                            "description": item_data.details.get("description", "No description available."),
                            "stock_amount": item_data.details.get("stock_amount", 0)
                        }
                        promo_dict_related = extract_promotion.invoke(
                            input={"product_description": item_data.details.get("description", ""), "product_name": item_data.product_name}
                        )
                        related_promo = PromotionDetails(**promo_dict_related) if isinstance(promo_dict_related, dict) else promo_dict_related
                        promos_text_related = related_promo.promotion_text if related_promo.has_promotion else None
                        
                        processed_related_results.append(ProductInformation(
                            product_id=item_data.product_id,
                            product_name=item_data.product_name,
                            details=details,
                            availability=availability,
                            price=item_data.price if hasattr(item_data, "price") else None,
                            promotions=promos_text_related
                        ))
            
            related_products = processed_related_results
        except Exception as e:
            print(f"Error finding related products: {e}")
            # Continue even if related products fail
    
    # 6. Generate response points
    response_points = await generate_response_points(
        primary_products=primary_products,
        answered_questions=answered_questions,
        related_products=related_products,
        unanswered_questions=unanswered_questions,
        unsuccessful_references=unsuccessful_references,
        llm=llm
    )
    
    # 7. Create the final response
    response = InquiryResponse(
        email_id=email_id,
        primary_products=primary_products,
        answered_questions=answered_questions,
        related_products=related_products,
        response_points=response_points,
        unanswered_questions=unanswered_questions,
        unsuccessful_references=unsuccessful_references
    )
    
    # 8. Verify the result
    verified_result = await verify_inquiry_response(response, llm)
    
    # Return the updated state
    return {"inquiry_result": verified_result.model_dump()}

async def resolve_product_reference(product_ref_dict: Dict[str, Any], product_catalog_df: pd.DataFrame, vector_store: Optional[Any], llm) -> Union[Product, ProductNotFound]:
    """
    Resolve a product reference from an email to a specific product in the catalog.
    Handles product ID, name, and description-based references.
    """
    product_id = product_ref_dict.get("product_id")
    product_name = product_ref_dict.get("product_name")
    reference_text = product_ref_dict.get("reference_text", "")
    reference_type = product_ref_dict.get("reference_type", "unknown")

    # Try resolving by ID first
    if product_id:
        product = find_product_by_id.invoke(input={"product_id": product_id, "product_catalog_df": product_catalog_df})
        if not isinstance(product, ProductNotFound):
            return product

    # Try resolving by name if ID fails or not provided
    if product_name:
        product = find_product_by_name.invoke(input={"name": product_name, "product_catalog_df": product_catalog_df})
        if not isinstance(product, ProductNotFound):
            return product

    # If still not found, try semantic search on reference_text (if available and vector store exists)
    if reference_text and vector_store:
        print(f"Attempting semantic search for: '{reference_text}'")
        # Use search_products_by_description (RAG tool)
        # This tool is expected to search the vector store
        # search_results = search_products_by_description( # Original call
        #     description_query=reference_text,
        #     product_catalog_df=product_catalog_df, # This tool might use the df to enrich results
        #     vector_store=vector_store,
        #     num_results=1 # We only need the top match for resolution
        # )
        search_results_data = search_products_by_description.invoke(
            input={
                "description_query": reference_text,
                "product_catalog_df": product_catalog_df,
                "vector_store": vector_store,
                "num_results": 1
            }
        )
        
        # Assuming search_products_by_description returns a list of Product-like dicts or Product objects
        # The tool's own schema would define this. For now, let's adapt based on a common pattern.
        if isinstance(search_results_data, list) and search_results_data:
            # If it returns dicts, instantiate Product. If Product objects, use directly.
            top_match_data = search_results_data[0]
            if isinstance(top_match_data, dict):
                # Ensure all necessary fields are present before instantiation
                # This might require a helper or careful validation of top_match_data structure
                try:
                    return Product(**top_match_data) 
                except TypeError as e:
                    print(f"Error instantiating Product from search result: {e}. Data: {top_match_data}")
                    # Fall through to ProductNotFound if instantiation fails
            elif isinstance(top_match_data, Product):
                return top_match_data
        elif isinstance(search_results_data, Product): # If it directly returns a single Product
            return search_results_data

    # If all attempts fail, return ProductNotFound
    return ProductNotFound(message=f"Could not resolve product reference: {reference_text or product_name or product_id}")

async def answer_product_question(question: str, primary_products: List[ProductInformation],
                                 product_catalog_df: pd.DataFrame, vector_store: Optional[Any], llm) -> Dict[str, Any]:
    """
    Answer a customer question about products using available information and RAG.
    
    Args:
        question: The customer's question
        primary_products: List of primary products being inquired about
        product_catalog_df: The product catalog DataFrame
        vector_store: Vector store for semantic search
        llm: The language model for generating answers
        
    Returns:
        Dictionary with answer information (is_answered, answer_text, confidence, product_ids)
    """
    # 1. First try to answer using the primary products
    if primary_products:
        # Construct product context
        products_context = ""
        for product in primary_products:
            products_context += f"Product ID: {product.product_id}\n"
            products_context += f"Name: {product.product_name}\n"
            products_context += f"Availability: {product.availability}\n"
            if product.price is not None:
                products_context += f"Price: ${product.price}\n"
            if product.promotions:
                products_context += f"Promotion: {product.promotions}\n"
            
            # Add details
            for key, value in product.details.items():
                if key != "description":  # Skip full description for brevity
                    products_context += f"{key.capitalize()}: {value}\n"
            
            # Add description at the end
            if "description" in product.details:
                products_context += f"Description: {product.details['description']}\n"
            
            products_context += "\n"
        
        # Create prompt for answering with primary products
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
            You are a helpful product specialist. Given product information and a customer question,
            provide an accurate, concise answer based only on the product information provided.
            If you cannot answer the question with the available information, say so clearly.
            """),
            HumanMessage(content=f"""
            Product Information:
            {products_context}
            
            Customer Question: {question}
            
            Answer the customer's question based only on the product information provided above.
            If you can answer the question, say 'Answer: [your answer]'.
            If you can't answer with the available information, say 'Unable to answer with available information'.
            """)
        ])
        
        # Try to get answer
        response = await (prompt | llm | StrOutputParser()).ainvoke({})
        
        if response and "Answer:" in response and "Unable to answer" not in response:
            # Extract the answer part
            answer_text = response.split("Answer:", 1)[1].strip()
            
            # Collect product IDs that were used
            product_ids = [product.product_id for product in primary_products]
            
            return {
                "is_answered": True,
                "answer_text": answer_text,
                "confidence": 0.9,  # High confidence since we're using primary products
                "product_ids": product_ids
            }
    
    # 2. If not answered with primary products, try RAG to find additional information
    # Perform semantic search
    semantic_results = search_products_by_description.invoke(
        input={
            "query": question,
            "vector_store": vector_store,
            "product_catalog_df": product_catalog_df,
            "top_k": 3  # Get top 3 results for more context
        }
    )
    
    if isinstance(semantic_results, list) and semantic_results:
        # Construct product context from semantic search results
        rag_context = ""
        product_ids = []
        
        for product in semantic_results:
            rag_context += f"Product ID: {product.product_id}\n"
            rag_context += f"Name: {product.product_name}\n"
            rag_context += f"Category: {product.details.get('category', 'Unknown')}\n"
            rag_context += f"Stock: {product.details.get('stock_amount', 0)}\n"
            if product.price:
                rag_context += f"Price: ${product.price}\n"
            rag_context += f"Description: {product.details.get('description', 'No description available')}\n\n"
            
            product_ids.append(product.product_id)
        
        # Create prompt for answering with RAG results
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
            You are a helpful product specialist. Given product information and a customer question,
            provide an accurate, concise answer based only on the product information provided.
            If you cannot answer the question with the available information, say so clearly.
            """),
            HumanMessage(content=f"""
            Product Information from Catalog:
            {rag_context}
            
            Customer Question: {question}
            
            Answer the customer's question based only on the product information provided above.
            If you can answer the question, say 'Answer: [your answer]'.
            If you can't answer with the available information, say 'Unable to answer with available information'.
            """)
        ])
        
        # Try to get answer
        response = await (prompt | llm | StrOutputParser()).ainvoke({})
        
        if response and "Answer:" in response and "Unable to answer" not in response:
            # Extract the answer part
            answer_text = response.split("Answer:", 1)[1].strip()
            
            return {
                "is_answered": True,
                "answer_text": answer_text,
                "confidence": 0.8,  # Good confidence but not as high as primary products
                "product_ids": product_ids
            }
    
    # 3. If we still can't answer, return not answered
    return {
        "is_answered": False,
        "answer_text": "",
        "confidence": 0.0,
        "product_ids": []
    }

async def generate_response_points(primary_products: List[ProductInformation],
                                 answered_questions: List[QuestionAnswer],
                                 related_products: List[ProductInformation],
                                 unanswered_questions: List[str],
                                 unsuccessful_references: List[str],
                                 llm) -> List[str]:
    """
    Generate key points to include in the customer response.
    
    Args:
        primary_products: List of primary products being inquired about
        answered_questions: List of questions with answers
        related_products: List of related products to suggest
        unanswered_questions: List of questions that couldn't be answered
        unsuccessful_references: List of product references that couldn't be resolved
        llm: The language model for generating response points
        
    Returns:
        List of response points to include
    """
    # Initialize response points
    response_points = []
    
    # Add points about primary products
    for product in primary_products:
        # Basic product information
        response_points.append(f"Provide information about {product.product_name} (ID: {product.product_id})")
        
        # Availability information
        response_points.append(f"Mention that {product.product_name} is {product.availability.lower()}")
        
        # Price information if available
        if product.price is not None:
            response_points.append(f"Include the price of {product.product_name}: ${product.price}")
        
        # Promotion information if available
        if product.promotions:
            response_points.append(f"Highlight the promotion for {product.product_name}: {product.promotions}")
    
    # Add points for answered questions
    for qa in answered_questions:
        response_points.append(f"Answer the question: '{qa.question}' with: '{qa.answer}'")
    
    # Add points for related products
    if related_products:
        related_names = [p.product_name for p in related_products]
        response_points.append(f"Suggest related products: {', '.join(related_names)}")
        
        # Add availability and price for related products
        for product in related_products:
            price_info = f" at ${product.price}" if product.price is not None else ""
            response_points.append(f"Mention that {product.product_name} is {product.availability.lower()}{price_info}")
    
    # Add points for unanswered questions
    if unanswered_questions:
        response_points.append("Acknowledge questions that couldn't be answered with available information")
        for question in unanswered_questions:
            response_points.append(f"Apologize for not being able to answer: '{question}'")
    
    # Add points for unsuccessful references
    if unsuccessful_references:
        response_points.append("Address products that couldn't be found in our catalog")
        for ref in unsuccessful_references:
            response_points.append(f"Apologize for not having information about: '{ref}'")
    
    # Add a general point about contacting for more information
    response_points.append("Invite customer to contact for additional information or clarification")
    
    return response_points

async def verify_inquiry_response(result: InquiryResponse, llm) -> InquiryResponse:
    """
    Verify inquiry response for completeness and correctness.
    
    Args:
        result: The InquiryResponse to verify
        llm: The language model to use for verification
        
    Returns:
        Verified (and potentially corrected) InquiryResponse
    """
    # Basic validation
    validation_errors = []
    
    # Check required fields
    if not result.email_id:
        validation_errors.append("Missing email_id")
    
    # Check that we have at least some content to respond with
    if not result.primary_products and not result.answered_questions and not result.related_products:
        if "This email is not a product inquiry" not in result.response_points:
            # Add a generic response point if we have nothing to say
            result.response_points.append("Acknowledge receipt of the inquiry and offer general assistance")
    
    # Make sure we have response points
    if not result.response_points:
        validation_errors.append("No response points generated")
        # Add a fallback response point
        result.response_points = ["Acknowledge receipt of the inquiry and offer general assistance"]
    
    # More complex validation would go here if needed
    
    # If there are serious structural issues, we would use the LLM to fix them,
    # similar to the approach in the email analyzer verification.
    
    return result

def search_vector_store(query: str, vector_store, num_results: int = 3, filter_dict: Optional[Dict[str, Any]] = None):
    """
    Search the vector store for similar products based on a query.
    This is primarily used to be mocked during testing.
    
    Args:
        query: The search query
        vector_store: The vector database to search
        num_results: Number of results to return
        filter_dict: Optional filters to apply to the search
        
    Returns:
        List of search results
    """
    if vector_store is None:
        # Return empty results for testing purposes
        return []
    
    # In a real implementation, this would call the vector store search
    results = vector_store.similarity_search(
        query=query,
        k=num_results,
        filter=filter_dict
    )
    
    return results

def create_structured_output_chain(prompt, llm, output_schema):
    """
    Helper function to create a structured output chain using LangChain components.
    This is used for generating structured outputs from LLM calls.
    
    This function exists primarily to be mocked during testing.
    
    Args:
        prompt: The prompt template to use
        llm: The language model to use
        output_schema: The Pydantic schema for the output
        
    Returns:
        A callable chain that produces structured output
    """
    from langchain_core.output_parsers import PydanticOutputParser
    output_parser = PydanticOutputParser(pydantic_object=output_schema)
    return prompt | llm | output_parser
""" {cell}
### Inquiry Responder Agent Implementation Notes

The Inquiry Responder Agent provides comprehensive information in response to customer product inquiries:

1. **RAG Architecture**:
   - This agent implements a classic Retrieval-Augmented Generation (RAG) pattern for product inquiries
   - Uses both structured lookups (by ID, name) and semantic search for more abstract references
   - Vector search makes the system scalable to large product catalogs (100,000+ products)

2. **Multi-Step Resolution Process**:
   - First attempts to resolve explicit product references from the email
   - Then extracts questions and uses available product details to answer them
   - Falls back to semantic search when specific product context is insufficient
   - Finally suggests related or complementary products to enhance the customer experience

3. **Question Answering**:
   - The `answer_product_question` function implements a two-stage approach:
     - First tries to answer using primary products identified in the email
     - Then tries semantic search when needed to find additional information
   - Each answer includes confidence levels and source product IDs for transparency

4. **Response Planning**:
   - Generates structured `response_points` that will guide the Response Composer
   - Handles edge cases like unanswerable questions and unidentifiable products
   - Ensures the customer receives a complete response even with partial information

5. **Verification Logic**:
   - The `verify_inquiry_response` function ensures a valid, actionable response
   - Adds fallbacks for edge cases where little product information was found

This agent balances depth of product information with natural question answering, ensuring customers receive helpful responses regardless of how they phrase their inquiries.
""" 