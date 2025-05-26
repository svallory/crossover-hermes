"""Stockkeeper prompts for use with LangChain."""

from langchain_core.prompts import PromptTemplate

from hermes.model.enums import Agents

# Dictionary to store all prompt templates
PROMPTS: dict[str, PromptTemplate] = {}

# Prompt for deduplicating product mentions
DEDUPLICATION_PROMPT_STR = """
You are an AI assistant specializing in product catalog management. Your
task is to identify and merge duplicate product mentions from an email.

## EMAIL CONTEXT:
{email_context}

## EXTRACTED PRODUCT MENTIONS:
{product_mentions}

## INSTRUCTIONS:
1. Analyze the list of product mentions from the email
2. Identify mentions that refer to the same product
3. Merge duplicate mentions into a single, more complete mention
4. For each set of duplicates, select the most specific/detailed mention or combine details from multiple mentions
5. Keep any non-duplicate mentions unchanged

## FACTORS TO CONSIDER:
- Direct references to the same product ID should be merged
- Different descriptions of the same product should be merged
- Different quantities for the same product should be summed
- Different product names/descriptions that clearly refer to the same item should be merged

## RESPONSE (JSON FORMAT):
Respond with a JSON array of deduplicated product mentions. For each mention, include:
- "product_id": The product ID if available (or null)
- "product_name": The product name if available (or null)
- "product_type": The product type if available (or null)
- "product_category": The category if available (or null)
- "product_description": The combined description if available (or null)
- "quantity": The total quantity (sum of duplicate mentions)
- "reasoning": Brief explanation of your deduplication decision (if mentions were merged)
"""

# Prompt for suggesting alternatives for out-of-stock items
ALTERNATIVE_SUGGESTION_PROMPT_STR = """
You are an AI assistant helping a customer find alternative products for an item that is out of stock or unavailable.

## ORIGINAL REQUESTED PRODUCT (Out of Stock/Unavailable):
- Product ID: {original_product_id}
- Name: {original_product_name}
- Description: {original_product_description}
- Category: {original_product_category}
- Type: {original_product_type}
- Price: ${original_product_price}

## AVAILABLE CANDIDATE ALTERNATIVES:
{candidate_products_text}

## INSTRUCTIONS:
1. Review the original requested product details.
2. Examine the list of available candidate alternatives, paying attention to their similarity scores and features.
3. Select up to {limit} best alternative products from the candidates.
4. For each selected alternative, provide a brief reasoning why it's a good alternative (e.g., similar style, good features, in stock).
5. Consider factors like category, product type, features described, and price range when making suggestions.
6. Prioritize candidates with higher similarity scores if they are suitable.
7. If no candidates are suitable, you can return an empty list.

## RESPONSE (JSON FORMAT):
Respond with a JSON array, where each object represents a suggested alternative and has these fields:
- "product_id": The ID of the suggested alternative product.
- "reasoning": Your brief explanation for suggesting this product.
- "similarity_score": The original similarity score of this candidate (if available, otherwise 0.0).
"""

# Create PromptTemplate objects and add them to the PROMPTS dictionary
PROMPTS[f"{Agents.STOCKKEEPER}_deduplication"] = PromptTemplate.from_template(
    DEDUPLICATION_PROMPT_STR
)
PROMPTS[f"{Agents.STOCKKEEPER}_alternative_suggestion"] = PromptTemplate.from_template(
    ALTERNATIVE_SUGGESTION_PROMPT_STR
)


def get_prompt(key: str) -> PromptTemplate:
    """Get a specific prompt template by key.

    Args:
        key: The key of the prompt template to retrieve.

    Returns:
        The requested PromptTemplate.

    Raises:
        KeyError: If the key doesn't exist in the PROMPTS dictionary.

    """
    if key not in PROMPTS:
        raise KeyError(
            f"Prompt key '{key}' not found. Available keys: {list(PROMPTS.keys())}"
        )
    return PROMPTS[key]
