# Hermes Model Refactoring Plan

## Agreed Changes

1. **Model Merges:**
   - Merge `OrderItem` (TypedDict) and `OrderedItem` (Pydantic) into a single Pydantic model called `OrderLine`
   - Merge `Order` and `ProcessedOrder` into a single Pydantic model called `Order`
   - Rename `OrderedItemStatus` to `OrderLineStatus`

2. **Standardization:**
   - Consolidate duplicate `ProductNotFound` model into a single location (e.g., `model/errors.py`)
   - All models should be well-defined and documented Pydantic models
   - Fix inconsistencies in promotion handling between dictionary access and Pydantic model access

3. **Missing Implementation:**
   - Implement the missing `find_alternatives_for_oos` function

## Implementation Plan

1. Create common error models in `model/errors.py`
2. Refactor the order models in `model/order.py`
3. Update all imports and usages across the codebase
4. Implement the missing function
5. Fix any type errors in tools and agent code

## Benefits

- Reduced model count and complexity
- Consistent typing (all Pydantic models)
- Clear separation of concerns
- Improved code maintainability 