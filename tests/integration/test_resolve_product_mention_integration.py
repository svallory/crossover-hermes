"""Integration tests for the resolve_product_mention function."""

import pytest
from hermes.tools.catalog_tools import resolve_product_mention
from hermes.model.email import ProductMention
from hermes.model.enums import ProductCategory
from hermes.model.errors import ProductNotFound
from hermes.model.product import Product
# from unittest.mock import patch, AsyncMock # Not typically used for integration tests unless specific passthroughs are needed


class TestResolveProductMentionIntegration:
    """Integration test cases for the resolve_product_mention function."""

    @pytest.mark.asyncio
    async def test_resolve_product_mention_exact_id_match(self):
        """Test resolving a product mention with an exact product ID match."""
        mention = ProductMention(
            product_id="RSG8901", product_name="Retro Sunglasses", quantity=1
        )

        result = await resolve_product_mention(mention)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple), "Result item should be a tuple"
        assert len(result[0]) == 2, "Tuple should have Product and L2 score"

        product, l2_score = result[0]

        assert isinstance(product, Product)
        assert isinstance(l2_score, float)
        assert l2_score == 0.0, "L2 score for exact match should be 0.0"

        assert product.product_id == "RSG8901"
        assert product.name == "Retro Sunglasses"
        assert product.metadata is not None
        assert "Resolution confidence: 1.000" in product.metadata
        assert "Found by exact product ID match" in product.metadata

    @pytest.mark.asyncio
    async def test_resolve_product_mention_name_match(self):
        """Test resolving a product mention with a name match."""
        mention = ProductMention(
            product_name="retro sunglasses",  # lowercase
            quantity=2,
        )

        result = await resolve_product_mention(mention)

        # The function should return candidates or ProductNotFound
        if isinstance(result, list):
            assert len(result) >= 1
            # All results should be (Product, l2_score) tuples with good confidence
            for item in result:
                assert isinstance(item, tuple), "Each result item should be a tuple"
                assert len(item) == 2, "Tuple should have Product and L2 score"
                product, l2_score = item

                assert isinstance(product, Product)
                assert isinstance(l2_score, float)
                assert l2_score >= 0.0, "L2 score should be non-negative"

                assert product.metadata is not None
        else:
            # It's okay if it doesn't find a match with sufficient confidence
            assert isinstance(result, ProductNotFound)

    @pytest.mark.asyncio
    async def test_resolve_product_mention_with_metadata(self):
        """Test that resolved products have proper metadata."""
        mention = ProductMention(product_id="RSG8901", quantity=3)

        result = await resolve_product_mention(mention)

        assert isinstance(result, list)
        assert len(result) >= 1

        assert isinstance(result[0], tuple), "Result item should be a tuple"
        assert len(result[0]) == 2, "Tuple should have Product and L2 score"
        product, l2_score = result[0]

        assert isinstance(product, Product)
        assert isinstance(l2_score, float)
        assert l2_score == 0.0, "L2 score for exact match should be 0.0"

        assert product.metadata is not None
        assert "Resolution confidence: 1.000" in product.metadata
        assert "Found by exact product ID match" in product.metadata
        assert "Requested quantity: 3" in product.metadata

    @pytest.mark.asyncio
    async def test_resolve_product_mention_description_search(self):
        """Test resolving a product mention using description search."""
        mention = ProductMention(
            product_description="sunglasses for summer",
            product_category=ProductCategory.ACCESSORIES,
            quantity=1,
        )

        result = await resolve_product_mention(mention)

        # This might resolve to candidates or fail depending on semantic search results
        # We just verify the function doesn't crash and returns the expected types
        assert isinstance(result, (list, ProductNotFound))

        if isinstance(result, list):
            assert len(result) >= 1
            for item in result:
                assert isinstance(item, tuple), "Each result item should be a tuple"
                assert len(item) == 2, "Tuple should have Product and L2 score"
                product, l2_score = item

                assert isinstance(product, Product)
                assert isinstance(l2_score, float)
                assert l2_score >= 0.0, "L2 score should be non-negative"

                assert product.metadata is not None

                expected_method_phrases_in_metadata = [
                    "found by exact product id match",
                    "found through semantic search",
                    "found through fuzzy name matching",
                ]
                metadata_lower = product.metadata.lower()
                # print(f"DEBUG: Metadata for description_search: [{metadata_lower}]") # Optional: for debugging
                found_method = False
                for phrase in expected_method_phrases_in_metadata:
                    is_present = phrase in metadata_lower
                    # print(f'DEBUG: Checking descriptive phrase "[{phrase}]" in metadata -> {is_present}') # Optional: for debugging
                    if is_present:
                        found_method = True
                        break
                assert found_method, f'Metadata "{product.metadata}" did not contain any expected resolution method descriptions.'
        else:
            assert isinstance(result, ProductNotFound)

    @pytest.mark.asyncio
    async def test_resolve_product_mention_returns_multiple_candidates(self):
        """Test that the function can return multiple candidates for ambiguous mentions."""
        mention = ProductMention(
            product_name="jacket",  # Generic term that might match multiple products
            quantity=1,
        )

        result = await resolve_product_mention(mention, top_k=3)

        # Should return candidates or ProductNotFound
        if isinstance(result, list):
            # Could return 1 to 3 candidates
            assert 1 <= len(result) <= 3
            for item in result:
                assert isinstance(item, tuple), "Each result item should be a tuple"
                assert len(item) == 2, "Tuple should have Product and L2 score"
                product, l2_score = item

                assert isinstance(product, Product)
                assert isinstance(l2_score, float)
                assert l2_score >= 0.0, "L2 score should be non-negative"

                assert product.metadata is not None
        else:
            assert isinstance(result, ProductNotFound)


# Fixtures like hermes_config or mock_runnable_config might be needed if resolve_product_mention
# depends on them, or if the underlying tools it calls need them.
# For true integration tests, they would use the actual config.
# These tests assume resolve_product_mention can be called directly and will use the
# default vector store and product data.
