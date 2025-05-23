"""Main function for responding to customer inquiries."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from ...config import HermesConfig
from ...data_processing.vector_store import VectorStore
from ...model.enums import Agents, Season
from ...model.product import Product
from ...custom_types import WorkflowNodeOutput
from ...utils.errors import create_node_response
from ...utils.llm_client import get_llm_client
from ..classifier.models import SegmentType
from .models import (
    AdvisorInput,
    AdvisorOutput,
    InquiryAnswers,
)
from .prompts import get_prompt

def format_resolved_products(products: list[Product]) -> str:
    """Format resolved products into a string for LLM context.

    Args:
        products: A list of resolved Product objects

    Returns:
        A formatted string containing all product information

    """
    if not products:
        return "No resolved products available."

    formatted_products = []
    for product in products:
        # Format seasons correctly
        seasons_str = ", ".join([s if isinstance(s, str) else s.value for s in product.seasons])

        # Format product details
        product_info = (
            f"Product: {product.name}\n"
            f"ID: {product.product_id}\n"
            f"Type: {product.product_type}\n"
            f"Category: {product.category.value if hasattr(product.category, 'value') else product.category}\n"
            f"Price: ${float(product.price):.2f}\n"
            f"Availability: {product.stock} in stock\n"
            f"Seasons: {seasons_str}\n"
            f"Description: {product.description}\n"
            f"Confidence: High (Exact catalog match)\n"
        )
        formatted_products.append(product_info)

    return "\n\n".join(formatted_products)


def search_vector_store(queries: list[str], hermes_config: HermesConfig) -> str:
    """Search the vector store for products matching the queries.
    Uses the VectorStore singleton to ensure the vector store is initialized.

    Args:
        queries: A list of search terms (product names, descriptions, questions).
        hermes_config: Configuration for accessing the vector store if needed.

    Returns:
        A string containing formatted product information relevant to the queries,
        or a message indicating no products were found.

    """
    print(f"Vector store search called with queries: {queries}")

    # Get the vector store instance using the singleton
    vector_store = VectorStore(hermes_config)

    # Check if vector store is initialized
    if vector_store is None:
        print("WARNING: Vector store is not initialized! Using placeholder data.")
        return (
            "No relevant product information found in the catalog for the given queries "
            "(vector store not initialized)."
        )

    # Combine queries into a single search query (if multiple)
    search_query = ". ".join(queries) if queries else ""
    if not search_query:
        return "No specific queries provided for product search."

    # Use the vector store instance's search method
    try:
        results = vector_store.similarity_search_with_score(
            query_text=search_query, n_results=5, filter_criteria=None
        )

        # Format the results
        if not results:
            return "No relevant products found in the catalog for the given queries."

        # Format the results for the LLM
        formatted_products = []
        for metadata, score in results:
            # Extract product details from metadata
            product_name = metadata.get("name", "Unknown Product")
            product_type = metadata.get("product_type", "Unknown Type")
            product_category = metadata.get("category", "Unknown Category")
            price = metadata.get("price", "Price not available")
            stock = metadata.get("stock", "Stock unknown")
            description = metadata.get("description", "No description available")

            # Handle seasons correctly - use valid Season enum values
            seasons_str = metadata.get("seasons", "")
            if seasons_str == "All seasons":
                # Use Spring as a default valid season if "All seasons" is encountered
                seasons = "Spring, Summer, Autumn, Winter"
            else:
                seasons = seasons_str or "Spring"  # Default to Spring if empty

            # Format as a string
            product_info = (
                f"Product: {product_name}\n"
                f"Type: {product_type}\n"
                f"Category: {product_category}\n"
                f"Price: ${float(price):.2f}\n"
                f"Availability: {stock} in stock\n"
                f"Seasons: {seasons}\n"  # Now uses valid season values
                f"Description: {description}\n"
                f"Relevance Score: {score:.2f}\n"
            )
            formatted_products.append(product_info)

        return "\n\n".join(formatted_products)

    except Exception as e:
        print(f"Error in vector store search: {e}")
        return f"Error searching product catalog: {str(e)}"


@traceable(
    run_type="chain",
    name="Advisor agent Agent",
)
async def respond_to_inquiry(
    state: AdvisorInput,
    runnable_config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.ADVISOR], AdvisorOutput]:
    """Extracts and answers customer inquiries with factual information about products.
    Uses RAG techniques to retrieve relevant product information.

    Args:
        state (OverallState): The input model containing the EmailAnalysisResult from the Classifier agent.
        runnable_config (Optional[Dict[Literal['configurable'], Dict[Literal['hermes_config'],
        HermesConfig]]]): Optional config dict with key 'configurable' containing a HermesConfig instance.

    Returns:
        Dict[str, Any]: In the LangGraph workflow, returns {Agents.RESPOND_TO_INQUIRY: AdvisorOutput}
        or {"errors": Error}

    """
    try:
        # Validate the input
        if state.classifier is None or state.classifier.email_analysis is None:
            return create_node_response(
                Agents.ADVISOR, Exception("No email analysis available for inquiry response.")
            )

        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        # Extract email_id from the analysis result - safely handle different formats
        email_id = "unknown_id"

        # The email_analysis object should be available now
        email_analysis = state.classifier.email_analysis
        email_id = email_analysis.email_id

        print(f"Generating factual answers for inquiry {email_id}")

        # --- RAG Step: Query Extraction and Vector Search ---
        search_queries: list[str] = []
        if email_analysis.segments:
            for segment in email_analysis.segments:
                if segment.segment_type == SegmentType.INQUIRY:
                    if segment.main_sentence:
                        search_queries.append(segment.main_sentence)
                    search_queries.extend(segment.related_sentences)

                # Add product mentions from all segments as search terms
                for p_mention in segment.product_mentions:
                    query_parts = []
                    if p_mention.product_name:
                        query_parts.append(p_mention.product_name)
                    if p_mention.product_type:
                        query_parts.append(p_mention.product_type)
                    if p_mention.product_description:
                        query_parts.append(p_mention.product_description)
                    if p_mention.product_category:
                        query_parts.append(p_mention.product_category.value)  # Assuming category is an Enum

                    if query_parts:
                        search_queries.append(" ".join(query_parts))

        # Deduplicate queries
        unique_search_queries = sorted(list(set(q for q in search_queries if q)))

        print(f"  Extracted search queries: {unique_search_queries}")

        # Format resolved products from the product resolver if available
        resolved_products_context = ""
        if state.stockkeeper and state.stockkeeper.resolved_products:
            resolved_products_context = format_resolved_products(state.stockkeeper.resolved_products)
            print(f"  Using {len(state.stockkeeper.resolved_products)} resolved products")

        # Perform vector search for additional context
        retrieved_products_context = search_vector_store(unique_search_queries, hermes_config)
        print(f"  Retrieved additional products context (length: {len(retrieved_products_context)} chars)")

        # Combine both sources of product information
        product_context = ""
        if resolved_products_context:
            product_context += "### EXACTLY MATCHED PRODUCTS (High Confidence):\n" + resolved_products_context + "\n\n"
        if retrieved_products_context:
            product_context += "### SIMILAR PRODUCTS (Vector Search Results):\n" + retrieved_products_context

        # If no product context, provide a note
        if not product_context:
            product_context = "No specific product information available for this inquiry."
        # --- End RAG Step ---

        # Use a strong model for factual accuracy
        llm = get_llm_client(config=hermes_config, model_strength="strong", temperature=0.1)

        # Create the prompt and chain
        advisor_prompt = get_prompt(Agents.ADVISOR)

        # Add instructions to use valid Season enum values
        season_instruction = (
            "IMPORTANT: When specifying product seasons, only use the values: "
            "Spring, Summer, Autumn, Winter. Do not use 'All seasons'."
        )
        advisor_prompt = advisor_prompt.partial(seasons_instruction=season_instruction)

        inquiry_response_chain = advisor_prompt | llm.with_structured_output(InquiryAnswers)

        try:
            # Prepare input data - convert Pydantic model to dict if necessary
            email_analysis_data = (
                email_analysis.model_dump() if hasattr(email_analysis, "model_dump") else email_analysis
            )

            # Generate the inquiry response, now including combined product context
            response_data = await inquiry_response_chain.ainvoke(
                {
                    "email_analysis": email_analysis_data,
                    "retrieved_products_context": product_context,
                    "seasons_instruction": season_instruction,
                }
            )

            # Ensure we get the right type by instantiating from the response
            if isinstance(response_data, InquiryAnswers):
                inquiry_response = response_data
            # If we got a dict, convert it to InquiryAnswers
            elif isinstance(response_data, dict):
                # Make sure email_id is included
                response_data["email_id"] = email_id

                # Make sure products have valid seasons values
                response_data = fix_seasons_in_response(response_data)

                inquiry_response = InquiryAnswers(**response_data)
            else:
                # Fallback if we got something unexpected
                inquiry_response = InquiryAnswers(
                    email_id=email_id,
                    primary_products=[],
                    answered_questions=[],
                    unanswered_questions=["Unable to process inquiry due to unexpected response type."],
                    related_products=[],
                    unsuccessful_references=[],
                )

            # Make sure email_id is set correctly in the response
            inquiry_response.email_id = email_id

            # Log the results
            print(f"  Response generated for {email_id}")
            print(f"  Answered {len(inquiry_response.answered_questions)} questions")
            print(f"  Identified {len(inquiry_response.primary_products)} primary products")
            print(f"  Suggested {len(inquiry_response.related_products)} related products")

            return create_node_response(Agents.ADVISOR, AdvisorOutput(inquiry_answers=inquiry_response))

        except Exception as e:
            print(f"Error generating inquiry response for {email_id}: {e}")

            # Create a factual fallback response without customer-facing language
            fallback_response = InquiryAnswers(
                email_id=email_id,
                primary_products=[],
                answered_questions=[],
                unanswered_questions=["Unable to process inquiry due to system error."],
                related_products=[],
                unsuccessful_references=[],
            )

            return create_node_response(Agents.ADVISOR, AdvisorOutput(inquiry_answers=fallback_response))

    except Exception as e:
        # Return errors in the format expected by LangGraph
        return create_node_response(Agents.ADVISOR, e)


def fix_seasons_in_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """Fix invalid seasons values in response data.
    This ensures that all seasons in product objects are using valid Season enum values.

    Args:
        response_data: The response data dictionary

    Returns:
        The response data with fixed seasons values

    """

    # Helper function to fix seasons in a product object
    def fix_product_seasons(product: dict[str, Any]) -> dict[str, Any]:
        if "product" in product and "seasons" in product["product"]:
            seasons = product["product"]["seasons"]

            if isinstance(seasons, list):
                fixed_seasons = []
                for season in seasons:
                    if season in [s.value for s in Season]:
                        fixed_seasons.append(season)
                    elif season.lower() == "all seasons":
                        # Include all seasons
                        fixed_seasons = [s.value for s in Season]
                        break
                    else:
                        # Default to Spring
                        fixed_seasons.append("Spring")

                if not fixed_seasons:
                    fixed_seasons = ["Spring"]  # Default if list is empty

                product["product"]["seasons"] = fixed_seasons
        return product

    # Fix primary_products
    if "primary_products" in response_data and response_data["primary_products"]:
        response_data["primary_products"] = [
            fix_product_seasons(prod) for prod in response_data["primary_products"]
        ]

    # Fix related_products
    if "related_products" in response_data and response_data["related_products"]:
        response_data["related_products"] = [
            fix_product_seasons(prod) for prod in response_data["related_products"]
        ]

    return response_data
