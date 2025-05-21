# Hermes Refactoring Plan: Product Resolution Node

## Overview
Add a dedicated "ProductResolver" node to the workflow that converts ProductMention objects from the Email Analyzer to actual Product objects from the catalog.

## Step 1: Create New Models ✅
1. ✅ Create a new file: `src/hermes/agents/product_resolver/models.py`
   - ✅ Define `ResolvedProductsOutput` class
   - ✅ Include lists for resolved products and unresolved mentions
   - ✅ Add metadata like resolution rate, confidence scores

2. ✅ Update `src/hermes/agents/workflow/states.py`
   - ✅ Add the new output model to the OverallState

## Step 2: Implement the Resolver Node ✅
1. ✅ Create a new directory: `src/hermes/agents/product_resolver/`
2. ✅ Create `src/hermes/agents/product_resolver/resolve_products.py`:
   ```python
   @traceable(run_type="chain", name="Product Resolution Agent")
   async def resolve_product_mentions(
       state: EmailAnalyzerOutput,
       runnable_config: Optional[RunnableConfig] = None,
   ) -> WorkflowNodeOutput[Literal["PRODUCT_RESOLVER"], ResolvedProductsOutput]:
       """Resolves ProductMention objects to actual Product objects from the catalog."""
       
       resolved_products = []
       unresolved_mentions = []
       
       for mention in state.unique_products:
           query = build_resolution_query(mention)
           result = resolve_product_reference(query=query)
           
           if isinstance(result, Product):
               resolved_products.append(result)
           else:
               unresolved_mentions.append(mention)
       
       return create_node_response(
           "PRODUCT_RESOLVER",
           ResolvedProductsOutput(
               resolved_products=resolved_products,
               unresolved_mentions=unresolved_mentions
           )
       )
   ```

3. ✅ Add helper functions for query building and resolution attempts

## Step 3: Update the Workflow Graph ✅
1. ✅ Edit `src/hermes/agents/workflow/graph.py`:
   - ✅ Add the new node to the workflow graph
   - ✅ Update the edges to include the new node
   - ✅ Place it after Email Analyzer but before Order Processor and Inquiry Responder

2. ✅ Update `src/hermes/model/enums.py`:
   - ✅ Add "PRODUCT_RESOLVER" to the Agents enum

## Step 4: Modify Dependent Agents ✅
1. ✅ Update `src/hermes/agents/order_processor/process_order.py`:
   - ✅ Modify to use resolved products from state instead of raw mentions
   - ✅ Fall back to direct resolution only for products not already resolved

2. ✅ Update `src/hermes/agents/inquiry_responder/respond_to_inquiry.py`:
   - ✅ Adjust to use both resolved products and vector search results
   - ✅ Prioritize resolved products for precise answers

## Step 5: Testing 🔄
1. Create unit tests for the resolution logic
2. Create integration tests for the full workflow
3. Check edge cases:
   - No product mentions
   - All mentions resolved
   - No mentions resolved
   - Mixed resolution results

## Step 6: Documentation ✅
1. ✅ Update architecture diagrams
2. ✅ Document the new node in `agents-flow.md`
3. ✅ Add examples of how the resolution works

## Implementation Summary
- Created a new ProductResolver node that resolves product mentions to catalog products
- Modified the workflow to include the new node in the processing pipeline
- Updated dependent agents to utilize resolved products
- Added comprehensive documentation and updated architecture diagrams

## Potential Enhancements
- Add a confidence threshold for resolution
- Implement fallback strategies for low-confidence resolutions
- Consider caching resolved products
- Add resolution statistics to telemetry 

## Revised Resolution Strategy
The resolver will use a hybrid approach:

1. **Primary Resolution**: Use deterministic methods in a cascading strategy:
   - Exact ID matching (highest confidence)
   - Fuzzy name matching (with confidence threshold)
   - Semantic vector search (for description-based matching)

2. **LLM Disambiguation**: When primary resolution produces multiple plausible matches with similar confidence scores:
   - Invoke an LLM to analyze the product mentions in the broader email context
   - Provide the LLM with details of the ambiguous matches
   - Ask the LLM to select the most likely product or explicitly state if resolution is undecidable
   - Include the LLM's reasoning in the resolution metadata

3. **Confidence Scoring**:
   - Assign confidence scores to all resolutions
   - Use higher thresholds for automatic resolution
   - Flag low-confidence resolutions for human review if needed

This hybrid approach maximizes efficiency by using deterministic methods for straightforward cases while leveraging LLM reasoning only when disambiguation is needed. This keeps token usage low while handling complex cases appropriately. 