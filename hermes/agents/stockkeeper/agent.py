"""Functions for resolving product mentions to catalog products."""

import time
from typing import Literal, Tuple
import re

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from hermes.agents.stockkeeper.models import (
    StockkeeperInput,
    StockkeeperOutput,
)
from hermes.model.enums import Agents
from hermes.model.errors import ProductNotFound
from hermes.model.product import Product
from hermes.model.email import ProductMention
from hermes.workflow.types import WorkflowNodeOutput
from hermes.utils.response import create_node_response
from hermes.tools.catalog_tools import resolve_product_mention
from hermes.utils.logger import logger, get_agent_logger


def extract_l2_distance_from_metadata(metadata_str: str | None) -> float | None:
    """Extract L2 distance (similarity_score) from metadata string."""
    if not metadata_str:
        return None
    # Match "Resolution confidence: " followed by a float.
    # This is the format used by catalog_tools for L2-like scores.
    match = re.search(r"Resolution confidence: ([\d\.]+)", metadata_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def create_stockkeeper_metadata_string(
    total_mentions: int,
    resolution_attempts: int,
    resolution_time_ms: int,
    mentions_with_candidates: int,
    mentions_without_candidates: int,
    candidate_log: list,
) -> str:
    """Create a natural language metadata string for stockkeeper output."""
    parts = []

    parts.append(f"Processed {total_mentions} product mentions")
    parts.append(f"Made {resolution_attempts} resolution attempts for these mentions")
    parts.append(f"Found candidates for {mentions_with_candidates} mentions")
    parts.append(
        f"{mentions_without_candidates} mentions had no candidates found (unresolved)"
    )
    parts.append(f"Processing took {resolution_time_ms}ms")

    # Simplified candidate log part for this metadata string
    # Detailed candidate info is now in the structured output field
    mentions_with_any_candidates_in_log = 0
    if candidate_log:
        for log_entry in candidate_log:
            if log_entry.get("num_candidates_found_for_mention", 0) > 0:
                mentions_with_any_candidates_in_log += 1
    parts.append(
        f"(Debug log: {mentions_with_any_candidates_in_log} mentions showed >0 candidates in detailed log)"
    )
    return "; ".join(parts)


@traceable(run_type="chain", name="Product Candidate Provider Agent")
async def run_stockkeeper(
    state: StockkeeperInput,
    config: RunnableConfig | None = None,
) -> WorkflowNodeOutput[Literal[Agents.STOCKKEEPER], StockkeeperOutput]:
    """Resolves ProductMention objects to actual Product objects from the catalog.

    Args:
        state: The input model containing the email analyzer output with product mentions
        config: Configuration for the runnable

    Returns:
        A WorkflowNodeOutput containing either resolved products or an error

    """
    agent_name = Agents.STOCKKEEPER.value.capitalize()
    email_id = state.email.email_id
    logger.info(
        get_agent_logger(
            agent_name,
            f"Providing product candidates for email [cyan]{email_id}[/cyan]",
        )
    )

    try:
        candidate_products_for_mention: list[Tuple[ProductMention, list[Product]]] = []
        unresolved_mentions_list: list[ProductMention] = []
        exact_id_misses_list: list[ProductMention] = []

        # Extract all product mentions from segments
        all_product_mentions = []

        # For compatibility, access the classifier output
        classifier_output = state.classifier

        # Extract product mentions from email analysis segments
        if (
            classifier_output.email_analysis
            and classifier_output.email_analysis.segments
        ):
            # Collect product mentions from all segments
            for segment in classifier_output.email_analysis.segments:
                # Collect product mentions from this segment
                if hasattr(segment, "product_mentions") and segment.product_mentions:
                    all_product_mentions.extend(segment.product_mentions)

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
        logger.debug(
            get_agent_logger(
                agent_name,
                f"Found {len(all_product_mentions) if all_product_mentions else 0} product mentions for resolution for email [cyan]{email_id}[/cyan]",
            )
        )

        # Process all product mentions directly without deduplication
        product_mentions_to_process = all_product_mentions or []

        # Track resolution metrics for the metadata
        total_mentions = len(product_mentions_to_process)
        resolution_attempts = 0
        resolution_time_ms = 0
        mentions_with_candidates_count = 0
        candidate_log_per_mention_for_metadata = []

        # Process each product mention using the resolve_product_mention function
        start_time = time.time()
        for mention in product_mentions_to_process:
            resolution_attempts += 1
            logger.debug(
                get_agent_logger(
                    agent_name,
                    f"Attempting to find candidates for mention: [yellow]{mention.model_dump_json(indent=1)}[/yellow]",
                )
            )

            original_mention_product_id = mention.product_id

            # resolve_product_mention returns list[Product] (candidates) or ProductNotFound
            # Candidates already have L2 distance in metadata and are filtered by L2 <= 1.2 by catalog_tools
            # UPDATED: resolve_product_mention now returns list[tuple[Product, float]] | ProductNotFound
            candidates_result: (
                list[tuple[Product, float]] | ProductNotFound
            ) = await resolve_product_mention(mention=mention, top_k=3)

            num_actual_candidates_found = 0
            final_status_for_log = "unresolved_no_candidates"
            best_l2_distance_this_mention: float | None = None
            best_candidate_id_this_mention = None
            exact_match_found_for_id_mention = False

            if (
                isinstance(candidates_result, list) and candidates_result
            ):  # candidates_result is list[tuple[Product, float]]
                processed_candidates_for_output: list[
                    Product
                ] = []  # For StockkeeperOutput

                # Sort candidates by L2 score (ascending) before processing,
                # as resolve_product_mention already returns them sorted if from a single source (vector/fuzzy)
                # but if it were to combine them in future, explicit sort here would be good.
                # For now, resolve_product_mention ensures sorted output.

                for cand_prod, l2_score in candidates_result:
                    if (
                        original_mention_product_id
                        and cand_prod.product_id == original_mention_product_id
                    ):
                        exact_match_found_for_id_mention = True

                    current_cand_l2 = l2_score  # Use L2 score directly from the tuple

                    if best_l2_distance_this_mention is None or (
                        # current_cand_l2 is now always a float if candidates_result is a list of tuples
                        current_cand_l2 < best_l2_distance_this_mention
                    ):
                        best_l2_distance_this_mention = current_cand_l2
                        best_candidate_id_this_mention = cand_prod.product_id

                    # Add full mention info to metadata if not already perfectly set by catalog_tools
                    mention_info = (
                        f"Original mention: {mention.product_name or 'N/A'} "
                        f"(ID: {mention.product_id or 'N/A'}, Type: {mention.product_type or 'N/A'}, "
                        f"Category: {mention.product_category.value if mention.product_category else 'N/A'}, "
                        f"Quantity: {mention.quantity})"
                    )
                    if cand_prod.metadata and mention_info not in cand_prod.metadata:
                        cand_prod.metadata = f"{cand_prod.metadata}; {mention_info}"
                    elif not cand_prod.metadata:
                        cand_prod.metadata = mention_info

                    processed_candidates_for_output.append(cand_prod)

                if (
                    processed_candidates_for_output
                ):  # If any candidates were processed and added
                    candidate_products_for_mention.append(
                        (mention, processed_candidates_for_output)
                    )
                    mentions_with_candidates_count += 1
                    num_actual_candidates_found = len(processed_candidates_for_output)
                    final_status_for_log = f"{num_actual_candidates_found}_candidates_found (best_L2: {best_l2_distance_this_mention if best_l2_distance_this_mention is not None else 'N/A'})"

            elif isinstance(candidates_result, ProductNotFound):
                logger.info(
                    f"ProductNotFound for mention '{mention.mention_text}': {candidates_result.message}"
                )
                unresolved_mentions_list.append(mention)
                final_status_for_log = "explicit_product_not_found_response"
                if original_mention_product_id:
                    exact_match_found_for_id_mention = False
            else:  # Should be an empty list if not ProductNotFound and not list with items
                logger.info(
                    f"No candidates returned by resolve_product_mention for '{mention.mention_text}' (empty list)."
                )
                unresolved_mentions_list.append(mention)
                if original_mention_product_id:
                    exact_match_found_for_id_mention = False

            # Populate exact_id_misses_list
            if original_mention_product_id and not exact_match_found_for_id_mention:
                if mention not in exact_id_misses_list:
                    exact_id_misses_list.append(mention)

            candidate_log_per_mention_for_metadata.append(
                {
                    "mention_text": str(mention.mention_text),
                    "num_candidates_found_for_mention": num_actual_candidates_found,
                    "final_status_for_mention": final_status_for_log,
                    "best_candidate_id_for_mention": best_candidate_id_this_mention,
                    "best_candidate_l2_distance_for_mention": best_l2_distance_this_mention,
                }
            )

        resolution_time_ms = int((time.time() - start_time) * 1000)
        mentions_without_candidates_count = len(unresolved_mentions_list)

        metadata_str = create_stockkeeper_metadata_string(
            total_mentions=total_mentions,
            resolution_attempts=resolution_attempts,
            resolution_time_ms=resolution_time_ms,
            mentions_with_candidates=mentions_with_candidates_count,
            mentions_without_candidates=mentions_without_candidates_count,
            candidate_log=candidate_log_per_mention_for_metadata,
        )

        logger.info(
            get_agent_logger(
                agent_name,
                f"Candidate provision complete for email [cyan]{email_id}[/cyan]. Metadata: {metadata_str}",
            )
        )

        output = StockkeeperOutput(
            candidate_products_for_mention=candidate_products_for_mention,
            unresolved_mentions=unresolved_mentions_list,
            exact_id_misses=exact_id_misses_list,
            metadata=metadata_str,
        )

        return create_node_response(Agents.STOCKKEEPER, output)

    except Exception as e:
        error_message = f"Error in {agent_name} for email {email_id}: {e}"
        logger.error(get_agent_logger(agent_name, error_message), exc_info=True)
        raise RuntimeError(
            f"Stockkeeper: Error during candidate provision for email {state.email.email_id}"
        ) from e
