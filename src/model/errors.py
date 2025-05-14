from typing import Optional
from pydantic import BaseModel

class ProductNotFound(BaseModel):
    """Indicates that a product was not found."""
    message: str
    query_product_id: Optional[str] = None
    query_product_name: Optional[str] = None 