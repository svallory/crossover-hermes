"""Tests for the Email Classifier Agent."""

import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableSerializable

from src.hermes.agents.classifier import analyze_email_node
from src.hermes.config import HermesConfig
from src.hermes.state import CustomerSignal, EmailAnalysis, HermesState, ProductReference
from tests.__init__ import mock_openai
from tests.fixtures import get_test_cases

@mock_openai()
class TestEmailClassifier(unittest.IsolatedAsyncioTestCase):
    """Test cases for the Email Classifier Agent."""

    def setUp(self):
        """Set up the test environment."""
        self.config = HermesConfig()
        self.test_cases = get_test_cases()

    @patch("src.hermes.agents.email_classifier.verify_email_analysis")
    @patch("src.hermes.agents.email_classifier.get_llm_client")
    async def test_multi_language_email(self, mock_get_llm_client, mock_verify_analysis, mock_openai_client):
        """Test that Spanish emails are correctly classified and language is detected."""
        # Setup
        email_data = self.test_cases["multi_language"]
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
        )

        # Mock the LLM output to simulate Spanish language detection
        mock_llm_output = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.95,
            classification_evidence="Pregunta sobre material y uso en invierno",
            language="Spanish",
            tone_analysis={
                "tone": "inquiring",
                "formality_level": 4,
                "key_phrases": ["De qué material", "Es lo suficientemente cálido"],
            },
            product_references=[
                ProductReference(
                    reference_text="DHN0987 Gorro de punto grueso",
                    reference_type="product_id",
                    product_id="DHN0987",
                    product_name="Gorro de punto grueso",
                    quantity=1,
                    confidence=0.9,
                    excerpt="tengo una pregunta sobre el DHN0987 Gorro de punto grueso",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="material_question",
                    signal_category="Request Specificity",
                    signal_text="¿De qué material está hecho?",
                    signal_strength=0.9,
                    excerpt="¿De qué material está hecho?",
                ),
                CustomerSignal(
                    signal_type="use_case_question",
                    signal_category="Request Specificity",
                    signal_text="¿Es lo suficientemente cálido para usar en invierno?",
                    signal_strength=0.9,
                    excerpt="¿Es lo suficientemente cálido para usar en invierno?",
                ),
            ],
            reasoning="El correo es claramente una consulta sobre un producto específico (gorro). Pregunta sobre material y si es adecuado para invierno, sin intención de compra.",
        )

        # Configure mock for get_llm_client
        # Define a mock Runnable LLM that PydanticOutputParser can work with
        class MockRunnableLLM(RunnableSerializable):
            # Add name to satisfy RunnableSerializable requirements if necessary, though often optional for basic mocks
            name: str = "MockRunnableLLMForTestMultiLanguage"

            async def ainvoke(self, input, config=None, **kwargs):
                # This mock will be used by the main analysis_chain.
                # It directly returns an AIMessage with the JSON string content,
                # simulating an LLM call that the PydanticOutputParser can process.
                json_string = mock_llm_output.model_dump_json()
                return AIMessage(content=json_string)

            def invoke(self, input, config=None, **kwargs):
                # Synchronous version, for completeness of the Runnable interface.
                json_string = mock_llm_output.model_dump_json()
                return AIMessage(content=json_string)

        mock_llm_instance = MockRunnableLLM()
        mock_get_llm_client.return_value = mock_llm_instance

        # Configure mock for verify_email_analysis to bypass its LLM call
        async def mock_verify_side_effect(analysis_result, *args, **kwargs):
            return analysis_result  # Return the input analysis directly

        mock_verify_analysis.side_effect = mock_verify_side_effect

        # Execute
        result = await analyze_email_node(state.__dict__, self.config)

        # Assert
        self.assertIn("email_analysis", result)
        analysis = result["email_analysis"]
        self.assertEqual(analysis["classification"], "product_inquiry")
        self.assertEqual(analysis["language"], "Spanish")
        self.assertGreaterEqual(len(analysis["product_references"]), 1)
        self.assertGreaterEqual(len(analysis["customer_signals"]), 1)

    @patch("src.hermes.agents.email_classifier.verify_email_analysis")
    @patch("src.hermes.agents.email_classifier.get_llm_client")
    async def test_mixed_intent_email(self, mock_get_llm_client, mock_verify_analysis, mock_openai_client):
        """Test emails with both order elements and future interests."""
        # Setup
        email_data = self.test_cases["mixed_intent"]
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
        )

        # Mock the LLM output to simulate mixed intent detection
        mock_output = EmailAnalysis(
            classification="order_request",
            classification_confidence=0.8,
            classification_evidence="I would like to buy Chelsea Boots [CBT 89 01]",
            language="English",
            tone_analysis={
                "tone": "enthusiastic",
                "formality_level": 3,
                "key_phrases": ["like to buy", "so impressed", "probably next time"],
            },
            product_references=[
                ProductReference(
                    reference_text="Chelsea Boots [CBT 89 01]",
                    reference_type="product_id",
                    product_id="CBT8901",
                    product_name="Chelsea Boots",
                    quantity=1,
                    confidence=0.9,
                    excerpt="I would like to buy Chelsea Boots [CBT 89 01]",
                ),
                ProductReference(
                    reference_text="Fuzzy Slippers - FZZ1098",
                    reference_type="product_id",
                    product_id="FZZ1098",
                    product_name="Fuzzy Slippers",
                    quantity=0,  # Not ordering, just mentioning
                    confidence=0.9,
                    excerpt="the quality of Fuzzy Slippers - FZZ1098 I've bought from you before",
                ),
                ProductReference(
                    reference_text="Retro sunglasses",
                    reference_type="product_name",
                    product_id="RSG8901",
                    product_name="Retro Sunglasses",
                    quantity=0,  # Future interest, not current order
                    confidence=0.8,
                    excerpt="I would like to order Retro sunglasses from you, but probably next time",
                ),
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="direct_purchase_intent",
                    signal_category="Purchase Intent",
                    signal_text="I would like to buy Chelsea Boots",
                    signal_strength=0.95,
                    excerpt="I would like to buy Chelsea Boots [CBT 89 01]",
                ),
                CustomerSignal(
                    signal_type="future_purchase_intent",
                    signal_category="Purchase Intent",
                    signal_text="would like to order Retro sunglasses from you, but probably next time",
                    signal_strength=0.7,
                    excerpt="I would like to order Retro sunglasses from you, but probably next time",
                ),
                CustomerSignal(
                    signal_type="past_purchase",
                    signal_category="Customer Context",
                    signal_text="Fuzzy Slippers - FZZ1098 I've bought from you before",
                    signal_strength=0.8,
                    excerpt="I'm so impressed with the quality of Fuzzy Slippers - FZZ1098 I've bought from you before",
                ),
            ],
            reasoning="This email contains a direct purchase intent for Chelsea Boots which makes it primarily an order request. It also mentions past purchases and future interests, but the main actionable request is for the boots.",
        )

        # Configure mock for get_llm_client
        class MockRunnableLLM(RunnableSerializable):
            name: str = "MockRunnableLLMForTestMixedIntent"

            async def ainvoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

            def invoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

        mock_llm_instance = MockRunnableLLM()
        mock_get_llm_client.return_value = mock_llm_instance

        # Configure mock for verify_email_analysis
        async def mock_verify_side_effect(analysis_result, *args, **kwargs):
            return analysis_result

        mock_verify_analysis.side_effect = mock_verify_side_effect

        # Execute
        result = await analyze_email_node(state.__dict__, self.config)

        # Assert
        self.assertIn("email_analysis", result)
        analysis = result["email_analysis"]
        self.assertEqual(analysis["classification"], "order_request")

        # Check product references
        products = analysis["product_references"]
        self.assertGreaterEqual(len(products), 2)

        # Find the Chelsea Boots reference (primary order item)
        chelsea_boots = next((p for p in products if p["product_id"] == "CBT8901"), None)
        self.assertIsNotNone(chelsea_boots)
        self.assertEqual(chelsea_boots["quantity"], 1)

        # Find the Retro Sunglasses reference (future interest)
        retro_sunglasses = next((p for p in products if p["product_id"] == "RSG8901"), None)
        self.assertIsNotNone(retro_sunglasses)
        self.assertEqual(retro_sunglasses["quantity"], 0)  # Not ordering now

        # Check for future purchase intent signal
        future_intent = next(
            (s for s in analysis["customer_signals"] if s["signal_type"] == "future_purchase_intent"),
            None,
        )
        self.assertIsNotNone(future_intent)

    @patch("src.hermes.agents.email_classifier.verify_email_analysis")
    @patch("src.hermes.agents.email_classifier.get_llm_client")
    async def test_vague_reference_email(self, mock_get_llm_client, mock_verify_analysis, mock_openai_client):
        """Test emails with vague product references like 'that popular item'."""
        # Setup
        email_data = self.test_cases["vague_reference"]
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
        )

        # Mock the LLM output for vague reference
        mock_llm_output = EmailAnalysis(
            classification="product_inquiry",  # Corrected: Vague reference should be inquiry
            classification_confidence=0.7,
            classification_evidence="Vague reference to 'that popular item' suggests user is seeking information.",
            language="English",
            tone_analysis={
                "tone": "curious",
                "formality_level": 3,
                "key_phrases": [
                    "that popular item",
                    "saw on your website",
                    "tell me more",
                ],
            },
            product_references=[
                ProductReference(
                    reference_text="that popular item",
                    reference_type="description",
                    product_id=None,  # Cannot determine ID from vague reference
                    product_name=None,  # Cannot determine name
                    quantity=0,  # No quantity specified, not an order
                    confidence=0.6,
                    excerpt="that popular item I saw on your website",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="information_seeking",
                    signal_category="Intent",
                    signal_text="Can you tell me more about it?",
                    signal_strength=0.85,
                    excerpt="Can you tell me more about it?",
                )
            ],
            reasoning="The email uses a vague term 'that popular item' and asks for more information, which is characteristic of a product inquiry, not an order.",
        )

        # Configure mock for get_llm_client
        class MockRunnableLLM(RunnableSerializable):
            name: str = "MockRunnableLLMForTestVagueRef"

            async def ainvoke(self, input, config=None, **kwargs):
                json_string = mock_llm_output.model_dump_json()
                return AIMessage(content=json_string)

            def invoke(self, input, config=None, **kwargs):
                json_string = mock_llm_output.model_dump_json()
                return AIMessage(content=json_string)

        mock_llm_instance = MockRunnableLLM()
        mock_get_llm_client.return_value = mock_llm_instance

        # Configure mock for verify_email_analysis
        async def mock_verify_side_effect(analysis_result, *args, **kwargs):
            return analysis_result

        mock_verify_analysis.side_effect = mock_verify_side_effect

        # Execute
        result = await analyze_email_node(state.__dict__, self.config)

        # Assert
        self.assertIn("email_analysis", result)
        analysis = result["email_analysis"]
        self.assertEqual(analysis["classification"], "product_inquiry")

        # Check product references
        self.assertGreaterEqual(len(analysis["product_references"]), 1)
        vague_ref = analysis["product_references"][0]
        self.assertIsNone(vague_ref["product_id"])  # Should be None since it's vague
        self.assertLess(vague_ref["confidence"], 0.7)  # Should have low confidence

        # Check for vague product reference signal
        vague_signal = next(
            (s for s in analysis["customer_signals"] if s["signal_type"] == "information_seeking"),
            None,
        )
        self.assertIsNotNone(vague_signal)

    @patch("src.hermes.agents.email_classifier.verify_email_analysis")
    @patch("src.hermes.agents.email_classifier.get_llm_client")
    async def test_missing_subject_email(self, mock_get_llm_client, mock_verify_analysis, mock_openai_client):
        """Test emails with missing subjects."""
        # Setup
        email_data = self.test_cases["missing_subject"]
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject="",  # Empty subject
            email_body=email_data["email_body"],
        )

        # Mock the LLM output
        mock_output = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.85,
            classification_evidence="I was thinking of ordering a pair of CBT8901 Chelsea Boots, but I'll wait until Fall",
            language="English",
            tone_analysis={
                "tone": "casual",
                "formality_level": 2,
                "key_phrases": ["thinking of ordering", "wait until Fall"],
            },
            product_references=[
                ProductReference(
                    reference_text="CBT8901 Chelsea Boots",
                    reference_type="product_id",
                    product_id="CBT8901",
                    product_name="Chelsea Boots",
                    quantity=0,  # Not ordering now
                    confidence=0.95,
                    excerpt="I was thinking of ordering a pair of CBT8901 Chelsea Boots",
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="browsing_intent",
                    signal_category="Purchase Intent",
                    signal_text="I was thinking of ordering... but I'll wait",
                    signal_strength=0.9,
                    excerpt="I was thinking of ordering a pair of CBT8901 Chelsea Boots, but I'll wait until Fall",
                ),
                CustomerSignal(
                    signal_type="seasonal_need",
                    signal_category="Customer Context",
                    signal_text="wait until Fall",
                    signal_strength=0.8,
                    excerpt="I'll wait until Fall to actually place the order",
                ),
            ],
            reasoning="Email has no subject line. Body content suggests a product question rather than an order.",
        )

        # Configure mock for get_llm_client
        class MockRunnableLLM(RunnableSerializable):
            name: str = "MockRunnableLLMForTestMissingSubject"

            async def ainvoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

            def invoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

        mock_llm_instance = MockRunnableLLM()
        mock_get_llm_client.return_value = mock_llm_instance

        # Configure mock for verify_email_analysis
        async def mock_verify_side_effect(analysis_result, *args, **kwargs):
            return analysis_result

        mock_verify_analysis.side_effect = mock_verify_side_effect

        # Execute
        result = await analyze_email_node(state.__dict__, self.config)

        # Assert
        self.assertIn("email_analysis", result)
        analysis = result["email_analysis"]
        self.assertEqual(analysis["classification"], "product_inquiry")

        # Ensure the analysis doesn't depend on subject
        self.assertGreaterEqual(len(analysis["product_references"]), 1)
        self.assertEqual(analysis["product_references"][0]["product_id"], "CBT8901")

        # Check for future intent signal
        browsing_intent = next(
            (s for s in analysis["customer_signals"] if s["signal_type"] == "browsing_intent"),
            None,
        )
        self.assertIsNotNone(browsing_intent)

    @patch("src.hermes.agents.email_classifier.verify_email_analysis")
    @patch("src.hermes.agents.email_classifier.get_llm_client")
    async def test_tangential_info_email(self, mock_get_llm_client, mock_verify_analysis, mock_openai_client):
        """Test emails where primary intent is mixed with tangential info."""
        # Setup
        email_data = self.test_cases["tangential_info"]
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
        )

        # Mock the LLM output
        mock_output = EmailAnalysis(
            classification="product_inquiry",
            classification_confidence=0.8,
            classification_evidence="what were some of the other messenger bag or briefcase style options you have",
            language="English",
            tone_analysis={
                "tone": "rambling",
                "formality_level": 2,
                "key_phrases": [
                    "other messenger bag",
                    "briefcase style options",
                    "really nice leather briefcase",
                ],
            },
            product_references=[
                ProductReference(
                    reference_text="leather briefcase",
                    reference_type="description",
                    product_id=None,  # Generic reference
                    product_name="leather briefcase",
                    quantity=0,  # Not ordering
                    confidence=0.7,
                    excerpt="my wife Emily got me a really nice leather briefcase from your store",
                ),
                ProductReference(
                    reference_text="messenger bag or briefcase",
                    reference_type="category",
                    product_id=None,  # Category reference
                    product_name="messenger bag or briefcase",
                    quantity=0,  # Not ordering
                    confidence=0.8,
                    excerpt="what were some of the other messenger bag or briefcase style options you have",
                ),
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="researching_intent",
                    signal_category="Purchase Intent",
                    signal_text="what were some of the other messenger bag or briefcase style options",
                    signal_strength=0.85,
                    excerpt="what were some of the other messenger bag or briefcase style options you have",
                ),
                CustomerSignal(
                    signal_type="past_purchase",
                    signal_category="Customer Context",
                    signal_text="my wife Emily got me a really nice leather briefcase from your store",
                    signal_strength=0.8,
                    excerpt="my wife Emily got me a really nice leather briefcase from your store",
                ),
                CustomerSignal(
                    signal_type="size_preference",
                    signal_category="Request Specificity",
                    signal_text="something slightly smaller than my previous one",
                    signal_strength=0.7,
                    excerpt="I could go for something slightly smaller than my previous one",
                ),
                CustomerSignal(
                    signal_type="irrelevant_information",
                    signal_category="Irrelevant Information",
                    signal_text="need to get my lawnmower fixed before spring",
                    signal_strength=0.9,
                    excerpt="I also need to get my lawnmower fixed before spring",
                ),
                CustomerSignal(
                    signal_type="irrelevant_information",
                    signal_category="Irrelevant Information",
                    signal_text="dinner reservations for our anniversary",
                    signal_strength=0.9,
                    excerpt="we also need to make dinner reservations for our anniversary next month",
                ),
            ],
            reasoning="Primary intent is an order request for a T-shirt. The mention of jeans is secondary and more of an open-ended question, not directly part of the order itself.",
        )

        # Configure mock for get_llm_client
        class MockRunnableLLM(RunnableSerializable):
            name: str = "MockRunnableLLMForTestTangential"

            async def ainvoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

            def invoke(self, input, config=None, **kwargs):
                json_string = mock_output.model_dump_json()
                return AIMessage(content=json_string)

        mock_llm_instance = MockRunnableLLM()
        mock_get_llm_client.return_value = mock_llm_instance

        # Configure mock for verify_email_analysis
        async def mock_verify_side_effect(analysis_result, *args, **kwargs):
            return analysis_result

        mock_verify_analysis.side_effect = mock_verify_side_effect

        # Execute
        result = await analyze_email_node(state.__dict__, self.config)

        # Assert
        self.assertIn("email_analysis", result)
        analysis = result["email_analysis"]
        self.assertEqual(analysis["classification"], "product_inquiry")

        # Check product references
        self.assertGreaterEqual(len(analysis["product_references"]), 1)

        # Check for irrelevant information signals
        irrelevant_signals = [s for s in analysis["customer_signals"] if s["signal_type"] == "irrelevant_information"]
        self.assertGreaterEqual(len(irrelevant_signals), 2)

        # Check for actual product inquiry signal
        inquiry_signal = next(
            (s for s in analysis["customer_signals"] if s["signal_type"] == "researching_intent"),
            None,
        )
        self.assertIsNotNone(inquiry_signal)

        # Ensure tangential info is handled gracefully (e.g., no product references for lawnmower)
        if analysis["product_references"]:  # Check if list is not empty
            for ref in analysis["product_references"]:
                self.assertNotIn("lawnmower", ref.get("product_name", "").lower())
                self.assertNotIn("lawnmower", ref.get("reference_text", "").lower())
                self.assertNotIn("reservation", ref.get("product_name", "").lower())
                self.assertNotIn("reservation", ref.get("reference_text", "").lower())


if __name__ == "__main__":
    unittest.main()
