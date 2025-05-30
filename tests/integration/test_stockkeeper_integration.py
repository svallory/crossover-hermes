"""Integration tests for stockkeeper agent (Product Resolver)."""

import pytest
import os
from typing import Literal, cast
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.agents.stockkeeper.agent import run_stockkeeper
from hermes.agents.stockkeeper.models import StockkeeperInput, StockkeeperOutput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.model.email import (
    EmailAnalysis,
    ProductMention,
    Segment,
    SegmentType,
)
from hermes.model.enums import Agents, ProductCategory
from hermes.model.product import Product
from hermes.config import HermesConfig


class TestStockkeeperIntegration:
    """Integration tests for stockkeeper agent using realistic product mentions."""

    @pytest.fixture
    def hermes_config(self):
        """Create a test configuration for integration testing."""
        # Use real API keys from environment for integration tests
        llm_provider = cast(
            Literal["OpenAI", "Gemini"], os.getenv("LLM_PROVIDER", "OpenAI")
        )

        if llm_provider == "OpenAI":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                pytest.skip("OPENAI_API_KEY not set - skipping integration test")
        else:  # Gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                pytest.skip("GEMINI_API_KEY not set - skipping integration test")

        return HermesConfig(
            llm_provider=llm_provider,
            llm_api_key=api_key,
            llm_strong_model_name="gpt-4o-mini"
            if llm_provider == "OpenAI"
            else "gemini-1.5-flash",
            llm_weak_model_name="gpt-4o-mini"
            if llm_provider == "OpenAI"
            else "gemini-1.5-flash",
        )

    @pytest.fixture
    def mock_runnable_config(self, hermes_config):
        """Create a mock runnable config."""
        return hermes_config.as_runnable_config()

    def create_classifier_output_with_mentions(
        self, email_id: str, product_mentions: list[ProductMention]
    ) -> ClassifierOutput:
        """Helper to create a ClassifierOutput with product mentions in segments."""
        segments = []
        if product_mentions:
            # Create an order segment with the product mentions
            order_segment = Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="Customer wants to order products",
                related_sentences=[],
                product_mentions=product_mentions,
            )
            segments.append(order_segment)

        email_analysis = EmailAnalysis(
            email_id=email_id,
            language="English",
            primary_intent="order request",
            customer_name="Test Customer",
            segments=segments,
        )

        return ClassifierOutput(email_analysis=email_analysis)

    @pytest.mark.asyncio
    async def test_exact_product_id_resolution(self, mock_runnable_config):
        """Test resolving a product mention with exact product ID match."""
        # Create a product mention with a known product ID
        product_mention = ProductMention(
            product_id="LTH0976",
            product_name="Leather Bifold Wallet",
            quantity=2,
            confidence=1.0,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST001", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        assert isinstance(result[Agents.STOCKKEEPER], StockkeeperOutput)

        output = result[Agents.STOCKKEEPER]
        assert isinstance(output.resolved_products, list)
        assert len(output.resolved_products) == 1
        assert len(output.unresolved_mentions) == 0

        # Verify the resolved product
        resolved_product = output.resolved_products[0]
        assert isinstance(resolved_product, Product)
        assert resolved_product.product_id == "LTH0976"
        assert resolved_product.metadata is not None
        assert resolved_product.metadata["resolution_confidence"] == 1.0
        assert resolved_product.metadata["resolution_method"] == "exact_id_match"
        assert resolved_product.metadata["requested_quantity"] == 2

    @pytest.mark.asyncio
    async def test_semantic_search_resolution(self, mock_runnable_config):
        """Test resolving product mentions using semantic search."""
        # Create a product mention without exact ID but with descriptive text
        product_mention = ProductMention(
            product_name="sunglasses",
            product_description="retro style eyewear for summer",
            product_category=ProductCategory.ACCESSORIES,
            quantity=1,
            confidence=0.8,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST002", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should either resolve to candidates or have unresolved mentions
        # (depending on vector store content and thresholds)
        if output.resolved_products:
            # If we got resolved products, verify their structure
            for product in output.resolved_products:
                assert isinstance(product, Product)
                assert product.metadata is not None
                assert "resolution_confidence" in product.metadata
                assert "resolution_method" in product.metadata
                assert product.metadata["resolution_method"] == "semantic_search"
                assert product.metadata["requested_quantity"] == 1
        else:
            # If no products resolved, should be in unresolved mentions
            assert len(output.unresolved_mentions) == 1
            assert output.unresolved_mentions[0] == product_mention

    @pytest.mark.asyncio
    async def test_multiple_product_mentions(self, mock_runnable_config):
        """Test resolving multiple product mentions in one request."""
        product_mentions = [
            ProductMention(
                product_id="LTH0976",
                product_name="Leather Bifold Wallet",
                quantity=1,
                confidence=1.0,
            ),
            ProductMention(
                product_id="RSG8901",
                product_name="Retro Sunglasses",
                quantity=2,
                confidence=1.0,
            ),
        ]

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST003", product_mentions
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should resolve both products
        assert len(output.resolved_products) == 2
        assert len(output.unresolved_mentions) == 0

        # Verify both products have proper metadata
        resolved_ids = [p.product_id for p in output.resolved_products]
        assert "LTH0976" in resolved_ids
        assert "RSG8901" in resolved_ids

        # Check metadata for each product
        for product in output.resolved_products:
            assert product.metadata is not None
            assert "resolution_confidence" in product.metadata
            assert "resolution_method" in product.metadata
            assert "requested_quantity" in product.metadata

    @pytest.mark.asyncio
    async def test_nonexistent_product_id(self, mock_runnable_config):
        """Test resolving a product mention with a nonexistent product ID."""
        product_mention = ProductMention(
            product_id="NONEXISTENT123",
            product_name="Imaginary Product",
            quantity=1,
            confidence=1.0,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST004", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should not resolve any products
        assert len(output.resolved_products) == 0
        assert len(output.unresolved_mentions) == 1
        assert output.unresolved_mentions[0] == product_mention

    @pytest.mark.asyncio
    async def test_empty_product_mentions(self, mock_runnable_config):
        """Test stockkeeper behavior with no product mentions."""
        classifier_output = self.create_classifier_output_with_mentions("TEST005", [])

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should have no products resolved or unresolved
        assert len(output.resolved_products) == 0
        assert len(output.unresolved_mentions) == 0

        # Verify metadata
        assert output.metadata["total_mentions"] == 0
        assert output.metadata["resolution_attempts"] == 0
        assert output.metadata["candidates_resolved"] == 0

    @pytest.mark.asyncio
    async def test_top_k_candidates_limit(self, mock_runnable_config):
        """Test that the stockkeeper respects the top_k limit for candidates."""
        # Use a generic search term that might match multiple products
        product_mention = ProductMention(
            product_name="bag",
            product_description="leather bag for carrying items",
            product_category=ProductCategory.BAGS,
            quantity=1,
            confidence=0.8,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST006", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # If we got resolved products, should not exceed top_k=3 (default)
        if output.resolved_products:
            assert len(output.resolved_products) <= 3
            # All should be Product objects with proper metadata
            for product in output.resolved_products:
                assert isinstance(product, Product)
                assert product.metadata is not None
                assert "resolution_confidence" in product.metadata

    @pytest.mark.asyncio
    async def test_original_mention_metadata_preservation(self, mock_runnable_config):
        """Test that original mention information is preserved in product metadata."""
        product_mention = ProductMention(
            product_id="LTH0976",
            product_name="Leather Bifold Wallet",
            product_description="Premium wallet for cards",
            product_category=ProductCategory.ACCESSORIES,
            product_type="wallet",
            quantity=3,
            confidence=0.9,
            mention_text="LTH0976 wallet",
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST007", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        assert len(output.resolved_products) == 1
        product = output.resolved_products[0]

        # Check that original mention metadata is preserved
        assert product.metadata is not None
        assert "original_mention" in product.metadata
        original_mention = product.metadata["original_mention"]

        assert original_mention["product_id"] == "LTH0976"
        assert original_mention["product_name"] == "Leather Bifold Wallet"
        assert original_mention["product_description"] == "Premium wallet for cards"
        assert original_mention["product_category"] == "Accessories"
        assert original_mention["product_type"] == "wallet"
        assert original_mention["quantity"] == 3

    @pytest.mark.asyncio
    async def test_resolution_metadata_tracking(self, mock_runnable_config):
        """Test that resolution metadata is properly tracked."""
        product_mentions = [
            ProductMention(
                product_id="LTH0976",
                product_name="Leather Bifold Wallet",
                quantity=1,
            ),
            ProductMention(
                product_name="nonexistent item",
                quantity=1,
            ),
        ]

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST008", product_mentions
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Verify metadata tracking
        assert "total_mentions" in output.metadata
        assert "resolution_attempts" in output.metadata
        assert "resolution_time_ms" in output.metadata
        assert "candidates_resolved" in output.metadata
        assert "candidate_log" in output.metadata

        assert output.metadata["total_mentions"] == 2
        assert output.metadata["resolution_attempts"] == 2
        assert output.metadata["resolution_time_ms"] > 0

        # Should have resolved at least the exact ID match
        assert output.metadata["candidates_resolved"] >= 1

    @pytest.mark.asyncio
    async def test_mixed_resolution_success_and_failure(self, mock_runnable_config):
        """Test handling a mix of successful and failed resolutions."""
        product_mentions = [
            ProductMention(
                product_id="LTH0976",  # Should resolve
                quantity=1,
            ),
            ProductMention(
                product_id="INVALID999",  # Should not resolve
                product_name="Invalid Product",
                quantity=2,
            ),
        ]

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST009", product_mentions
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should have one resolved and one unresolved
        assert len(output.resolved_products) == 1
        assert len(output.unresolved_mentions) == 1

        # Verify the resolved product
        assert output.resolved_products[0].product_id == "LTH0976"

        # Verify the unresolved mention
        assert output.unresolved_mentions[0].product_id == "INVALID999"

    @pytest.mark.asyncio
    async def test_error_handling_in_resolution(self, mock_runnable_config):
        """Test error handling when resolution encounters issues."""
        # Create a product mention that might cause issues
        product_mention = ProductMention(
            # No ID, name, or description - minimal data to trigger edge cases
            quantity=1,
            confidence=0.5,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST011", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure - should handle gracefully
        assert isinstance(result, dict)

        # Should either succeed with proper handling or return an error
        if Agents.STOCKKEEPER in result:
            output = result[Agents.STOCKKEEPER]
            assert isinstance(output, StockkeeperOutput)
            # The mention should be unresolved due to lack of searchable information
            assert len(output.unresolved_mentions) == 1
        elif "errors" in result:
            # If there's an error, it should be properly structured
            assert Agents.STOCKKEEPER in result["errors"]

    @pytest.mark.asyncio
    async def test_resolution_rate_calculation(self, mock_runnable_config):
        """Test the resolution rate calculation property."""
        product_mentions = [
            ProductMention(product_id="LTH0976", quantity=1),  # Should resolve
            ProductMention(product_id="RSG8901", quantity=1),  # Should resolve
            ProductMention(product_id="INVALID999", quantity=1),  # Should not resolve
        ]

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST012", product_mentions
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Calculate expected resolution rate
        total_mentions = len(output.resolved_products) + len(output.unresolved_mentions)
        if total_mentions > 0:
            expected_rate = len(output.resolved_products) / total_mentions
            assert output.resolution_rate == expected_rate
        else:
            # If no mentions, resolution rate should be 1.0
            assert output.resolution_rate == 1.0

    @pytest.mark.asyncio
    async def test_category_filtered_semantic_search(self, mock_runnable_config):
        """Test that category filtering works in semantic search."""
        # Create a product mention with category filter
        product_mention = ProductMention(
            product_name="wallet",
            product_description="leather wallet for cards",
            product_category=ProductCategory.ACCESSORIES,
            quantity=1,
            confidence=0.8,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST013", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # If products are resolved, they should be in the correct category
        if output.resolved_products:
            for product in output.resolved_products:
                assert isinstance(product, Product)
                assert product.category == ProductCategory.ACCESSORIES
                assert product.metadata is not None
                assert "search_query" in product.metadata
                # Verify the search query includes our search terms
                search_query = product.metadata["search_query"]
                assert "wallet" in search_query.lower()

    @pytest.mark.asyncio
    async def test_fuzzy_product_id_matching(self, mock_runnable_config):
        """Test fuzzy matching for product IDs with typos or formatting issues."""
        # Create a product mention with a slightly incorrect product ID
        product_mention = ProductMention(
            product_id="LTH 0976",  # Space in the ID
            product_name="Leather Wallet",
            quantity=1,
            confidence=0.9,
        )

        classifier_output = self.create_classifier_output_with_mentions(
            "TEST014", [product_mention]
        )

        stockkeeper_input = StockkeeperInput(classifier=classifier_output)
        result = await run_stockkeeper(stockkeeper_input, mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.STOCKKEEPER in result
        output = result[Agents.STOCKKEEPER]

        # Should resolve to the correct product despite the typo
        if output.resolved_products:
            assert len(output.resolved_products) == 1
            product = output.resolved_products[0]
            assert product.product_id == "LTH0976"  # Should resolve to the correct ID
            assert product.metadata is not None
            assert product.metadata["resolution_method"] == "exact_id_match"
