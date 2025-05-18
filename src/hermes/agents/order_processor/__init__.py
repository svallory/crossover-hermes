"""
Order Processor Agent - Handles product order requests from customers.

This agent verifies stock availability, updates inventory, suggests alternatives
for out-of-stock items, and processes product promotions.
"""

from .models import (
    OrderedItem,
    ProcessedOrder,
    OrderProcessorInput,
    OrderProcessorOutput,
)
from .process_order import process_order

__all__ = [
    "OrderedItem",
    "ProcessedOrder",
    "OrderProcessorInput",
    "OrderProcessorOutput",
    "process_order",
]
