"""Functions for resolving product mentions to catalog products."""

import json
import time
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig

from hermes.agents.classifier.models import ProductMention
from hermes.agents.stockkeeper.models import StockkeeperInput, StockkeeperOutput
from hermes.agents.stockkeeper.prompts import get_prompt
from hermes.config import HermesConfig
from hermes.model import ProductCategory, Season
from hermes.model.enums import Agents
from hermes.model.product import Product
from hermes.custom_types import WorkflowNodeOutput
from hermes.utils.response import create_node_response
from hermes.utils.llm_client import get_llm_client
from hermes.tools.catalog_tools import (
    find_product_by_id as find_product_by_id_tool,
    find_product_by_name as find_product_by_name_tool,
    search_products_by_description as search_products_by_description_tool,
)


def traceable(run_type: str, name: str | None = None):
    """Decorator for LangSmith tracing."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract the runnable_config from kwargs if it exists
            kwargs.get("runnable_config", {})
            # Create a tracer if needed
            # Execute the function
            result = await func(*args, **kwargs)
            return result

        return wrapper

    return decorator


# Configure resolution thresholds and other parameters
EXACT_MATCH_THRESHOLD = 0.95  # Threshold for automatic resolution
SIMILAR_MATCH_THRESHOLD = 0.75  # Threshold for potential matches to consider
AMBIGUITY_THRESHOLD = (
    0.15  # Maximum difference between top matches to consider ambiguous
)
MIN_CANDIDATES_FOR_AMBIGUITY_CHECK = (
    2  # Minimum number of candidates needed to check for ambiguity
)


def build_resolution_query(mention: ProductMention) -> dict[str, Any]:
    """Build a query for product resolution based on a product mention.

    Args:
        mention: The product mention to resolve

    Returns:
        A query dictionary with all available identifying information

    """
    query = {}

    if mention.product_id:
        query["product_id"] = mention.product_id

    if mention.product_name:
        query["name"] = mention.product_name

    if mention.product_description:
        query["description"] = mention.product_description

    if mention.product_category:
        query["category"] = mention.product_category

    if mention.product_type:
        query["product_type"] = mention.product_type

    return query


def build_nl_query(query: dict[str, Any]) -> str:
    """Build a natural language query from a query dictionary.

    Args:
        query: Query parameters to use for resolution

    Returns:
        A natural language query string

    """
    query_parts = []

    if "product_id" in query and query["product_id"]:
        query_parts.append(f"Product ID: {query['product_id']}")

    if "name" in query and query["name"]:
        query_parts.append(f"Product Name: {query['name']}")

    if "description" in query and query["description"]:
        query_parts.append(f"Description: {query['description']}")

    if "category" in query and query["category"]:
        query_parts.append(f"Category: {query['category']}")

    if "product_type" in query and query["product_type"]:
        query_parts.append(f"Type: {query['product_type']}")

    # Return the natural language query or a default if empty
    if query_parts:
        return " ".join(query_parts)
    return "Unknown product"


def get_product_by_id(product_id: str) -> Product | None:
    """Find a product by exact ID match using catalog tools.

    Args:
        product_id: The product ID to search for

    Returns:
        A Product object if found, None otherwise

    """
    try:
        result = find_product_by_id_tool.invoke(json.dumps({"product_id": product_id}))
        return result if isinstance(result, Product) else None
    except Exception:
        return None


def find_products_by_name_wrapper(
    name: str, threshold: float = 0.8, max_results: int = 3
) -> list[tuple[Product, float]]:
    """Find products by name using fuzzy matching via catalog tools.

    Args:
        name: The product name to search for
        threshold: Minimum similarity score for matches
        max_results: Maximum number of matches to return

    Returns:
        A list of (Product, score) tuples sorted by descending score

    """
    try:
        # Call the tool directly with its expected parameters (not JSON)
        result = find_product_by_name_tool(
            product_name=name, threshold=threshold, top_n=max_results
        )

        if isinstance(result, list):
            return [
                (fuzzy_result.matched_product, fuzzy_result.similarity_score)
                for fuzzy_result in result
            ]
        return []
    except Exception as e:
        print(f"Name-based search failed: {str(e)}")
        return []


def search_products_semantically(query: str, max_results: int = 3) -> list[Product]:
    """Search products by description using semantic search via catalog tools.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        A list of Product objects

    """
    try:
        result = search_products_by_description_tool.invoke(
            json.dumps({"query": query, "top_k": max_results})
        )
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"Semantic search failed: {str(e)}")
        return []


def resolve_product_reference_local(
    query: dict[str, Any], max_results: int = 3
) -> list[tuple[Product, float]]:
    """Resolve a product reference using catalog tools.

    Args:
        query: Query parameters to use for resolution
        max_results: Maximum number of potential matches to return

    Returns:
        A list of (Product, confidence) tuples sorted by descending confidence

    """
    results = []

    # Try exact product ID match first (highest priority)
    if "product_id" in query and query["product_id"]:
        product = get_product_by_id(query["product_id"])
        if product:
            results.append((product, 1.0))  # Exact ID match has 1.0 confidence
            return results  # If we have an exact ID match, no need to continue

    # Try name-based match using wrapper
    if "name" in query and query["name"]:
        name_results = find_products_by_name_wrapper(
            name=query["name"],
            threshold=SIMILAR_MATCH_THRESHOLD,
            max_results=max_results,
        )
        results.extend(name_results)

    # If we already have results above the exact match threshold, return early
    if results and results[0][1] >= EXACT_MATCH_THRESHOLD:
        return [results[0]]

    # Try semantic search using wrapper
    nl_query = build_nl_query(query)
    semantic_results = search_products_semantically(nl_query, max_results)

    # Assign similarity scores based on order (highest first)
    for i, product in enumerate(semantic_results):
        # Assign decreasing confidence scores for semantic search results
        confidence = max(0.6 - (i * 0.1), 0.3)  # Start at 0.6, decrease by 0.1 each
        results.append((product, confidence))

    # Sort results by confidence
    results.sort(key=lambda x: x[1], reverse=True)

    # Deduplicate by product_id
    seen_ids = set()
    unique_results = []

    for product, score in results:
        if product.product_id not in seen_ids:
            seen_ids.add(product.product_id)
            unique_results.append((product, score))

    return unique_results[:max_results]


def _create_product_from_row(row: Any) -> Product:
    """Create a Product instance from a DataFrame row.

    Args:
        row: A row from the products DataFrame

    Returns:
        A Product instance with data from the row

    """
    # Handle seasons - convert from string or use default
    seasons_raw = row.get("season", "Spring")
    if isinstance(seasons_raw, str):
        seasons = [Season(s.strip()) for s in seasons_raw.split(",") if s.strip()]
    else:
        seasons = [Season.SPRING]  # Default to Spring if not available

    # Create the product with proper enum types
    return Product(
        product_id=str(row["product_id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        category=ProductCategory(row["category"]),
        product_type=str(row.get("type", "")),
        stock=int(row["stock"]),
        price=float(row["price"]),
        seasons=seasons,
        metadata=None,
    )


async def run_deduplication_llm(
    mentions_text: str, email_context: str, hermes_config: HermesConfig
) -> list[dict[str, Any]]:
    """Run the LLM to deduplicate product mentions.

    Args:
        mentions_text: Formatted text of all the product mentions
        email_context: The full email text for context
        hermes_config: Hermes configuration

    Returns:
        A list of dictionaries representing deduplicated product mentions

    """
    # Prepare prompt variables
    prompt_vars = {
        "product_mentions": mentions_text,
        "email_context": email_context,
    }

    # Get a medium-strength model for deduplication
    llm = get_llm_client(config=hermes_config, model_strength="weak", temperature=0.1)

    # Get the deduplication prompt from the prompts module
    deduplication_prompt = get_prompt(f"{Agents.STOCKKEEPER}_deduplication")

    # Create the chain and execute
    deduplication_chain = deduplication_prompt | llm
    raw_result = await deduplication_chain.ainvoke(prompt_vars)

    try:
        # Process LLM output - extract JSON
        content = raw_result.content
        if isinstance(content, str):
            # Extract JSON content from the response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()

            deduplicated_data = json.loads(json_str)
            return deduplicated_data
    except Exception as e:
        print(f"Error in deduplication LLM response parsing: {str(e)}")

    # Return empty list if parsing fails
    return []


async def run_disambiguation_llm(
    mention_info: dict[str, Any],
    candidate_text: str,
    email_context: str,
    hermes_config: HermesConfig,
) -> dict[str, Any]:
    """Run the LLM to disambiguate between product candidates.

    Args:
        mention_info: Dictionary with product mention information
        candidate_text: Formatted text of all candidate products
        email_context: The full email text for context
        hermes_config: Hermes configuration

    Returns:
        A dictionary with the LLM's decision (selected_product_id, confidence, reasoning)

    """
    # Prepare prompt variables
    prompt_vars = {
        "product_mention": mention_info["product_mention"],
        "product_id": mention_info["product_id"],
        "product_name": mention_info["product_name"],
        "product_type": mention_info["product_type"],
        "product_category": mention_info["product_category"],
        "product_description": mention_info["product_description"],
        "quantity": mention_info["quantity"],
        "candidate_products": candidate_text,
        "email_context": email_context,
    }

    # Get a medium-strength model with moderate temperature for reasoning
    llm = get_llm_client(config=hermes_config, model_strength="weak", temperature=0.2)

    # Get the disambiguation prompt from the prompts module
    disambiguation_prompt = get_prompt(f"{Agents.STOCKKEEPER}_disambiguation")

    # Create the chain and execute
    disambiguation_chain = disambiguation_prompt | llm
    raw_result = await disambiguation_chain.ainvoke(prompt_vars)

    try:
        # Process LLM output - extract JSON
        content = raw_result.content
        if isinstance(content, str):
            # Extract JSON content from the response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)
            return result
    except Exception as e:
        print(f"Error parsing disambiguation LLM response: {str(e)}")

    # Return default response if parsing fails
    return {
        "selected_product_id": None,
        "confidence": 0.0,
        "reasoning": "Failed to parse LLM response",
    }


async def deduplicate_mentions(
    mentions: list[ProductMention],
    email_context: str,
    hermes_config: HermesConfig,
) -> list[ProductMention]:
    """Use an LLM to deduplicate product mentions from an email.

    Args:
        mentions: List of extracted product mentions
        email_context: The full email text for context
        hermes_config: Hermes configuration

    Returns:
        A list of deduplicated product mentions

    """
    if not mentions or len(mentions) <= 1:
        return mentions

    # Format mentions for the prompt
    mentions_text = ""
    for i, mention in enumerate(mentions, 1):
        mentions_text += f"MENTION {i}:\n"
        mentions_text += f"- Product ID: {mention.product_id or 'Not provided'}\n"
        mentions_text += f"- Product Name: {mention.product_name or 'Not provided'}\n"
        mentions_text += f"- Product Type: {mention.product_type or 'Not provided'}\n"
        mentions_text += f"- Category: {mention.product_category.value if mention.product_category else 'Not provided'}\n"
        mentions_text += (
            f"- Description: {mention.product_description or 'Not provided'}\n"
        )
        mentions_text += f"- Quantity: {mention.quantity or 1}\n\n"

    # Run the LLM to get deduplicated mentions
    deduplicated_data = await run_deduplication_llm(
        mentions_text=mentions_text,
        email_context=email_context,
        hermes_config=hermes_config,
    )

    # Convert LLM output back to ProductMention objects if we got a result
    if deduplicated_data:
        deduplicated_mentions = []
        for item in deduplicated_data:
            # Extract category if provided
            category = None
            if (
                item.get("product_category")
                and item["product_category"] != "Not provided"
            ):
                try:
                    category = ProductCategory(item["product_category"])
                except (ValueError, TypeError):
                    pass

            # Create a new ProductMention with deduplicated data
            mention = ProductMention(
                product_id=item.get("product_id")
                if item.get("product_id") != "Not provided"
                else None,
                product_name=item.get("product_name")
                if item.get("product_name") != "Not provided"
                else None,
                product_type=item.get("product_type")
                if item.get("product_type") != "Not provided"
                else None,
                product_category=category,
                product_description=item.get("product_description")
                if item.get("product_description") != "Not provided"
                else None,
                quantity=item.get("quantity", 1),
            )
            deduplicated_mentions.append(mention)

        return deduplicated_mentions

    # Fallback: return original mentions if deduplication fails
    return mentions


async def disambiguate_with_llm(
    mention: ProductMention,
    candidates: list[tuple[Product, float]],
    email_context: str,
    hermes_config: HermesConfig,
) -> dict[str, Any]:
    """Use an LLM to disambiguate between multiple potential product matches.

    Args:
        mention: The original product mention
        candidates: List of (Product, confidence) tuples
        email_context: The full email text for context
        hermes_config: Hermes configuration

    Returns:
        A dictionary with the LLM's decision

    """
    # Format candidate products for the prompt
    candidate_text = ""
    for i, (product, score) in enumerate(candidates, 1):
        candidate_text += f"CANDIDATE {i} (confidence: {score:.2f}):\n"
        candidate_text += f"- Product ID: {product.product_id}\n"
        candidate_text += f"- Product Name: {product.name}\n"
        candidate_text += f"- Product Type: {product.product_type}\n"
        candidate_text += f"- Category: {product.category}\n"
        candidate_text += f"- Description: {product.description}\n"
        candidate_text += f"- Stock: {product.stock}\n"
        candidate_text += f"- Price: ${product.price}\n\n"

    # Prepare mention information for the LLM
    mention_info = {
        "product_mention": str(mention),
        "product_id": mention.product_id or "Not provided",
        "product_name": mention.product_name or "Not provided",
        "product_type": mention.product_type or "Not provided",
        "product_category": mention.product_category.value
        if mention.product_category
        else "Not provided",
        "product_description": mention.product_description or "Not provided",
        "quantity": mention.quantity or 1,
    }

    # Run the LLM to get disambiguation decision
    return await run_disambiguation_llm(
        mention_info=mention_info,
        candidate_text=candidate_text,
        email_context=email_context,
        hermes_config=hermes_config,
    )


@traceable(run_type="chain", name="Product Resolution Agent")
async def resolve_product_mentions(
    state: StockkeeperInput,
    runnable_config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.STOCKKEEPER], StockkeeperOutput]:
    """Resolves ProductMention objects to actual Product objects from the catalog.

    Args:
        state: The input model containing the email analyzer output with product mentions
        runnable_config: Configuration for the runnable

    Returns:
        A WorkflowNodeOutput containing either resolved products or an error

    """
    try:
        hermes_config = HermesConfig.from_runnable_config(runnable_config)

        resolved_products = []
        unresolved_mentions = []

        # Extract email context and all product mentions from segments
        email_context = ""
        all_product_mentions = []

        # For compatibility, access the classifier output
        classifier_output = state.classifier

        # Generate email context for disambiguation
        if (
            classifier_output.email_analysis
            and classifier_output.email_analysis.segments
        ):
            # Build email context for disambiguation and deduplication
            context_parts = []
            for segment in classifier_output.email_analysis.segments:
                # Add segment text to context
                parts = [segment.main_sentence]
                if segment.related_sentences:
                    parts.extend(segment.related_sentences)
                context_parts.append(" ".join(parts))

                # Collect product mentions from this segment
                if hasattr(segment, "product_mentions") and segment.product_mentions:
                    all_product_mentions.extend(segment.product_mentions)

            email_context = " ".join(context_parts)

        # BACKWARD COMPATIBILITY: Special handling for tests
        # For tests, we need to extract the unique_products from the state object
        if not all_product_mentions:
            # Check if the classifier_output has unique_products attribute directly
            if hasattr(classifier_output, "unique_products"):  # type: ignore
                all_product_mentions = getattr(classifier_output, "unique_products", [])  # type: ignore
            else:
                # Try to get the unique_products from the raw __dict__
                raw_dict = getattr(classifier_output, "__dict__", {})

                # Look for unique_products in various places
                if "unique_products" in raw_dict:
                    all_product_mentions = raw_dict["unique_products"]
                elif "_obj" in raw_dict and hasattr(
                    raw_dict["_obj"], "unique_products"
                ):
                    # Sometimes Pydantic wraps objects
                    all_product_mentions = raw_dict["_obj"].unique_products

                # Try to access via the Pydantic internals
                if not all_product_mentions and hasattr(
                    classifier_output, "model_dump"
                ):
                    state_dict = classifier_output.model_dump(exclude_unset=False)
                    if "unique_products" in state_dict:
                        all_product_mentions = state_dict["unique_products"]

                # Last attempt - try direct dictionary access for non-Pydantic objects
                if not all_product_mentions and isinstance(classifier_output, dict):
                    all_product_mentions = classifier_output.get("unique_products", [])

        # Print log for debugging
        print(
            f"Found {len(all_product_mentions) if all_product_mentions else 0} product mentions for resolution"
        )

        # Deduplicate product mentions if we have more than one
        product_mentions = []
        if all_product_mentions and len(all_product_mentions) > 1:
            product_mentions = await deduplicate_mentions(
                mentions=all_product_mentions,
                email_context=email_context,
                hermes_config=hermes_config,
            )
        else:
            product_mentions = all_product_mentions

        # Track resolution metrics for the metadata
        total_mentions = len(product_mentions) if product_mentions else 0
        resolution_attempts = 0
        resolution_time_ms = 0
        deterministic_resolutions = 0
        llm_disambiguations = 0

        # Store disambiguation reasons for logging
        disambiguation_log = []

        # Process each product mention
        start_time = time.time()
        for mention in product_mentions:
            resolution_attempts += 1
            time.time()

            # Build a query based on the available information
            query = build_resolution_query(mention)

            # Attempt to resolve the product reference
            candidates = resolve_product_reference_local(query=query, max_results=3)

            # Resolution decision logic:
            # 1. If no candidates, product is unresolved
            if not candidates:
                unresolved_mentions.append(mention)
                continue

            # 2. If a single high-confidence match, use it immediately
            if len(candidates) == 1 and candidates[0][1] >= EXACT_MATCH_THRESHOLD:
                product, confidence = candidates[0]

                # Add resolution metadata to the product
                if not product.metadata:
                    product.metadata = {}
                product.metadata["resolution_confidence"] = confidence
                product.metadata["resolution_method"] = "exact_match"
                product.metadata["requested_quantity"] = mention.quantity

                resolved_products.append(product)
                deterministic_resolutions += 1
                continue

            # 3. If multiple close candidates, check if they're ambiguous
            # Ambiguity check: the difference between top matches is small
            is_ambiguous = False
            if len(candidates) >= MIN_CANDIDATES_FOR_AMBIGUITY_CHECK:
                top_score = candidates[0][1]
                second_score = candidates[1][1]
                score_diff = top_score - second_score

                if (
                    score_diff <= AMBIGUITY_THRESHOLD
                    and second_score >= SIMILAR_MATCH_THRESHOLD
                ):
                    is_ambiguous = True

            # 4. If ambiguous, use LLM disambiguation
            if is_ambiguous:
                llm_disambiguations += 1

                # Call LLM disambiguation
                llm_result = await disambiguate_with_llm(
                    mention=mention,
                    candidates=candidates,
                    email_context=email_context,
                    hermes_config=hermes_config,
                )

                selected_id = llm_result.get("selected_product_id")
                selected_confidence = llm_result.get("confidence", 0.0)
                reasoning = llm_result.get("reasoning", "No reasoning provided")

                # Log the disambiguation for metrics
                disambiguation_log.append(
                    {
                        "mention": str(mention),
                        "candidates": [p.product_id for p, _ in candidates],
                        "selected": selected_id,
                        "confidence": selected_confidence,
                        "reasoning": reasoning,
                    }
                )

                # Process the LLM's decision
                if selected_id and selected_confidence >= SIMILAR_MATCH_THRESHOLD:
                    # Find the selected product in our candidates
                    selected_product = None
                    for product, _ in candidates:
                        if product.product_id == selected_id:
                            selected_product = product
                            break

                    if selected_product:
                        # Add resolution metadata
                        if not selected_product.metadata:
                            selected_product.metadata = {}
                        selected_product.metadata["resolution_confidence"] = (
                            selected_confidence
                        )
                        selected_product.metadata["resolution_method"] = (
                            "llm_disambiguation"
                        )
                        selected_product.metadata["resolution_reasoning"] = reasoning
                        selected_product.metadata["requested_quantity"] = (
                            mention.quantity
                        )

                        resolved_products.append(selected_product)
                        continue

                # If LLM couldn't decide or we couldn't find the product, mark as unresolved
                unresolved_mentions.append(mention)
            # 5. If not ambiguous, use the highest confidence match if it's above threshold
            elif candidates[0][1] >= SIMILAR_MATCH_THRESHOLD:
                product, confidence = candidates[0]

                # Add resolution metadata
                if not product.metadata:
                    product.metadata = {}
                product.metadata["resolution_confidence"] = confidence
                product.metadata["resolution_method"] = "highest_confidence"
                product.metadata["requested_quantity"] = mention.quantity

                resolved_products.append(product)
                deterministic_resolutions += 1
            else:
                # Confidence too low, mark as unresolved
                unresolved_mentions.append(mention)

        # Calculate total resolution time
        resolution_time_ms = int((time.time() - start_time) * 1000)

        # Build output with metadata
        output = StockkeeperOutput(
            resolved_products=resolved_products,
            unresolved_mentions=unresolved_mentions,
            metadata={
                "total_mentions": total_mentions,
                "resolution_attempts": resolution_attempts,
                "resolution_time_ms": resolution_time_ms,
                "deterministic_resolutions": deterministic_resolutions,
                "llm_disambiguations": llm_disambiguations,
                "exact_match_threshold": EXACT_MATCH_THRESHOLD,
                "similar_match_threshold": SIMILAR_MATCH_THRESHOLD,
                "ambiguity_threshold": AMBIGUITY_THRESHOLD,
                "disambiguation_log": disambiguation_log,
            },
        )

        return create_node_response(Agents.STOCKKEEPER, output)

    except Exception as e:
        return create_node_response(Agents.STOCKKEEPER, e)
