"""Integration tests for advisor agent using complex inquiry emails from emails.csv."""

import pytest
import os
from typing import Literal, cast, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.agents.advisor.agent import run_advisor
from hermes.agents.advisor.models import AdvisorInput, AdvisorOutput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.model.email import (
    EmailAnalysis,
    ProductMention,
    Segment,
    SegmentType,
)
from hermes.model.enums import ProductCategory, Season, Agents
from hermes.model.product import Product
from hermes.config import HermesConfig


class TestAdvisorIntegration:
    """Integration tests for advisor agent using complex inquiry scenarios."""

    @pytest.fixture
    def hermes_config(self):
        """Create a test configuration for integration testing.
        This will now primarily rely on HermesConfig to pick up defaults
        from environment variables or its internal _DEFAULT_CONFIG,
        ensuring test LLM configuration aligns with the project's base config.
        """
        # Ensure .env is loaded (already present at top of file, but good to be mindful)
        # load_dotenv() # This is typically at the top of the test file.

        # Determine provider from environment or HermesConfig default
        # HermesConfig will handle defaulting if LLM_PROVIDER is not set.
        llm_provider_env = os.getenv("LLM_PROVIDER")
        temp_config_for_provider = (
            HermesConfig()
        )  # Create a temporary instance to get provider default

        llm_provider_to_use = llm_provider_env or temp_config_for_provider.llm_provider

        # Load the specific API key for the determined provider
        api_key = os.getenv(f"{llm_provider_to_use.upper()}_API_KEY")
        if not api_key:
            # Fallback to generic OPENAI_API_KEY or GEMINI_API_KEY if specific one isn't set
            # This maintains compatibility with older .env setups for tests
            if llm_provider_to_use == "OpenAI":
                api_key = os.getenv("OPENAI_API_KEY")
            elif llm_provider_to_use == "Gemini":
                api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                pytest.skip(
                    f"{llm_provider_to_use.upper()}_API_KEY (or fallback OPENAI/GEMINI_API_KEY) not set - skipping integration test"
                )

        # Instantiate HermesConfig. It will use its logic to determine model names
        # based on the provider and environment variables (e.g., GEMINI_STRONG_MODEL)
        # or its internal defaults if those env vars aren't set.
        # We pass the llm_provider and api_key explicitly to ensure they are used,
        # and let other model name resolution happen within HermesConfig.
        return HermesConfig(
            llm_provider=cast(Literal["OpenAI", "Gemini"], llm_provider_to_use),
            llm_api_key=api_key,
            # No need to explicitly set llm_strong_model_name or llm_weak_model_name here,
            # let HermesConfig's @model_validator handle it based on llm_provider and env vars.
        )

    @pytest.fixture
    def mock_runnable_config(self, hermes_config):
        """Create a mock runnable config."""
        return hermes_config.as_runnable_config()

    def create_classifier_output_with_inquiry(
        self,
        email_id: str,
        message: str,
        product_mentions: list[ProductMention],
        customer_name: Optional[str] = None,
        language: str = "English",
    ) -> ClassifierOutput:
        """Helper to create a ClassifierOutput with inquiry segments."""
        # Create an inquiry segment with the product mentions
        inquiry_segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence=message,
            related_sentences=[],
            product_mentions=product_mentions,
        )

        email_analysis = EmailAnalysis(
            email_id=email_id,
            language=language,
            primary_intent="product inquiry",
            customer_name=customer_name,
            segments=[inquiry_segment],
        )

        return ClassifierOutput(email_analysis=email_analysis)

    def create_stockkeeper_output_with_products(
        self, mentions_and_candidates: list[tuple[ProductMention, list[Product]]]
    ) -> StockkeeperOutput:
        """Helper to create a StockkeeperOutput with resolved products mapped to mentions."""
        return StockkeeperOutput(
            candidate_products_for_mention=mentions_and_candidates,
            unresolved_mentions=[],  # Default to empty for these tests
            metadata="Test metadata for advisor integration.",  # Generic metadata
            exact_id_misses=[],  # Default to empty
        )

    def create_product(
        self,
        product_id: str,
        name: str,
        category: str,
        description: str,
        stock: int,
        seasons: str,
        price: float,
        product_type: Optional[str] = None,
    ) -> Product:
        """Helper to create a Product object."""
        # Auto-generate product_type from name if not provided
        if product_type is None:
            product_type = name.split()[-1].lower()  # Use last word as type

        # Parse seasons string into list of Season enums
        season_list = []
        if seasons == "All seasons":
            season_list = [Season.ALL_SEASONS]
        else:
            for season_str in seasons.split(", "):
                season_str = season_str.strip()
                if season_str == "Spring":
                    season_list.append(Season.SPRING)
                elif season_str == "Summer":
                    season_list.append(Season.SUMMER)
                elif season_str == "Fall":
                    season_list.append(Season.FALL)
                elif season_str == "Winter":
                    season_list.append(Season.WINTER)

        return Product(
            product_id=product_id,
            name=name,
            category=ProductCategory(category),
            description=description,
            product_type=product_type,
            stock=stock,
            seasons=season_list,
            price=price,
        )

    @pytest.mark.asyncio
    async def test_bag_comparison_inquiry_e003(self, mock_runnable_config):
        """Test E003: David comparing Leather Backpack vs Leather Tote, asking about organizational pockets."""
        # Create product mentions for the bags mentioned
        mention_backpack = ProductMention(
            product_id="LTH1098",
            product_name="Leather Backpack",
            product_category=ProductCategory.BAGS,
            mention_text="LTH1098 Leather Backpack",
            confidence=1.0,
        )
        mention_tote = ProductMention(
            product_name="Leather Tote",
            product_category=ProductCategory.BAGS,
            mention_text="Leather Tote",
            confidence=0.8,
        )
        product_mentions_for_classifier = [mention_backpack, mention_tote]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E003",
            message="Hello, I need a new bag to carry my laptop and documents for work. My name is David and I'm having a hard time deciding which would be better - the LTH1098 Leather Backpack or the Leather Tote? Does one have more organizational pockets than the other? Any insight would be appreciated!",
            product_mentions=product_mentions_for_classifier,
            customer_name="David",
        )

        # Create resolved products that would come from stockkeeper
        product_backpack = self.create_product(
            product_id="LTH1098",
            name="Leather Backpack",
            category="Bags",
            description="Upgrade your daily carry with our leather backpack. Crafted from premium leather, this stylish backpack features multiple compartments, a padded laptop sleeve, and adjustable straps for a comfortable fit. Perfect for work, travel, or everyday use.",
            stock=7,
            seasons="All seasons",
            price=43.99,
            product_type="backpack",
        )
        product_tote = self.create_product(
            product_id="LTH5432",  # Assuming this ID for the tote based on typical test patterns
            name="Leather Tote",
            category="Bags",
            description="Elevate your everyday carry with our leather tote bag. Crafted from premium, full-grain leather, this bag features a spacious interior, multiple pockets, and sturdy handles. Perfect for work, travel, or running errands in style.",
            stock=6,
            seasons="All seasons",
            price=28.0,
            product_type="tote",
        )

        stockkeeper_candidates = [
            (mention_backpack, [product_backpack]),
            (mention_tote, [product_tote]),
        ]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E003"

        # Should have at least one answered question about organizational features
        assert len(inquiry_answers.answered_questions) > 0

        # Check that the questions are about comparison and organization
        answered_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "pocket" in answered_questions_text
            or "compartment" in answered_questions_text
            or "organization" in answered_questions_text
        )

        # Should identify the primary products mentioned
        assert len(inquiry_answers.primary_products) >= 1
        product_ids = [p.product_id for p in inquiry_answers.primary_products]
        assert "LTH1098" in product_ids or "LTH5432" in product_ids

        # Answers should mention organizational features
        answered_text = " ".join(
            [qa.answer.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "compartment" in answered_text
            or "pocket" in answered_text
            or "laptop" in answered_text
        )

    @pytest.mark.asyncio
    async def test_shawl_quality_inquiry_e005(self, mock_runnable_config):
        """Test E005: Question about CSH1098 Cozy Shawl quality - lap blanket vs wrapping scarf."""
        # Create product mention for the shawl
        mention_shawl = ProductMention(
            product_id="CSH1098",
            product_name="Cozy Shawl",
            product_category=ProductCategory.ACCESSORIES,
            mention_text="CSH1098 Cozy Shawl",
            confidence=1.0,
        )
        product_mentions_for_classifier = [mention_shawl]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E005",
            message="Good day, For the CSH1098 Cozy Shawl, the description mentions it can be worn as a lightweight blanket. At $22, is the material good enough quality to use as a lap blanket? Or is it more like a thick wrapping scarf? I'm considering buying it as a gift for my grandmother. Thank you!",
            product_mentions=product_mentions_for_classifier,
        )

        # Create resolved product
        product_cozy_shawl = self.create_product(
            product_id="CSH1098",
            name="Cozy Shawl",
            category="Accessories",
            description="Wrap yourself in comfort with our cozy shawl. Knitted from soft, warm yarn, this versatile accessory can be worn as a shawl, scarf, or even a lightweight blanket. Perfect for chilly evenings or adding a cozy layer to your outfit.",
            stock=3,
            seasons="Fall, Winter",
            price=22.0,
            product_type="shawl",
        )

        stockkeeper_candidates = [(mention_shawl, [product_cozy_shawl])]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E005"

        # Should have answered questions about material quality and usage
        assert len(inquiry_answers.answered_questions) > 0

        # Check that questions are about material/quality/usage
        answered_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "material" in answered_questions_text
            or "quality" in answered_questions_text
            or "blanket" in answered_questions_text
        )

        # Should identify the CSH1098 product
        assert len(inquiry_answers.primary_products) >= 1
        product_ids = [p.product_id for p in inquiry_answers.primary_products]
        assert "CSH1098" in product_ids

        # Answer should reference the description and versatility
        answered_text = " ".join(
            [qa.answer.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "yarn" in answered_text
            or "knitted" in answered_text
            or "versatile" in answered_text
        )

    @pytest.mark.asyncio
    async def test_spanish_beanie_inquiry_e009(self, mock_runnable_config):
        """Test E009: Spanish inquiry about CHN0987 material and winter warmth."""
        # Create product mention for the beanie (note: CHN0987 is likely DHN0987 in the email)
        mention_beanie = ProductMention(
            product_id="CHN0987",  # Assuming CHN0987 is the canonical ID
            product_name="Chunky Knit Beanie",  # English name for system consistency
            product_category=ProductCategory.ACCESSORIES,
            mention_text="DHN0987 Gorro de punto grueso",  # Original mention text
            confidence=0.9,
        )
        product_mentions_for_classifier = [mention_beanie]

        # Create the classifier output with Spanish language
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E009",
            message="Hola, tengo una pregunta sobre el DHN0987 Gorro de punto grueso. ¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno? Gracias de antemano.",
            product_mentions=product_mentions_for_classifier,
            language="Spanish",
        )

        # Create resolved product
        product_chunky_beanie = self.create_product(
            product_id="CHN0987",
            name="Chunky Knit Beanie",
            category="Accessories",
            description="Keep your head toasty with our chunky knit beanie. Knitted from thick, cozy yarn, this trendy beanie offers a slouchy, oversized fit and a touch of rustic charm. A versatile accessory to elevate your cold-weather looks.",
            stock=2,
            seasons="Fall, Winter",
            price=22.0,
            product_type="beanie",
        )
        stockkeeper_candidates = [(mention_beanie, [product_chunky_beanie])]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E009"

        # Should have answered questions about material and warmth
        assert len(inquiry_answers.answered_questions) > 0

        # Check that questions are about material and winter suitability
        answered_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "material" in answered_questions_text
            or "winter" in answered_questions_text
            or "warm" in answered_questions_text
        )

        # Should identify the CHN0987 product
        assert len(inquiry_answers.primary_products) >= 1
        product_ids = [p.product_id for p in inquiry_answers.primary_products]
        assert "CHN0987" in product_ids

        # Answer should reference the materials and winter suitability
        answered_text = " ".join(
            [qa.answer.lower() for qa in inquiry_answers.answered_questions]
        )
        # Response is in Spanish, check for Spanish terms or general meaning
        assert any(
            term in answered_text
            for term in [
                "hilo",
                "grueso",
                "invierno",
                "cálido",
                "material",  # Spanish
                "yarn",
                "thick",
                "winter",
                "warm",  # English fallback/general terms
            ]
        )

    @pytest.mark.asyncio
    async def test_sunglasses_era_inquiry_e011(self, mock_runnable_config):
        """Test E011: Question about RSG8901 Retro Sunglasses era inspiration."""
        # Create product mention for the sunglasses
        mention_sunglasses = ProductMention(
            product_id="RSG8901",
            product_name="Retro Sunglasses",
            product_category=ProductCategory.ACCESSORIES,
            mention_text="RSG8901 Retro Sunglasses",
            confidence=1.0,
        )
        product_mentions_for_classifier = [mention_sunglasses]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E011",
            message="Hi there, The description for the RSG8901 Retro Sunglasses says they offer 'a cool, nostalgic vibe'. What era are they inspired by exactly? The 1950s, 1960s? I'm just curious about the style inspiration. Thank you!",
            product_mentions=product_mentions_for_classifier,
        )

        # Create resolved product
        product_retro_sunglasses = self.create_product(
            product_id="RSG8901",
            name="Retro Sunglasses",
            category="Accessories",
            description="Transport yourself back in time with our retro sunglasses. These vintage-inspired shades offer a cool, nostalgic vibe while protecting your eyes from the sun's rays. Perfect for beach days or city strolls.",
            stock=1,
            seasons="Spring, Summer",
            price=26.99,
            product_type="sunglasses",
        )
        stockkeeper_candidates = [(mention_sunglasses, [product_retro_sunglasses])]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E011"

        # Should have at least one question about era/style inspiration
        # This might be unanswered since the product description doesn't specify the exact era
        total_questions = len(inquiry_answers.answered_questions) + len(
            inquiry_answers.unanswered_questions
        )
        assert total_questions > 0

        # Check that the question is about era/inspiration
        all_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        all_questions_text += " ".join(inquiry_answers.unanswered_questions).lower()
        assert (
            "era" in all_questions_text
            or "1950" in all_questions_text
            or "1960" in all_questions_text
            or "inspire" in all_questions_text
        )

        # Should identify the RSG8901 product
        assert len(inquiry_answers.primary_products) >= 1
        product_ids = [p.product_id for p in inquiry_answers.primary_products]
        assert "RSG8901" in product_ids

        # If answered, should reference vintage/retro aspects, if unanswered that's also valid
        if inquiry_answers.answered_questions:
            answered_text = " ".join(
                [qa.answer.lower() for qa in inquiry_answers.answered_questions]
            )
            assert (
                "retro" in answered_text
                or "vintage" in answered_text
                or "nostalgic" in answered_text
            )

    @pytest.mark.asyncio
    async def test_work_bag_rambling_inquiry_e012(self, mock_runnable_config):
        """Test E012: Rambling inquiry about work bags/messenger bags."""
        # Create product mentions for messenger bags and briefcases
        mention_messenger = ProductMention(
            product_name="messenger bag",
            product_category=ProductCategory.BAGS,
            mention_text="messenger bag",
            confidence=0.8,
        )
        mention_briefcase = (
            ProductMention(  # Assuming briefcase is a separate general mention
                product_name="briefcase",
                product_category=ProductCategory.BAGS,
                mention_text="briefcase style options",  # more specific text from email
                confidence=0.8,
            )
        )
        product_mentions_for_classifier = [mention_messenger, mention_briefcase]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E012",
            message="Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!",
            product_mentions=product_mentions_for_classifier,
        )

        # Create relevant work bag products
        product_messenger_bag = self.create_product(
            product_id="LTH2109",
            name="Leather Messenger Bag",
            category="Bags",
            description="Carry your essentials in style with our leather messenger bag. Crafted from premium, full-grain leather, this bag features a spacious main compartment, multiple pockets, and an adjustable strap for a comfortable fit. A timeless choice for work, travel, or everyday use.",
            stock=4,
            seasons="All seasons",
            price=37.99,
            product_type="messenger bag",
        )
        product_leather_backpack = self.create_product(  # A general alternative if briefcase implies structure
            product_id="LTH1098",
            name="Leather Backpack",
            category="Bags",
            description="Upgrade your daily carry with our leather backpack. Crafted from premium leather, this stylish backpack features multiple compartments, a padded laptop sleeve, and adjustable straps for a comfortable fit. Perfect for work, travel, or everyday use.",
            stock=7,
            seasons="All seasons",
            price=43.99,
            product_type="backpack",
        )

        stockkeeper_candidates = [
            (mention_messenger, [product_messenger_bag]),
            (
                mention_briefcase,
                [product_leather_backpack],
            ),  # Assuming briefcase mention might resolve to a structured backpack or other similar items
        ]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E012"

        # Should extract meaningful questions despite the rambling nature
        total_questions = len(inquiry_answers.answered_questions) + len(
            inquiry_answers.unanswered_questions
        )
        assert total_questions > 0

        # Should identify work bag products as related
        assert (
            len(inquiry_answers.related_products) >= 1
            or len(inquiry_answers.primary_products) >= 1
        )

        # Questions or content should be about work bags/alternatives/recommendations
        all_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        all_questions_text += " ".join(inquiry_answers.unanswered_questions).lower()
        assert (
            "bag" in all_questions_text
            or "work" in all_questions_text
            or "recommend" in all_questions_text
        )

    @pytest.mark.asyncio
    async def test_mens_bag_recommendation_e015(self, mock_runnable_config):
        """Test E015: Recommendation for men's bag for work and outdoor activities."""
        # Create product mentions for men's bags
        mention_mens_bag = ProductMention(
            product_name="men's bag",
            product_category=ProductCategory.BAGS,
            mention_text="men's bag",
            confidence=0.8,
        )
        product_mentions_for_classifier = [mention_mens_bag]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E015",
            message="Good morning, I'm looking for a nice bag for my husband Thomas for our anniversary. He has a professional office job, but also likes outdoor activities on weekends. Which men's bag would you recommend that's both stylish and practical? Something he can use for work but also take on hikes. Thank you in advance!",
            product_mentions=product_mentions_for_classifier,
        )

        # Create relevant men's bag products
        product_leather_backpack = self.create_product(
            product_id="LTH1098",
            name="Leather Backpack",
            category="Bags",
            description="Upgrade your daily carry with our leather backpack. Crafted from premium leather, this stylish backpack features multiple compartments, a padded laptop sleeve, and adjustable straps for a comfortable fit. Perfect for work, travel, or everyday use.",
            stock=7,
            seasons="All seasons",
            price=43.99,
            product_type="backpack",
        )
        product_messenger_bag = self.create_product(
            product_id="LTH2109",
            name="Leather Messenger Bag",
            category="Bags",
            description="Carry your essentials in style with our leather messenger bag. Crafted from premium, full-grain leather, this bag features a spacious main compartment, multiple pockets, and an adjustable strap for a comfortable fit. A timeless choice for work, travel, or everyday use.",
            stock=4,
            seasons="All seasons",
            price=37.99,
            product_type="messenger bag",
        )

        # Assuming the "men's bag" mention could resolve to either or both if they fit criteria
        stockkeeper_candidates = [
            (mention_mens_bag, [product_leather_backpack, product_messenger_bag])
        ]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E015"

        # Should have questions about recommendations
        total_questions = len(inquiry_answers.answered_questions) + len(
            inquiry_answers.unanswered_questions
        )
        assert total_questions > 0

        # Should recommend suitable bags
        assert (
            len(inquiry_answers.related_products) >= 1
            or len(inquiry_answers.answered_questions) > 0
        )

        # Questions should be about recommendations and versatility
        all_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        all_questions_text += " ".join(inquiry_answers.unanswered_questions).lower()
        assert (
            "recommend" in all_questions_text
            or "bag" in all_questions_text
            or "practical" in all_questions_text
        )

    @pytest.mark.asyncio
    async def test_saddle_bag_price_season_e020(self, mock_runnable_config):
        """Test E020: Price and season suitability of Saddle bag."""
        # Create product mention for saddle bag
        mention_saddle_bag = ProductMention(
            product_name="Saddle bag",
            product_category=ProductCategory.BAGS,
            mention_text="Saddle bag",
            confidence=0.9,
        )
        product_mentions_for_classifier = [mention_saddle_bag]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E020",
            message="Hello I'd like to know how much does Saddle bag cost and if it is suitable for spring season? Thank you, Antonio",
            product_mentions=product_mentions_for_classifier,
            customer_name="Antonio",
        )

        # Create resolved product
        product_saddle_bag_resolved = self.create_product(
            product_id="SDE2345",
            name="Saddle Bag",
            category="Bags",
            description="Channel vintage charm with our saddle bag. This compact crossbody features a classic saddle shape and a trendy, minimalist design. Perfect for adding a touch of retro flair to any ensemble. Limited stock available!",
            stock=1,
            seasons="All seasons",  # Test asks about spring, "All seasons" is suitable
            price=39.0,
            product_type="crossbody",
        )
        stockkeeper_candidates = [(mention_saddle_bag, [product_saddle_bag_resolved])]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E020"

        # Should have answered questions about price and spring suitability
        assert len(inquiry_answers.answered_questions) > 0

        # Check that questions are about price and season
        answered_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "price" in answered_questions_text
            or "cost" in answered_questions_text
            or "spring" in answered_questions_text
        )

        # Should identify the saddle bag product
        assert len(inquiry_answers.primary_products) >= 1
        product_names = [p.name.lower() for p in inquiry_answers.primary_products]
        assert any("saddle" in name for name in product_names)

        # Answer should reference the price and season compatibility
        answered_text = " ".join(
            [qa.answer.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "39" in answered_text or "$39" in answered_text or "season" in answered_text
        )

    @pytest.mark.asyncio
    async def test_winter_hats_inquiry_e021(self, mock_runnable_config):
        """Test E021: Inquiry about winter hats after mentioning previous purchases."""
        # Create product mentions for the previously purchased items and winter hats inquiry
        mention_saddle_bag_prev = ProductMention(
            product_id="SDE2345",
            product_name="Saddle Bag",
            product_category=ProductCategory.BAGS,
            mention_text="SDE2345",
            confidence=1.0,
        )
        mention_jeans_prev = ProductMention(
            product_id="DJN8901",
            product_name="Distressed Jeans",
            product_category=ProductCategory.MENS_CLOTHING,
            mention_text="DJN8901",
            confidence=1.0,
        )
        mention_winter_hats = ProductMention(
            product_name="winter hats",
            product_category=ProductCategory.ACCESSORIES,
            mention_text="winter hats",
            confidence=0.8,
        )
        # These are also mentioned but not in resolved_products: RGD7654, CRD3210.
        # They would be unresolved or handled by exact_id_misses if Stockkeeper was run for real.
        # For this test, we focus on the winter hats part.

        product_mentions_for_classifier = [
            mention_saddle_bag_prev,
            mention_jeans_prev,
            mention_winter_hats,
        ]

        # Create the classifier output
        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E021",
            message="So I've bought quite large collection of vintage items from your store: SDE2345, DJN8901, RGD7654, CRD3210, those are perfect fit for my style! I need your advice if there are any winter hats in your store? Thank you!",
            product_mentions=product_mentions_for_classifier,
        )

        # Create winter hat products and some previously mentioned items
        product_chunky_beanie = self.create_product(
            product_id="CHN0987",
            name="Chunky Knit Beanie",
            category="Accessories",
            description="Keep your head toasty with our chunky knit beanie. Knitted from thick, cozy yarn, this trendy beanie offers a slouchy, oversized fit and a touch of rustic charm. A versatile accessory to elevate your cold-weather looks.",
            stock=2,
            seasons="Fall, Winter",
            price=22.0,
            product_type="beanie",
        )
        product_cable_beanie = self.create_product(
            product_id="CLF2109",
            name="Cable Knit Beanie",
            category="Accessories",
            description="Bundle up in our cable knit beanie. Knitted from premium wool, this classic beanie features a timeless cable knit pattern and a soft, stretchy fit. A versatile accessory for adding a touch of warmth and texture to your cold-weather looks.",
            stock=2,
            seasons="Winter",
            price=16.0,
            product_type="beanie",
        )
        product_saddle_bag_resolved_prev = self.create_product(  # Previously mentioned, now resolved
            product_id="SDE2345",
            name="Saddle Bag",
            category="Bags",
            description="Channel vintage charm with our saddle bag. This compact crossbody features a classic saddle shape and a trendy, minimalist design. Perfect for adding a touch of retro flair to any ensemble. Limited stock available!",
            stock=1,
            seasons="All seasons",
            price=39.0,
            product_type="crossbody",
        )
        # DJN8901 Distressed Jeans is mentioned but not explicitly created/mapped here for simplicity,
        # assuming focus is on winter hats. A real Stockkeeper would attempt to resolve it.

        stockkeeper_candidates = [
            (
                mention_saddle_bag_prev,
                [product_saddle_bag_resolved_prev],
            ),  # Mapping for previously bought item
            # (mention_jeans_prev, [some_jeans_product]), # if we wanted to map it
            (
                mention_winter_hats,
                [product_chunky_beanie, product_cable_beanie],
            ),  # Mapping for "winter hats"
        ]
        stockkeeper_output = self.create_stockkeeper_output_with_products(
            stockkeeper_candidates
        )

        # Create the advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=stockkeeper_output,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E021"

        # Should have answered questions about winter hats availability
        assert len(inquiry_answers.answered_questions) > 0

        # Check that questions are about winter hats
        answered_questions_text = " ".join(
            [qa.question.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "winter" in answered_questions_text
            or "hat" in answered_questions_text
            or "beanie" in answered_questions_text
        )

        # Should identify winter hat products as related
        assert len(inquiry_answers.related_products) >= 1
        related_product_names = [
            p.name.lower() for p in inquiry_answers.related_products
        ]
        assert any("beanie" in name for name in related_product_names)

        # Answer should reference available winter hat options
        answered_text = " ".join(
            [qa.answer.lower() for qa in inquiry_answers.answered_questions]
        )
        assert (
            "beanie" in answered_text
            or "hat" in answered_text
            or "winter" in answered_text
        )

    @pytest.mark.asyncio
    async def test_advisor_with_no_stockkeeper_output(self, mock_runnable_config):
        """Test advisor behavior when stockkeeper output is None (no resolved products)."""
        # Create a simple inquiry without specific product mentions
        product_mentions = [
            ProductMention(
                product_name="dress",
                product_category=ProductCategory.WOMENS_CLOTHING,
                mention_text="dress",
                confidence=0.5,
            ),
        ]

        classifier_output = self.create_classifier_output_with_inquiry(
            email_id="E_NO_STOCKKEEPER",
            message="I'm looking for a nice dress for a wedding. What do you recommend?",
            product_mentions=product_mentions,
        )

        # Create advisor input with no stockkeeper output
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=None,
        )

        # Run the advisor agent
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]
        assert isinstance(output_or_error, AdvisorOutput)
        advisor_output = cast(AdvisorOutput, output_or_error)
        assert isinstance(advisor_output, AdvisorOutput)

        inquiry_answers = advisor_output.inquiry_answers
        assert inquiry_answers.email_id == "E_NO_STOCKKEEPER"

        # Should handle the case gracefully, possibly with unanswered questions
        # Since no product context is available
        total_items = (
            len(inquiry_answers.answered_questions)
            + len(inquiry_answers.unanswered_questions)
            + len(inquiry_answers.unsuccessful_references)
        )
        assert total_items > 0

    @pytest.mark.asyncio
    async def test_advisor_error_handling(self, mock_runnable_config):
        """Test advisor error handling with malformed input."""
        # Create minimal classifier output that might cause issues
        email_analysis = EmailAnalysis(
            email_id="E_ERROR_TEST",
            language="English",
            primary_intent="product inquiry",
            customer_name=None,
            segments=[],  # Empty segments
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)

        # Create advisor input
        advisor_input = AdvisorInput(
            classifier=classifier_output,
            stockkeeper=None,
        )

        # Run the advisor agent - should handle gracefully
        result = await run_advisor(state=advisor_input, config=mock_runnable_config)

        # Verify the result structure
        assert Agents.ADVISOR in result
        output_or_error = result[Agents.ADVISOR]

        # Should return a valid result (AdvisorOutput or Error) even with minimal input
        if isinstance(output_or_error, AdvisorOutput):
            advisor_output = cast(AdvisorOutput, output_or_error)
            inquiry_answers = advisor_output.inquiry_answers
            assert inquiry_answers.email_id == "E_ERROR_TEST"
            # Further assertions can be made on the content of inquiry_answers if needed
        elif isinstance(output_or_error, Exception):
            # This case is acceptable if the agent is expected to raise an exception
            # for malformed input, though typically it should return an Error model.
            # For now, just acknowledge it.
            pass  # Or assert specific exception type if known
        else:
            # If it's an Error model, ensure it's structured as expected.
            # This part depends on how your Error model is defined.
            # For now, we'll assume it's either AdvisorOutput or Exception.
            # To be more robust, you'd check `isinstance(output_or_error, Error)`
            # and then assert its properties.
            pytest.fail(f"Unexpected type from advisor: {type(output_or_error)}")

        # No further assertions if it's an Exception or Error, as the goal is to check graceful handling.
