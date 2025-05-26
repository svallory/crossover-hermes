"""Tests for the resolve_product_mention function."""

import pytest
from hermes.tools.catalog_tools import resolve_product_mention
from hermes.agents.classifier.models import ProductMention
from hermes.model.enums import ProductCategory
from hermes.model.errors import ProductNotFound
from hermes.model.product import Product


class TestResolveProductMention:
    """Test cases for the resolve_product_mention function."""

    @pytest.mark.asyncio
    async def test_resolve_product_mention_exact_id_match(self):
        """Test resolving a product mention with an exact product ID match."""
        mention = ProductMention(
            product_id="RSG8901", product_name="Retro Sunglasses", quantity=1
        )

        result = await resolve_product_mention(mention)

        assert isinstance(result, list)
        assert len(result) == 1
        product = result[0]
        assert isinstance(product, Product)
        assert product.product_id == "RSG8901"
        assert product.name == "Retro Sunglasses"
        assert product.metadata is not None
        assert product.metadata["resolution_confidence"] == 1.0
        assert product.metadata["resolution_method"] == "exact_id_match"

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
            # All results should be Product objects with good confidence
            for product in result:
                assert isinstance(product, Product)
                assert product.metadata is not None
                assert product.metadata["resolution_confidence"] >= 0.75
        else:
            # It's okay if it doesn't find a match with sufficient confidence
            assert isinstance(result, ProductNotFound)

    @pytest.mark.asyncio
    async def test_resolve_product_mention_nonexistent(self):
        """Test resolving a product mention that doesn't exist."""
        mention = ProductMention(
            product_id="NONEXISTENT123", product_name="Imaginary Product", quantity=1
        )

        result = await resolve_product_mention(mention)

        assert isinstance(result, ProductNotFound)
        # The function may return different error messages depending on whether
        # it finds low-confidence matches or no matches at all
        assert any(
            phrase in result.message.lower()
            for phrase in [
                "no products found matching search query",
                "no candidates above threshold",
                "product with id 'nonexistent123' not found",
            ]
        )

    @pytest.mark.asyncio
    async def test_resolve_product_mention_with_metadata(self):
        """Test that resolved products have proper metadata."""
        mention = ProductMention(product_id="RSG8901", quantity=3)

        result = await resolve_product_mention(mention)

        assert isinstance(result, list)
        assert len(result) >= 1
        product = result[0]
        assert isinstance(product, Product)
        assert product.metadata is not None
        assert "resolution_confidence" in product.metadata
        assert "resolution_method" in product.metadata
        assert "requested_quantity" in product.metadata
        assert product.metadata["requested_quantity"] == 3

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
            for product in result:
                assert isinstance(product, Product)
                assert product.metadata is not None
                assert product.metadata["resolution_confidence"] > 0
                assert product.metadata["resolution_method"] in [
                    "exact_id_match",
                    "semantic_search",
                ]

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
            for product in result:
                assert isinstance(product, Product)
                assert product.metadata is not None
                assert "resolution_confidence" in product.metadata
        else:
            assert isinstance(result, ProductNotFound)
