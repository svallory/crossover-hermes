#!/usr/bin/env python3

import asyncio
from hermes.agents.fulfiller.agent import run_fulfiller
from hermes.agents.fulfiller.models import FulfillerInput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.model.email import (
    EmailAnalysis,
    ProductMention,
    Segment,
    SegmentType,
    CustomerEmail,
)
from hermes.model.product import Product
from hermes.model.promotions import (
    PromotionSpec,
    PromotionConditions,
    PromotionEffects,
    DiscountSpec,
)
from hermes.model.enums import ProductCategory, Season, Agents
from hermes.config import HermesConfig


async def debug_fulfiller():
    # Create promotion spec
    percentage_promotion = PromotionSpec(
        conditions=PromotionConditions(min_quantity=1),
        effects=PromotionEffects(
            apply_discount=DiscountSpec(
                type="percentage", amount=25.0, to_product_id="QTP5432"
            )
        ),
    )

    # Create product with promotion
    quilted_tote = Product(
        product_id="QTP5432",
        name="Quilted Tote",
        description="Carry your essentials in style with our quilted tote bag. This spacious bag features a classic quilted design, multiple interior pockets, and sturdy handles. A chic and practical choice for work, travel, or everyday use. Limited-time sale - get 25% off!",
        category=ProductCategory.BAGS,
        product_type="bag",
        stock=10,
        seasons=[Season.ALL_SEASONS],
        price=29.0,
        promotion=percentage_promotion,
        promotion_text="Limited-time sale - get 25% off!",
    )

    # Create test input
    customer_email = CustomerEmail(
        email_id="test_002",
        subject="Order Request",
        message="I want to buy a quilted tote bag",
    )

    email_analysis = EmailAnalysis(
        email_id="test_002",
        primary_intent="order request",
        segments=[
            Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="I want to buy a quilted tote bag",
                product_mentions=[
                    ProductMention(
                        product_name="quilted tote",
                        quantity=1,
                    )
                ],
            )
        ],
    )

    classifier_output = ClassifierOutput(email_analysis=email_analysis)
    stockkeeper_output = StockkeeperOutput(
        resolved_products=[quilted_tote], unresolved_mentions=[]
    )

    fulfiller_input = FulfillerInput(
        email=customer_email,
        classifier=classifier_output,
        stockkeeper=stockkeeper_output,
    )

    hermes_config = HermesConfig(
        llm_provider="OpenAI",
        llm_api_key="test-key",
        llm_model_weak="gpt-3.5-turbo",
        llm_model_strong="gpt-4",
        vector_store_path="./test_chroma_db",
    )

    # Run the fulfiller agent
    print("Running fulfiller agent...")
    result = await run_fulfiller(
        state=fulfiller_input,
        runnable_config={"configurable": {"hermes_config": hermes_config}},
    )

    print(f"Result keys: {result.keys()}")
    if Agents.FULFILLER in result:
        fulfiller_output = result[Agents.FULFILLER]
        print(f"Fulfiller output type: {type(fulfiller_output)}")
        if hasattr(fulfiller_output, "order_result"):
            order = fulfiller_output.order_result
            print(f"\nOrder details:")
            print(f"Email ID: {order.email_id}")
            print(f"Lines count: {len(order.lines)}")

            if order.lines:
                line = order.lines[0]
                print(f"\nLine details:")
                print(f"Product ID: {line.product_id}")
                print(f"Quantity: {line.quantity}")
                print(f"Base price: ${line.base_price}")
                print(f"Unit price: ${line.unit_price}")
                print(f"Total price (line): ${line.total_price}")
                print(f"Promotion applied: {line.promotion_applied}")
                print(f"Promotion description: {line.promotion_description}")

            print(f"\nOrder totals:")
            print(f"Total price: ${order.total_price}")
            print(f"Total discount: ${order.total_discount}")
            print(f"Expected discount: ${29.0 * 0.25}")
            print(f"Difference: ${abs(order.total_discount - 29.0 * 0.25)}")
    else:
        print(f"Error in result: {result}")


if __name__ == "__main__":
    asyncio.run(debug_fulfiller())
