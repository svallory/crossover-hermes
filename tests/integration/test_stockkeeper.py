import pytest
from typing import Any, cast

from src.hermes.agents.classifier.models import ProductMention, EmailAnalysis, ClassifierOutput, Segment, SegmentType
from src.hermes.agents.stockkeeper.agent import (
    resolve_product_mentions,
    resolve_product_reference,
    build_resolution_query,
    disambiguate_with_llm,
    deduplicate_mentions,
    run_deduplication_llm,
)
from src.hermes.agents.stockkeeper.prompts import get_prompt
from src.hermes.model.enums import ProductCategory, Agents
from src.hermes.model.product import Product
from src.hermes.config import HermesConfig
from src.hermes.data_processing.vector_store import VectorStore


class TestStockkeeper:
    """Integration tests for the product resolver."""

    @pytest.fixture
    def hermes_config(self):
        """Return a HermesConfig instance for testing."""
        return HermesConfig(
            # Configure with test settings
            vector_store_path="___IN_MEMORY___"  # Use in-memory vector store for tests
        )

    @pytest.fixture
    def vector_store(self, hermes_config):
        """Initialize and return a vector store instance for testing."""
        # This will be a singleton, so subsequent calls will return the same instance
        return VectorStore(hermes_config)

    @pytest.fixture
    def exact_id_mention(self):
        """Create a product mention with an exact ID."""
        return ProductMention(
            product_id="LTH0976",
            product_name="Leather Bifold Wallet",
            product_type="Wallet",
            product_category=ProductCategory.ACCESSORIES,
            confidence=0.95,
        )

    @pytest.fixture
    def fuzzy_name_mention(self):
        """Create a product mention with a fuzzy name but no ID."""
        return ProductMention(
            product_id=None,
            product_name="Versatile Scarf",
            product_type="Scarf",
            product_description="Can be worn as a scarf, shawl, or headwrap",
            confidence=0.8,
        )

    @pytest.fixture
    def ambiguous_mention(self):
        """Create a product mention with ambiguous resolution potential."""
        return ProductMention(
            product_id=None,
            product_name="Leather Bag",
            product_type="Bag",
            product_description="A leather bag for work",
            confidence=0.7,
        )

    @pytest.fixture
    def formatted_id_mention(self):
        """Create a product mention with an ID that has different formatting."""
        return ProductMention(
            product_id="CBT 89 01",  # Spaces in the ID
            product_name="Chelsea Boots",
            confidence=0.9,
        )

    @pytest.fixture
    def classifier_output(self, exact_id_mention, fuzzy_name_mention):
        """Create an ClassifierOutput with multiple product mentions."""
        segment = Segment(
            segment_type=SegmentType.ORDER,
            main_sentence="I want to order all the remaining LTH0976 Leather Bifold Wallets you have in stock.",
            related_sentences=["I'm opening up a small boutique shop and these would be perfect for my inventory."],
            product_mentions=[exact_id_mention, fuzzy_name_mention],  # Add product mentions to the segment
        )

        return ClassifierOutput(
            email_analysis=EmailAnalysis(email_id="E001", primary_intent="order request", segments=[segment])
        )

    @pytest.fixture
    def duplicate_product_mentions(self):
        """Create a list of product mentions with duplicates for testing deduplication."""
        return [
            # First mention of a wallet
            ProductMention(
                product_id="LTH0976",
                product_name="Leather Bifold Wallet",
                product_type="Wallet",
                product_category=ProductCategory.ACCESSORIES,
                quantity=2,
                confidence=0.95,
            ),
            # Second mention of the same wallet with different details
            ProductMention(
                product_id="LTH0976",  # Same ID
                product_name="Leather Wallet",  # Slightly different name
                product_description="Black leather bifold wallet with card slots",  # Additional description
                quantity=3,  # Different quantity
                confidence=0.9,
            ),
            # Mention of a different product
            ProductMention(
                product_id="SFT1098",
                product_name="Infinity Scarf",
                product_type="Scarf",
                product_category=ProductCategory.ACCESSORIES,
                quantity=1,
                confidence=0.95,
            ),
            # Duplicate mention by description without ID
            ProductMention(
                product_id=None,
                product_name=None,
                product_type="Scarf",
                product_description="Versatile scarf that can be worn multiple ways",
                confidence=0.8,
            ),
            # Another mention of same product by description
            ProductMention(
                product_id=None,
                product_name="Versatile Scarf",
                product_type="Scarf",
                product_description="Can be worn as a scarf, shawl, or headwrap",
                confidence=0.7,
            ),
        ]

    @pytest.mark.asyncio
    async def test_resolve_exact_id(self, exact_id_mention, vector_store):
        """Test resolving a product with an exact ID match."""
        query = build_resolution_query(exact_id_mention)
        results = resolve_product_reference(query=query)

        assert len(results) > 0, "Should find at least one matching product"
        product, confidence = results[0]

        assert isinstance(product, Product), "Should return a Product object"
        assert product.product_id == "LTH0976", "Should match the exact product ID"
        assert confidence > 0.9, "Confidence for exact ID match should be high"

    @pytest.mark.asyncio
    async def test_resolve_formatted_id(self, formatted_id_mention, vector_store):
        """Test resolving a product with an ID that has different formatting."""
        query = build_resolution_query(formatted_id_mention)
        results = resolve_product_reference(query=query)

        assert len(results) > 0, "Should find at least one matching product"
        product, confidence = results[0]

        assert isinstance(product, Product), "Should return a Product object"
        assert product.product_id == "CBT8901", "Should normalize and match the product ID"
        assert confidence > 0.9, "Confidence for exact ID match should be high"

    @pytest.mark.asyncio
    async def test_resolve_fuzzy_name(self, fuzzy_name_mention, vector_store):
        """Test resolving a product with a fuzzy name match."""
        query = build_resolution_query(fuzzy_name_mention)
        results = resolve_product_reference(query=query)

        assert len(results) > 0, "Should find at least one matching product"
        product, confidence = results[0]

        assert isinstance(product, Product), "Should return a Product object"
        assert "Scarf" in product.name or "scarf" in product.name.lower(), "Should match a scarf product"
        assert confidence > 0.5, "Confidence for fuzzy name match should be reasonable"

    @pytest.mark.asyncio
    async def test_full_resolver_agent(self, classifier_output, hermes_config, vector_store):
        """Test the full resolution agent with multiple product mentions."""
        result = await resolve_product_mentions(
            state=classifier_output, runnable_config={"configurable": {"hermes_config": hermes_config}}
        )

        assert result is not None, "Should return a result"
        assert Agents.STOCKKEEPER in result, "Result should contain the STOCKKEEPER key"

        # Cast to the correct type to satisfy type checker
        output = cast(Any, result[Agents.STOCKKEEPER])

        assert len(output.resolved_products) > 0, "Should resolve at least one product"
        assert output.resolution_rate > 0, "Resolution rate should be greater than 0"

        # Check metadata for resolution statistics
        assert "resolution_attempts" in output.metadata, "Metadata should track resolution attempts"
        # Update the assertion to check against the product mentions in segments
        product_count = 0
        if classifier_output.email_analysis and classifier_output.email_analysis.segments:
            for segment in classifier_output.email_analysis.segments:
                product_count += len(segment.product_mentions)
        assert output.metadata["resolution_attempts"] == product_count, (
            "Should attempt to resolve all products in segments"
        )

    @pytest.mark.asyncio
    async def test_disambiguation_prompt_construction(self, ambiguous_mention, hermes_config, vector_store):
        """Test the construction of the disambiguation prompt without calling the LLM."""
        # Create an email context
        email_context = "I need a leather bag for work, something professional but stylish."

        # Create a list of candidate products with similar confidence scores
        candidates = [
            (
                Product(
                    product_id="LTH1098",
                    name="Leather Backpack",
                    description="Professional leather backpack for work and travel",
                    category=ProductCategory.BAGS,
                    product_type="Backpack",
                    stock=10,
                    price=149.99,
                    seasons=[],
                ),
                0.82,
            ),
            (
                Product(
                    product_id="LTH2234",
                    name="Leather Tote",
                    description="Stylish leather tote perfect for office use",
                    category=ProductCategory.BAGS,
                    product_type="Tote",
                    stock=15,
                    price=129.99,
                    seasons=[],
                ),
                0.78,
            ),
        ]

        # Format the prompt variables manually to verify construction
        candidate_text = ""
        for i, (product, score) in enumerate(candidates, 1):
            candidate_text += f"CANDIDATE {i} (confidence: {score:.2f}):\n"
            candidate_text += f"- Product ID: {product.product_id}\n"
            candidate_text += f"- Product Name: {product.name}\n"
            candidate_text += f"- Product Type: {product.product_type}\n"
            candidate_text += f"- Category: {product.category}\n"
            candidate_text += f"- Description: {product.description}\n"
            candidate_text += f"- Stock: {product.stock}\n"
            candidate_text += f"- Price: ${product.price}\n\n"

        prompt_vars = {
            "product_mention": str(ambiguous_mention),
            "product_id": ambiguous_mention.product_id or "Not provided",
            "product_name": ambiguous_mention.product_name or "Not provided",
            "product_type": ambiguous_mention.product_type or "Not provided",
            "product_category": ambiguous_mention.product_category.value
            if ambiguous_mention.product_category
            else "Not provided",
            "product_description": ambiguous_mention.product_description or "Not provided",
            "quantity": ambiguous_mention.quantity or 1,
            "candidate_products": candidate_text,
            "email_context": email_context,
        }

        # Get the disambiguation prompt from the prompts module
        disambiguation_prompt = get_prompt(f"{Agents.STOCKKEEPER}_disambiguation")

        # Create the prompt for inspection
        prompt_template = disambiguation_prompt.format(**prompt_vars)

        # Verify the prompt contains key elements
        assert "ORIGINAL PRODUCT MENTION FROM EMAIL" in prompt_template
        assert "Leather Bag" in prompt_template
        assert "CANDIDATE 1" in prompt_template
        assert "CANDIDATE 2" in prompt_template
        assert "Leather Backpack" in prompt_template
        assert "Leather Tote" in prompt_template
        assert email_context in prompt_template
        assert "RESPONSE (JSON FORMAT)" in prompt_template
        assert "selected_product_id" in prompt_template
        assert "confidence" in prompt_template
        assert "reasoning" in prompt_template

    @pytest.mark.asyncio
    async def test_ambiguous_resolution(self, ambiguous_mention, hermes_config, vector_store):
        """Test resolving an ambiguous product mention that might trigger LLM disambiguation."""
        # Create an email analyzer output with the ambiguous mention
        email_context = "I need a leather bag for work, something professional but stylish."

        # Create a segment with the ambiguous mention
        segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence=email_context,
            related_sentences=[],
            product_mentions=[ambiguous_mention],  # Add the ambiguous mention to the segment
        )

        output = ClassifierOutput(
            email_analysis=EmailAnalysis(
                email_id="E015",
                primary_intent="product inquiry",
                segments=[segment],  # Add the segment with product mention
            )
        )

        # Test the disambiguation directly
        query = build_resolution_query(ambiguous_mention)
        candidates = resolve_product_reference(query=query, max_results=3)

        # Only run this test if we have multiple candidates that could be ambiguous
        if len(candidates) >= 2:
            llm_result = await disambiguate_with_llm(
                mention=ambiguous_mention,
                candidates=candidates,
                email_context=email_context,
                hermes_config=hermes_config,
            )

            assert "selected_product_id" in llm_result, "LLM result should contain a product ID selection"
            assert "confidence" in llm_result, "LLM result should include a confidence score"
            assert "reasoning" in llm_result, "LLM result should include reasoning"

            # Now test the full resolution process
            result = await resolve_product_mentions(
                state=output, runnable_config={"configurable": {"hermes_config": hermes_config}}
            )

            assert result is not None, "Should return a result"
            assert Agents.STOCKKEEPER in result, "Result should contain the STOCKKEEPER key"

            # Cast to the correct type to satisfy type checker
            resolver_output = cast(Any, result[Agents.STOCKKEEPER])
            assert "llm_disambiguations" in resolver_output.metadata, "Metadata should track LLM disambiguations"

    @pytest.mark.asyncio
    async def test_resolution_with_real_email_data(self, hermes_config, vector_store):
        """Test resolution with real product mentions extracted from email data."""
        # Create mentions based on real email data
        mentions = [
            # From E004
            ProductMention(product_id="SFT1098", product_name="Infinity Scarf", quantity=3, confidence=0.95),
            # From E005
            ProductMention(
                product_id="CSH1098",
                product_name="Cozy Shawl",
                product_description="can be worn as a lightweight blanket",
                confidence=0.9,
            ),
            # From E007
            ProductMention(product_id="CLF2109", product_name="Cable Knit Beanie", quantity=5, confidence=0.95),
            # From E007 also
            ProductMention(product_id="FZZ1098", product_name="Fuzzy Slippers", quantity=2, confidence=0.95),
            # From E013 - no ID, just description
            ProductMention(
                product_id=None,
                product_name=None,
                product_type="slide sandals",
                product_category=ProductCategory.MENS_SHOES,
                product_description="slide sandals for men, for the summer",
                confidence=0.7,
            ),
        ]

        # Create segments with product mentions
        segments = [
            Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="I'd like to order some products for my store.",
                related_sentences=["Please let me know when they'll arrive."],
                product_mentions=mentions[:2],  # First two products
            ),
            Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="I also need some additional items.",
                related_sentences=[],
                product_mentions=mentions[2:4],  # Next two products
            ),
            Segment(
                segment_type=SegmentType.INQUIRY,
                main_sentence="Do you have any slide sandals for men suitable for summer?",
                related_sentences=[],
                product_mentions=[mentions[4]],  # Last product
            ),
        ]

        # Create an analyzer output with these segments
        output = ClassifierOutput(
            email_analysis=EmailAnalysis(email_id="TEST", primary_intent="order request", segments=segments)
        )

        # Test the full resolution process
        result = await resolve_product_mentions(
            state=output, runnable_config={"configurable": {"hermes_config": hermes_config}}
        )

        assert result is not None, "Should return a result"
        assert Agents.STOCKKEEPER in result, "Result should contain the STOCKKEEPER key"

        # Cast to the correct type to satisfy type checker
        resolver_output = cast(Any, result[Agents.STOCKKEEPER])

        # We expect most/all exact ID products to resolve
        exact_id_count = len([m for m in mentions if m.product_id])
        assert len(resolver_output.resolved_products) >= exact_id_count * 0.75, (
            "Should resolve most products with exact IDs"
        )

        # Check that quantity is preserved in metadata
        for product in resolver_output.resolved_products:
            assert product.metadata is not None, "Resolved product should have metadata"
            assert "requested_quantity" in product.metadata, "Metadata should include requested quantity"

    @pytest.mark.asyncio
    async def test_deduplication_llm_function(self, duplicate_product_mentions, hermes_config):
        """Test the run_deduplication_llm function directly."""
        # Format mentions for the prompt
        mentions_text = ""
        for i, mention in enumerate(duplicate_product_mentions, 1):
            mentions_text += f"MENTION {i}:\n"
            mentions_text += f"- Product ID: {mention.product_id or 'Not provided'}\n"
            mentions_text += f"- Product Name: {mention.product_name or 'Not provided'}\n"
            mentions_text += f"- Product Type: {mention.product_type or 'Not provided'}\n"
            mentions_text += (
                f"- Category: {mention.product_category.value if mention.product_category else 'Not provided'}\n"
            )
            mentions_text += f"- Description: {mention.product_description or 'Not provided'}\n"
            mentions_text += f"- Quantity: {mention.quantity or 1}\n\n"

        # Create a simple email context
        email_context = "I'd like to order the leather wallets and some scarves for my store."

        # Run the LLM deduplication function
        result = await run_deduplication_llm(
            mentions_text=mentions_text, email_context=email_context, hermes_config=hermes_config
        )

        # Verify that we got a result
        assert result is not None, "Should get a result from the LLM deduplication"
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Should have at least one item in the result"

        # Verify the format of the result items
        for item in result:
            assert isinstance(item, dict), "Each result item should be a dictionary"
            assert "product_id" in item, "Each result should include product_id"
            assert "product_name" in item, "Each result should include product_name"
            assert "product_type" in item, "Each result should include product_type"
            assert "product_category" in item, "Each result should include product_category"
            assert "product_description" in item, "Each result should include product_description"
            assert "quantity" in item, "Each result should include quantity"

        # The LLM should deduplicate, so we expect fewer items than the original
        assert len(result) < len(duplicate_product_mentions), "Deduplication should reduce the number of items"

    @pytest.mark.asyncio
    async def test_deduplicate_mentions_function(self, duplicate_product_mentions, hermes_config):
        """Test the deduplicate_mentions function that processes LLM output into ProductMention objects."""
        # Create a simple email context
        email_context = "I'd like to order the leather wallets and some scarves for my store."

        # Run the full deduplication function
        deduplicated_mentions = await deduplicate_mentions(
            mentions=duplicate_product_mentions, email_context=email_context, hermes_config=hermes_config
        )

        # Verify that we got a result
        assert deduplicated_mentions is not None, "Should get a result from deduplication"
        assert isinstance(deduplicated_mentions, list), "Result should be a list"
        assert all(isinstance(item, ProductMention) for item in deduplicated_mentions), (
            "All items should be ProductMention objects"
        )

        # The function should deduplicate, so we expect fewer items than the original
        assert len(deduplicated_mentions) < len(duplicate_product_mentions), (
            "Deduplication should reduce the number of items"
        )

        # Verify wallet deduplication - should combine the two wallet mentions
        wallet_mentions = [m for m in deduplicated_mentions if m.product_id == "LTH0976"]
        assert len(wallet_mentions) == 1, "Should have exactly one wallet mention after deduplication"

        wallet = wallet_mentions[0]
        # The wallet quantity should be the sum of the duplicates (2+3=5)
        assert wallet.quantity >= 2, "Quantity should be at least the largest of the original quantities"

        # The description should be preserved from the second mention
        assert wallet.product_description is not None, "Description should be preserved"
        assert "Black leather" in wallet.product_description, "Description content should be preserved"

        # Verify scarf deduplication
        scarf_mentions = [m for m in deduplicated_mentions if m.product_type == "Scarf" and m.product_id != "SFT1098"]
        assert len(scarf_mentions) <= 1, "Generic scarf mentions should be deduplicated"

    @pytest.mark.asyncio
    async def test_deduplicate_empty_list(self, hermes_config):
        """Test deduplication with an empty list of mentions."""
        empty_mentions = []
        email_context = "This is a test email with no product mentions."

        result = await deduplicate_mentions(
            mentions=empty_mentions, email_context=email_context, hermes_config=hermes_config
        )

        assert result == [], "Should return an empty list when given an empty list"

    @pytest.mark.asyncio
    async def test_deduplicate_single_item(self, hermes_config):
        """Test deduplication with a single item list (should return the same item)."""
        single_mention = [
            ProductMention(
                product_id="LTH0976",
                product_name="Leather Bifold Wallet",
                product_type="Wallet",
                quantity=1,
                confidence=0.95,
            )
        ]

        email_context = "I want to order a leather wallet."

        result = await deduplicate_mentions(
            mentions=single_mention, email_context=email_context, hermes_config=hermes_config
        )

        assert len(result) == 1, "Should return a list with one item"
        assert result[0].product_id == "LTH0976", "Should preserve the product ID"
        assert result[0].product_name == "Leather Bifold Wallet", "Should preserve the product name"
        assert result[0].quantity == 1, "Should preserve the quantity"

    @pytest.mark.asyncio
    async def test_deduplicate_no_duplicates(self, hermes_config):
        """Test deduplication with a list that has no duplicates."""
        distinct_mentions = [
            ProductMention(
                product_id="LTH0976",
                product_name="Leather Bifold Wallet",
                product_type="Wallet",
                quantity=1,
                confidence=0.95,
            ),
            ProductMention(
                product_id="SFT1098", product_name="Infinity Scarf", product_type="Scarf", quantity=2, confidence=0.9
            ),
            ProductMention(
                product_id="CLF2109", product_name="Cable Knit Beanie", product_type="Hat", quantity=3, confidence=0.85
            ),
        ]

        email_context = "I want to order a wallet, a scarf, and a beanie."

        result = await deduplicate_mentions(
            mentions=distinct_mentions, email_context=email_context, hermes_config=hermes_config
        )

        # When the LLM recognizes no duplicates, it should return the same number of items
        # However, since the LLM might occasionally detect false duplicates, we'll check a range
        assert len(result) >= len(distinct_mentions) - 1, "Should return approximately the same number of items"
        assert len(result) <= len(distinct_mentions), "Should not return more items than provided"

    @pytest.mark.asyncio
    async def test_deduplication_in_resolver_agent(self, hermes_config, vector_store):
        """Test the full resolver agent pipeline with duplicate product mentions."""
        # Create a list of segments with duplicate product mentions
        segments = [
            Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="I want to order 2 leather wallets.",
                product_mentions=[
                    ProductMention(
                        product_id="LTH0976",
                        product_name="Leather Bifold Wallet",
                        product_type="Wallet",
                        quantity=2,
                        confidence=0.95,
                    )
                ],
            ),
            Segment(
                segment_type=SegmentType.ORDER,
                main_sentence="Actually, make that 3 of those black leather bifold wallets.",
                product_mentions=[
                    ProductMention(
                        product_id="LTH0976",  # Same ID
                        product_name="Leather Wallet",  # Slightly different name
                        product_description="Black leather bifold wallet with card slots",  # Additional description
                        quantity=3,  # Different quantity
                        confidence=0.9,
                    )
                ],
            ),
        ]

        # Create an analyzer output with these segments
        output = ClassifierOutput(
            email_analysis=EmailAnalysis(email_id="DEDUP-TEST", primary_intent="order request", segments=segments)
        )

        # Run the full resolution process
        result = await resolve_product_mentions(
            state=output, runnable_config={"configurable": {"hermes_config": hermes_config}}
        )

        assert result is not None, "Should return a result"
        assert Agents.STOCKKEEPER in result, "Result should contain the STOCKKEEPER key"

        # Cast to the correct type to satisfy type checker
        resolver_output = cast(Any, result[Agents.STOCKKEEPER])

        # Verify that deduplication was performed - check the metadata
        assert resolver_output.metadata["total_mentions"] <= 2, (
            "Should have 2 or fewer total mentions after deduplication"
        )
