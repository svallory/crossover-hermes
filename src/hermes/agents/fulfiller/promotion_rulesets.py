"""
Rule-based promotion system for Hermes.

This module provides a flexible, declarative approach to defining promotions
through combinations of conditions and effects. This allows for creating complex
promotion rules without requiring code changes when new promotion types are introduced.
"""

from typing import Dict

from .models import PromotionSpec


# Example promotions defined as dictionaries
EXAMPLE_PROMOTIONS: Dict[str, PromotionSpec] = {
    # Standard percentage discount (e.g. "Get 25% off!")
    "percentage_discount": {
        "conditions": {
            "min_quantity": 1
        },
        "effects": {
            "apply_discount": {
                "type": "percentage",
                "amount": 25
            }
        }
    },
    
    # Fixed amount discount (e.g. "$25 off your order")
    "fixed_amount_discount": {
        "conditions": {
            "min_quantity": 1
        },
        "effects": {
            "apply_discount": {
                "type": "fixed",
                "amount": 25.0
            }
        }
    },

    # 10% discount when buying 3 or more items
    "bulk_discount": {
        "conditions": {
            "min_quantity": 3,
            "applies_every": 1
        },
        "effects": {
            "apply_discount": {
                "type": "percentage",
                "amount": 10
            }
        }
    },
    
    # Buy X Get Y Free (e.g. "Buy one, get one free")
    "buy_x_get_y_free": {
        "conditions": {
            "min_quantity": 2,  # Minimum quantity to activate
            "applies_every": 2  # Apply to every 2 items (buy 1, get 1)
        },
        "effects": {
            "free_items": 1  # Number of free items
        }
    },
    
    # Buy X Get Y at discount (e.g. "Buy one, get one 50% off")
    "buy_x_get_y_discount": {
        "conditions": {
            "min_quantity": 2,  # Minimum quantity to activate
            "applies_every": 2  # Apply to every second items
        },
        "effects": {
            "apply_discount": {
                "type": "percentage",
                "amount": 50
            }
        }
    },
    
    # Free gift (e.g. "Buy now and get a free matching beanie!")
    "free_gift": {
        "conditions": {
            "min_quantity": 1
        },
        "effects": {
            "free_gift": "matching beanie"
        }
    },
    
    # Combo deal (e.g. "When you buy both a jacket and a sweater, get a matching plaid shirt at 50% off!")
    "combo_deal": {
        "conditions": {
            "min_quantity": 1,
            "applies_every": 1,
            "product_combination": ["JKT5432", "SWT7651"]  # All of these products must be present to trigger the promotion
        },
        "effects": {
            "apply_discount": {
                "to_product_id": "SWT7651",  # Product ID to receive the discount
                "type": "percentage",
                "amount": 50     # 50% off the specified product
            }
        }
    }
}