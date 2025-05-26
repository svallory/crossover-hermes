"""Stockkeeper prompts for use with LangChain."""

from langchain_core.prompts import PromptTemplate

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

# Create PromptTemplate objects
ALTERNATIVE_SUGGESTION_PROMPT = PromptTemplate.from_template(
    ALTERNATIVE_SUGGESTION_PROMPT_STR
)
