from typing import List, Any, Union

from hermes.model.order import Order
from hermes.model.promotions import PromotionSpec


def apply_promotion(
    order: Order,
    promotion_specs: Union[list[PromotionSpec], list[dict[str, Any]]],
) -> Order:
    """Apply promotions to an existing order and modify it in place.

    This tool processes an existing Order object and applies any applicable promotions based on
    the provided promotion specifications. It handles different types of promotions including
    quantity-based discounts, product combinations, and free items.

    Args:
        order: The Order object to apply promotions to.
        promotion_specs: List of PromotionSpec objects or dictionaries defining the promotions to apply.

    Returns:
        The modified Order object with all promotions applied and totals recalculated
    """
    # Convert dictionaries to PromotionSpec objects if needed
    processed_promotion_specs: List[PromotionSpec] = []
    for spec in promotion_specs:
        if isinstance(spec, dict):
            processed_promotion_specs.append(PromotionSpec.model_validate(spec))
        else:
            processed_promotion_specs.append(spec)

    # Initialize discount tracking
    total_discount = 0.0

    # Process each order line and check for applicable promotions
    for line in order.lines:
        # Reset promotion fields
        original_unit_price = line.base_price
        line.unit_price = line.base_price
        line.promotion_applied = False
        line.promotion_description = None

        # Check each promotion spec for applicability
        for promotion in processed_promotion_specs:
            # Check min_quantity condition
            if (
                promotion.conditions.min_quantity is not None
                and line.quantity >= promotion.conditions.min_quantity
            ):
                # Apply percentage discount if specified
                if promotion.effects.apply_discount is not None and (
                    promotion.effects.apply_discount.to_product_id is None
                    or promotion.effects.apply_discount.to_product_id == line.product_id
                ):
                    discount_spec = promotion.effects.apply_discount
                    if discount_spec.type == "percentage":
                        discount_amount = line.unit_price * (discount_spec.amount / 100)
                        line.unit_price -= discount_amount
                        total_discount += discount_amount * line.quantity
                        line.promotion_applied = True
                        line.promotion_description = (
                            f"{discount_spec.amount}% discount applied"
                        )
                    elif discount_spec.type == "fixed":
                        discount_amount = min(
                            discount_spec.amount, line.unit_price
                        )  # Cannot discount below zero
                        line.unit_price -= discount_amount
                        total_discount += discount_amount * line.quantity
                        line.promotion_applied = True
                        line.promotion_description = (
                            f"${discount_spec.amount} discount applied"
                        )

                # Handle free items if specified
                if promotion.effects.free_items is not None:
                    free_count = min(promotion.effects.free_items, line.quantity)
                    effective_quantity = line.quantity
                    # Calculate effective price considering free items
                    if effective_quantity > 0:
                        discount_per_item = line.unit_price * (
                            free_count / effective_quantity
                        )
                        total_discount += discount_per_item * line.quantity
                        line.unit_price -= discount_per_item
                        line.promotion_applied = True
                        line.promotion_description = f"Buy {effective_quantity - free_count}, get {free_count} free"

                # Handle free gift if specified (don't affect unit price but note in description)
                if promotion.effects.free_gift is not None:
                    line.promotion_applied = True
                    gift_description = promotion.effects.free_gift
                    line.promotion_description = (
                        f"Free gift: {gift_description}"
                        if line.promotion_description is None
                        else f"{line.promotion_description} + Free gift: {gift_description}"
                    )

            # Check product_combination condition
            # This is a more complex condition that would require checking multiple items together
            # For now, we'll implement a simplified version
            if promotion.conditions.product_combination is not None:
                # Future enhancement: implement combination logic
                pass

            # Check applies_every condition (e.g., every Nth item gets discount)
            if promotion.conditions.applies_every is not None:
                # Future enhancement: implement applies_every logic
                pass

        # Update the line's total price
        line.total_price = line.unit_price * line.quantity

    # Update order totals
    order.total_discount = total_discount
    order.total_price = sum(line.total_price or 0.0 for line in order.lines)

    return order
