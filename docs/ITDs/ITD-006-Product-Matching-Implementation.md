# ITD-006: Product Matching Implementation Strategy

**Date:** 2024-07-29
**Author:** Gemini Assistant
**Status:** Revised

## 1. Context

Expanding on ITD-003 (Product Name/ID Mapping Strategy), this document details the specific implementation approach for matching product mentions in customer emails to actual product IDs in the catalog. While ITD-003 selected the LLM Extraction + Fuzzy String Matching approach, additional specifics are needed regarding:

1. Which product fields to include in the matching process
2. How to prioritize and weight different match types
3. How to handle multiple potential matches
4. Fallback strategies when matching fails

## 2. Requirements

* **Accuracy:** Maximize correct product identification while minimizing false matches
* **Robustness:** Handle variations in naming, typos, plurals, and incomplete descriptions
* **Transparency:** Provide confidence scores for matches to enable appropriate responses
* **Flexibility:** Adapt matching strategy based on the type of product mention

## 3. Matching Fields and Weights

### 3.1 Fields to Match Against

The following product fields will be used in the matching process:

1. **Product Code/ID:** Exact match attempted first (highest priority)
2. **Product Name:** Primary field for fuzzy matching
3. **Product Description:** Secondary field for fuzzy matching (when name matching is inconclusive)
4. **Category + Name:** Combination field for handling category-qualified mentions (e.g., "blue summer dress")

### 3.2 Weighting Strategy

Matches will be scored according to the following weights:

* **Exact Code Match:** 100% confidence
* **Fuzzy Name Match:** Base confidence from thefuzz (scaled to 0-100%)
* **Name + Category Match:** Additional +10% to fuzzy match score when category aligns
* **Description Match:** 80% of the fuzzy match score (lower weight than name matches)

## 4. Matching Algorithm

### 4.1 Tiered Approach

1. **Stage 1: Exact ID/Code Matching**
   * Check if mention exactly matches a product code
   * If match found, return with 100% confidence

2. **Stage 2: Name Fuzzy Matching**
   * Use thefuzz.process.extractOne on product names
   * If score ≥ 90%, return match
   * If score < 60%, proceed to Stage 3
   * If 60% ≤ score < 90%, store as candidate and proceed to Stage 3

3. **Stage 3: Category-Enhanced Matching**
   * Extract potential category signals from the mention
   * Combine with fuzzy name matching, giving bonus to category matches
   * If enhanced score ≥ 85%, return match
   * If no match ≥ 85%, proceed to Stage 4

4. **Stage 4: Description Fallback**
   * Use fuzzy matching against product descriptions
   * If score ≥ 85%, return match
   * Otherwise, return best candidate from any stage or "no match"

### 4.2 Multiple Match Handling

When multiple potential matches exist:

1. **Primary Strategy:** Return the match with highest confidence
2. **Tiebreaker:** Prioritize matches in this order:
   * Exact code matches
   * Name matches
   * Category-enhanced matches
   * Description matches
3. **Secondary Tiebreaker:** If still tied, prioritize products with higher stock levels

## 5. Fallback Strategy

When no confident match is found:

1. **Classification Strategy:**
   * Classify as "mapping_failed" with the original mention preserved
   * Include the best candidate match and its confidence score

2. **Response Generation:**
   * In order responses: Request clarification about the specific product
   * In inquiry responses: Acknowledge ambiguity and request more details

## 6. Implementation Example

```python
def match_product(product_mention, products_df, threshold=85):
    # Stage 1: Exact code matching
    exact_matches = products_df[products_df['product_id'].str.lower() == product_mention.lower()]
    if not exact_matches.empty:
        return {
            'product_id': exact_matches.iloc[0]['product_id'],
            'product_name': exact_matches.iloc[0]['name'],
            'confidence': 100,
            'match_method': 'exact_code_match'
        }
    
    # Stage 2: Name fuzzy matching
    from thefuzz import process
    name_match, name_score = process.extractOne(
        product_mention, 
        products_df['name'].tolist()
    )
    
    if name_score >= 90:
        matched_row = products_df[products_df['name'] == name_match].iloc[0]
        return {
            'product_id': matched_row['product_id'],
            'product_name': matched_row['name'],
            'confidence': name_score,
            'match_method': 'fuzzy_name_match'
        }
    
    # Additional stages would follow...
    
    # If no match meets threshold
    if name_score >= threshold:
        matched_row = products_df[products_df['name'] == name_match].iloc[0]
        return {
            'product_id': matched_row['product_id'],
            'product_name': matched_row['name'],
            'confidence': name_score,
            'match_method': 'fuzzy_name_match_fallback'
        }
    else:
        return {
            'product_id': None,
            'product_name': None,
            'confidence': name_score if name_score else 0,
            'match_method': 'mapping_failed',
            'best_candidate': name_match if name_score else None,
            'best_score': name_score if name_score else 0
        }
```

## 7. Next Steps

1. Implement the tiered matching approach as a stand-alone function
2. Test with sample product mentions from the dataset
3. Fine-tune thresholds based on initial results
4. Integrate with the LLM extraction component 