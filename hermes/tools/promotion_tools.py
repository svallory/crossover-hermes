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
    new_lines = []  # For free gifts that need to be added as new lines

    # Process each promotion spec
    for promotion in processed_promotion_specs:
        # Check product_combination condition
        if promotion.conditions.product_combination is not None:
            # Check if all required products are in the order
            required_products = set(promotion.conditions.product_combination)
            order_products = {line.product_id for line in order.lines}

            if required_products.issubset(order_products):
                # Apply the promotion effects
                if promotion.effects.apply_discount is not None:
                    discount_spec = promotion.effects.apply_discount
                    target_product_id = discount_spec.to_product_id

                    # Find the target product line
                    for line in order.lines:
                        if (
                            target_product_id is None
                            or line.product_id == target_product_id
                        ):
                            # Ensure unit_price is set
                            if line.unit_price is None:
                                line.unit_price = line.base_price

                            if discount_spec.type == "percentage":
                                discount_amount = line.unit_price * (
                                    discount_spec.amount / 100
                                )
                                line.unit_price -= discount_amount
                                total_discount += discount_amount * line.quantity
                                line.promotion_applied = True
                                line.promotion_description = (
                                    f"{discount_spec.amount}% discount applied"
                                )
                            elif discount_spec.type == "fixed":
                                discount_amount = min(
                                    discount_spec.amount, line.unit_price
                                )
                                line.unit_price -= discount_amount
                                total_discount += discount_amount * line.quantity
                                line.promotion_applied = True
                                line.promotion_description = (
                                    f"${discount_spec.amount} discount applied"
                                )

                # Handle free gift
                if promotion.effects.free_gift is not None:
                    # Add free gift description to one of the qualifying products
                    for line in order.lines:
                        if line.product_id in required_products:
                            if line.promotion_description:
                                line.promotion_description += (
                                    f" + Free gift: {promotion.effects.free_gift}"
                                )
                            else:
                                line.promotion_description = (
                                    f"Free gift: {promotion.effects.free_gift}"
                                )
                            line.promotion_applied = True
                            break

    # Process each order line for individual promotions
    for line in order.lines:
        # Reset promotion fields if not already set by combination promotions
        if not line.promotion_applied:
            line.unit_price = line.base_price
            line.promotion_applied = False
            line.promotion_description = None

        # Ensure unit_price is set
        if line.unit_price is None:
            line.unit_price = line.base_price

        # Check each promotion spec for applicability to this line
        for promotion in processed_promotion_specs:
            # Skip combination promotions (already handled above)
            if promotion.conditions.product_combination is not None:
                continue

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
                        discount_amount = min(discount_spec.amount, line.unit_price)
                        line.unit_price -= discount_amount
                        total_discount += discount_amount * line.quantity
                        line.promotion_applied = True
                        line.promotion_description = (
                            f"${discount_spec.amount} discount applied"
                        )
                    elif discount_spec.type == "bogo_half":
                        # BOGO: Buy one get one 50% off
                        # For quantity >= 2, every second item gets 50% off
                        if line.quantity >= 2:
                            discounted_items = line.quantity // 2
                            discount_per_item = line.base_price * 0.5
                            total_item_discount = discount_per_item * discounted_items

                            # Calculate new unit price (average across all items)
                            total_original = line.base_price * line.quantity
                            total_after_discount = total_original - total_item_discount
                            line.unit_price = total_after_discount / line.quantity

                            total_discount += total_item_discount
                            line.promotion_applied = True
                            line.promotion_description = f"Buy one, get one 50% off (saved ${total_item_discount:.2f})"

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

            # Check applies_every condition (e.g., every Nth item gets discount)
            if promotion.conditions.applies_every is not None:
                # Future enhancement: implement applies_every logic
                pass

        # Update the line's total price
        line.total_price = (line.unit_price or line.base_price) * line.quantity

    # Add any new lines for free gifts
    order.lines.extend(new_lines)

    # Update order totals
    order.total_discount = total_discount
    order.total_price = sum(line.total_price or 0.0 for line in order.lines)

    return order
