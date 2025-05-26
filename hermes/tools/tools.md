# Tools

This module provides specialized tools for our agents to interact with external systems and data.

## Architecture Overview

Our tools follow an **LLM-first architecture** with two distinct categories:

### Direct Function Calls
Tools that WE call when we know they're needed based on workflow logic:
- Product resolution tools (we always resolve product mentions to multiple candidates)
- Stock management tools (we always check/update stock for orders)
- Price calculation tools (we always calculate prices for orders)

### LLM-Callable Tools (@tool decorator)
Tools that the **LLM decides** whether to call based on customer needs:
- Search tools when LLM needs additional product context
- Alternative finding when LLM thinks customer might want options
- Complementary product suggestions for enhanced customer experience

## Tool Organization

### Catalog Tools (`catalog_tools.py`)
**Direct Function Calls:**
- `find_product_by_id` - Exact product ID lookup with fuzzy matching
- `find_product_by_name` - Fuzzy name matching for product resolution
- `search_products_by_description` - Semantic search for context retrieval
- `resolve_product_mention` - **NEW ARCHITECTURE**: Returns top-K product candidates using ChromaDB's semantic search and metadata filtering (no longer attempts single product selection)

**LLM-Callable Tools (@tool):**
- `find_complementary_products` - LLM-driven complementary suggestions
- `search_products_with_filters` - Advanced filtering for complex requirements
- `find_products_for_occasion` - Occasion-based product discovery
- `find_alternatives` - Out-of-stock alternative suggestions

### Order Tools (`order_tools.py`)
**LLM-Callable Tools (@tool):**
- `check_stock` - Verify product availability for orders
- `update_stock` - Decrement inventory after fulfillment

### Promotion Tools (`promotion_tools.py`)
**LLM-Callable Tools (@tool):**
- `apply_promotion` - Apply promotions to ordered items

## Agent Toolkits

Each agent has its own toolkit defined in its `agent.py` file:

### AdvisorToolkit
**Purpose**: Provide contextual recommendations and enhanced customer responses
**Tools**:
- `find_complementary_products` - For suggesting additional items
- `search_products_with_filters` - For complex customer requirements
- `find_products_for_occasion` - For occasion-based suggestions

### ComposerToolkit
**Purpose**: Enhance final responses with additional suggestions
**Tools**:
- `find_complementary_products` - For suggesting additional items
- `find_products_for_occasion` - For occasion-based suggestions

### FulfillerToolkit
**Purpose**: Order processing (uses direct calls only)
**Tools**: None - uses direct function calls for deterministic workflow

### StockKeeperToolkit
**Purpose**: Product resolution (uses direct calls only)
**Tools**: None - uses direct function calls for deterministic workflow

### ClassifierToolkit
**Purpose**: Email analysis (pure LLM analysis)
**Tools**: None - uses pure LLM analysis only

## Design Principles

1. **LLM-First Architecture**: Minimize tool usage by letting LLMs handle complex logic
2. **Candidate-Based Resolution**: Return multiple viable options instead of forcing early decisions
3. **Deterministic vs Dynamic**: Direct calls for predictable workflow steps, @tool for LLM decisions
4. **Agent Specialization**: Each agent gets only the tools it needs via toolkits
5. **Token Optimization**: Smaller tool lists = faster LLM processing and reduced costs
6. **Strong Typing**: Using Pydantic models for inputs and outputs ensures robustness
7. **Error Handling**: Tools return structured error objects instead of raising exceptions

## Key Architectural Changes

### Eliminated Disambiguation Step
- **Old Flow**: `resolve_product_mention` → `run_disambiguation_llm` → single product
- **New Flow**: `resolve_product_mention` → multiple candidates → natural selection by downstream agents

### Enhanced Product Context
- Product candidates include confidence scores and original mention metadata
- Downstream agents receive grouped candidates for better decision-making
- Selection happens naturally during response generation, not in isolation

### Improved LLM Efficiency
- Reduced from 2 LLM calls to 1 call per product disambiguation
- Better context for LLM decision-making
- More natural and contextual product selection

## Implementation Notes

### Product Resolution Strategy
- `resolve_product_mention`: Returns top-K candidates (typically 1-3) with metadata
- Exact ID matches return immediately with single result
- Semantic searches return multiple candidates above confidence threshold
- Each candidate includes resolution method, confidence score, and original mention context

### Stock Management
- `check_stock`: Verifies product availability before order processing
- `update_stock`: Decrements inventory with validation to prevent errors
- Both tools include comprehensive error handling and status reporting

### LLM-Callable Tool Usage
Tools decorated with `@tool` are available for LLM decision-making:
- **Advisor Agent**: Uses tools to enhance customer responses with contextual suggestions
- **Composer Agent**: Uses tools to add complementary suggestions to final responses
- **Other Agents**: Use direct function calls for predictable workflow operations

### Enhanced Context Flow
- **Stockkeeper**: Provides multiple candidates per mention
- **Advisor**: Receives grouped candidates, selects naturally during response generation
- **Fulfiller**: Chooses appropriate products while processing orders
- **Composer**: Works with final selected products for response composition
