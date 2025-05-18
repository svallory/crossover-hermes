# Tools

This module provides specialized tools for our agents to interact with external systems and data.

## Organization

We've organized tools by their primary purpose:

1. **Catalog Tools** (`catalog_tools.py`): 
   - For looking up and searching products in the catalog
   - Includes vector search capabilities for semantic retrieval

2. **Order Tools** (`order_tools.py`):
   - For inventory management (checking stock, updating quantities)
   - For finding alternatives to out-of-stock items
   - For extracting promotions from product descriptions

3. **Response Tools** (`response_tools.py`):
   - For analyzing customer communication tone
   - For extracting questions from text
   - For generating natural language responses

## Design Principles

Our tools follow these key design principles:

1. **Clearly Defined Purpose**: Each tool has a single, focused responsibility.

2. **LLM-Friendly Documentation**: We provide detailed docstrings with clear parameters and return values, helping LLMs understand how to use the tools.

3. **Strong Typing**: Using Pydantic models for inputs and outputs ensures robustness.

4. **Error Handling**: Tools return structured error objects instead of raising exceptions, making error flows more predictable.

5. **Statelessness**: Tools generally don't maintain state between calls, with the exception of required resources like database connections.

```python {cell}
# In this section, we'll define our tools that enable agents to interact with the product catalog, 
# manage inventory, process orders, and generate customer-friendly responses.
# Each tool is decorated with @tool and has careful type annotations to help LLMs use them correctly.
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field 