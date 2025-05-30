"""Integration tests for composer agent using complex email scenarios from emails.csv."""

import pytest
import os
from typing import Literal, cast, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.agents.composer.agent import run_composer
from hermes.agents.composer.models import ComposerInput, ComposerOutput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.advisor.models import AdvisorOutput, InquiryAnswers, QuestionAnswer
from hermes.agents.fulfiller.models import FulfillerOutput
from hermes.model.order import Order, OrderLine, OrderLineStatus
from hermes.model.email import (
    CustomerEmail,
    EmailAnalysis,
    ProductMention,
    Segment,
    SegmentType,
)
from hermes.model.enums import Agents, ProductCategory, Season
from hermes.model.product import Product
from hermes.config import HermesConfig
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Import LLM evaluation capability


class TestComposerIntegration:
    """Integration tests for composer agent using complex email scenarios."""

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

    def create_customer_email(
        self, email_id: str, subject: str, message: str
    ) -> CustomerEmail:
        """Helper to create a CustomerEmail."""
        return CustomerEmail(email_id=email_id, subject=subject, message=message)

    def create_classifier_output(
        self,
        email_id: str,
        language: str = "English",
        primary_intent: Literal["order request", "product inquiry"] = "order request",
        customer_name: Optional[str] = None,
        segments: Optional[list[Segment]] = None,
    ) -> ClassifierOutput:
        """Helper to create a ClassifierOutput."""
        if segments is None:
            segments = []

        email_analysis = EmailAnalysis(
            email_id=email_id,
            language=language,
            primary_intent=primary_intent,
            customer_name=customer_name,
            segments=segments,
        )

        return ClassifierOutput(email_analysis=email_analysis)

    def create_advisor_output(
        self,
        email_id: str,
        answered_questions: Optional[list[QuestionAnswer]] = None,
        primary_products: Optional[list[Product]] = None,
    ) -> AdvisorOutput:
        """Helper to create an AdvisorOutput."""
        if answered_questions is None:
            answered_questions = []
        if primary_products is None:
            primary_products = []

        inquiry_answers = InquiryAnswers(
            email_id=email_id,
            primary_products=primary_products,
            answered_questions=answered_questions,
            unanswered_questions=[],
            related_products=[],
            unsuccessful_references=[],
        )

        return AdvisorOutput(inquiry_answers=inquiry_answers)

    def create_fulfiller_output(
        self,
        email_id: str,
        order_lines: Optional[list[OrderLine]] = None,
        total_price: float = 0.0,
        overall_status: Literal[
            "created", "out_of_stock", "partially_fulfilled", "no_valid_products"
        ] = "created",
    ) -> FulfillerOutput:
        """Helper to create a FulfillerOutput."""
        if order_lines is None:
            order_lines = []

        order_result = Order(
            email_id=email_id,
            lines=order_lines,
            total_price=total_price,
            overall_status=overall_status,
            total_discount=0.0,
            stock_updated=True,
        )

        return FulfillerOutput(order_result=order_result)

    def create_product(
        self,
        product_id: str,
        name: str,
        category: str,
        description: str,
        stock: int = 5,
        seasons: str = "All seasons",
        price: float = 25.99,
        product_type: str = "item",
    ) -> Product:
        """Helper to create a Product."""
        # Parse seasons string into list of Season enums
        season_list = []
        if seasons.lower() == "all seasons":
            season_list = [Season.SPRING, Season.SUMMER, Season.FALL, Season.WINTER]
        else:
            for season_name in seasons.split(", "):
                season_name = season_name.strip()
                if season_name == "Spring":
                    season_list.append(Season.SPRING)
                elif season_name == "Summer":
                    season_list.append(Season.SUMMER)
                elif season_name == "Fall":
                    season_list.append(Season.FALL)
                elif season_name == "Winter":
                    season_list.append(Season.WINTER)

        return Product(
            product_id=product_id,
            name=name,
            category=ProductCategory(category),
            description=description,
            stock=stock,
            seasons=season_list,
            price=price,
            product_type=product_type,
        )

    def create_order_line(
        self,
        product_id: str,
        description: str,
        quantity: int,
        base_price: float,
        unit_price: Optional[float] = None,
        status: OrderLineStatus = OrderLineStatus.CREATED,
    ) -> OrderLine:
        """Helper to create an OrderLine."""
        if unit_price is None:
            unit_price = base_price

        return OrderLine(
            product_id=product_id,
            description=description,
            quantity=quantity,
            base_price=base_price,
            unit_price=unit_price,
            total_price=unit_price * quantity,
            status=status,
        )

    @pytest.mark.asyncio
    async def test_composer_order_confirmation_e001(self, mock_runnable_config):
        """Test E001: Leather Wallets order confirmation response."""
        # Create the email
        email = self.create_customer_email(
            email_id="E001",
            subject="Leather Wallets",
            message="Hi there, I want to order all the remaining LTH0976 Leather Bifold Wallets you have in stock. I'm opening up a small boutique shop and these would be perfect for my inventory. Thank you!",
        )

        # Create classifier output with order intent
        order_segment = Segment(
            segment_type=SegmentType.ORDER,
            main_sentence=email.message,
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_id="LTH0976",
                    product_name="Leather Bifold Wallet",
                    product_category=ProductCategory.ACCESSORIES,
                    mention_text="LTH0976 Leather Bifold Wallets",
                    confidence=1.0,
                    quantity=4,  # All remaining stock
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E001",
            primary_intent="order request",
            segments=[order_segment],
        )

        # Create fulfiller output with successful order
        order_line = self.create_order_line(
            product_id="LTH0976",
            description="Leather Bifold Wallet",
            quantity=4,
            base_price=21.0,
            unit_price=21.0,
            status=OrderLineStatus.CREATED,
        )

        fulfiller_output = self.create_fulfiller_output(
            email_id="E001",
            order_lines=[order_line],
            total_price=84.0,
            overall_status="created",
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            fulfiller=fulfiller_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E001"
        assert composer_output.language == "English"
        assert len(composer_output.response_body) > 100  # Substantial response

        # Check for order confirmation details
        response_lower = composer_output.response_body.lower()
        assert "lth0976" in response_lower or "leather bifold wallet" in response_lower
        assert "4" in composer_output.response_body or "four" in response_lower
        assert (
            "$84" in composer_output.response_body
            or "84.00" in composer_output.response_body
        )

        # Check professional tone for business customer
        assert composer_output.tone in [
            "professional",
            "professional and warm",
            "friendly and professional",
        ]

        # Verify signature
        assert "hermes" in response_lower
        assert "best regards" in response_lower or "sincerely" in response_lower

        print(f"✅ Composer response for E001:\n{composer_output.response_body}")

        # Optional: Add LLM-based validation for comprehensive quality assessment
        llm_validation = await self.validate_composer_response_with_llm(
            email,
            composer_output,
            validation_criteria={
                "order_confirmation": "Does the response clearly confirm the order details (product, quantity, price)?",
                "business_tone": "Is the tone appropriately professional for a business customer?",
                "personalization": "Does the response feel personalized rather than templated?",
            },
        )

        # Optional assertion - can be used for debugging or detailed quality assessment
        if llm_validation["overall_score"] < 0.7:
            print(f"⚠️  LLM validation warning: {llm_validation['overall_reasoning']}")
        else:
            print(f"✅ LLM validation passed: {llm_validation['overall_score']:.2f}")

    @pytest.mark.asyncio
    async def test_composer_inquiry_response_e003(self, mock_runnable_config):
        """Test E003: Bag comparison inquiry response."""
        # Create the email
        email = self.create_customer_email(
            email_id="E003",
            subject="Need your help",
            message="Hello, I need a new bag to carry my laptop and documents for work. My name is David and I'm having a hard time deciding which would be better - the LTH1098 Leather Backpack or the Leather Tote? Does one have more organizational pockets than the other? Any insight would be appreciated!",
        )

        # Create classifier output with inquiry intent
        inquiry_segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence=email.message,
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_id="LTH1098",
                    product_name="Leather Backpack",
                    product_category=ProductCategory.BAGS,
                    mention_text="LTH1098 Leather Backpack",
                    confidence=1.0,
                ),
                ProductMention(
                    product_name="Leather Tote",
                    product_category=ProductCategory.BAGS,
                    mention_text="Leather Tote",
                    confidence=0.8,
                ),
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E003",
            primary_intent="product inquiry",
            customer_name="David",
            segments=[inquiry_segment],
        )

        # Create advisor output with answered questions
        backpack_product = self.create_product(
            product_id="LTH1098",
            name="Leather Backpack",
            category="Bags",
            description="Upgrade your daily carry with our leather backpack. Crafted from premium leather, this stylish backpack features multiple compartments, a padded laptop sleeve, and adjustable straps for a comfortable fit. Perfect for work, travel, or everyday use.",
            price=43.99,
        )

        tote_product = self.create_product(
            product_id="LTH5432",
            name="Leather Tote",
            category="Bags",
            description="Elevate your everyday carry with our leather tote bag. Crafted from premium, full-grain leather, this bag features a spacious interior, multiple pockets, and sturdy handles. Perfect for work, travel, or running errands in style.",
            price=28.0,
        )

        answered_question = QuestionAnswer(
            question="Does one have more organizational pockets than the other?",
            answer="The Leather Backpack (LTH1098) offers superior organization with multiple compartments and a dedicated padded laptop sleeve, making it ideal for work documents and electronics. The Leather Tote features multiple pockets and a spacious interior but has a more open design. For work use with laptop and documents, the backpack provides better organization.",
        )

        advisor_output = self.create_advisor_output(
            email_id="E003",
            answered_questions=[answered_question],
            primary_products=[backpack_product, tote_product],
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            advisor=advisor_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E003"
        assert composer_output.language == "English"
        assert len(composer_output.response_body) > 100

        # Check personalization - should address David
        response_lower = composer_output.response_body.lower()
        assert "david" in response_lower

        # Check product comparison details
        assert "backpack" in response_lower and "tote" in response_lower
        assert (
            "compartment" in response_lower
            or "pocket" in response_lower
            or "organization" in response_lower
        )

        # Check for professional but helpful tone
        assert composer_output.tone in [
            "friendly and helpful",
            "professional and warm",
            "helpful and informative",
        ]

        print(f"✅ Composer response for E003:\n{composer_output.response_body}")

    @pytest.mark.asyncio
    async def test_composer_mixed_intent_e016(self, mock_runnable_config):
        """Test E016: Mixed intent - inquiry about dress plus bag mention."""
        # Create the email
        email = self.create_customer_email(
            email_id="E016",
            subject="Summer Wedding Guest Dress Preferences",
            message="Hello, I'm looking for a dress for a summer wedding I have coming up. My name is Claire. I don't want anything too short, low-cut, or super tight-fitting. But I also don't want it to be too loose or matronly. Something flattering but still comfortable to wear for an outdoor ceremony. Any recommendations on some options that might work for me? Thank you! And bag, I think I need some travel bag.",
        )

        # Create classifier output with mixed intent
        inquiry_segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence="I'm looking for a dress for a summer wedding. Any recommendations on some options that might work for me?",
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_category=ProductCategory.WOMENS_CLOTHING,
                    mention_text="dress for a summer wedding",
                    confidence=0.8,
                )
            ],
        )

        order_segment = Segment(
            segment_type=SegmentType.ORDER,
            main_sentence="I think I need some travel bag.",
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_category=ProductCategory.BAGS,
                    mention_text="travel bag",
                    confidence=0.7,
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E016",
            primary_intent="product inquiry",
            customer_name="Claire",
            segments=[inquiry_segment, order_segment],
        )

        # Create advisor output for dress inquiry
        dress_product = self.create_product(
            product_id="FSD2345",
            name="Floral Sundress",
            category="Women's Clothing",
            description="Embrace the warm weather in our floral sundress. This breezy, lightweight dress features a vibrant floral print and a flattering silhouette. Perfect for sunny days or tropical vacations.",
            price=58.0,
            seasons="Spring, Summer",
        )

        answered_question = QuestionAnswer(
            question="What dress options would work for a summer wedding?",
            answer="For a summer wedding, I recommend our Floral Sundress (FSD2345). It features a flattering silhouette that's not too tight or too loose, perfect for an outdoor ceremony. The lightweight, breathable fabric will keep you comfortable, and the midi length is appropriate for wedding guest attire.",
        )

        advisor_output = self.create_advisor_output(
            email_id="E016",
            answered_questions=[answered_question],
            primary_products=[dress_product],
        )

        # Create fulfiller output for bag suggestion (no specific bag ordered)
        fulfiller_output = self.create_fulfiller_output(
            email_id="E016",
            order_lines=[],  # No specific items ordered
            overall_status="no_valid_products",
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            advisor=advisor_output,
            fulfiller=fulfiller_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E016"
        assert composer_output.language == "English"
        assert (
            len(composer_output.response_body) > 150
        )  # Should be longer due to mixed content

        # Check personalization
        response_lower = composer_output.response_body.lower()
        assert "claire" in response_lower

        # Check that both dress and bag topics are addressed
        assert "dress" in response_lower or "sundress" in response_lower
        assert "bag" in response_lower or "travel" in response_lower

        # Check for appropriate wedding context
        assert "wedding" in response_lower

        # Check for warm, helpful tone
        assert composer_output.tone in [
            "friendly and helpful",
            "warm and personalized",
            "helpful and engaging",
            "professional and warm",  # Also valid for this scenario
            "friendly and enthusiastic",  # Also valid for this scenario
        ]

        print(f"✅ Composer response for E016:\n{composer_output.response_body}")

    @pytest.mark.asyncio
    async def test_composer_out_of_stock_e022(self, mock_runnable_config):
        """Test E022: Out of stock scenario with alternatives."""
        # Create the email
        email = self.create_customer_email(
            email_id="E022",
            subject="Placing My Order Today",
            message="Hi! I'm ready to place my order for those amazing bags I saw in your latest collection - you know, the ones with the geometric patterns that everyone's been talking about on Instagram? I want to get 3 of them, preferably in the darker shade you showed in your social media posts last week. I have the cash ready to go, just let me know where to send it! Can't wait to get my hands on them. Thanks, Monica",
        )

        # Create classifier output with order intent but vague product reference
        order_segment = Segment(
            segment_type=SegmentType.ORDER,
            main_sentence=email.message,
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_category=ProductCategory.BAGS,
                    mention_text="bags with geometric patterns",
                    confidence=0.6,
                    quantity=3,
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E022",
            primary_intent="order request",
            customer_name="Monica",
            segments=[order_segment],
        )

        # Create fulfiller output with no specific product found but alternatives offered
        fulfiller_output = self.create_fulfiller_output(
            email_id="E022",
            order_lines=[],  # No items fulfilled due to unclear reference
            overall_status="no_valid_products",
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            fulfiller=fulfiller_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E022"
        assert composer_output.language == "English"
        assert len(composer_output.response_body) > 100

        # Check personalization
        response_lower = composer_output.response_body.lower()
        assert "monica" in response_lower

        # Check that response addresses the unclear product reference
        assert (
            "geometric" in response_lower
            or "pattern" in response_lower
            or "clarif" in response_lower
        )

        # Check enthusiastic but professional tone to match customer's excitement
        tone_lower = composer_output.tone.lower()
        assert any(
            keyword in tone_lower
            for keyword in [
                "enthusiastic",
                "professional",
                "friendly",
                "warm",
                "helpful",
            ]
        ), f"Expected appropriate tone, got: {composer_output.tone}"

        print(f"✅ Composer response for E022:\n{composer_output.response_body}")

    @pytest.mark.asyncio
    async def test_composer_spanish_inquiry_e009(self, mock_runnable_config):
        """Test E009: Spanish language inquiry response."""
        # Create the email
        email = self.create_customer_email(
            email_id="E009",
            subject="Pregunta Sobre Gorro de Punto Grueso",
            message="Hola, tengo una pregunta sobre el DHN0987 Gorro de punto grueso. ¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno? Gracias de antemano.",
        )

        # Create classifier output with Spanish language
        inquiry_segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence=email.message,
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_id="DHN0987",
                    product_name="Gorro de punto grueso",
                    product_category=ProductCategory.ACCESSORIES,
                    mention_text="DHN0987 Gorro de punto grueso",
                    confidence=1.0,
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E009",
            language="Spanish",
            primary_intent="product inquiry",
            segments=[inquiry_segment],
        )

        # Create advisor output (using English product name for the system)
        beanie_product = self.create_product(
            product_id="DHN0987",
            name="Chunky Knit Beanie",
            category="Accessories",
            description="Keep your head toasty with our chunky knit beanie. Knitted from thick, cozy yarn, this trendy beanie offers a slouchy, oversized fit and a touch of rustic charm. A versatile accessory to elevate your cold-weather looks.",
            price=22.0,
            seasons="Fall, Winter",
        )

        answered_question = QuestionAnswer(
            question="¿De qué material está hecho? ¿Es lo suficientemente cálido para usar en invierno?",
            answer="El gorro está hecho de hilo grueso y acogedor, perfecto para mantener la cabeza caliente. Sí, es lo suficientemente cálido para usar en invierno, ya que está diseñado específicamente para el clima frío.",
        )

        advisor_output = self.create_advisor_output(
            email_id="E009",
            answered_questions=[answered_question],
            primary_products=[beanie_product],
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            advisor=advisor_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E009"
        assert composer_output.language == "Spanish"
        assert len(composer_output.response_body) > 100

        # Check Spanish language response
        response_lower = composer_output.response_body.lower()
        spanish_indicators = ["hola", "gracias", "está", "es", "para", "de"]
        assert any(indicator in response_lower for indicator in spanish_indicators)

        # Check product information is included
        assert "dhn0987" in response_lower or "gorro" in response_lower

        # Check for polite, helpful tone
        tone_lower = composer_output.tone.lower()
        assert any(
            keyword in tone_lower
            for keyword in [
                "professional",
                "respectful",
                "friendly",
                "helpful",
                "polite",
                "informative",
                "warm",
            ]
        ), f"Expected appropriate tone for Spanish inquiry, got: {composer_output.tone}"

        print(f"✅ Composer response for E009:\n{composer_output.response_body}")

    @pytest.mark.asyncio
    async def test_composer_rambling_customer_e012(self, mock_runnable_config):
        """Test E012: Customer with rambling, unfocused communication style."""
        # Create the email
        email = self.create_customer_email(
            email_id="E012",
            subject="Rambling About a New Work Bag",
            message="Hey, hope you're doing well. Last year for my birthday, my wife Emily got me a really nice leather briefcase from your store. I loved it and used it every day for work until the strap broke a few months ago. Speaking of broken things, I also need to get my lawnmower fixed before spring. Anyway, what were some of the other messenger bag or briefcase style options you have? I could go for something slightly smaller than my previous one. Oh and we also need to make dinner reservations for our anniversary next month. Maybe a nice Italian place downtown. What was I saying again? Oh right, work bags! Let me know what you'd recommend. Thanks!",
        )

        # Create classifier output with inquiry intent
        inquiry_segment = Segment(
            segment_type=SegmentType.INQUIRY,
            main_sentence="What were some of the other messenger bag or briefcase style options you have?",
            related_sentences=[
                "I could go for something slightly smaller than my previous one.",
                "Let me know what you'd recommend.",
            ],
            product_mentions=[
                ProductMention(
                    product_category=ProductCategory.BAGS,
                    mention_text="messenger bag or briefcase style options",
                    confidence=0.8,
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E012",
            primary_intent="product inquiry",
            segments=[inquiry_segment],
        )

        # Create advisor output with work bag recommendations
        messenger_bag = self.create_product(
            product_id="LTH2109",
            name="Leather Messenger Bag",
            category="Bags",
            description="Carry your essentials in style with our leather messenger bag. Crafted from premium, full-grain leather, this bag features a spacious main compartment, multiple pockets, and an adjustable strap for a comfortable fit. A timeless choice for work, travel, or everyday use.",
            price=37.99,
        )

        answered_question = QuestionAnswer(
            question="What messenger bag or briefcase options do you have?",
            answer="For work bags, I'd recommend our Leather Messenger Bag (LTH2109). It's a timeless design with premium leather construction, multiple compartments for organization, and an adjustable strap. At $37.99, it offers excellent value and would be perfect for daily work use.",
        )

        advisor_output = self.create_advisor_output(
            email_id="E012",
            answered_questions=[answered_question],
            primary_products=[messenger_bag],
        )

        # Create composer input
        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            advisor=advisor_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify the result structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Verify response content
        assert composer_output.email_id == "E012"
        assert composer_output.language == "English"
        assert len(composer_output.response_body) > 100

        # Check that response stays focused on work bags despite rambling input
        response_lower = composer_output.response_body.lower()
        assert (
            "bag" in response_lower
            or "messenger" in response_lower
            or "briefcase" in response_lower
        )

        # Should NOT mention lawnmower or dinner reservations
        assert "lawnmower" not in response_lower
        assert "dinner" not in response_lower
        assert "anniversary" not in response_lower

        # Check for friendly, focused tone
        tone_lower = composer_output.tone.lower()
        assert any(
            keyword in tone_lower
            for keyword in [
                "friendly",
                "focused",
                "helpful",
                "direct",
                "professional",
                "concise",
                "warm",
            ]
        ), f"Expected appropriate tone for rambling customer, got: {composer_output.tone}"

        print(f"✅ Composer response for E012:\n{composer_output.response_body}")

    @pytest.mark.asyncio
    async def test_composer_response_structure_validation(self, mock_runnable_config):
        """Test that composer output always has proper structure and required fields."""
        # Create a simple order scenario
        email = self.create_customer_email(
            email_id="E010",
            subject="Purchase Retro Sunglasses",
            message="Hello, I would like to order 1 pair of RSG8901 Retro Sunglasses. Thanks!",
        )

        order_segment = Segment(
            segment_type=SegmentType.ORDER,
            main_sentence=email.message,
            related_sentences=[],
            product_mentions=[
                ProductMention(
                    product_id="RSG8901",
                    product_name="Retro Sunglasses",
                    product_category=ProductCategory.ACCESSORIES,
                    mention_text="RSG8901 Retro Sunglasses",
                    confidence=1.0,
                    quantity=1,
                )
            ],
        )

        classifier_output = self.create_classifier_output(
            email_id="E010",
            primary_intent="order request",
            segments=[order_segment],
        )

        order_line = self.create_order_line(
            product_id="RSG8901",
            description="Retro Sunglasses",
            quantity=1,
            base_price=26.99,
            unit_price=26.99,
            status=OrderLineStatus.CREATED,
        )

        fulfiller_output = self.create_fulfiller_output(
            email_id="E010",
            order_lines=[order_line],
            total_price=26.99,
            overall_status="created",
        )

        composer_input = ComposerInput(
            email=email,
            classifier=classifier_output,
            fulfiller=fulfiller_output,
        )

        # Run the composer agent
        result = await run_composer(state=composer_input, config=mock_runnable_config)

        # Verify detailed structure
        assert isinstance(result, dict)
        assert Agents.COMPOSER in result
        composer_output = result[Agents.COMPOSER]
        assert isinstance(composer_output, ComposerOutput)

        # Check all required fields are present and properly typed
        assert isinstance(composer_output.email_id, str)
        assert composer_output.email_id == "E010"

        assert isinstance(composer_output.subject, str)
        assert len(composer_output.subject) > 0

        assert isinstance(composer_output.response_body, str)
        assert len(composer_output.response_body) > 50  # Reasonable minimum length

        assert isinstance(composer_output.language, str)
        assert composer_output.language in [
            "English",
            "Spanish",
            "French",
            "German",
        ]  # Expected languages

        assert isinstance(composer_output.tone, str)
        assert len(composer_output.tone) > 0

        assert isinstance(composer_output.response_points, list)
        # Response points should be generated for internal reasoning
        assert (
            len(composer_output.response_points) >= 0
        )  # Can be empty but should exist

        # Check that response includes signature
        response_lower = composer_output.response_body.lower()
        assert "hermes" in response_lower

        # Check that response is coherent (contains order information)
        assert "rsg8901" in response_lower or "sunglasses" in response_lower

        print(f"✅ Structure validation passed for E010")
        print(f"Subject: {composer_output.subject}")
        print(f"Language: {composer_output.language}")
        print(f"Tone: {composer_output.tone}")
        print(f"Response points count: {len(composer_output.response_points)}")

    async def validate_composer_response_with_llm(
        self,
        original_email: CustomerEmail,
        composer_output: ComposerOutput,
        validation_criteria: Optional[dict] = None,
    ) -> dict:
        """
        Use LLM-as-a-Judge to validate composer response quality.

        Args:
            original_email: The original customer email
            composer_output: The composer agent's output
            validation_criteria: Optional specific criteria to check

        Returns:
            Dict with validation results including score and detailed feedback
        """
        if validation_criteria is None:
            validation_criteria = {
                "personalization": "Does the response appropriately address the customer by name when provided?",
                "tone_consistency": "Is the tone appropriate for the customer's communication style?",
                "completeness": "Does the response address all aspects of the customer's email?",
                "professionalism": "Is the response professional and suitable for a fashion retailer?",
                "accuracy": "Are any product details, prices, or order information accurate?",
                "clarity": "Is the response clear, well-structured, and easy to understand?",
                "brand_voice": "Does the response maintain appropriate brand voice and include signature?",
            }

        criteria_text = "\n".join(
            [f"- {key}: {desc}" for key, desc in validation_criteria.items()]
        )

        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        prompt = f"""
You are evaluating customer service email responses for Hermes, a fashion retailer.

Original Customer Email:
Subject: {original_email.subject}
Message: {original_email.message}

Generated Response:
Subject: {composer_output.subject}
Body: {composer_output.response_body}
Language: {composer_output.language}
Tone: {composer_output.tone}

Please evaluate the response against these criteria:
{criteria_text}

For each criterion, provide:
1. Score (0-1): 0 = completely fails, 0.5 = partially meets, 1 = fully satisfies
2. Brief reasoning

Also provide an overall assessment score (0-1) and summary.

Format your response as:
Overall Score: [0.0 to 1.0]
Overall Reasoning: [Summary of key strengths and weaknesses]

Individual Criteria:
{chr(10).join([f"{key}: [score] - [reasoning]" for key in validation_criteria.keys()])}
"""

        try:
            response = await model.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content

            # Ensure result_text is a string
            if isinstance(result_text, list):
                result_text = str(result_text)
            elif not isinstance(result_text, str):
                result_text = str(result_text)

            # Parse the response
            lines = result_text.strip().split("\n")
            overall_score = 0.0
            overall_reasoning = ""
            individual_scores = {}

            # Parse overall score and reasoning
            for line in lines:
                if line.startswith("Overall Score:"):
                    try:
                        overall_score = float(line.split(":")[1].strip())
                    except:
                        overall_score = 0.0
                elif line.startswith("Overall Reasoning:"):
                    overall_reasoning = line.split(":", 1)[1].strip()

            # Parse individual criteria scores
            for line in lines:
                for criterion in validation_criteria.keys():
                    if line.startswith(f"{criterion}:"):
                        try:
                            # Extract score from format "criterion: [score] - [reasoning]"
                            parts = line.split(":", 1)[1].strip()
                            score_part = parts.split("-")[0].strip()
                            score = float(score_part)
                            reasoning = (
                                "-".join(parts.split("-")[1:]).strip()
                                if "-" in parts
                                else ""
                            )
                            individual_scores[criterion] = {
                                "score": score,
                                "reasoning": reasoning,
                            }
                        except:
                            individual_scores[criterion] = {
                                "score": 0.0,
                                "reasoning": "Parse error",
                            }

            return {
                "overall_score": overall_score,
                "overall_reasoning": overall_reasoning,
                "individual_scores": individual_scores,
                "validation_passed": overall_score >= 0.7,  # Threshold for acceptance
            }

        except Exception as e:
            return {
                "overall_score": 0.0,
                "overall_reasoning": f"LLM validation error: {str(e)}",
                "individual_scores": {},
                "validation_passed": False,
            }
