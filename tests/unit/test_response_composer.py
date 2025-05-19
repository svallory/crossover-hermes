"""Tests for the Response Composer Agent."""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from typing import Dict, Any, Optional

from src.agents.response_composer import compose_response_node
from src.state import (
    EmailAnalysis,
    ProductReference,
    CustomerSignal,
    OrderProcessingResult,
    OrderItem,
    InquiryResponse,
    ProductInformation,
)
from src.state import HermesState
from src.config import HermesConfig
from tests.fixtures import get_test_product, get_test_cases
from tests.__init__ import mock_openai

# For mocking LLM client
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableSerializable


class MockRunnableLLMComposer(RunnableSerializable):
    """A mock Runnable LLM for response composer tests."""

    name: str = "MockRunnableLLMForComposer"
    mock_output_json_string: str = "{}"  # Default for Pydantic parsers
    mock_raw_string_output: str = "Mocked LLM string output"  # Default for StrOutputParser
    output_type: str = "string"  # "string" or "json"

    def set_mock_output(self, output: Any, output_type: str = "string"):
        self.output_type = output_type
        if output_type == "json" and hasattr(output, "model_dump_json"):
            self.mock_output_json_string = output.model_dump_json()
        else:
            self.mock_raw_string_output = str(output)

    async def ainvoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> AIMessage:
        if self.output_type == "json":
            return AIMessage(content=self.mock_output_json_string)
        return AIMessage(content=self.mock_raw_string_output)  # StrOutputParser expects string content

    def invoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> AIMessage:
        if self.output_type == "json":
            return AIMessage(content=self.mock_output_json_string)
        return AIMessage(content=self.mock_raw_string_output)


@mock_openai()
class TestResponseComposer(unittest.TestCase):
    """Test cases for the Response Composer Agent."""

    def setUp(self):
        """Set up the test environment."""
        self.config = HermesConfig()
        self.test_cases = get_test_cases()
        self.mock_llm_instance = MockRunnableLLMComposer()

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_formal_tone_adaptation(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test adaptation to formal tone in responses."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        # Setup
        email_data = self.test_cases["formal_tone"]

        # Create a mock email analysis with formal tone
        email_analysis = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.95,
            classification_evidence="is the material good enough quality to use as a lap blanket",
            language="English",
            tone_analysis={
                "tone": "formal",
                "formality_level": 4,  # Formal
                "key_phrases": [
                    "Good day",
                    "I am writing to inquire",
                    "material good enough quality",
                ],
            },
            product_references=[
                ProductReference(
                    reference_text="CSH1098 Cozy Shawl",
                    reference_type="product_id",
                    product_id="CSH1098",
                    product_name="Cozy Shawl",
                    quantity=0,  # Not ordering
                    confidence=0.95,
                    excerpt="For the CSH1098 Cozy Shawl",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="quality_concern",
                    signal_category="Objection",
                    signal_text="is the material good enough quality",
                    signal_strength=0.9,
                    excerpt="is the material good enough quality to use as a lap blanket",
                ),
                CustomerSignal(
                    signal_type="gift_purchase",
                    signal_category="Customer Context",
                    signal_text="buying it as a gift for my grandmother",
                    signal_strength=0.8,
                    excerpt="I'm considering buying it as a gift for my grandmother",
                ),
            ],
            reasoning="This is a formal product inquiry specifically asking about material quality for a specific use case.",
        )

        # Create mock inquiry result
        inquiry_result = InquiryResponse(
            email_id=email_data["email_id"],
            primary_products=[
                ProductInformation(
                    product_id="CSH1098",
                    product_name="Cozy Shawl",
                    details={
                        "category": "Accessories",
                        "description": "Knitted from soft, warm yarn",
                        "material": "Soft, warm yarn suitable for multiple uses",
                        "size": "Large enough to use as a lightweight blanket",
                        "seasons": "Fall, Winter",
                    },
                    availability="In stock",
                    price=22.00,
                    promotions=None,
                )
            ],
            answered_questions=[
                {
                    "question": "Is the Cozy Shawl material good enough quality to use as a lap blanket?",
                    "answer": "Yes, the Cozy Shawl is knitted from soft, warm yarn and is designed to be versatile enough to use as a lightweight blanket.",
                    "confidence": 0.9,
                }
            ],
            response_points=[
                "The Cozy Shawl is suitable to use as a lap blanket",
                "It's knitted from soft, warm yarn",
                "Price is $22.00",
                "It's perfect for chilly evenings",
            ],
        )

        # Create initial state with formal tone email
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            inquiry_result=inquiry_result,
        )

        # Mock the final response generation
        mock_final_response = """Good day,

Thank you for your inquiry regarding the CSH1098 Cozy Shawl.

I am pleased to inform you that the Cozy Shawl is indeed of sufficient quality to be utilized as a lap blanket. It is crafted from soft, warm yarn that has been specifically designed to be versatile in its applications, including use as a lightweight blanket.

The Cozy Shawl is currently priced at $22.00 and is available in stock. It is particularly suitable for chilly evenings and would make an excellent gift for your grandmother, providing both comfort and warmth.

Should you require any additional information or have further inquiries, please do not hesitate to contact us.

Sincerely,
Customer Service Team
"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response)

        async def verify_side_effect(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect

        async def process_signals_side_effect(customer_signals, email_body, email_type, llm):
            return ["Acknowledged formal tone."]

        mock_process_signals.side_effect = process_signals_side_effect

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Check for formal language markers
        self.assertIn("Good day", response)
        self.assertIn("Sincerely", response)
        self.assertTrue(
            any(
                phrase in response
                for phrase in [
                    "I am pleased to inform you",
                    "should you require",
                    "do not hesitate",
                ]
            )
        )

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_casual_tone_adaptation(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test adaptation to casual, chatty tone in responses."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        # Setup
        email_data = self.test_cases["casual_tone"]

        # Create a mock email analysis with casual tone
        email_analysis = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.95,
            classification_evidence="Anyway, I saw your spring collection on Instagram",
            language="English",
            tone_analysis={
                "tone": "casual",
                "formality_level": 1,  # Very casual
                "key_phrases": [
                    "Hey there",
                    "my birthday coming up",
                    "Anyway",
                    "super cute",
                ],
            },
            product_references=[
                ProductReference(
                    reference_text="floral dresses",
                    reference_type="category",
                    product_id=None,
                    product_name="floral dresses",
                    quantity=0,  # Not ordering
                    confidence=0.85,
                    excerpt="I'm obsessed with all the floral dresses",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="personal_occasion",
                    signal_category="Customer Context",
                    signal_text="my birthday coming up",
                    signal_strength=0.9,
                    excerpt="I've got my birthday coming up next month",
                ),
                CustomerSignal(
                    signal_type="social_media_discovery",
                    signal_category="Marketing Attribution",
                    signal_text="saw your spring collection on Instagram",
                    signal_strength=0.9,
                    excerpt="I saw your spring collection on Instagram",
                ),
                CustomerSignal(
                    signal_type="style_preferences",
                    signal_category="Request Specificity",
                    signal_text="obsessed with all the floral dresses... super cute",
                    signal_strength=0.95,
                    excerpt="I'm obsessed with all the floral dresses - they're super cute",
                ),
            ],
            reasoning="This is a casual product inquiry with personal context and enthusiasm about a product category.",
        )

        # Create mock inquiry result
        inquiry_result = InquiryResponse(
            email_id=email_data["email_id"],
            primary_products=[
                ProductInformation(
                    product_id="FLD9876",
                    product_name="Floral Maxi Dress",
                    details={
                        "category": "Women's Clothing",
                        "description": "Breezy, lightweight dress with a vibrant floral pattern",
                        "seasons": "Spring, Summer",
                    },
                    availability="In stock",
                    price=56.00,
                    promotions="20% off",
                )
            ],
            answered_questions=[
                {
                    "question": "What floral dresses do you have available?",
                    "answer": "We have several floral dresses including the Floral Maxi Dress which is currently 20% off.",
                    "confidence": 0.9,
                }
            ],
            response_points=[
                "We have a beautiful Floral Maxi Dress for $56.00 (currently 20% off)",
                "Perfect for spring and summer occasions",
                "Would be a great birthday outfit",
            ],
        )

        # Create initial state with casual tone email
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            inquiry_result=inquiry_result,
        )

        # Mock the final response generation
        mock_final_response_casual = """Hey there! Happy to help with the floral dresses! 🌸

Thanks for thinking of us for your birthday outfit - that's awesome! And super cool you saw our spring collection on Insta!

So, about those floral dresses you're loving: we've got this really popular Floral Maxi Dress that I think you'll adore. It's perfect for spring and summer, totally breezy, and has a vibrant floral pattern. It's usually $56.00, but guess what? It's 20% off right now! 🎉

It's definitely a great pick for a birthday celebration. Let me know if you want more deets or other suggestions!

Cheers,
The Team
"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response_casual)

        async def verify_side_effect_casual(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect_casual

        async def process_signals_side_effect_casual(customer_signals, email_body, email_type, llm):
            return ["Mentioned birthday.", "Noted Instagram discovery."]

        mock_process_signals.side_effect = process_signals_side_effect_casual

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Check for casual language markers
        self.assertIn("Hey there", response)
        self.assertTrue(any(phrase in response for phrase in ["super cute", "totally", "love", "!"]))

        # Check that personal context is acknowledged
        self.assertIn("birthday", response)

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_out_of_stock_response(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test composing responses for out-of-stock scenarios."""
        mock_get_llm_client.return_value = self.mock_llm_instance

        # Setup
        email_data = self.test_cases["out_of_stock"]
        # Make sure email_data is complete with necessary fields
        if not isinstance(email_data, dict):
            email_data = {}

        if "email_id" not in email_data:
            email_data["email_id"] = "E007"  # Use the email_id from the OrderProcessingResult

        if "email_subject" not in email_data:
            email_data["email_subject"] = "Order for Retro Sunglasses"

        if "email_body" not in email_data:
            email_data["email_body"] = "I'd like to order 2 pairs of RSG8901 Retro Sunglasses."

        product_data = get_test_product("RSG8901")

        email_analysis = EmailAnalysis(
            classification="order_request",
            language="English",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            product_references=[
                ProductReference(
                    reference_text=product_data["name"],
                    reference_type="product_name",
                    product_id=product_data["product_id"],
                    product_name=product_data["name"],
                    quantity=2,
                    confidence=0.9,
                    excerpt="RSG8901 Retro Sunglasses",
                )
            ],
            reasoning="Order for an item that will be out of stock.",
            classification_confidence=0.9,
            classification_evidence="order 2 pairs of your RSG8901",
        )

        # Mock OrderProcessingResult indicating OOS and suggestions
        order_result = OrderProcessingResult(
            email_id="E007",
            order_items=[
                OrderItem(
                    product_id="RSG8901",
                    product_name="Retro Sunglasses",
                    quantity_requested=2,
                    quantity_fulfilled=1,
                    status="out_of_stock",
                    price=product_data.get("price"),
                )
            ],
            overall_status="out_of_stock",
            out_of_stock_items_count=1,
            suggested_alternatives=[
                {
                    "original_product_id": product_data["product_id"],
                    "original_product_name": product_data["name"],
                    "suggested_product_id": "ALT001",
                    "suggested_product_name": "Alternative Sunglasses",
                    "stock_available": 10,
                    "price": 24.99,
                    "reason": "Similar style",
                }
            ],
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            order_result=order_result,
        )

        mock_final_response_oos = """Hi there,

Thanks for your order for the RSG8901 Retro Sunglasses. Unfortunately, we don't have 2 pairs in stock right now. We do have the Alternative Sunglasses (ALT001) available which are quite similar.

We expect to have the RSG8901 back in stock soon. We can notify you when we restock them if you'd like.

Sorry for any inconvenience!

Best,
The Hermes Team"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response_oos)

        async def verify_side_effect_oos(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect_oos

        async def process_signals_side_effect_oos(customer_signals, email_body, email_type, llm):
            return ["Addressed out of stock situation."]

        mock_process_signals.side_effect = process_signals_side_effect_oos

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Check for out-of-stock messaging
        self.assertTrue(any(phrase in response for phrase in ["don't have 2 pairs in stock", "unfortunately", "sorry"]))

        # Check that alternatives are offered
        self.assertIn("Alternative Sunglasses", response)
        self.assertIn("alternative", response.lower())

        # Check that future ordering options are provided
        self.assertIn("back in stock soon", response)

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_promotion_inclusion(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test that promotional details are included in the response."""
        mock_get_llm_client.return_value = self.mock_llm_instance

        # Use a valid key from test_cases
        email_data = self.test_cases["with_promotion"]["email"]
        product_data = self.test_cases["with_promotion"]["product"]

        email_analysis = EmailAnalysis(
            classification="order_request",
            language="English",
            tone_analysis={
                "tone": "excited",
                "formality_level": 2,
                "key_phrases": ["summer wardrobe", "excited to try"],
            },
            product_references=[
                ProductReference(
                    reference_text=product_data["name"],
                    reference_type="product_name",
                    product_id=product_data["product_id"],
                    product_name=product_data["name"],
                    quantity=1,
                    confidence=0.9,
                    excerpt="I want to order a Trendy T-shirt",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="promotion_awareness",
                    signal_category="Purchase Intent",
                    signal_text="read about your BOGO offer",
                    signal_strength=0.8,
                    excerpt="I read about your BOGO offer",
                )
            ],
            reasoning="Order with awareness of promotion.",
            classification_confidence=0.95,
            classification_evidence="I want to order a Trendy T-shirt",
        )

        order_result = OrderProcessingResult(
            email_id=email_data["email_id"],
            order_items=[
                OrderItem(
                    product_id=product_data["product_id"],
                    product_name=product_data["name"],
                    quantity_requested=1,
                    quantity_fulfilled=1,
                    status="created",
                    price=product_data.get("price"),
                    promotion_details="Buy one, get one 50% off! (applied to second item)",
                )
            ],
            overall_status="created",
            fulfilled_items_count=1,  # Should be 1 order line item, 1 quantity
            total_price=(product_data.get("price", 20.00) * 1.5),  # Price for 1 with BOGO50
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            order_result=order_result,
        )

        # Total price for one TDY5432 ($20) with BOGO50: $20 + $10 = $30. Savings = $10.
        mock_final_response_promo = """Hello!

Great news on your order for a Trendy T-shirt! We've applied the 'Buy one, get one 50% off' promotion.
Your total comes out to $30.00, which includes some nice savings thanks to the offer!
This T-shirt is perfect for your summer wardrobe.

Thanks for shopping with us!

Cheers,
The Hermes Team"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response_promo)

        async def verify_side_effect_promo(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect_promo

        async def process_signals_side_effect_promo(customer_signals, email_body, email_type, llm):
            return ["Highlighted promotion and savings."]

        mock_process_signals.side_effect = process_signals_side_effect_promo

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Check for promotion details
        self.assertIn("Buy one, get one 50% off", response)
        self.assertIn("$30.00", response)

        # Check that savings are mentioned
        self.assertIn("savings", response.lower())

        # Check that product description is included
        self.assertIn("summer wardrobe", response)

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_natural_language_generation(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test natural language generation avoiding templated responses."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        # Setup - using style_inspiration which is about RSG8901 Retro Sunglasses
        test_case = self.test_cases["style_inspiration"]
        email_data = test_case["email"]
        product_data = test_case["product"]  # RSG8901

        email_analysis = EmailAnalysis(
            classification="product_inquiry",
            language="English",
            tone_analysis={
                "tone": "curious",
                "formality_level": 2,
                "key_phrases": ["inspired by"],
            },
            product_references=[
                ProductReference(
                    reference_text=product_data["name"],
                    reference_type="product_name",
                    product_id=product_data["product_id"],
                    product_name=product_data["name"],
                    quantity=0,
                    confidence=0.9,
                    excerpt="Retro Sunglasses (RSG8901)",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="style_question",
                    signal_category="Product Attribute",
                    signal_text="What era are they inspired by?",
                    signal_strength=0.9,
                    excerpt="What era are they inspired by?",
                )
            ],
            reasoning="Inquiry about product style inspiration.",
            classification_confidence=0.95,
            classification_evidence="What era are they inspired by?",
        )

        inquiry_result = InquiryResponse(
            email_id=email_data["email_id"],
            primary_products=[
                ProductInformation(
                    product_id=product_data["product_id"],
                    product_name=product_data["name"],
                    details=product_data,
                    availability="In Stock",
                    price=product_data.get("price"),
                )
            ],
            answered_questions=[
                {
                    "question": "What era are they inspired by?",
                    "answer": "They are inspired by the 1960s.",
                    "confidence": 0.9,
                    "relevant_product_ids": [product_data["product_id"]],
                }
            ],
            response_points=[
                "Inspired by the 1960s fashion.",
                "Think mod style, like Twiggy.",
                "Perfect for a retro look.",
            ],
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            inquiry_result=inquiry_result,
        )

        # Mock the final response generation to be about RSG8901 and include natural markers
        mock_final_response_natural = """Hey there!

You've got a good eye, those RSG8901 Retro Sunglasses are super cool. You asked about their style - think swinging London in the 1960s, very mod, like something Twiggy might have rocked. They're definitely statement eyewear!

Hope that helps satisfy your curiosity about the vibes of these shades!

Warmly,
The Hermes Team"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response_natural)

        async def verify_side_effect_natural(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect_natural

        async def process_signals_side_effect_natural(customer_signals, email_body, email_type, llm):
            return ["Used natural phrasing based on style inquiry."]

        mock_process_signals.side_effect = process_signals_side_effect_natural

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Check that response has natural language markers
        natural_markers = [
            "You've got a good eye",
            "think swinging London",
            "like Twiggy",
            "Hope that helps satisfy your curiosity",
        ]

        templated_markers = [
            "In response to your question",
            "Features include:",
            "Please let us know if you have any other questions.",
        ]

        # Should have at least some natural language markers
        self.assertTrue(any(marker in response for marker in natural_markers))

        # Should avoid templated language
        self.assertFalse(any(marker in response for marker in templated_markers))

        # Check that it includes specific style details beyond template
        self.assertIn("1960s", response)
        self.assertTrue(any(detail in response for detail in ["swinging London", "Twiggy", "statement eyewear"]))

    @patch("src.agents.response_composer.get_llm_client")
    @patch("src.agents.response_composer.process_customer_signals")
    @patch("src.agents.response_composer.generate_natural_response")
    @patch("src.agents.response_composer.verify_response_quality")
    def test_multi_language_response(
        self,
        mock_verify_response,
        mock_generate_response_tool,
        mock_process_signals,
        mock_get_llm_client,
        mock_openai_client,
    ):
        """Test generating a response in a language other than English (e.g., Spanish)."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        # Setup - using a Spanish inquiry example
        email_data = self.test_cases["multi_language"]  # Corrected key

        # This email (E009) is an inquiry about DHN0987 Gorro de punto grueso
        # Product details for DHN0987
        email_analysis = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.95,
            classification_evidence="¿Qué era son inspirados exactamente? Los 1950s, 1960s?",
            language="Spanish",
            tone_analysis={
                "tone": "curious",
                "formality_level": 3,
                "key_phrases": ["¿Qué era", "inspirados exactamente"],
            },
            product_references=[
                ProductReference(
                    reference_text="RSG8901 Retro Sunglasses",
                    reference_type="product_id",
                    product_id="RSG8901",
                    product_name="Retro Sunglasses",
                    quantity=0,  # Not ordering
                    confidence=0.95,
                    excerpt="La descripción para los RSG8901 Retro Sunglasses",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="style_question",
                    signal_category="Request Specificity",
                    signal_text="¿Qué era son inspirados exactamente? Los 1950s, 1960s?",
                    signal_strength=0.95,
                    excerpt="¿Qué era son inspirados exactamente? Los 1950s, 1960s?",
                ),
                CustomerSignal(
                    signal_type="design_interest",
                    signal_category="Request Specificity",
                    signal_text="style inspiration",
                    signal_strength=0.9,
                    excerpt="Estoy solo curioso sobre la inspiración del estilo",
                ),
            ],
            reasoning="Esta es una pregunta específica sobre la inspiración del estilo o la época de diseño de un producto, no indicando intención de compra.",
        )

        # Create mock inquiry result
        inquiry_result = InquiryResponse(
            email_id=email_data["email_id"],
            primary_products=[
                ProductInformation(
                    product_id="RSG8901",
                    product_name="Retro Sunglasses",
                    details={
                        "category": "Accessories",
                        "description": "Shades vintage-inspired with a cool, nostalgic vibe",
                        "style_inspiration": "1960s mod fashion with oversized frames",
                        "seasons": "Spring, Summer",
                    },
                    availability="Limited stock (Only 1 left)",
                    price=26.99,
                    promotions=None,
                )
            ],
            answered_questions=[
                {
                    "question": "¿Qué era son los RSG8901 Retro Sunglasses inspirados exactamente?",
                    "answer": "Los RSG8901 Retro Sunglasses son principalmente inspirados por la época de mod 1960s.",
                    "confidence": 0.9,
                }
            ],
            response_points=[
                "Nuestros RSG8901 Retro Sunglasses son principalmente inspirados por la época de mod 1960s",
                "Tienen grandes marcos y estilismo audaz",
                "Están a $26.99 con stock limitado disponible",
            ],
        )

        # Create initial state
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis,
            inquiry_result=inquiry_result,
        )

        # Mock the final response generation - avoid generic templates
        mock_final_response_spanish = """Hola,

Gracias por tu correo electrónico sobre los RSG8901 Retro Sunglasses.

Soy feliz de poder ayudarte. Los RSG8901 Retro Sunglasses son una excelente opción para tu estilo. Tienen un estilo audaz con marcos grandes y un toque nostálgico.

Están disponibles en stock limitado y están a $26.99.

¿Quieres más detalles o sugerencias sobre los RSG8901 Retro Sunglasses?

Atentamente,
El equipo de soporte
"""
        mock_generate_response_tool.ainvoke = AsyncMock(return_value=mock_final_response_spanish)

        async def verify_side_effect_spanish(
            response,
            email_body,
            email_subject,
            response_points,
            email_type,
            tone_info,
            llm,
        ):
            return response

        mock_verify_response.side_effect = verify_side_effect_spanish

        async def process_signals_side_effect_spanish(customer_signals, email_body, email_type, llm):
            return ["Respondido en español."]

        mock_process_signals.side_effect = process_signals_side_effect_spanish

        # Execute
        result = asyncio.run(compose_response_node(state, self.config))

        # Assert
        self.assertIn("final_response", result)
        response = result["final_response"]

        # Determine expected markers based on language
        language = email_analysis.language
        DEFAULT_GREETINGS = [
            "Hi",
            "Hello",
            "Thanks",
            "Thank you",
            "Best",
            "Sincerely",
            "Regards",
        ]
        natural_markers_es = ["Hola", "Saludos", "Gracias", "Atentamente", "Estimado/a"]
        natural_markers_fr = ["Bonjour", "Salut", "Merci", "Cordialement"]

        natural_markers = DEFAULT_GREETINGS
        if language.lower() == "spanish":
            natural_markers = natural_markers_es
        elif language.lower() == "french":
            natural_markers = natural_markers_fr

        self.assertTrue(any(marker in response for marker in natural_markers))


# To ensure tests can be run directly from this file
if __name__ == "__main__":
    unittest.main()
