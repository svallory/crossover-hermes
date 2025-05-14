"""Tests for the Inquiry Responder Agent."""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
import pandas as pd
from typing import Dict, Any, List, Optional

from src.agents.inquiry_responder import process_inquiry_node
from src.state import EmailAnalysis, ProductReference, CustomerSignal, InquiryResponse, ProductInformation, QuestionAnswer
from src.state import HermesState
from src.config import HermesConfig
from src.tools.catalog_tools import Product, ProductNotFound
from tests.fixtures import get_test_email, get_test_product, get_test_cases, load_sample_data
from tests.__init__ import mock_openai

# For mocking LLM client
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableSerializable

class MockRunnableLLMInquiry(RunnableSerializable):
    """A mock Runnable LLM for inquiry responder tests."""
    name: str = "MockRunnableLLMForInquiryResponder"
    mock_output_json_string: str = "{}" # Default empty JSON

    # Store the actual Pydantic model instance used to create the JSON string
    _mock_pydantic_object: Optional[Any] = None

    def set_mock_output(self, pydantic_model_instance: Any):
        self._mock_pydantic_object = pydantic_model_instance
        self.mock_output_json_string = pydantic_model_instance.model_dump_json()

    async def ainvoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> AIMessage:
        # In a more sophisticated mock, you might inspect input_data or config
        # For PydanticOutputParser, the content of AIMessage should be a JSON string
        # that the parser can validate against its pydantic_object.
        # For StrOutputParser, it can be any string.
        # Here, we assume it will be parsed by PydanticOutputParser for structured output like QuestionAnswer or response points list.
        # The actual object that was used to create this JSON string can be accessed via self._mock_pydantic_object if needed
        return AIMessage(content=self.mock_output_json_string)

    def invoke(self, input_data: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> AIMessage:
        return AIMessage(content=self.mock_output_json_string)

@mock_openai()
class TestInquiryResponder(unittest.TestCase):
    """Test cases for the Inquiry Responder Agent."""

    def _transform_fixture_to_product_input(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms a product fixture dict to match Product model fields."""
        transformed = fixture_data.copy()
        if 'product ID' in transformed:
            transformed['product_id'] = transformed.pop('product ID')
        if 'stock amount' in transformed:
            transformed['stock_amount'] = int(transformed.pop('stock amount'))
        
        # Ensure all required fields for Product model are present
        for field_name, field_info in Product.model_fields.items():
            if field_name not in transformed and field_info.is_required():
                if field_info.annotation == int:
                    transformed[field_name] = 0 
                elif field_info.annotation == str:
                    transformed[field_name] = f"Default {field_name}"
                elif field_info.annotation == float:
                    transformed[field_name] = 0.0
                # Add other default types if necessary
        return transformed

    def setUp(self):
        """Set up the test environment."""
        self.config = HermesConfig()
        self.test_cases = get_test_cases()
        self.products_df, _ = load_sample_data()
        self.mock_llm = MagicMock()
        self.mock_llm_instance = MockRunnableLLMInquiry()
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.similarity_search_with_score.return_value = []
    
    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_seasonal_inquiry(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference, 
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test handling of seasonal-specific inquiries."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case = self.test_cases["seasonal_inquiry"]
        email_data = test_case["email"]
        product_fixture_raw = test_case["product"]
        transformed_product_fixture = self._transform_fixture_to_product_input(product_fixture_raw)

        mock_product_info = ProductInformation(
            product_id=transformed_product_fixture["product_id"],
            product_name=transformed_product_fixture["name"],
            details=transformed_product_fixture,
            availability="In Stock", # Or derive from fixture if it has this info
            price=transformed_product_fixture.get("price", 20.0)
        )
        
        # Mock extract_questions to raise an exception, forcing process_inquiry_node to use the fallback questions list
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")
        
        # Mock resolve_product_reference - ensure it's async and matches signature
        async def resolve_side_effect(ref_dict, catalog_df, vector_store, llm):
            return mock_product_info # mock_product_info is ProductInformation
        mock_resolve_reference.side_effect = resolve_side_effect
        
        # Mock answer_product_question - ensure it's async and matches signature
        async def answer_side_effect(question, primary_products, product_catalog_df, vector_store, llm):
            return None # No questions to answer
        mock_answer_question.side_effect = answer_side_effect
        
        # Mock generate_response_points - ensure it's async and matches signature
        async def generate_points_side_effect(primary_products, answered_questions, related_products, unanswered_questions, unsuccessful_references, llm):
            return ["This product is great for spring."]
        mock_generate_points.side_effect = generate_points_side_effect
        
        mock_search_products.return_value = [] # Not actively searching via description here

        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry",
            language="English",
            product_references=[
                ProductReference(
                    reference_text=transformed_product_fixture["name"],
                    reference_type="product_name",
                    product_id=transformed_product_fixture["product_id"],
                    product_name=transformed_product_fixture["name"],
                    quantity=0,
                    confidence=0.9,
                    excerpt="about the saddle bag" 
                )
            ],
            customer_signals=[
                CustomerSignal(signal_type="seasonal_preference", signal_category="Context", signal_text="for spring", signal_strength=0.8, excerpt="for spring")
            ],
            classification_confidence=0.9,
            classification_evidence="mock evidence for seasonal inquiry",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            reasoning="Mocked seasonal inquiry"
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))

        self.assertIn("inquiry_result", result)
        inquiry_result_dict = result["inquiry_result"]
        self.assertIsInstance(inquiry_result_dict, dict)
        self.assertIn("This product is great for spring.", inquiry_result_dict.get("response_points", []))
        mock_resolve_reference.assert_called()
        mock_generate_points.assert_called()
        
        if not mock_extract_questions.return_value:
            mock_answer_question.assert_not_called()
        else:
            mock_answer_question.assert_called()
    
    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_occasion_specific_inquiry(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference, 
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test handling of occasion-specific inquiries (e.g., dress for wedding)."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case = self.test_cases["occasion_inquiry"]
        email_data = test_case["email"]
        product_fixture_raw = get_test_product("FLD9876")
        transformed_product_fixture = self._transform_fixture_to_product_input(product_fixture_raw)
        
        mock_product_info = ProductInformation(
            product_id=transformed_product_fixture["product_id"],
            product_name=transformed_product_fixture["name"],
            details=transformed_product_fixture,
            availability="In Stock",
            price=transformed_product_fixture.get("price", 56.00)
        )
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")
        
        # Mock answer_product_question
        mock_q_answer = QuestionAnswer(question="Is this good for a wedding?", answer="Yes, it is perfect.", confidence=0.9, relevant_product_ids=[transformed_product_fixture["product_id"]])
        async def answer_side_effect_occasion(question, primary_products, product_catalog_df, vector_store, llm):
            return {"is_answered": True, "answer_text": mock_q_answer.answer, "confidence": mock_q_answer.confidence, "product_ids": mock_q_answer.relevant_product_ids}
        mock_answer_question.side_effect = answer_side_effect_occasion
        
        # Mock resolve_product_reference
        async def resolve_side_effect_occasion(ref_dict, catalog_df, vector_store, llm):
            return mock_product_info
        mock_resolve_reference.side_effect = resolve_side_effect_occasion
        
        # Mock generate_response_points
        async def generate_points_side_effect_occasion(primary_products, answered_questions, related_products, unanswered_questions, unsuccessful_references, llm):
            return ["Perfect for weddings."]
        mock_generate_points.side_effect = generate_points_side_effect_occasion
        
        mock_search_products.return_value = [Product(**transformed_product_fixture)]

        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry",
            language="English",
            product_references=[
                 ProductReference(
                    reference_text="dress for summer wedding", 
                    reference_type="description", 
                    product_id=None, # Initially unknown
                    product_name="dress for summer wedding",
                    quantity=0, confidence=0.8, excerpt="dress for a summer wedding"
                )
            ],
            customer_signals=[
                CustomerSignal(signal_type="occasion", signal_category="Context", signal_text="summer wedding", signal_strength=0.9, excerpt="summer wedding")
            ],
            classification_confidence=0.9,
            classification_evidence="mock evidence for occasion inquiry",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            reasoning="Mocked occasion inquiry"
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))
        self.assertIn("inquiry_result", result)
        inquiry_result_dict = result["inquiry_result"]
        self.assertIsInstance(inquiry_result_dict, dict)
        self.assertIn("Perfect for weddings.", inquiry_result_dict.get("response_points", []))
        self.assertIn("response_points", inquiry_result_dict)
        mock_answer_question.assert_called()
        mock_generate_points.assert_called()
    
    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_material_quality_inquiry(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference, 
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test handling of material/quality questions."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case = self.test_cases["material_quality"]
        email_data = test_case["email"]
        product_fixture_raw = test_case["product"]
        transformed_product_fixture = self._transform_fixture_to_product_input(product_fixture_raw)

        mock_product_info = ProductInformation(
            product_id=transformed_product_fixture["product_id"],
            product_name=transformed_product_fixture["name"],
            details=transformed_product_fixture,
            availability="In Stock",
            price=transformed_product_fixture.get("price", 22.00)
        )
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")
        
        # Mock answer_product_question
        mock_q_answer_material = QuestionAnswer(question="Is the material good?", answer="Yes, top quality.", confidence=0.9, relevant_product_ids=[transformed_product_fixture["product_id"]])
        async def answer_side_effect_material(question, primary_products, product_catalog_df, vector_store, llm):
             return {"is_answered": True, "answer_text": mock_q_answer_material.answer, "confidence": mock_q_answer_material.confidence, "product_ids": mock_q_answer_material.relevant_product_ids}
        mock_answer_question.side_effect = answer_side_effect_material

        # Mock resolve_product_reference
        async def resolve_side_effect_material(ref_dict, catalog_df, vector_store, llm):
            return mock_product_info
        mock_resolve_reference.side_effect = resolve_side_effect_material
        
        # Mock generate_response_points
        async def generate_points_side_effect_material(primary_products, answered_questions, related_products, unanswered_questions, unsuccessful_references, llm):
            return ["Top quality material."]
        mock_generate_points.side_effect = generate_points_side_effect_material
        
        mock_search_products.return_value = [Product(**transformed_product_fixture)]

        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry",
            language="English", 
            product_references=[{
                "reference_text": transformed_product_fixture["name"], "reference_type": "product_name", 
                "product_id": transformed_product_fixture["product_id"], "product_name": transformed_product_fixture["name"], 
                "quantity": 0, "confidence": 0.9, "excerpt": "test"
            }],
            customer_signals=[
                 CustomerSignal(signal_type="quality_concern", signal_category="Objection", signal_text="is the material good enough", signal_strength=0.9, excerpt="material good enough")
            ],
            classification_confidence=0.9,
            classification_evidence="mock evidence for material quality",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            reasoning="Mocked material quality inquiry"
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))
        self.assertIn("inquiry_result", result)
        inquiry_result_dict = result["inquiry_result"]
        self.assertIsInstance(inquiry_result_dict, dict)
        self.assertIn("Top quality material.", inquiry_result_dict.get("response_points", []))
        self.assertIn("response_points", inquiry_result_dict)
        mock_resolve_reference.assert_called()
        mock_answer_question.assert_called()
        mock_generate_points.assert_called()
    
    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_style_inspiration_inquiry(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference, 
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test handling of style/inspiration questions."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case = self.test_cases["style_inspiration"]
        email_data = test_case["email"]
        # Create a mock product - use RSG8901 instead of JNS001 since we know it exists
        product_data = get_test_product("RSG8901")
        jean_product_fixture = self._transform_fixture_to_product_input(product_data)
        
        mock_product_info = ProductInformation(
            product_id=jean_product_fixture["product_id"],
            product_name=jean_product_fixture["name"],
            details=jean_product_fixture,
            availability="In Stock",
            price=jean_product_fixture.get("price", 45.0)
        )
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")

        # Mock answer_product_question
        mock_q_answer = QuestionAnswer(question="What era are these inspired by?", answer="1960s mod era", confidence=0.9, relevant_product_ids=[jean_product_fixture["product_id"]])
        async def answer_side_effect_style(question, primary_products, product_catalog_df, vector_store, llm):
            return {"is_answered": True, "answer_text": mock_q_answer.answer, "confidence": mock_q_answer.confidence, "product_ids": mock_q_answer.relevant_product_ids}
        mock_answer_question.side_effect = answer_side_effect_style
        
        # Mock resolve_product_reference
        async def resolve_side_effect_style(ref_dict, catalog_df, vector_store, llm):
            return mock_product_info # mock_product_info is ProductInformation
        mock_resolve_reference.side_effect = resolve_side_effect_style
        
        # Mock generate_response_points
        async def generate_points_side_effect_style(primary_products, answered_questions, related_products, unanswered_questions, unsuccessful_references, llm):
            return ["Inspired by 1960s Mod."]
        mock_generate_points.side_effect = generate_points_side_effect_style
        
        # search_products_by_description might be called if the question triggers a broad search for recommendations.
        # This mock should return products that could be style recommendations.
        mock_search_products.return_value = [Product(**jean_product_fixture)]

        # Set up the email analysis object 
        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry", # Make sure this is correct
            language="English", 
            product_references=[
                ProductReference(
                    reference_text=jean_product_fixture["name"], 
                    reference_type="product_name", 
                    product_id=jean_product_fixture["product_id"], 
                    product_name=jean_product_fixture["name"], 
                    quantity=0, 
                    confidence=0.9, 
                    excerpt="test"
                )
            ],
            customer_signals=[
                CustomerSignal(
                    signal_type="style_inspiration_question", 
                    signal_category="Product Attribute",
                    signal_text="What era are these inspired by?", 
                    signal_strength=0.9,
                    excerpt="What era are these inspired by?"
                )
            ],
            classification_confidence=0.9,
            classification_evidence="evidence for style inspiration inquiry",
            tone_analysis={"tone": "curious", "formality_level": 3, "key_phrases": []},
            reasoning="Inquiry about product style inspiration"
        )
        
        # Create the state object with email_analysis set properly
        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj,
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))
        self.assertIn("inquiry_result", result)
        inquiry_result_dict = result["inquiry_result"]
        self.assertIsInstance(inquiry_result_dict, dict)
        self.assertIn("Inspired by 1960s Mod.", inquiry_result_dict.get("response_points", []))
        self.assertIn("response_points", inquiry_result_dict)
        mock_resolve_reference.assert_called()
        mock_answer_question.assert_called()
        mock_generate_points.assert_called()
    
    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_product_not_found_resolution(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference,
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test when resolve_product_reference returns ProductNotFound."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case_name = "seasonal_inquiry"
        test_case_email_data = self.test_cases[test_case_name]["email"]
        
        product_ref_text = "NonExistent Magic Scarf"
        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry",
            language="English",
            product_references=[
                ProductReference(
                    reference_text=product_ref_text,
                    reference_type="product_name",
                    product_name=product_ref_text,
                    quantity=0, confidence=0.9, excerpt=f"looking for {product_ref_text}"
                )
            ],
            classification_confidence=0.9, classification_evidence="mock evidence",
            tone_analysis={"tone": "neutral", "formality_level": 3, "key_phrases": []},
            customer_signals=[], reasoning="Mocked for not found test"
        )
        
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")
        mock_answer_question.return_value = None
        mock_generate_points.return_value = ["Could not find the product you mentioned."]
        mock_search_products.return_value = []

        # Mock resolve_product_reference to return ProductNotFound
        async def resolve_side_effect_not_found(ref_dict, catalog_df, vector_store, llm):
            return ProductNotFound(
                message="Product not found in catalog",
                query_product_name=product_ref_text
            )
        mock_resolve_reference.side_effect = resolve_side_effect_not_found

        state = HermesState(
            email_id=test_case_email_data["email_id"],
            email_subject=test_case_email_data["email_subject"],
            email_body=test_case_email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))
        
        self.assertIn("inquiry_result", result)
        inquiry_result = InquiryResponse(**result["inquiry_result"])
        
        self.assertIn("Could not find the product you mentioned.", inquiry_result.response_points)
        self.assertTrue(any(
            unsuccessful_ref == product_ref_text 
            for unsuccessful_ref in inquiry_result.unsuccessful_references
        ), f"Expected '{product_ref_text}' in unsuccessful_references, got {inquiry_result.unsuccessful_references}")
        mock_resolve_reference.assert_called()
        mock_generate_points.assert_called()

    @patch('src.agents.inquiry_responder.search_products_by_description')
    @patch('src.tools.response_tools.extract_questions')
    @patch('src.agents.inquiry_responder.resolve_product_reference')
    @patch('src.agents.inquiry_responder.answer_product_question')
    @patch('src.agents.inquiry_responder.generate_response_points')
    @patch('src.agents.inquiry_responder.get_llm_client')
    @patch('src.agents.inquiry_responder.find_related_products')
    def test_multi_language_inquiry(
        self, 
        mock_find_related,
        mock_get_llm_client,
        mock_generate_points,
        mock_answer_question,
        mock_resolve_reference, 
        mock_extract_questions, 
        mock_search_products,
        mock_openai_client
    ):
        """Test handling of non-English inquiries (e.g., Spanish)."""
        mock_get_llm_client.return_value = self.mock_llm_instance
        mock_find_related.invoke.return_value = []

        test_case = self.test_cases["multi_language"]
        email_data = test_case
        product_fixture_raw = get_test_product("CHN0987")
        transformed_product_fixture = self._transform_fixture_to_product_input(product_fixture_raw)

        mock_product_info = ProductInformation(
            product_id=transformed_product_fixture["product_id"],
            product_name=transformed_product_fixture["name"],
            details=transformed_product_fixture,
            availability="In Stock",
            price=transformed_product_fixture.get("price", 15.00)
        )
        mock_extract_questions.invoke.side_effect = Exception("Test exception - expected in test environment")
        
        # Mock answer_product_question (assuming it will be answered in detected language or points generated in language)
        mock_q_answer_lang = QuestionAnswer(question="¿De qué material está hecho?", answer="Es de lana y acrílico.", confidence=0.9, relevant_product_ids=[transformed_product_fixture["product_id"]])
        async def answer_side_effect_lang(question, primary_products, product_catalog_df, vector_store, llm):
            return {"is_answered": True, "answer_text": mock_q_answer_lang.answer, "confidence": mock_q_answer_lang.confidence, "product_ids": mock_q_answer_lang.relevant_product_ids}
        mock_answer_question.side_effect = answer_side_effect_lang

        # Mock resolve_product_reference
        async def resolve_side_effect_lang(ref_dict, catalog_df, vector_store, llm):
            return mock_product_info
        mock_resolve_reference.side_effect = resolve_side_effect_lang

        # Mock generate_response_points
        async def generate_points_side_effect_lang(primary_products, answered_questions, related_products, unanswered_questions, unsuccessful_references, llm):
            # For testing, assume points are generated based on the inquiry language context (Spanish)
            return ["Material: Lana y acrílico.", "Perfecto para el invierno."]
        mock_generate_points.side_effect = generate_points_side_effect_lang
        
        mock_search_products.return_value = [Product(**transformed_product_fixture)]

        email_analysis_obj = EmailAnalysis(
            classification="product_inquiry",
            language="Spanish",
            product_references=[
                ProductReference(
                    reference_text="CHN0987 Gorro de punto grueso",
                    reference_type="product_id", 
                    product_id="CHN0987",
                    product_name="Gorro de punto grueso",
                    quantity=0, confidence=0.9, excerpt="pregunta sobre el CHN0987"
                )
            ],
            customer_signals=[],
            classification_confidence=0.95,
            classification_evidence="Pregunta sobre material y uso en invierno",
            tone_analysis={"tone": "inquiring", "formality_level": 4, "key_phrases": ["De qué material", "Es lo suficientemente cálido"]},
            reasoning="El correo es claramente una consulta sobre un producto específico (gorro)."
        )

        state = HermesState(
            email_id=email_data["email_id"],
            email_subject=email_data["email_subject"],
            email_body=email_data["email_body"],
            email_analysis=email_analysis_obj.model_dump(),
            product_catalog_df=self.products_df,
            vector_store=self.mock_vector_store
        )
        
        agent_config = self.config.model_copy(deep=True)

        result = asyncio.run(process_inquiry_node(state.__dict__, agent_config))

        self.assertIn("inquiry_result", result)
        inquiry_result_dict = result["inquiry_result"]
        self.assertIsInstance(inquiry_result_dict, dict)
        self.assertTrue(any("Material: Lana y acrílico." in p for p in inquiry_result_dict.get("response_points", [])))
        self.assertIn("response_points", inquiry_result_dict)
        mock_resolve_reference.assert_called()
        mock_answer_question.assert_called()
        mock_generate_points.assert_called()


if __name__ == "__main__":
    unittest.main() 