"""Integration tests for fulfiller agent promotion detection and processing."""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Literal, Optional, cast
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.agents.fulfiller.agent import run_fulfiller
from hermes.agents.fulfiller.models import FulfillerInput, FulfillerOutput
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
from hermes.model.order import Order, OrderLine, OrderLineStatus
from hermes.model.enums import ProductCategory, Season, Agents
from hermes.config import HermesConfig


class TestFulfillerPromotionDetection:
    """Integration tests for fulfiller agent promotion detection."""

    @pytest.fixture
    def hermes_config(self):
        """Create a test configuration for integration testing.
        This will now primarily rely on HermesConfig to pick up defaults
        from environment variables or its internal _DEFAULT_CONFIG,
        ensuring test LLM configuration aligns with the project's base config.
        """
        llm_provider_env = os.getenv("LLM_PROVIDER")
        temp_config_for_provider = HermesConfig()

        llm_provider_to_use = llm_provider_env or temp_config_for_provider.llm_provider

        api_key = os.getenv(f"{llm_provider_to_use.upper()}_API_KEY")
        if not api_key:
            if llm_provider_to_use == "OpenAI":
                api_key = os.getenv("OPENAI_API_KEY")
            elif llm_provider_to_use == "Gemini":
                api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                pytest.skip(
                    f"{llm_provider_to_use.upper()}_API_KEY (or fallback OPENAI/GEMINI_API_KEY) not set - skipping integration test"
                )

        return HermesConfig(
            llm_provider=cast(Literal["OpenAI", "Gemini"], llm_provider_to_use),
            llm_api_key=api_key,
        )

    @pytest.fixture
    def mock_runnable_config(self, hermes_config):
        """Create a mock runnable config."""
        return hermes_config.as_runnable_config()

    def create_product_with_promotion(
        self,
        product_id: str,
        name: str,
        description: str,
        price: float,
        promotion_text: Optional[str] = None,
        promotion_spec: Optional[PromotionSpec] = None,
        category: ProductCategory = ProductCategory.BAGS,
        product_type: str = "bag",
    ):
        """Helper to create a product with promotion information."""
        return Product(
            product_id=product_id,
            name=name,
            description=description,
            category=category,
            product_type=product_type,
            stock=10,
            seasons=[Season.ALL_SEASONS],
            price=price,
            promotion=promotion_spec,
            promotion_text=promotion_text,
        )

    def create_mock_order_response(
        self,
        email_id: str,
        product_id: str,
        name: str,
        quantity: int,
        base_price: float,
        promotion_text: Optional[str] = None,
        promotion_spec: Optional[PromotionSpec] = None,
    ) -> Order:
        """Create a mock order response that simulates LLM output."""
        order_line = OrderLine(
            product_id=product_id,
            name=name,
            description=f"Test product {product_id} - {name}",
            quantity=quantity,
            base_price=base_price,
            unit_price=base_price,
            total_price=base_price * quantity,
            status=OrderLineStatus.CREATED,  # LLM sets initial status
            stock=None,  # Stock will be set by fulfiller agent
            promotion_applied=False,  # Promotions will be applied by fulfiller agent
            promotion_description=promotion_text,
            promotion=promotion_spec,
        )

        return Order(
            email_id=email_id,
            overall_status="created",
            lines=[order_line],
            total_price=base_price * quantity,
            total_discount=0.0,  # Discounts will be calculated by fulfiller agent
            message="Order processed successfully",
            stock_updated=False,  # Stock will be updated by fulfiller agent
        )

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_canvas_beach_bag_bogo_promotion(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that the fulfiller correctly processes Canvas Beach Bag BOGO promotion."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create product with BOGO promotion from CSV data
        bogo_promotion = PromotionSpec(
            conditions=PromotionConditions(min_quantity=2),
            effects=PromotionEffects(
                apply_discount=DiscountSpec(
                    type="bogo_half", amount=50.0, to_product_id="CBG9876"
                )
            ),
        )

        canvas_bag = self.create_product_with_promotion(
            product_id="CBG9876",
            name="Canvas Beach Bag",
            description="Pack your essentials in style with our canvas beach bag. Spacious and durable, this bag features a nautical-inspired print and interior pockets for organization. Perfectly sized for a day at the beach or a weekend getaway. Buy one, get one 50% off!",
            price=24.0,
            promotion_text="Buy one, get one 50% off!",
            promotion_spec=bogo_promotion,
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_001",
            subject="Order Request",
            message="I'd like to order 2 canvas beach bags",
        )

        product_mention_for_stockkeeper = ProductMention(
            product_name="canvas beach bag",
            quantity=2,
        )

        email_analysis = EmailAnalysis(
            email_id="test_001",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I'd like to order 2 canvas beach bags",
                    product_mentions=[product_mention_for_stockkeeper],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[
                (product_mention_for_stockkeeper, [canvas_bag])
            ],
            unresolved_mentions=[],
            metadata="Test metadata for canvas beach bag BOGO.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the fulfiller agent (no mocking - real integration test)
        result = await run_fulfiller(state=fulfiller_input, config=mock_runnable_config)

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_001"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.product_id == "CBG9876"
        assert line.quantity == 2
        assert line.base_price == 24.0

        # Check that promotion was applied
        assert line.promotion_applied
        assert line.promotion_description is not None
        assert "Buy one, get one 50% off" in line.promotion_description

        # Check that total discount was calculated correctly for BOGO
        # For 2 items at $24 each: 1 full price + 1 at 50% off = $24 + $12 = $36
        # Discount = $24 - $12 = $12
        expected_discount = 12.0
        assert order.total_discount is not None
        assert abs(order.total_discount - expected_discount) < 0.01

        # Total should be $36 (not $24 as in the original incorrect output)
        expected_total = 36.0
        assert order.total_price is not None
        assert abs(order.total_price - expected_total) < 0.01

        # Unit price should be $18 (average of $24 + $12 = $36 / 2 items)
        expected_unit_price = 18.0
        assert line.unit_price is not None
        assert abs(line.unit_price - expected_unit_price) < 0.01

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_quilted_tote_percentage_promotion(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that the fulfiller correctly processes Quilted Tote 25% off promotion."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create product with percentage promotion from CSV data
        percentage_promotion = PromotionSpec(
            conditions=PromotionConditions(min_quantity=1),
            effects=PromotionEffects(
                apply_discount=DiscountSpec(
                    type="percentage", amount=25.0, to_product_id="QTP5432"
                )
            ),
        )

        quilted_tote = self.create_product_with_promotion(
            product_id="QTP5432",
            name="Quilted Tote",
            description="Carry your essentials in style with our quilted tote bag. This spacious bag features a classic quilted design, multiple interior pockets, and sturdy handles. A chic and practical choice for work, travel, or everyday use. Limited-time sale - get 25% off!",
            price=29.0,
            promotion_text="Limited-time sale - get 25% off!",
            promotion_spec=percentage_promotion,
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_002",
            subject="Order Request",
            message="I want to buy a quilted tote bag",
        )

        product_mention_for_stockkeeper_tote = ProductMention(
            product_name="quilted tote",
            quantity=1,
        )

        email_analysis = EmailAnalysis(
            email_id="test_002",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I want to buy a quilted tote bag",
                    product_mentions=[product_mention_for_stockkeeper_tote],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[
                (product_mention_for_stockkeeper_tote, [quilted_tote])
            ],
            unresolved_mentions=[],
            metadata="Test metadata for quilted tote promotion.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the fulfiller agent (no mocking - real integration test)
        result = await run_fulfiller(state=fulfiller_input, config=mock_runnable_config)

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_002"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.product_id == "QTP5432"
        assert line.quantity == 1
        assert line.base_price == 29.0

        # Check that promotion was applied
        assert line.promotion_applied
        assert line.promotion_description is not None
        assert "25" in line.promotion_description and "%" in line.promotion_description

        # Check that total discount was calculated (25% off $29 = $7.25 discount)
        expected_discount = 29.0 * 0.25
        assert order.total_discount is not None
        assert abs(order.total_discount - expected_discount) < 0.01

        # Check final price is correct ($29 - $7.25 = $21.75)
        expected_total = 29.0 - expected_discount
        assert order.total_price is not None
        assert abs(order.total_price - expected_total) < 0.01

        # Check unit price is correct ($21.75)
        expected_unit_price = 29.0 - expected_discount
        assert line.unit_price is not None
        assert abs(line.unit_price - expected_unit_price) < 0.01

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_plaid_flannel_vest_combination_promotion(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that the fulfiller correctly processes Plaid Flannel Vest combination promotion."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create combination promotion: Buy PLV8765, get PLD9876 at 50% off
        combination_promotion = PromotionSpec(
            conditions=PromotionConditions(product_combination=["PLV8765", "PLD9876"]),
            effects=PromotionEffects(
                apply_discount=DiscountSpec(
                    type="percentage", amount=50.0, to_product_id="PLD9876"
                )
            ),
        )

        # Create both products
        plaid_vest = self.create_product_with_promotion(
            product_id="PLV8765",
            name="Plaid Flannel Vest",
            description="Layer up with our plaid flannel vest. This cozy vest features a classic plaid pattern and is crafted from soft, warm flannel. Perfect for adding a touch of ruggedness to your casual or outdoor looks. Buy one, get a matching plaid shirt at 50% off!",
            price=42.0,
            promotion_text="Buy one, get a matching plaid shirt at 50% off!",
            promotion_spec=combination_promotion,
            category=ProductCategory.MENS_CLOTHING,
            product_type="vest",
        )

        plaid_shirt = self.create_product_with_promotion(
            product_id="PLD9876",
            name="Plaid Button-Down",
            description="Add a touch of classic style to your wardrobe with our plaid button-down shirt. Crafted from soft, lightweight cotton, this shirt features a timeless plaid pattern and a relaxed, comfortable fit. A go-to choice for casual Fridays at the office or weekend brunch.",
            price=49.0,
            category=ProductCategory.MENS_CLOTHING,
            product_type="shirt",
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_combination",
            subject="Order Request",
            message="I'd like to order the plaid flannel vest and matching plaid shirt",
        )

        product_mention_vest = ProductMention(
            product_name="plaid flannel vest",
            quantity=1,
        )
        product_mention_shirt = ProductMention(
            product_name="plaid shirt",
            quantity=1,
        )

        email_analysis = EmailAnalysis(
            email_id="test_combination",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I'd like to order the plaid flannel vest and matching plaid shirt",
                    product_mentions=[product_mention_vest, product_mention_shirt],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[
                (product_mention_vest, [plaid_vest]),
                (product_mention_shirt, [plaid_shirt]),
            ],
            unresolved_mentions=[],
            metadata="Test metadata for combination promotion.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the fulfiller agent (no mocking - real integration test)
        result = await run_fulfiller(state=fulfiller_input, config=mock_runnable_config)

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_combination"
        assert len(order.lines) == 2

        # Find the vest and shirt lines
        vest_line = next(line for line in order.lines if line.product_id == "PLV8765")
        shirt_line = next(line for line in order.lines if line.product_id == "PLD9876")

        # Vest should be full price
        assert vest_line.base_price == 42.0
        assert not vest_line.promotion_applied  # Vest doesn't get discount

        # Shirt should have 50% discount applied
        assert shirt_line.base_price == 49.0
        assert shirt_line.promotion_applied
        assert shirt_line.unit_price == 24.5  # 50% off
        assert shirt_line.promotion_description is not None
        assert (
            "50" in shirt_line.promotion_description
            and "%" in shirt_line.promotion_description
        )

        # Check total discount (50% off $49 = $24.50 discount)
        expected_discount = 49.0 * 0.50
        assert order.total_discount is not None
        assert abs(order.total_discount - expected_discount) < 0.01

        # Total should be $42 + $24.50 = $66.50
        expected_total = 42.0 + 24.5
        assert order.total_price is not None
        assert abs(order.total_price - expected_total) < 0.01

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_bomber_jacket_free_beanie_promotion(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that the LLM correctly processes Bomber Jacket free beanie promotion."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create product with free gift promotion from CSV data
        free_gift_promotion = PromotionSpec(
            conditions=PromotionConditions(min_quantity=1),
            effects=PromotionEffects(free_gift="Free matching beanie"),
        )

        bomber_jacket = self.create_product_with_promotion(
            product_id="BMX5432",
            name="Bomber Jacket",
            description="Channel your inner rebel with our bomber jacket. Crafted from soft, lightweight material, this jacket features a classic bomber silhouette and a trendy, cropped length. Perfect for layering or making a statement on its own. Buy now and get a free matching beanie!",
            price=62.99,
            promotion_text="Buy now and get a free matching beanie!",
            promotion_spec=free_gift_promotion,
            category=ProductCategory.MENS_CLOTHING,
            product_type="jacket",
        )

        # Mock LLM response
        mock_order_response = self.create_mock_order_response(
            email_id="test_004",
            product_id="BMX5432",
            name="Bomber Jacket",
            quantity=1,
            base_price=62.99,
            promotion_text="Buy now and get a free matching beanie!",
            promotion_spec=free_gift_promotion,
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_004",
            subject="Order Request",
            message="I want the bomber jacket",
        )

        product_mention_bomber = ProductMention(
            product_name="bomber jacket",
            quantity=1,
        )

        email_analysis = EmailAnalysis(
            email_id="test_004",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I want the bomber jacket",
                    product_mentions=[product_mention_bomber],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[(product_mention_bomber, [bomber_jacket])],
            unresolved_mentions=[],
            metadata="Test metadata for bomber jacket promotion.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Mock the chain execution directly
        with patch("hermes.agents.fulfiller.agent.FULFILLER_PROMPT") as mock_prompt:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value=mock_order_response.model_dump()
            )
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            # Run the fulfiller agent
            result = await run_fulfiller(
                state=fulfiller_input, config=mock_runnable_config
            )

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_004"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.product_id == "BMX5432"
        assert line.quantity == 1
        assert line.base_price == 62.99

        # Check that promotion was applied
        assert line.promotion_applied
        assert line.promotion_description is not None
        assert (
            "free" in line.promotion_description.lower()
            and "beanie" in line.promotion_description.lower()
        )

        # For free gift promotions, price should remain the same
        assert order.total_price == 62.99
        assert order.total_discount == 0.0  # Free gifts don't affect price

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_knit_mini_dress_bogo_promotion(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that the LLM correctly processes Knit Mini Dress BOGO promotion."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create product with BOGO promotion from CSV data
        bogo_promotion = PromotionSpec(
            conditions=PromotionConditions(min_quantity=2),
            effects=PromotionEffects(
                apply_discount=DiscountSpec(
                    type="percentage", amount=50.0, to_product_id="KMN3210"
                )
            ),
        )

        knit_dress = self.create_product_with_promotion(
            product_id="KMN3210",
            name="Knit Mini Dress",
            description="Effortless and chic, our knit mini dress is a must-have for your wardrobe. Crafted from a soft, stretchy knit material, this form-fitting dress features a flattering silhouette and a trendy, mini length. Perfect for date nights, girls' nights out, or dressing up or down. Limited-time sale - get two for the price of one!",
            price=53.0,
            promotion_text="Limited-time sale - get two for the price of one!",
            promotion_spec=bogo_promotion,
            category=ProductCategory.WOMENS_CLOTHING,
            product_type="dress",
        )

        # Mock LLM response
        mock_order_response = self.create_mock_order_response(
            email_id="test_005",
            product_id="KMN3210",
            name="Knit Mini Dress",
            quantity=2,
            base_price=53.0,
            promotion_text="Limited-time sale - get two for the price of one!",
            promotion_spec=bogo_promotion,
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_005",
            subject="Order Request",
            message="I want 2 knit mini dresses",
        )

        product_mention_knit_dress = ProductMention(
            product_name="knit mini dress",
            quantity=2,
        )

        email_analysis = EmailAnalysis(
            email_id="test_005",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I want 2 knit mini dresses",
                    product_mentions=[product_mention_knit_dress],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[(product_mention_knit_dress, [knit_dress])],
            unresolved_mentions=[],
            metadata="Test metadata for knit dress BOGO.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Mock the chain execution directly
        with patch("hermes.agents.fulfiller.agent.FULFILLER_PROMPT") as mock_prompt:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value=mock_order_response.model_dump()
            )
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            # Run the fulfiller agent
            result = await run_fulfiller(
                state=fulfiller_input, config=mock_runnable_config
            )

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_005"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.product_id == "KMN3210"
        assert line.quantity == 2
        assert line.base_price == 53.0

        # Check that promotion was applied
        assert line.promotion_applied
        assert line.promotion_description is not None
        assert "50" in line.promotion_description and "%" in line.promotion_description

        # Check that total discount was calculated (50% off total = $53 discount)
        expected_discount = 53.0  # 50% off $106 total
        assert order.total_discount is not None
        assert abs(order.total_discount - expected_discount) < 0.01
        assert order.total_price == 53.0  # Price of one dress

    @pytest.mark.asyncio
    @patch("hermes.tools.order_tools.check_stock")
    @patch("hermes.tools.order_tools.update_stock")
    @patch("hermes.tools.catalog_tools.find_alternatives")
    async def test_no_promotion_product(
        self,
        mock_find_alternatives,
        mock_update_stock,
        mock_check_stock,
        mock_runnable_config,
    ):
        """Test that products without promotions are processed correctly."""
        # Setup mocks
        from hermes.tools.order_tools import StockStatus, StockUpdateStatus

        mock_check_stock.return_value = StockStatus(is_available=True, current_stock=10)
        mock_update_stock.return_value = StockUpdateStatus.SUCCESS
        mock_find_alternatives.return_value = []

        # Create product without promotion
        regular_product = Product(
            product_id="RSG8901",
            name="Retro Sunglasses",
            description="Transport yourself back in time with our retro sunglasses. These vintage-inspired shades offer a cool, nostalgic vibe while protecting your eyes from the sun's rays. Perfect for beach days or city strolls.",
            category=ProductCategory.ACCESSORIES,
            product_type="sunglasses",
            stock=10,
            seasons=[Season.SPRING, Season.SUMMER],
            price=26.99,
            promotion=None,
            promotion_text=None,
        )

        # Mock LLM response
        mock_order_response = self.create_mock_order_response(
            email_id="test_006",
            product_id="RSG8901",
            name="Retro Sunglasses",
            quantity=1,
            base_price=26.99,
            promotion_text=None,
            promotion_spec=None,
        )

        # Create test input
        customer_email = CustomerEmail(
            email_id="test_006",
            subject="Order Request",
            message="I want retro sunglasses",
        )

        product_mention_sunglasses = ProductMention(
            product_name="retro sunglasses",
            quantity=1,
        )

        email_analysis = EmailAnalysis(
            email_id="test_006",
            primary_intent="order request",
            segments=[
                Segment(
                    segment_type=SegmentType.ORDER,
                    main_sentence="I want retro sunglasses",
                    product_mentions=[product_mention_sunglasses],
                )
            ],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        stockkeeper_output = StockkeeperOutput(
            candidate_products_for_mention=[
                (product_mention_sunglasses, [regular_product])
            ],
            unresolved_mentions=[],
            metadata="Test metadata for no promotion product.",
            exact_id_misses=[],
        )

        fulfiller_input = FulfillerInput(
            email=customer_email,
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Mock the chain execution directly
        with patch("hermes.agents.fulfiller.agent.FULFILLER_PROMPT") as mock_prompt:
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value=mock_order_response.model_dump()
            )
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            # Run the fulfiller agent
            result = await run_fulfiller(
                state=fulfiller_input, config=mock_runnable_config
            )

        # Verify the result
        assert Agents.FULFILLER in result
        output_or_error = result[Agents.FULFILLER]
        assert isinstance(output_or_error, FulfillerOutput)
        fulfiller_output = cast(FulfillerOutput, output_or_error)

        order = fulfiller_output.order_result
        assert order.email_id == "test_006"
        assert len(order.lines) == 1

        line = order.lines[0]
        assert line.product_id == "RSG8901"
        assert line.quantity == 1
        assert line.base_price == 26.99

        # Check that no promotion was applied
        assert not line.promotion_applied
        assert line.promotion_description is None

        # Check that no discount was applied
        assert order.total_discount == 0.0
        assert order.total_price == 26.99
