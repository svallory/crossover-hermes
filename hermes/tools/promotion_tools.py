from typing import List, Any

from hermes.model.order import OrderLine, Order
from hermes.model.promotions import PromotionSpec


def apply_promotion(
    ordered_items: list[dict[str, Any]],
    promotion_specs: list[dict[str, Any]],
    email_id: str,
) -> Order:
    """Apply promotions to ordered items and create an Order object.

    This tool processes a list of ordered items and applies any applicable promotions based on
    the provided promotion specifications. It handles different types of promotions including
    quantity-based discounts, product combinations, and free items.

    Args:
        ordered_items: List of dictionaries representing ordered items with keys:
                      product_id, description, quantity, base_price.
        promotion_specs: List of promotion specification dictionaries.
        email_id: The email identifier for this order.

    Returns:
        An Order object with all promotions applied and totals calculated
    """
    # Initialize order lines and discount tracking
    order_lines: List[OrderLine] = []
    total_discount = 0.0

    # Convert promotion_specs to PromotionSpec objects if they aren't already
    promotion_specs_objects = []
    for spec_data in promotion_specs:
        if isinstance(spec_data, dict):
            try:
                promotion_specs_objects.append(PromotionSpec(**spec_data))
            except Exception:
                # Skip invalid promotion specs
                pass
        elif isinstance(spec_data, PromotionSpec):
            promotion_specs_objects.append(spec_data)

    # Process each item and check for applicable promotions
    for item in ordered_items:
        # Default values when no promotion applies
        product_id = item.get("product_id", "")
        description = item.get("description", "")
        quantity = item.get("quantity", 1)
        base_price = item.get("base_price", 0.0)

        unit_price = base_price
        promotion_applied = False
        promotion_description = None

        # Check each promotion spec for applicability
        for promotion in promotion_specs_objects:
            # Check min_quantity condition
            if (
                promotion.conditions.min_quantity is not None
                and quantity >= promotion.conditions.min_quantity
            ):
                # Apply percentage discount if specified
                if promotion.effects.apply_discount is not None and (
                    promotion.effects.apply_discount.to_product_id is None
                    or promotion.effects.apply_discount.to_product_id == product_id
                ):
                    discount_spec = promotion.effects.apply_discount
                    if discount_spec.type == "percentage":
                        discount_amount = unit_price * (discount_spec.amount / 100)
                        unit_price -= discount_amount
                        total_discount += discount_amount * quantity
                        promotion_applied = True
                        promotion_description = (
                            f"{discount_spec.amount}% discount applied"
                        )
                    elif discount_spec.type == "fixed":
                        discount_amount = min(
                            discount_spec.amount, unit_price
                        )  # Cannot discount below zero
                        unit_price -= discount_amount
                        total_discount += discount_amount * quantity
                        promotion_applied = True
                        promotion_description = (
                            f"${discount_spec.amount} discount applied"
                        )

                # Handle free items if specified
                if promotion.effects.free_items is not None:
                    free_count = min(promotion.effects.free_items, quantity)
                    effective_quantity = quantity
                    # Calculate effective price considering free items
                    if effective_quantity > 0:
                        discount_per_item = unit_price * (
                            free_count / effective_quantity
                        )
                        total_discount += discount_per_item * quantity
                        unit_price -= discount_per_item
                        promotion_applied = True
                        promotion_description = f"Buy {effective_quantity - free_count}, get {free_count} free"

                # Handle free gift if specified (don't affect unit price but note in description)
                if promotion.effects.free_gift is not None:
                    promotion_applied = True
                    gift_description = promotion.effects.free_gift
                    promotion_description = (
                        f"Free gift: {gift_description}"
                        if promotion_description is None
                        else f"{promotion_description} + Free gift: {gift_description}"
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

        # Create the order line with final price using Pydantic model
        order_line = OrderLine(
            product_id=product_id,
            description=description,
            quantity=quantity,
            base_price=base_price,
            unit_price=unit_price,
            total_price=unit_price * quantity,
            promotion_applied=promotion_applied,
            promotion_description=promotion_description,
        )

        order_lines.append(order_line)

    # Create and return the final order using Pydantic model
    order = Order(
        email_id=email_id,
        overall_status="created" if order_lines else "no_valid_products",
        lines=order_lines,
        total_discount=total_discount,
        total_price=sum(line.total_price or 0.0 for line in order_lines),
        stock_updated=False,
    )

    return order
