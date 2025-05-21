# Condition literals that can be used in promotion specifications
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator


Condition = Literal[
    "min_quantity",  # Minimum quantity required to activate the promotion
    "applies_every",  # How many items the promotion applies to (e.g., every Nth item gets discount)
    "product_combination",  # A specific combination of products that must all be present in the order
]

# Effect literals that can be used in promotion specifications
Effect = Literal[
    "free_items",  # Add free items of the same product
    "free_gift",  # Add a free gift with description (not a specific product)
    "apply_discount",  # Apply a configurable discount to specific products
]


# Type for discount specification
class DiscountSpec(BaseModel):
    """Specification for a discount."""

    to_product_id: Optional[str] = Field(
        default=None, description="Optional ID of product to apply discount to (if omitted, applies to all)"
    )
    type: Literal["percentage", "fixed"] = Field(description="Type of discount")
    amount: float = Field(gt=0, description="Amount of discount (percentage or fixed amount)")


class PromotionConditions(BaseModel):
    """Strongly typed model for promotion conditions."""

    min_quantity: Optional[int] = Field(
        default=None, ge=1, description="Minimum quantity required to activate the promotion"
    )
    applies_every: Optional[int] = Field(
        default=None, ge=1, description="How many items the promotion applies to (e.g., every Nth item gets discount)"
    )
    product_combination: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        description="A specific combination of product IDs that must all be present in the order",
    )

    @field_validator("product_combination")
    def validate_product_combination(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("product_combination must contain at least one product ID")
        return v


class PromotionEffects(BaseModel):
    """Strongly typed model for promotion effects."""

    free_items: Optional[int] = Field(default=None, ge=1, description="Number of free items of the same product to add")
    free_gift: Optional[str] = Field(
        default=None, min_length=1, description="Description of a free gift to include with the order"
    )
    apply_discount: Optional[DiscountSpec] = Field(default=None, description="Specification for a discount to apply")

    @field_validator("free_gift")
    def validate_free_gift(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("free_gift description cannot be empty")
        return v


class PromotionSpec(BaseModel):
    """Model representing a promotion with conditions and effects."""

    conditions: PromotionConditions = Field(description="Conditions that must be met to trigger this promotion")
    effects: PromotionEffects = Field(description="Effects that are applied when the promotion is triggered")

    @field_validator("conditions")
    def validate_conditions(cls, v):
        # Ensure at least one condition is set
        if not any(getattr(v, field) is not None for field in v.model_fields):
            raise ValueError("At least one condition must be specified")
        return v

    @field_validator("effects")
    def validate_effects(cls, v):
        # Ensure at least one effect is set
        if not any(getattr(v, field) is not None for field in v.model_fields):
            raise ValueError("At least one effect must be specified")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "conditions": {"min_quantity": 2, "product_combination": ["product-123", "product-456"]},
                    "effects": {
                        "free_items": 1,
                        "apply_discount": {"to_product_id": "product-123", "type": "percentage", "amount": 10.0},
                    },
                }
            ]
        }
    }
