"""
Order Processor Agent - Handles product order requests from customers.

This agent verifies stock availability, updates inventory, suggests alternatives
for out-of-stock items, and processes product promotions.
"""

from .models import *
from .agent import *
from .prompts import *
from .promotion_rulesets import *