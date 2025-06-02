"""Tests for the resolve_product_mention function."""

import pytest
from hermes.tools.catalog_tools import resolve_product_mention
from hermes.model.email import ProductMention
from hermes.model.errors import ProductNotFound
from unittest.mock import patch, AsyncMock


class TestResolveProductMentionUnit:
    """Unit test cases for the resolve_product_mention function with proper mocks."""

    @pytest.mark.asyncio
    @patch("hermes.tools.catalog_tools.find_product_by_name", new_callable=AsyncMock)
    @patch("hermes.tools.catalog_tools.get_vector_store")
    @patch("hermes.tools.catalog_tools.find_product_by_id", new_callable=AsyncMock)
    async def test_resolve_product_mention_nonexistent(
        self,
        mock_find_by_id_tool,
        mock_create_vector_store_func,
        mock_find_by_name_tool,
    ):
        """Test resolving a product mention that doesn't exist, ensuring all dependencies are mocked."""
        # Get the mock vector store instance from the patched aliased function
        mock_vector_store_instance = mock_create_vector_store_func.return_value

        # Configure the .ainvoke method on the mocked tools
        mock_find_by_id_tool.ainvoke = AsyncMock(
            return_value=ProductNotFound(
                message="Mocked: ID not found", query_product_id="NONEXISTENT123"
            )
        )

        # Ensure the vector store's similarity search also returns no matches if it's called
        mock_vector_store_instance.similarity_search_with_score.return_value = []

        mock_find_by_name_tool.ainvoke = AsyncMock(
            return_value=ProductNotFound(
                message="Mocked: Name not found by fuzzy match",
                query_product_name="Imaginary Product",
            )
        )

        mention = ProductMention(
            product_id="NONEXISTENT123", product_name="Imaginary Product", quantity=1
        )

        result = await resolve_product_mention(mention)

        assert isinstance(result, ProductNotFound)
        # Check for the message when an ID is provided and not found by find_product_by_id
        assert mention.product_id is not None
        # The message should now be the one from the initial ProductNotFound returned by the mocked find_product_by_id
        expected_message_part = "Mocked: ID not found"
        assert expected_message_part.lower() in result.message.lower()
        assert result.query_product_id == mention.product_id
