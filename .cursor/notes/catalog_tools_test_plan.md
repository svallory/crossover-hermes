# Catalog Tools Test Plan

## Overview
Testing the catalog tools to handle messy customer references in emails, including typos, language differences, vague descriptions, and various edge cases.

## Critical Test Scenarios

### 1. Product ID Issues
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Typo in Product ID** | `DHN0987` | Should resolve to `CHN0987 Chunky Knit Beanie` | E009 |
| **Spaces in Product ID** | `CBT 89 01` | Should resolve to `CBT8901 Chelsea Boots` | E019 |
| **Case sensitivity** | `rsg8901` | Should resolve to `RSG8901 Retro Sunglasses` | - |
| **Non-existent ID** | `XXX9999` | Should return ProductNotFound | - |

### 2. Language/Translation Issues
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Spanish to English** | `Gorro de punto grueso` | Should resolve to `CHN0987 Chunky Knit Beanie` | E009 |
| **Partial translation** | `Gorro` + context | Should find beanie products | E009 |

### 3. Partial Product Names
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Just product name** | `Sleek Wallet` | Should resolve to `SWL2345 Sleek Wallet` | E014 |
| **Partial name** | `Versatile Scarf` | Should resolve to `VSC6789 Versatile Scarf` | E008 |
| **Generic name** | `Saddle bag` | Should resolve to `SDE2345 Saddle Bag` | E020 |

### 4. Vague Descriptions
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Very vague** | `popular item selling like hotcakes` | Should return ProductNotFound or ask for clarification | E017 |
| **Descriptive but vague** | `bags with geometric patterns` | Should return ProductNotFound or multiple candidates | E022 |
| **Functional description** | `bag to carry laptop and documents` | Should find work bags/backpacks | E003 |

### 5. Product Categories & Filters
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Category search** | `slide sandals for men` | Should find `SLD7654 Slide Sandals` | E013 |
| **Season filtering** | `winter hats` | Should find winter accessories | E021 |
| **Multiple criteria** | `leather bag for work and hiking` | Should find versatile bags | E015 |

### 6. Semantic Similarity
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Synonyms** | `messenger bag, briefcase` | Should find `LTH2109 Leather Messenger Bag` | E012 |
| **Related terms** | `laptop bag` vs `backpack` | Should find relevant products | E003 |
| **Product features** | `organizational pockets` | Should find bags with organization features | E003 |

### 7. Multiple Products in One Query
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **List of IDs** | `SDE2345, DJN8901, RGD7654, CRD3210` | Should resolve all valid IDs | E021 |
| **Mixed valid/invalid** | `Chelsea Boots, Fuzzy Slippers, Retro sunglasses` | Should handle mix of formats | E019 |

### 8. Edge Cases
| Scenario | Input | Expected Output | Email Ref |
|----------|-------|----------------|-----------|
| **Empty query** | `""` | Should return ProductNotFound | - |
| **Special characters** | `[CBT 89 01]` | Should extract and resolve ID | E019 |
| **Malformed JSON** | Invalid JSON input | Should handle gracefully | - |

## Test Implementation Strategy

### Phase 1: Fix Existing Tests
- Update tests to work with simplified vector store
- Mock the new `get_vector_store()` function
- Ensure basic functionality works

### Phase 2: Add Critical Scenario Tests
- **Product ID Resolution**: Focus on typos and formatting issues
- **Language/Translation**: Test Spanish-English matching
- **Semantic Search**: Test description-based matching
- **Edge Cases**: Test error handling and malformed inputs

### Phase 3: Integration Tests
- Test complete email scenarios from emails.csv
- Test stockkeeper agent integration
- Validate end-to-end workflows

## Required Improvements

### 1. Enhanced Product ID Matching
```python
def resolve_product_id_with_fuzzy_matching(product_id: str) -> str | None:
    """Resolve product IDs with typos using fuzzy matching."""
    # Remove spaces, normalize case
    # Use fuzzy matching against known product IDs
    # Return best match if confidence > threshold
```

### 2. Cross-Language Matching
```python
def translate_and_match(foreign_text: str, context: str) -> list[Product]:
    """Handle non-English product references."""
    # Use LLM to translate/understand foreign text
    # Match against English descriptions
    # Consider product ID context
```

### 3. Enhanced Semantic Search
```python
def semantic_product_search(description: str, filters: dict) -> list[Product]:
    """Improved semantic search with better context understanding."""
    # Better embedding strategies
    # Context-aware matching
    # Handle vague descriptions better
```

## Success Criteria
1. **Product ID Resolution**: 95% accuracy on typos/formatting issues
2. **Language Handling**: Successfully resolve E009 scenario
3. **Semantic Matching**: Handle 80% of descriptive queries correctly
4. **Error Handling**: Graceful failure for impossible queries
5. **Performance**: All searches complete in <2 seconds