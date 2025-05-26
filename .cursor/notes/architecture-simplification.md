# Architecture Simplification: Product Resolution

## Problem Identified

The original architecture had a fundamental inefficiency:

1. **Stockkeeper** runs `resolve_product_mention` → gets candidates → runs `run_disambiguation_llm` → picks ONE product
2. **Advisor** gets the single resolved product → calls `format_resolved_products()` → passes to LLM as context

This resulted in **two LLM calls** when only **one** was needed.

## Solution Implemented

### New Efficient Flow:
1. **Stockkeeper** runs `resolve_product_mention` → returns ALL top-K candidates
2. **Advisor** gets all candidates → passes them as context → LLM picks the right one while generating the response

### Key Changes:

1. **Simplified `resolve_product_mention`** in `hermes/tools/catalog_tools.py`:
   - Now returns `list[Product]` (top-K candidates) instead of trying to pick one
   - Each candidate includes metadata about confidence and original mention
   - Eliminated need for separate disambiguation step

2. **Removed `run_disambiguation_llm`** from `hermes/agents/stockkeeper/agent.py`:
   - No longer needed since downstream agents handle selection naturally
   - Simplified the stockkeeper logic significantly
   - Updated metrics to track candidates instead of disambiguations

3. **Enhanced `format_resolved_products`** in `hermes/agents/advisor/agent.py`:
   - Now groups candidates by original mention
   - Provides clear context for multiple candidates
   - Helps LLM make informed selections during response generation

4. **Updated disambiguation prompt** in `hermes/agents/stockkeeper/prompts.py`:
   - Removed the disambiguation prompt entirely
   - Only kept deduplication prompt which is still needed

## Benefits

1. **Reduced LLM calls**: From 2 calls to 1 call per disambiguation
2. **Better context**: Downstream agents get all candidates with confidence scores
3. **More flexible**: LLM can consider customer intent while selecting products
4. **Simpler code**: Less complex disambiguation logic in stockkeeper
5. **Better UX**: More natural responses since selection happens during response generation

## Tests Updated

- `tests/test_resolve_product_mention.py`: Updated to expect `list[Product]` instead of `ProductResolutionResult`
- Added test for multiple candidates scenario
- All tests passing

## Architectural Insight

This change demonstrates a key principle: **Push disambiguation to the point where you have the most context**. The Advisor agent has access to:
- Customer's exact request
- Full email context
- All product candidates with confidence scores
- The ability to generate a natural response

This makes it the ideal place to handle product selection, not the Stockkeeper which only has isolated product mentions.