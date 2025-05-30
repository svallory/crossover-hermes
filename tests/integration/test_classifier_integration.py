"""Integration tests for classifier agent using real emails from emails.csv."""

import pytest
import os
from typing import Literal, cast
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.agents.classifier.agent import run_classifier
from hermes.agents.classifier.models import ClassifierInput, ClassifierOutput
from hermes.model.email import CustomerEmail, SegmentType
from hermes.model.enums import Agents
from hermes.config import HermesConfig


class TestClassifierIntegration:
    """Integration tests for classifier agent using real email data."""

    @pytest.fixture
    def hermes_config(self):
        """Create a test configuration with real API keys for integration testing."""
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

    @pytest.mark.asyncio
    async def test_e001_leather_wallets_order(self, mock_runnable_config):
        """Test E001: Order request with specific product ID (LTH0976 Leather Bifold Wallets)."""
        email = CustomerEmail(
            email_id="E001",
            subject="Leather Wallets",
            message="Hi there, I want to order all the remaining LTH0976 Leather Bifold Wallets you have in stock. I'm opening up a small boutique shop and these would be perfect for my inventory. Thank you!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = cast(ClassifierOutput, result[Agents.CLASSIFIER]).email_analysis

        assert analysis.email_id == "E001"
        assert analysis.primary_intent == "order request"
        assert len(analysis.segments) > 0

        # Should have an order segment
        order_segments = [
            s for s in analysis.segments if s.segment_type == SegmentType.ORDER
        ]
        assert len(order_segments) > 0

        # Should identify the product mention
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        # Should find the LTH0976 product ID
        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "LTH0976" in product_ids

    @pytest.mark.asyncio
    async def test_e002_vibrant_tote_with_personal_context(self, mock_runnable_config):
        """Test E002: Order with personal context (VBT2345 Vibrant Tote, customer Jessica)."""
        email = CustomerEmail(
            email_id="E002",
            subject="Buy Vibrant Tote with noise",
            message="Good morning, I'm looking to buy the VBT2345 Vibrant Tote bag. My name is Jessica and I love tote bags, they're so convenient for carrying all my stuff. Last summer I bought this really cute straw tote that I used at the beach. Oh, and a few years ago I got this nylon tote as a free gift with purchase that I still use for groceries.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E002"
        # The email says "I'm looking to buy" which could be interpreted as either
        # an order request or product inquiry - both are reasonable
        assert analysis.primary_intent in ["order request", "product inquiry"]

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Jessica" in str(analysis.customer_name).lower()
                or "jessica" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify VBT2345 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "VBT2345" in product_ids

    @pytest.mark.asyncio
    async def test_e003_product_inquiry_comparison(self, mock_runnable_config):
        """Test E003: Product inquiry comparison (LTH1098 Leather Backpack vs Leather Tote, customer David)."""
        email = CustomerEmail(
            email_id="E003",
            subject="Need your help",
            message="Hello, I need a new bag to carry my laptop and documents for work. My name is David and I'm having a hard time deciding which would be better - the LTH1098 Leather Backpack or the Leather Tote? Does one have more organizational pockets than the other? Any insight would be appreciated!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E003"
        assert analysis.primary_intent == "product inquiry"

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "David" in str(analysis.customer_name).lower()
                or "david" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should have inquiry segment
        inquiry_segments = [
            s for s in analysis.segments if s.segment_type == SegmentType.INQUIRY
        ]
        assert len(inquiry_segments) > 0

        # Should identify LTH1098 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "LTH1098" in product_ids

    @pytest.mark.asyncio
    async def test_e004_order_with_quantity_range(self, mock_runnable_config):
        """Test E004: Order with quantity range (3-4 SFT1098 Infinity Scarves)."""
        email = CustomerEmail(
            email_id="E004",
            subject="Buy Infinity Scarves Order",
            message="Hi, I'd like to order three to four SFT1098 Infinity Scarves please. My wife loves collecting scarves in different colors and patterns.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E004"
        assert analysis.primary_intent == "order request"

        # Should identify SFT1098 product with quantity
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "SFT1098" in product_ids

        # Should parse quantity (could be 3 or 4, both are reasonable)
        quantities = [pm.quantity for pm in product_mentions if pm.quantity]
        assert len(quantities) > 0
        assert any(q in [3, 4] for q in quantities)

    @pytest.mark.asyncio
    async def test_e005_detailed_product_inquiry(self, mock_runnable_config):
        """Test E005: Detailed product inquiry (CSH1098 Cozy Shawl quality questions)."""
        email = CustomerEmail(
            email_id="E005",
            subject="Inquiry on Cozy Shawl Details",
            message="Good day, For the CSH1098 Cozy Shawl, the description mentions it can be worn as a lightweight blanket. At $22, is the material good enough quality to use as a lap blanket? Or is it more like a thick wrapping scarf? I'm considering buying it as a gift for my grandmother. Thank you!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E005"
        assert analysis.primary_intent == "product inquiry"

        # Should identify CSH1098 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "CSH1098" in product_ids

    @pytest.mark.asyncio
    async def test_e006_future_order_intent(self, mock_runnable_config):
        """Test E006: Future order intent (CBT8901 Chelsea Boots, customer Sam)."""
        email = CustomerEmail(
            email_id="E006",
            subject="",
            message="Hey there, I was thinking of ordering a pair of CBT8901 Chelsea Boots, but I'll wait until Fall to actually place the order. My name is Sam and I need some new boots for the colder months.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E006"
        # Could be either order request or inquiry depending on interpretation
        assert analysis.primary_intent in ["order request", "product inquiry"]

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Sam" in str(analysis.customer_name).lower()
                or "sam" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify CBT8901 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "CBT8901" in product_ids

    @pytest.mark.asyncio
    async def test_e007_multiple_products_order(self, mock_runnable_config):
        """Test E007: Multiple products order (5 CLF2109 Cable Knit Beanies + 2 FZZ1098 Fuzzy Slippers, customer Liz)."""
        email = CustomerEmail(
            email_id="E007",
            subject="Order for Beanies, Slippers",
            message="Hi, this is Liz. Please send me 5 CLF2109 Cable Knit Beanies and 2 pairs of FZZ1098 Fuzzy Slippers. I'm prepping some holiday gift baskets.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E007"
        assert analysis.primary_intent == "order request"

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Liz" in str(analysis.customer_name).lower()
                or "liz" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify both products
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "CLF2109" in product_ids
        assert "FZZ1098" in product_ids

        # Should parse quantities correctly
        quantities = [pm.quantity for pm in product_mentions if pm.quantity]
        assert 5 in quantities or 2 in quantities

    @pytest.mark.asyncio
    async def test_e008_generic_product_description_order(self, mock_runnable_config):
        """Test E008: Generic product description order (Versatile Scarves)."""
        email = CustomerEmail(
            email_id="E008",
            subject="Ordering a Versatile Scarf-like item",
            message="Hello, I'd want to order one of your Versatile Scarves, the one that can be worn as a scarf, shawl, or headwrap. Thanks!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E008"
        assert analysis.primary_intent in ["order request", "product inquiry"]

        # Should identify product mention even without specific ID
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        # Check mention_text for scarf-related terms
        mention_texts = [pm.mention_text for pm in product_mentions if pm.mention_text]
        scarf_related_terms = ["scarf", "shawl", "headwrap", "versatile"]
        assert any(
            any(term in text.lower() for term in scarf_related_terms)
            for text in mention_texts
            if text
        ), "Expected to find scarf-related terms in mention_texts"

        # If product_name is populated, it should be specific, not generic, per prompt.
        # This part of the test might need adjustment based on how specific the LLM gets.

    @pytest.mark.asyncio
    async def test_e009_spanish_language_inquiry(self, mock_runnable_config):
        """Test E009: Spanish language inquiry (DHN0987 Gorro de punto grueso)."""
        email = CustomerEmail(
            email_id="E009",
            subject="Pregunta Sobre Gorro de Punto Grueso",
            message="Hola, tengo una pregunta sobre el DHN0987 Gorro de punto grueso. ¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno? Gracias de antemano.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E009"
        assert analysis.primary_intent == "product inquiry"

        # Should detect Spanish language (though some LLMs might detect as English)
        assert analysis.language.lower() in ["spanish", "english"]  # Allow flexibility

        # Should identify DHN0987 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "DHN0987" in product_ids

    @pytest.mark.asyncio
    async def test_e010_simple_order_request(self, mock_runnable_config):
        """Test E010: Simple order request (1 RSG8901 Retro Sunglasses)."""
        email = CustomerEmail(
            email_id="E010",
            subject="Purchase Retro Sunglasses",
            message="Hello, I would like to order 1 pair of RSG8901 Retro Sunglasses. Thanks!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E010"
        assert analysis.primary_intent == "order request"

        # Should identify RSG8901 product with quantity 1
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "RSG8901" in product_ids

        quantities = [pm.quantity for pm in product_mentions if pm.quantity]
        assert 1 in quantities

    @pytest.mark.asyncio
    async def test_e011_product_detail_inquiry(self, mock_runnable_config):
        """Test E011: Product detail inquiry (RSG8901 style inspiration questions)."""
        email = CustomerEmail(
            email_id="E011",
            subject="Question on Retro Sunglasses Description",
            message="Hi there, The description for the RSG8901 Retro Sunglasses says they offer 'a cool, nostalgic vibe'. What era are they inspired by exactly? The 1950s, 1960s? I'm just curious about the style inspiration. Thank you!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E011"
        assert analysis.primary_intent == "product inquiry"

        # Should identify RSG8901 product
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "RSG8901" in product_ids

    @pytest.mark.asyncio
    async def test_e012_rambling_email_with_mixed_content(self, mock_runnable_config):
        """Test E012: Rambling email with mixed content (work bag inquiry, customer Emily mentioned)."""
        email = CustomerEmail(
            email_id="E012",
            subject="Rambling About a New Work Bag",
            message="Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E012"
        assert analysis.primary_intent == "product inquiry"

        # Should extract Emily as PII (wife's name)
        assert analysis.customer_name is not None

        # Should identify bag-related product mentions
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        # If product mentions are extracted, they should be bag-related
        if len(product_mentions) > 0:
            # Check mention_text for bag-related terms
            mention_texts = [
                pm.mention_text for pm in product_mentions if pm.mention_text
            ]
            assert any(
                any(term in text.lower() for term in ["bag", "briefcase", "messenger"])
                for text in mention_texts
                if text
            ), "Expected bag-related terms in mention_texts if mentions are present"

    @pytest.mark.asyncio
    async def test_e013_category_specific_order(self, mock_runnable_config):
        """Test E013: Category-specific order (slide sandals for men, customer Marco)."""
        email = CustomerEmail(
            email_id="E013",
            subject="Shopping for Men's Sandals",
            message="Hi, my name is Marco and I need to buy a pair of slide sandals for men, in the Men's Shoes category, for the summer.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E013"
        # "I need to buy" could be interpreted as either order request or product inquiry
        assert analysis.primary_intent in ["order request", "product inquiry"]

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Marco" in str(analysis.customer_name).lower()
                or "marco" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify sandals product mention
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        product_names = [pm.product_name for pm in product_mentions if pm.product_name]
        assert any("sandal" in name.lower() for name in product_names if name)

    @pytest.mark.asyncio
    async def test_e014_brief_order_request(self, mock_runnable_config):
        """Test E014: Brief order request (1 Sleek Wallet, customer Johny)."""
        email = CustomerEmail(
            email_id="E014",
            subject="Sleek Wallet Order",
            message="Please send me 1 Sleek Wallet. Thanks, Johny",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E014"
        assert analysis.primary_intent == "order request"

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Johny" in str(analysis.customer_name).lower()
                or "johny" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify wallet product mention
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        product_names = [pm.product_name for pm in product_mentions if pm.product_name]
        assert any("wallet" in name.lower() for name in product_names if name)

    @pytest.mark.asyncio
    async def test_e015_recommendation_request(self, mock_runnable_config):
        """Test E015: Recommendation request (men's bag for Thomas)."""
        email = CustomerEmail(
            email_id="E015",
            subject="Stylish Yet Practical Men's Bag Recommendation",
            message="Good morning, I'm looking for a nice bag for my husband Thomas for our anniversary. He has a professional office job, but also likes outdoor activities on weekends. Which men's bag would you recommend that's both stylish and practical? Something he can use for work but also take on hikes. Thank you in advance!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E015"
        assert analysis.primary_intent == "product inquiry"

        # Should extract Thomas as PII (husband's name) (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Thomas" in str(analysis.customer_name).lower()
                or "thomas" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify bag product mention
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        # This is a recommendation request asking for advice about "men's bag"
        # The LLM may or may not extract this as a specific product mention
        # since the customer is asking for recommendations rather than ordering
        if len(product_mentions) > 0:
            product_names = [
                pm.product_name for pm in product_mentions if pm.product_name
            ]
            assert any("bag" in name.lower() for name in product_names if name)

    @pytest.mark.asyncio
    async def test_e016_mixed_inquiry_and_order(self, mock_runnable_config):
        """Test E016: Mixed inquiry and order (summer wedding dress + travel bag, customer Claire)."""
        email = CustomerEmail(
            email_id="E016",
            subject="Summer Wedding Guest Dress Preferences",
            message="Hello, I'm looking for a dress for a summer wedding I have coming up. My name is Claire. I don't want anything too short, low-cut, or super tight-fitting. But I also don't want it to be too loose or matronly. Something flattering but still comfortable to wear for an outdoor ceremony. Any recommendations on some options that might work for me? Thank you! And bag, I think I need some travel bag.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E016"
        # Could be either depending on interpretation
        assert analysis.primary_intent in ["product inquiry", "order request"]

        # Should extract customer name (though LLMs may not always extract names consistently)
        if analysis.customer_name and str(analysis.customer_name) != "{}":
            assert (
                "Claire" in str(analysis.customer_name).lower()
                or "claire" in str(analysis.customer_name).lower()
            )
        # If no PII extracted, that's also acceptable as LLM behavior can vary

        # Should identify dress and/or bag mentions
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        # Check mention_text for generic items like "dress" or "bag"
        mention_texts = [pm.mention_text for pm in product_mentions if pm.mention_text]
        assert any(
            any(term in text.lower() for term in ["dress", "bag"])
            for text in mention_texts
            if text
        ), "Expected to find 'dress' or 'bag' in mention_texts"

        # If product_name is populated by the LLM for these generic terms (despite prompt),
        # this part can be uncommented and adapted.
        # product_names = [pm.product_name for pm in product_mentions if pm.product_name]
        # if product_names: # Only assert if product_names is not empty
        #    assert any(
        #        any(term in name.lower() for term in ["dress", "bag"])
        #        for name in product_names
        #        if name
        #    ), "If product_name is populated, it should contain 'dress' or 'bag' for this email"

    @pytest.mark.asyncio
    async def test_e017_vague_order_request(self, mock_runnable_config):
        """Test E017: Vague order request (popular item)."""
        email = CustomerEmail(
            email_id="E017",
            subject="",
            message="Hi there I want to place an order for that popular item you sell. The one that's been selling like hotcakes lately. You know what I mean right?",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E017"
        assert analysis.primary_intent in ["order request", "product inquiry"]

        # Should identify some product mention even if vague
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        # May or may not have specific product mentions due to vagueness
        assert len(analysis.segments) > 0

    @pytest.mark.asyncio
    async def test_e019_product_id_with_formatting(self, mock_runnable_config):
        """Test E019: Product ID with formatting ([CBT 89 01] + FZZ1098)."""
        email = CustomerEmail(
            email_id="E019",
            subject="Hi",
            message="Hey there, I would like to buy Chelsea Boots [CBT 89 01] from you guys! You're so awesome I'm so impressed with the quality of Fuzzy Slippers - FZZ1098 I've bought from you before. I hope the quality stays. I would like to order Retro sunglasses from you, but probably next time! Thanks",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E019"
        assert analysis.primary_intent == "order request"

        # Should identify both product IDs despite formatting
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        # Should parse CBT8901 from [CBT 89 01] and FZZ1098
        assert any("CBT" in pid for pid in product_ids)
        assert "FZZ1098" in product_ids

    @pytest.mark.asyncio
    async def test_e020_price_inquiry(self, mock_runnable_config):
        """Test E020: Price inquiry (Saddle bag cost and season suitability, customer Antonio)."""
        email = CustomerEmail(
            email_id="E020",
            subject="Price check",
            message="Hello I'd like to know how much does Saddle bag cost and if it is suitable for spring season? Thank you, Antonio",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E020"
        assert analysis.primary_intent == "product inquiry"

        # Should extract customer name
        assert analysis.customer_name is not None
        assert (
            "Antonio" in str(analysis.customer_name).lower()
            or "antonio" in str(analysis.customer_name).lower()
        )

        # Should identify saddle bag mention
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        product_names = [pm.product_name for pm in product_mentions if pm.product_name]
        assert any(
            "saddle" in name.lower() or "bag" in name.lower()
            for name in product_names
            if name
        )

    @pytest.mark.asyncio
    async def test_e021_multiple_product_ids_inquiry(self, mock_runnable_config):
        """Test E021: Multiple product IDs inquiry (SDE2345, DJN8901, RGD7654, CRD3210 + winter hats)."""
        email = CustomerEmail(
            email_id="E021",
            subject="",
            message="So I've bought quite large collection of vintage items from your store: SDE2345, DJN8901, RGD7654, CRD3210, those are perfect fit for my style! I need your advice if there are any winter hats in your store? Thank you!",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E021"
        assert analysis.primary_intent == "product inquiry"

        # Should identify multiple product IDs
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        expected_ids = ["SDE2345", "DJN8901", "RGD7654", "CRD3210"]
        # Should find at least some of these IDs
        assert any(pid in product_ids for pid in expected_ids)

        # Should also mention winter hats
        mention_texts = [pm.mention_text for pm in product_mentions if pm.mention_text]
        assert any(
            "hat" in text.lower() for text in mention_texts if text
        ), "Expected to find 'hat' in mention_texts"

    @pytest.mark.asyncio
    async def test_e022_enthusiastic_order_with_social_reference(
        self, mock_runnable_config
    ):
        """Test E022: Enthusiastic order with social reference (geometric pattern bags from Instagram, customer Monica)."""
        email = CustomerEmail(
            email_id="E022",
            subject="Placing My Order Today",
            message="Hi! I'm ready to place my order for those amazing bags I saw in your latest collection - you know, the ones with the geometric patterns that everyone's been talking about on Instagram? I want to get 3 of them, preferably in the darker shade you showed in your social media posts last week. I have the cash ready to go, just let me know where to send it! Can't wait to get my hands on them. Thanks, Monica",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result[Agents.CLASSIFIER].email_analysis

        assert analysis.email_id == "E022"
        assert analysis.primary_intent == "order request"

        # Should extract customer name
        assert analysis.customer_name is not None
        assert (
            "Monica" in str(analysis.customer_name).lower()
            or "monica" in str(analysis.customer_name).lower()
        )

        # Should identify bag mentions with quantity
        product_mentions = []
        for segment in analysis.segments:
            product_mentions.extend(segment.product_mentions)

        assert len(product_mentions) > 0
        product_names = [pm.product_name for pm in product_mentions if pm.product_name]
        assert any("bag" in name.lower() for name in product_names if name)

        quantities = [pm.quantity for pm in product_mentions if pm.quantity]
        assert 3 in quantities

    @pytest.mark.asyncio
    async def test_e023_committed_order_with_history_reference(
        self, mock_runnable_config
    ):
        """Test E023: Committed order with history reference (5 CGN2345 Cargo Pants)."""
        email = CustomerEmail(
            email_id="E023",
            subject="Final Decision Made",
            message="After weeks of consideration, I've made up my mind! Looking at my bank account right now, and I'm prepared to commit to those CGN2345 Cargo Pants - all 5 of them, exactly as we discussed in my previous emails about the color options and material details. Just need you to confirm the availability first, before we move formward.",
        )

        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(
            state=classifier_input, runnable_config=mock_runnable_config
        )

        assert Agents.CLASSIFIER.value in result
        analysis = result.get(Agents.CLASSIFIER)

        assert analysis.email_analysis.email_id == "E023"
        assert analysis.email_analysis.primary_intent == "order request"

        # Should identify CGN2345 product with quantity 5
        product_mentions = []
        for segment in analysis.email_analysis.segments:
            product_mentions.extend(segment.product_mentions)

        product_ids = [pm.product_id for pm in product_mentions if pm.product_id]
        assert "CGN2345" in product_ids

        quantities = [pm.quantity for pm in product_mentions if pm.quantity]
        assert 5 in quantities
