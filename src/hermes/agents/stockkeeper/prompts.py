"""Product Resolver prompts for use with LangChain."""


from langchain_core.prompts import PromptTemplate

from src.hermes.model.enums import Agents

# Dictionary to store all prompt templates
PROMPTS: dict[str, PromptTemplate] = {}

# LLM prompt for disambiguating products
DISAMBIGUATION_PROMPT_STR = """
You are an AI assistant specializing in product catalog resolution. Your task is to determine the most likely product match based on the context provided.

## ORIGINAL PRODUCT MENTION FROM EMAIL:
{product_mention}

## EXTRACTED INFORMATION:
- Product ID (if provided): {product_id}
- Product Name (if provided): {product_name}
- Product Type (if provided): {product_type}
- Product Category (if provided): {product_category}
- Product Description (if provided): {product_description}
- Quantity: {quantity}

## CANDIDATE PRODUCTS:
{candidate_products}

## EMAIL CONTEXT:
{email_context}

## INSTRUCTIONS:
1. Analyze the original mention in the context of the whole email
2. Compare the mention details with each candidate product
3. Select the most likely match based on:
   - ID match > name match > description match
   - Consider product type and category
   - Consider the email context
4. If no single product can be determined with reasonable confidence, state that the resolution is undecidable

## RESPONSE (JSON FORMAT):
Respond with a JSON object having these fields:
- "selected_product_id": The ID of the selected product or null if undecidable
- "confidence": Your confidence score (0.0-1.0)
- "reasoning": Brief explanation of your decision
"""

# Prompt for deduplicating product mentions
DEDUPLICATION_PROMPT_STR = """
You are an AI assistant specializing in product catalog management. Your task is to identify and merge duplicate product mentions from an email.

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

# Create PromptTemplate objects and add them to the PROMPTS dictionary
PROMPTS[f"{Agents.STOCKKEEPER}_disambiguation"] = PromptTemplate.from_template(DISAMBIGUATION_PROMPT_STR)
PROMPTS[f"{Agents.STOCKKEEPER}_deduplication"] = PromptTemplate.from_template(DEDUPLICATION_PROMPT_STR)


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
        raise KeyError(f"Prompt key '{key}' not found. Available keys: {list(PROMPTS.keys())}")
    return PROMPTS[key]
