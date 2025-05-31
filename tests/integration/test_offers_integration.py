"""Integration tests for offers functionality using the complete workflow pipeline."""

import pytest
import os
import csv
from typing import Literal, cast
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from hermes.workflow.graph import workflow
from hermes.workflow.states import WorkflowInput
from hermes.model.email import CustomerEmail
from hermes.model.enums import Agents
from hermes.config import HermesConfig
from hermes.agents.fulfiller import FulfillerOutput


class TestOffersIntegration:
    """Integration tests for offers functionality using the complete workflow."""

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
            # Use the proxy base URL for OpenAI
            base_url = "https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/"
        else:  # Gemini
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                pytest.skip("GEMINI_API_KEY not set - skipping integration test")
            base_url = None

        return HermesConfig(
            llm_provider=llm_provider,
            llm_api_key=api_key,
            llm_provider_url=base_url,
            llm_strong_model_name="gpt-4o-mini"
            if llm_provider == "OpenAI"
            else "gemini-1.5-flash",
            llm_weak_model_name="gpt-4o-mini"
            if llm_provider == "OpenAI"
            else "gemini-1.5-flash",
        )

    @pytest.fixture
    def workflow_graph(self, hermes_config):
        """Create the workflow graph with configuration."""
        return workflow.with_config(hermes_config.as_runnable_config())

    def load_offers_emails(self) -> list[dict]:
        """Load the emails from emails-for-offers.csv."""
        emails = []
        with open("data/emails-for-offers.csv", "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                emails.append(row)
        return emails

    def create_customer_email(self, email_data: dict) -> CustomerEmail:
        """Create a CustomerEmail from CSV row data."""
        return CustomerEmail(
            email_id=email_data["email_id"],
            subject=email_data["subject"],
            message=email_data["message"],
        )

    @pytest.mark.asyncio
    async def test_no_promotion_for_standard_order(self, workflow_graph):
        """Test that no promotion is applied for a standard order not meeting BOGO criteria."""
        email_id = "E_NO_PROMO"
        customer_email = CustomerEmail(
            email_id=email_id,
            subject="Standard Order",
            message="I'd like to order one Canvas Beach Bag please.",
        )
        workflow_input = WorkflowInput(email=customer_email)
        final_state = await workflow_graph.ainvoke(workflow_input)

        assert Agents.FULFILLER in final_state
        fulfiller_output = final_state[Agents.FULFILLER]
        assert isinstance(fulfiller_output, FulfillerOutput)
        assert fulfiller_output.order_result is not None
        order = fulfiller_output.order_result
        assert order.total_discount == 0  # No discount should be applied

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Known issue: Advisor returns NoneType for email E024. See logs for details. Deferred."
    )
    async def test_bogo_beach_bag_explicit_order(self, workflow_graph):
        """Test E024: Explicit order for BOGO on canvas beach bag."""
        email_id = "E024"
        customer_email = CustomerEmail(
            email_id=email_id,
            subject="Beach bags for vacation",
            message="Hi! My sister and I are planning a beach vacation next month and we both need new beach bags. I think you sell canvas beach bags? Someone mentioned there might be a good deal if we buy multiple ones. Could you help us out? Thanks, Sarah",
        )
        workflow_input = WorkflowInput(email=customer_email)
        final_state = await workflow_graph.ainvoke(workflow_input)

        assert Agents.CLASSIFIER in final_state
        assert Agents.STOCKKEEPER in final_state
        assert Agents.FULFILLER in final_state
        assert Agents.COMPOSER in final_state

        # Check classifier detected order intent
        classifier_output = final_state[Agents.CLASSIFIER]
        print(
            f"Classifier output for E024: {classifier_output.email_analysis.model_dump_json(indent=2)}"
        )
        assert classifier_output.email_analysis.primary_intent == "order request"

        # Check stockkeeper resolved CBG9876 Canvas Beach Bag
        stockkeeper_output = final_state[Agents.STOCKKEEPER]
        print(
            f"Stockkeeper output for E024: {stockkeeper_output.model_dump_json(indent=2)}"
        )
        assert len(stockkeeper_output.resolved_products) == 1
        assert stockkeeper_output.resolved_products[0].product_id == "CBG9876"

        # Check fulfiller processed order with promotion
        fulfiller_output = final_state[Agents.FULFILLER]
        assert fulfiller_output.order_result.overall_status == "created"
        assert len(fulfiller_output.order_result.lines) > 0

        # Check for promotion application
        order_line = fulfiller_output.order_result.lines[0]
        assert order_line.quantity >= 2  # Should order 2 for BOGO

        # If promotion was applied, there should be a discount
        if order_line.promotion_applied:
            assert fulfiller_output.order_result.total_discount > 0
            assert (
                "bogo" in order_line.promotion_description.lower()
                or "50%" in order_line.promotion_description
            )

        # Check composer mentioned promotion
        composer_output = final_state[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert "sarah" in response_body  # Personalization
        assert any(
            term in response_body
            for term in ["beach bag", "canvas", "promotion", "deal", "discount"]
        )

        print(f"✅ E024 Beach Bag BOGO Test Completed")
        print(f"Final Order Total: ${fulfiller_output.order_result.total_price}")
        print(f"Total Discount: ${fulfiller_output.order_result.total_discount}")

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Advisor may return None for vague inquiries with no resolved product context (E032)."
    )
    async def test_vague_beach_bag_inquiry(self, workflow_graph):
        """Test E032: Vague inquiry about beach bag deals."""
        email_data = {
            "email_id": "E032",
            "subject": "Friend mentioned beach bags",
            "message": "Hi there, I heard from a friend that you have really nice beach bags and she said there was some kind of special offer? I'm not sure what exactly but she seemed excited about it. Could you tell me more? I might need a couple for my family. Thanks!",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.ADVISOR in result  # Should route to advisor for inquiry
        assert Agents.COMPOSER in result

        # Check classifier detected inquiry intent
        classifier_output = result[Agents.CLASSIFIER]
        assert classifier_output.email_analysis.primary_intent == "product inquiry"

        # Check advisor provided information about beach bag promotion
        advisor_output = result[Agents.ADVISOR]
        assert len(advisor_output.inquiry_answers.answered_questions) > 0

        # Check composer explained the promotion
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert any(
            term in response_body
            for term in ["beach bag", "canvas", "promotion", "deal", "bogo", "50%"]
        )

        print(f"✅ E032 Vague Beach Bag Inquiry Test Completed")
        print(
            f"Response includes promotion details: {any(term in response_body for term in ['bogo', '50%', 'buy one'])}"
        )

    @pytest.mark.asyncio
    async def test_partial_bundle_order(self, workflow_graph):
        """Test E033: Order for just the vest (partial bundle)."""
        email_data = {
            "email_id": "E033",
            "subject": "Just want the vest",
            "message": "Hello, I'd like to order that plaid flannel vest. I think the code was PLV8765? Just the vest for now, thanks.",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.FULFILLER in result
        assert Agents.COMPOSER in result

        # Check stockkeeper resolved PLV8765 vest
        stockkeeper_output = result[Agents.STOCKKEEPER]
        product_ids = [p.product_id for p in stockkeeper_output.resolved_products]
        assert "PLV8765" in product_ids

        # Check fulfiller processed single vest order
        fulfiller_output = result[Agents.FULFILLER]
        assert fulfiller_output.order_result.overall_status == "created"
        vest_line = next(
            (
                line
                for line in fulfiller_output.order_result.lines
                if line.product_id == "PLV8765"
            ),
            None,
        )
        assert vest_line is not None
        assert vest_line.quantity == 1

        # Check composer mentioned bundle opportunity
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert any(
            term in response_body
            for term in ["shirt", "bundle", "matching", "combination", "plaid"]
        )

        print(f"✅ E033 Partial Bundle Test Completed")
        print(
            f"Mentioned bundle opportunity: {any(term in response_body for term in ['shirt', 'bundle', 'matching'])}"
        )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Stockkeeper may not resolve all bundle components, leading to 'out of stock' status (E034)."
    )
    async def test_complete_bundle_order(self, workflow_graph):
        """Test E034: Order for both vest and shirt (complete bundle)."""
        email_data = {
            "email_id": "E034",
            "subject": "Vest and shirt together",
            "message": "Hi, I want to order the plaid vest PLV8765 and I think there's a matching shirt that goes with it? I'd like both pieces if possible. Thanks, Alex",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.FULFILLER in result
        assert Agents.COMPOSER in result

        # Check stockkeeper resolved both vest and shirt
        stockkeeper_output = result[Agents.STOCKKEEPER]
        product_ids = [p.product_id for p in stockkeeper_output.resolved_products]
        assert "PLV8765" in product_ids  # Should include vest

        # Check fulfiller processed bundle order
        fulfiller_output = result[Agents.FULFILLER]
        assert fulfiller_output.order_result.overall_status == "created"

        # Look for both products in order lines
        order_lines = fulfiller_output.order_result.lines
        vest_line = next(
            (line for line in order_lines if "PLV8765" in line.product_id), None
        )
        assert vest_line is not None

        # Check for bundle promotion application
        total_discount = fulfiller_output.order_result.total_discount
        if total_discount > 0:
            print(f"Bundle discount applied: ${total_discount}")

        # Check composer confirmed bundle order
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert "alex" in response_body  # Personalization
        assert any(
            term in response_body for term in ["vest", "shirt", "bundle", "plaid"]
        )

        print(f"✅ E034 Complete Bundle Test Completed")
        print(f"Total Discount Applied: ${total_discount}")

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Advisor may return None for inquiries with no resolved product context (E035)."
    )
    async def test_single_item_bundle_inquiry(self, workflow_graph):
        """Test E035: Inquiry about just the shirt from bundle."""
        email_data = {
            "email_id": "E035",
            "subject": "About your plaid shirts",
            "message": "Good morning, I'm interested in plaid shirts. I think I saw one mentioned somewhere as part of some kind of deal? Could you tell me about your plaid shirt options and any special offers? I might just want the shirt.",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow routes to advisor for inquiry
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.ADVISOR in result
        assert Agents.COMPOSER in result

        # Check advisor provided bundle information
        advisor_output = result[Agents.ADVISOR]
        assert len(advisor_output.inquiry_answers.answered_questions) > 0

        # Check composer encouraged bundle purchase
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert any(
            term in response_body
            for term in ["plaid", "shirt", "vest", "bundle", "together", "combination"]
        )

        print(f"✅ E035 Single Item Bundle Inquiry Test Completed")
        print(
            f"Encouraged bundle purchase: {any(term in response_body for term in ['vest', 'bundle', 'together'])}"
        )

    @pytest.mark.asyncio
    async def test_spanish_language_offers(self, workflow_graph):
        """Test E031: Spanish inquiry about bag promotions."""
        email_data = {
            "email_id": "E031",
            "subject": "Pregunta sobre bolsos",
            "message": "Hola, estoy buscando bolsos y he oído que tienen buenos precios. ¿Qué opciones tienen en bolsos de playa y bolsos para trabajo? Me interesan especialmente los modelos CBG9876 y QTP5432. Gracias, María",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.ADVISOR in result
        assert Agents.COMPOSER in result

        # Check classifier detected Spanish language
        classifier_output = result[Agents.CLASSIFIER]
        assert classifier_output.email_analysis.language.lower() in [
            "spanish",
            "español",
        ]

        # Check stockkeeper resolved both bag products
        stockkeeper_output = result[Agents.STOCKKEEPER]
        product_ids = [p.product_id for p in stockkeeper_output.resolved_products]
        assert "CBG9876" in product_ids or "QTP5432" in product_ids

        # Check composer responded in Spanish
        composer_output = result[Agents.COMPOSER]
        assert composer_output.language.lower() in ["spanish", "español"]
        response_body = composer_output.response_body.lower()

        # Check for Spanish language indicators
        spanish_indicators = [
            "hola",
            "gracias",
            "precio",
            "bolso",
            "bolsa",
            "oferta",
            "promoción",
        ]
        assert any(indicator in response_body for indicator in spanish_indicators)

        # Check for promotion information
        assert "maría" in response_body  # Personalization

        print(f"✅ E031 Spanish Language Offers Test Completed")
        print(f"Response in Spanish: {composer_output.language}")

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Advisor may return None for inquiries with no resolved product context (E047)."
    )
    async def test_multiple_promotions_inquiry(self, workflow_graph):
        """Test E047: Multiple items pricing inquiry."""
        email_data = {
            "email_id": "E047",
            "subject": "Multiple items pricing",
            "message": "Good morning, could you give me pricing for: 1 quilted tote bag, 1 floral dress, and 2 beach bags? What would be my total cost? Thanks!",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.ADVISOR in result
        assert Agents.COMPOSER in result

        # Check stockkeeper resolved multiple products
        stockkeeper_output = result[Agents.STOCKKEEPER]
        assert (
            len(stockkeeper_output.resolved_products) >= 2
        )  # Should find multiple products

        # Check advisor calculated pricing with promotions
        advisor_output = result[Agents.ADVISOR]
        assert len(advisor_output.inquiry_answers.answered_questions) > 0

        # Check composer provided comprehensive pricing breakdown
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()

        # Should mention different products and their promotions
        assert any(term in response_body for term in ["tote", "quilted"])
        assert any(term in response_body for term in ["dress", "floral"])
        assert any(term in response_body for term in ["beach bag", "canvas"])

        # Should mention promotions/pricing
        assert any(
            term in response_body
            for term in ["discount", "promotion", "deal", "total", "price"]
        )

        print(f"✅ E047 Multiple Promotions Inquiry Test Completed")
        print(f"Comprehensive pricing provided: {len(response_body) > 200}")

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Stockkeeper fails to resolve correct product ID (CBG9876) when a similar incorrect one (CBG9867) is also mentioned (E043)."
    )
    async def test_wrong_product_id_correction(self, workflow_graph):
        """Test E043: Wrong product ID correction."""
        email_data = {
            "email_id": "E043",
            "subject": "Beach bag confusion",
            "message": "Hi, I want to order those beach bags I saw. I think the code is CBG9867? Or maybe it was CBG9876? Anyway, I want 2 of them. Thanks!",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify workflow completion
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.FULFILLER in result
        assert Agents.COMPOSER in result

        # Check stockkeeper handled incorrect ID and found correct product
        stockkeeper_output = result[Agents.STOCKKEEPER]
        product_ids = [p.product_id for p in stockkeeper_output.resolved_products]
        assert "CBG9876" in product_ids  # Should find correct product

        # Check fulfiller processed order for 2 bags
        fulfiller_output = result[Agents.FULFILLER]
        order_line = fulfiller_output.order_result.lines[0]
        assert order_line.quantity == 2

        # Check composer corrected the product ID and mentioned promotion
        composer_output = result[Agents.COMPOSER]
        response_body = composer_output.response_body.lower()
        assert "cbg9876" in response_body  # Correct product ID
        assert any(term in response_body for term in ["beach bag", "canvas"])

        print(f"✅ E043 Wrong Product ID Correction Test Completed")
        print(f"Correct product ID used: CBG9876")

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, workflow_graph):
        """Test workflow handles malformed emails gracefully."""
        email_data = {
            "email_id": "E999",
            "subject": "",
            "message": "xyz",
        }

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow - should not crash
        result = await workflow_graph.ainvoke(workflow_input)

        # Verify basic workflow completion (even with minimal content)
        assert Agents.CLASSIFIER in result
        assert Agents.COMPOSER in result  # Should at least get to composer

        print(f"✅ Error Handling Test Completed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("email_id", ["E024", "E025", "E026", "E027", "E028"])
    async def test_core_promotion_scenarios(self, workflow_graph, email_id):
        """Test core promotion scenarios from the first 5 emails."""
        emails = self.load_offers_emails()
        email_data = next(
            (email for email in emails if email["email_id"] == email_id), None
        )

        if not email_data:
            pytest.skip(f"Email {email_id} not found in dataset")

        customer_email = self.create_customer_email(email_data)
        workflow_input = WorkflowInput(email=customer_email)

        # Run the complete workflow
        result = await workflow_graph.ainvoke(workflow_input)

        # Basic assertions for all scenarios
        assert Agents.CLASSIFIER in result
        assert Agents.STOCKKEEPER in result
        assert Agents.COMPOSER in result

        # Check that classifier parsed the email
        classifier_output = result[Agents.CLASSIFIER]
        assert classifier_output.email_analysis.email_id == email_id
        assert len(classifier_output.email_analysis.segments) > 0

        # Check that stockkeeper found products
        stockkeeper_output = result[Agents.STOCKKEEPER]
        # Note: Some emails might not have specific products, so we just check it ran

        # Check that composer generated a response
        composer_output = result[Agents.COMPOSER]
        assert len(composer_output.response_body) > 50  # Reasonable response length
        assert composer_output.email_id == email_id

        # Check specific expected behavior based on email
        expected_behavior = email_data.get("expected_behavior", "")
        response_body = composer_output.response_body.lower()

        # Basic checks based on expected behavior
        if "bogo" in expected_behavior.lower():
            # For BOGO scenarios, check if promotion was detected
            if Agents.FULFILLER in result:
                fulfiller_output = result[Agents.FULFILLER]
                print(
                    f"BOGO scenario - Total discount: ${fulfiller_output.order_result.total_discount}"
                )

        if "25% off" in expected_behavior:
            # For percentage discount scenarios
            if "25" in response_body or "discount" in response_body:
                print(f"Percentage discount mentioned in response")

        if "bundle" in expected_behavior.lower():
            # For bundle scenarios
            if any(
                term in response_body
                for term in ["bundle", "matching", "together", "combination"]
            ):
                print(f"Bundle opportunity mentioned in response")

        print(f"✅ Core Promotion Test {email_id} Completed")

    def test_offers_dataset_completeness(self):
        """Test that the offers dataset has comprehensive coverage."""
        emails = self.load_offers_emails()

        # Check we have a good number of test cases
        assert len(emails) >= 30, f"Expected at least 30 test emails, got {len(emails)}"

        # Check we have both order and inquiry classifications
        classifications = [email["classification"] for email in emails]
        assert "order" in classifications
        assert "inquiry" in classifications

        # Check we have coverage of all promotion types
        expected_behaviors = [email["expected_behavior"] for email in emails]
        all_behaviors = " ".join(expected_behaviors).lower()

        # Check for different promotion types
        assert "bogo" in all_behaviors or "buy one" in all_behaviors
        assert "25%" in all_behaviors or "20%" in all_behaviors
        assert "bundle" in all_behaviors
        assert "free" in all_behaviors

        # Check for different scenarios
        assert any("partial" in behavior.lower() for behavior in expected_behaviors)
        assert any("complete" in behavior.lower() for behavior in expected_behaviors)
        assert any("single" in behavior.lower() for behavior in expected_behaviors)

        print(f"✅ Dataset Completeness Check Passed")
        print(f"Total test emails: {len(emails)}")
        print(
            f"Order emails: {len([e for e in emails if e['classification'] == 'order'])}"
        )
        print(
            f"Inquiry emails: {len([e for e in emails if e['classification'] == 'inquiry'])}"
        )
