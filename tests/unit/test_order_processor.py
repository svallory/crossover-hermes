"""Tests for the Order Processor Agent."""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import pandas as pd

from src.hermes.agents.order_processor import (
    process_order,
)
from src.hermes.model.product import AlternativeProduct, Product
from src.hermes.model import EmailAnalysis, ProductReference
from src.hermes.state import HermesState
from src.hermes.config import HermesConfig
from src.hermes.tools.order_tools import PromotionDetails
from src.hermes.tools.catalog_tools import ProductNotFound

from tests.fixtures import get_test_product, get_test_cases
from tests.__init__ import mock_openai

# For mocking LLM client
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableSerializable


class MockRunnableLLMOrder(RunnableSerializable):
    """A mock Runnable LLM for order processor tests."""

    name: str = "MockRunnableLLMForOrderProcessor"
    mock_output_json_string: str = "{}"  # Default empty JSON

    def set_mock_output(self, pydantic_model_instance):
        self.mock_output_json_string = pydantic_model_instance.model_dump_json()

    async def ainvoke(self, input, config=None, **kwargs):
        return AIMessage(content=self.mock_output_json_string)

    def invoke(self, input, config=None, **kwargs):
        return AIMessage(content=self.mock_output_json_string)


@mock_openai()
class TestOrderProcessor(unittest.TestCase):
    """Test cases for the Order Processor Agent."""

    def setUp(self):
        """Set up the test environment."""
        self.config = HermesConfig()
        self.test_cases = get_test_cases()
        self.mock_llm_instance = MockRunnableLLMOrder()
        # Helper to create a default EmailAnalysis if one isn't provided by the test case
        self.default_email_analysis = EmailAnalysis(
            classification="order_request",  # Default, can be overridden
            classification_confidence=0.9,
            classification_evidence="Mock evidence",
            language="English",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            product_references=[],  # Should be populated by each test
            customer_signals=[],
            reasoning="Default mock email analysis for order processing.",
        )

    @patch("src.agents.order_processor.verify_order_processing")
    @patch("src.agents.order_processor.extract_promotion")
    @patch("src.agents.order_processor.resolve_product_reference")
    @patch("src.agents.order_processor.find_alternatives_for_oos")
    @patch("src.agents.order_processor.check_stock")
    @patch("src.agents.order_processor.find_product_by_name")
    @patch("src.agents.order_processor.find_product_by_id")
    @patch("src.agents.order_processor.get_llm_client")
    def test_last_item_stock(
        self,
        mock_get_llm_client,  # Corresponds to @patch (bottom one)
        mock_find_by_id,
        mock_find_by_name,
        mock_check_stock,
        mock_find_alternatives,
        mock_resolve_reference,
        mock_extract_promotion,
        mock_verify_processing,  # Corresponds to @patch (top one)
        mock_openai_client,
    ):
        """Test processing an order for the last item in stock."""
        # Setup LLM Mocks
        mock_get_llm_client.return_value = self.mock_llm_instance

        async def async_verify_side_effect(result, llm):
            return result

        mock_verify_processing.side_effect = async_verify_side_effect

        test_case = self.test_cases["last_item_stock"]
        email_data = test_case["email"]
        product_data = test_case["product"]

        email_analysis_obj = self.default_email_analysis.model_copy(deep=True)
        email_analysis_obj.product_references = [
            ProductReference(
                reference_text="RSG8901 Retro Sunglasses",
                reference_type="product_id",
                product_id="RSG8901",
                product_name="Retro Sunglasses",
                quantity=1,
                confidence=0.95,
                excerpt="I would like to order 1 pair of RSG8901 Retro Sunglasses",
            )
        ]
        email_analysis_obj.reasoning = "Order for last item in stock."

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),  # Use model_dump()
            product_catalog_df=pd.DataFrame([product_data]),
        )

        mock_find_alternatives.return_value = []

        # Mock resolve_product_reference to return a Product object
        async def resolve_side_effect(ref, catalog_df, llm):
            return Product(
                product_id="RSG8901",
                name="Retro Sunglasses",
                category="Accessories",
                stock_amount=1,
                description="Cool shades",
                price=product_data.get("price", 25.00),
            )

        mock_resolve_reference.side_effect = resolve_side_effect

        # Mock check_stock to reflect current stock (return dict)
        mock_check_stock.return_value = {
            "product_id": "RSG8901",
            "product_name": "Retro Sunglasses",
            "current_stock": 1,
            "requested_quantity": 1,
            "is_available": True,
        }

        # Mock extract_promotion
        mock_extract_promotion.return_value = PromotionDetails(has_promotion=False)

        result = asyncio.run(process_order_node(state, self.config))  # Pass state object directly

        self.assertIn("order_result", result)
        order_result = result["order_result"]
        self.assertIsNotNone(order_result, "Order result should not be None")
        self.assertEqual(len(order_result["order_items"]), 1)
        self.assertEqual(order_result["order_items"][0]["status"], "created")
        self.assertEqual(order_result["fulfilled_items_count"], 1)

        # Verify that the product_catalog_df in the state has been updated
        self.assertIsNotNone(state.product_catalog_df, "Product catalog DataFrame should exist in state.")
        updated_product_row = state.product_catalog_df[state.product_catalog_df["product_id"] == "RSG8901"]
        self.assertFalse(
            updated_product_row.empty,
            "Product RSG8901 should exist in the updated catalog.",
        )
        # The 'stock_amount' column might be object type if read from string, ensure comparison is with numeric 0
        self.assertEqual(
            pd.to_numeric(updated_product_row["stock_amount"].iloc[0]),
            0,
            "Stock amount for RSG8901 should be 0 after order.",
        )

    @patch("src.agents.order_processor.verify_order_processing")
    @patch("src.agents.order_processor.extract_promotion")
    @patch("src.agents.order_processor.resolve_product_reference")
    @patch("src.agents.order_processor.find_alternatives_for_oos")
    @patch("src.agents.order_processor.update_stock")
    @patch("src.agents.order_processor.check_stock")
    @patch("src.agents.order_processor.find_product_by_name")
    @patch("src.agents.order_processor.find_product_by_id")
    @patch("src.agents.order_processor.get_llm_client")
    def test_exceeds_stock(
        self,
        mock_get_llm_client,
        mock_find_by_id,
        mock_find_by_name,
        mock_check_stock,
        mock_update_stock,
        mock_find_alternatives,
        mock_resolve_reference,
        mock_extract_promotion,
        mock_verify_processing,
        mock_openai_client,
    ):
        """Test processing an order that exceeds available stock."""
        # Setup LLM Mocks
        mock_get_llm_client.return_value = self.mock_llm_instance

        async def async_verify_side_effect(result, llm):
            return result

        mock_verify_processing.side_effect = async_verify_side_effect

        test_case = self.test_cases["exceeds_stock"]
        email_data = test_case["email"]
        product_data = test_case["product"]

        email_analysis_obj = self.default_email_analysis.model_copy(deep=True)
        email_analysis_obj.product_references = [
            ProductReference(
                reference_text="retro sun glasses (RSG8901)",
                reference_type="product_id",
                product_id="RSG8901",
                product_name="Retro Sunglasses",
                quantity=2,
                confidence=0.95,
                excerpt="I'd like to buy 2 pairs of the retro sun glasses (RSG8901)",
            )
        ]
        email_analysis_obj.reasoning = "Order exceeds stock."

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),  # Use model_dump()
            product_catalog_df=pd.DataFrame([product_data]),
        )

        # Mock resolve_product_reference
        async def resolve_side_effect(ref, catalog_df, llm):
            return Product(
                product_id="RSG8901",
                name="Retro Sunglasses",
                category="Accessories",
                stock_amount=1,
                description="Cool shades",
                price=product_data.get("price", 25.00),
            )

        mock_resolve_reference.side_effect = resolve_side_effect

        # Mock check_stock (return dict)
        mock_check_stock.return_value = {
            "product_id": "RSG8901",
            "product_name": "Retro Sunglasses",
            "current_stock": 1,
            "requested_quantity": 2,
            "is_available": False,  # Use a simple boolean False
        }
        
        # Create an alternative product using the new structure
        alt_product = Product(
            product_id="BKR0123",
            name="Biker Shorts",
            description="Comfortable shorts for biking",
            category="Accessories",
            product_type="Shorts",
            stock=10,
            seasons=["Summer"],
            price=19.99
        )
        alternative = AlternativeProduct(
            product=alt_product,
            similarity_score=0.75,
            reason="Similar summer accessory"
        )
        
        mock_find_alternatives.return_value = [alternative.model_dump()]  # Ensure it's a dict if the agent node expects it

        # Mock extract_promotion
        mock_extract_promotion.return_value = PromotionDetails(has_promotion=False)

        result = asyncio.run(process_order_node(state, self.config))  # Pass state object directly

        self.assertIn("order_result", result)
        order_result = result["order_result"]
        self.assertIsNotNone(order_result, "Order result should not be None")
        self.assertEqual(len(order_result["order_items"]), 1)
        self.assertEqual(order_result["order_items"][0]["status"], "out_of_stock")
        self.assertEqual(order_result["out_of_stock_items_count"], 1)
        self.assertGreaterEqual(len(order_result["suggested_alternatives"]), 1)
        mock_update_stock.assert_not_called()

    @patch("src.agents.order_processor.verify_order_processing")
    @patch("src.agents.order_processor.extract_promotion")
    @patch("src.agents.order_processor.resolve_product_reference")
    @patch("src.agents.order_processor.find_alternatives_for_oos")
    @patch("src.agents.order_processor.update_stock")
    @patch("src.agents.order_processor.check_stock")
    @patch("src.agents.order_processor.find_product_by_name")
    @patch("src.agents.order_processor.find_product_by_id")
    @patch("src.agents.order_processor.get_llm_client")
    def test_complex_format_reference(
        self,
        mock_get_llm_client,
        mock_find_by_id,
        mock_find_by_name,
        mock_check_stock,
        mock_update_stock,
        mock_find_alternatives,
        mock_resolve_reference,
        mock_extract_promotion,
        mock_verify_processing,
        mock_openai_client,
    ):
        """Test processing an order with a complex product reference format."""
        # Setup LLM Mocks
        mock_get_llm_client.return_value = self.mock_llm_instance

        async def async_verify_side_effect(result, llm):
            return result

        mock_verify_processing.side_effect = async_verify_side_effect

        test_case = self.test_cases["complex_format"]
        email_data = test_case["email"]
        product_data = test_case["product"]  # CBT8901

        email_analysis_obj = self.default_email_analysis.model_copy(deep=True)
        email_analysis_obj.product_references = [
            ProductReference(
                reference_text="Chelsea Boots [CBT 89 01]",
                reference_type="product_id",  # Will be normalized
                product_id="CBT8901",
                product_name="Chelsea Boots",
                quantity=1,
                confidence=0.9,
                excerpt="I would like to buy Chelsea Boots [CBT 89 01]",
            )
        ]
        email_analysis_obj.reasoning = "Order with complex product ID format."

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=pd.DataFrame([product_data, get_test_product("RSG8901")]),  # Add another product to df
        )

        # Mock resolve_product_reference
        async def resolve_side_effect(ref, catalog_df, llm):
            return Product(
                product_id="CBT8901",
                name="Chelsea Boots",
                category="Footwear",
                stock_amount=product_data.get("stock amount", 5),
                description="Stylish boots",
                price=product_data.get("price", 75.00),
            )

        mock_resolve_reference.side_effect = resolve_side_effect

        # Mock check_stock (return dict)
        mock_check_stock.return_value = {
            "product_id": "CBT8901",
            "product_name": "Chelsea Boots",
            "current_stock": 5,
            "requested_quantity": 1,
            "is_available": True,
        }
        mock_find_alternatives.return_value = []
        # Set up a mock promotion with direct string value that will work with our code
        mock_promo = MagicMock()
        mock_promo.has_promotion = True
        mock_promo.promotion_text = "Buy one get one free!"
        mock_extract_promotion.return_value = mock_promo

        # Configure the mock to return the string directly when accessed
        mock_extract_promotion.invoke.return_value.promotion_text = "Buy one get one free!"

        result = asyncio.run(process_order_node(state, self.config))  # Pass state object directly

        self.assertIn("order_result", result)
        order_result = result["order_result"]
        self.assertIsNotNone(order_result, "Order result should not be None")
        self.assertEqual(len(order_result["order_items"]), 1)
        self.assertEqual(order_result["order_items"][0]["product_id"], "CBT8901")
        self.assertEqual(order_result["order_items"][0]["status"], "created")
        mock_update_stock.assert_called_once()

    @patch("src.agents.order_processor.verify_order_processing")
    @patch("src.agents.order_processor.extract_promotion")
    @patch("src.agents.order_processor.resolve_product_reference")
    @patch("src.agents.order_processor.find_alternatives_for_oos")
    @patch("src.agents.order_processor.update_stock")
    @patch("src.agents.order_processor.check_stock")
    @patch("src.agents.order_processor.find_product_by_name")
    @patch("src.agents.order_processor.find_product_by_id")
    @patch("src.agents.order_processor.get_llm_client")
    def test_multiple_item_order(
        self,
        mock_get_llm_client,
        mock_find_by_id,
        mock_find_by_name,
        mock_check_stock,
        mock_update_stock,
        mock_find_alternatives,
        mock_resolve_reference,
        mock_extract_promotion,
        mock_verify_processing,
        mock_openai_client,
    ):
        """Test processing an order with multiple items."""
        # Setup LLM Mocks
        mock_get_llm_client.return_value = self.mock_llm_instance

        async def async_verify_side_effect(result, llm):
            return result

        mock_verify_processing.side_effect = async_verify_side_effect

        test_case = self.test_cases["multiple_items"]  # Corrected key
        email_data = test_case["email"]
        products_data = test_case["products"]  # List of product dicts

        clf2109_data = next(p for p in products_data if p["product_id"] == "CLF2109")
        fzz1098_data = next(p for p in products_data if p["product_id"] == "FZZ1098")

        email_analysis_obj = self.default_email_analysis.model_copy(deep=True)
        email_analysis_obj.product_references = [
            ProductReference(
                reference_text="cable knit beanies",
                reference_type="product_id",
                product_id="CLF2109",
                product_name="Cable Knit Beanie",
                quantity=5,
                confidence=0.9,
                excerpt="5 cable knit beanies",
            ),
            ProductReference(
                reference_text="fuzzy slippers",
                reference_type="product_id",
                product_id="FZZ1098",
                product_name="Fuzzy Slippers",
                quantity=2,
                confidence=0.9,
                excerpt="2 pairs of fuzzy slippers",
            ),
        ]
        email_analysis_obj.reasoning = "Order for multiple items."

        # Ensure product_catalog_df in state has all relevant products
        # Ensure product_catalog_df in state has all relevant products
        catalog_list = [get_test_product("CLF2109"), get_test_product("FZZ1098")]
        # Add other products if resolve_product_reference might try to access them from the df
        # For instance, if an ID in product_references is slightly off and find_product_by_name is triggered.
        catalog_list.append(get_test_product("RSG8901"))  # Example

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=pd.DataFrame(catalog_list),  # Use all products
        )

        # Mocking resolve_product_reference to handle multiple calls
        async def resolve_product_side_effect(product_ref: Dict[str, Any], catalog_df, llm):
            pid = product_ref.get("product_id")
            if pid == "CLF2109":
                return Product(**self._transform_fixture_to_product_input(clf2109_data))
            elif pid == "FZZ1098":
                return Product(**self._transform_fixture_to_product_input(fzz1098_data))
            return ProductNotFound(message="Product not found in multi-item test mock")

        mock_resolve_reference.side_effect = resolve_product_side_effect

        # Mocking check_stock for multiple items (using side_effect returning dict)
        def check_stock_side_effect(input_dict):
            product_id = input_dict["product_id"]
            requested_quantity = input_dict["requested_quantity"]

            # Use fixture data directly for simplicity
            stock_amount = 0
            product_name = "Unknown"

            if product_id == "CLF2109":
                stock_amount = 2  # From fixture
                product_name = "Cable Knit Beanie"
                # Make sure is_available is True for this test
                is_available = True
            elif product_id == "FZZ1098":
                stock_amount = 2  # From fixture
                product_name = "Fuzzy Slippers"
                # Make sure is_available is True for this test
                is_available = True
            else:
                is_available = False

            return {
                "product_id": product_id,
                "product_name": product_name,
                "current_stock": stock_amount,
                "requested_quantity": requested_quantity,
                "is_available": is_available,
            }

        mock_check_stock.side_effect = check_stock_side_effect

        mock_find_alternatives.return_value = []
        mock_extract_promotion.return_value = PromotionDetails(has_promotion=False)

        result = asyncio.run(process_order_node(state, self.config))  # Pass state object directly

        self.assertIn("order_result", result)
        order_result = result["order_result"]
        self.assertIsNotNone(order_result, "Order result should not be None")
        self.assertEqual(len(order_result["order_items"]), 2)
        self.assertEqual(order_result["fulfilled_items_count"], 2)  # Both should be fulfilled based on typical stock
        self.assertEqual(mock_update_stock.call_count, 2)
        mock_update_stock.assert_any_call(
            product_id="CLF2109",
            quantity_to_decrement=1,
            product_catalog_df=state.product_catalog_df,
        )
        mock_update_stock.assert_any_call(
            product_id="FZZ1098",
            quantity_to_decrement=2,
            product_catalog_df=state.product_catalog_df,
        )

    @patch("src.agents.order_processor.verify_order_processing")
    @patch("src.agents.order_processor.extract_promotion")
    @patch("src.agents.order_processor.resolve_product_reference")
    @patch("src.agents.order_processor.find_alternatives_for_oos")
    @patch("src.agents.order_processor.update_stock")
    @patch("src.agents.order_processor.check_stock")
    @patch("src.agents.order_processor.find_product_by_name")
    @patch("src.agents.order_processor.find_product_by_id")
    @patch("src.agents.order_processor.get_llm_client")
    def test_promotion_detection(
        self,
        mock_get_llm_client,
        mock_find_by_id,
        mock_find_by_name,
        mock_check_stock,
        mock_update_stock,
        mock_find_alternatives,
        mock_resolve_reference,
        mock_extract_promotion,
        mock_verify_processing,
        mock_openai_client,
    ):
        """Test that promotions are correctly detected and applied."""
        # Setup LLM Mocks
        mock_get_llm_client.return_value = self.mock_llm_instance

        async def async_verify_side_effect(result, llm):
            return result

        mock_verify_processing.side_effect = async_verify_side_effect

        test_case = self.test_cases["with_promotion"]
        email_data = test_case["email"]
        product_data = test_case["product"]  # CBG9876

        email_analysis_obj = self.default_email_analysis.model_copy(deep=True)
        email_analysis_obj.product_references = [
            ProductReference(
                reference_text="those amazing bags",
                reference_type="product_name",  # Name based reference
                product_name="Canvas Beach Bag",
                quantity=1,  # Assuming 1 for simplicity here, email is vague
                confidence=0.85,
                excerpt="those amazing bags with the summer vibe",
            )
        ]
        email_analysis_obj.reasoning = "Order with potential promotion."
        email_analysis_obj.customer_signals = [
            {
                "signal_type": "promotion_awareness",
                "signal_text": "read about your BOGO offer",
                "signal_strength": 0.8,
            }
        ]

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=pd.DataFrame([product_data, get_test_product("RSG8901")]),
        )

        # Mock resolve_product_reference for name-based lookup
        # It should find CBG9876 based on "Canvas Beach Bag"
        async def resolve_side_effect(ref, catalog_df, llm):
            return Product(
                product_id="CBG9876",
                name="Canvas Beach Bag",
                category="Accessories",
                stock_amount=20,
                description="Large beach bag",
                price=product_data.get("price", 20.00),
            )

        mock_resolve_reference.side_effect = resolve_side_effect

        # Mock check_stock (return dict)
        mock_check_stock.return_value = {
            "product_id": "CBG9876",
            "product_name": "Canvas Beach Bag",
            "current_stock": 20,
            "requested_quantity": 1,
            "is_available": True,
        }
        mock_find_alternatives.return_value = []
        # Set up a mock promotion with direct string value that will work with our code
        mock_promo = MagicMock()
        mock_promo.has_promotion = True
        mock_promo.promotion_text = "Buy one get one free!"
        mock_extract_promotion.return_value = mock_promo

        # Configure the mock to return the string directly when accessed
        mock_extract_promotion.invoke.return_value.promotion_text = "Buy one get one free!"

        result = asyncio.run(process_order_node(state, self.config))  # Pass state object directly

        self.assertIn("order_result", result)
        order_result = result["order_result"]
        self.assertIsNotNone(order_result, "Order result should not be None")
        self.assertEqual(len(order_result["order_items"]), 1)
        order_item = order_result["order_items"][0]
        # Check the correct field for promotion text
        self.assertIsNotNone(order_item.get("promotion_details"))
        self.assertEqual(order_item["promotion_details"], "Buy one get one free!")
        # Check that extract_promotion was called with the correct description
        mock_extract_promotion.assert_called_once_with(
            product_description="Large beach bag", product_name="Canvas Beach Bag"
        )
        mock_update_stock.assert_called_once()

    # Helper to transform fixture (if needed, or ensure fixtures match Product model)
    def _transform_fixture_to_product_input(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        transformed = fixture_data.copy()
        if "product ID" in transformed:
            transformed["product_id"] = transformed.pop("product ID")
        if "stock amount" in transformed:
            transformed["stock_amount"] = int(transformed.pop("stock amount"))
        if "price" in transformed and isinstance(transformed["price"], str):
            transformed["price"] = float(transformed["price"].replace("$", ""))

        # Ensure all required fields for Product model are present
        # This is a simplified version. A more robust version would check Product.model_fields
        for field_name in ["name", "category", "description"]:
            if field_name not in transformed:
                transformed[field_name] = f"Default {field_name}"
        if "product_id" not in transformed:
            transformed["product_id"] = "DEFAULT_ID"
        if "stock_amount" not in transformed:
            transformed["stock_amount"] = 0
        if "price" not in transformed:
            transformed["price"] = 0.0

        return transformed


if __name__ == "__main__":
    unittest.main()
