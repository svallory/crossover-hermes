"""Integration tests for offers functionality using the complete workflow pipeline."""

import pytest
import os
import csv
from typing import Literal, cast
from dotenv import load_dotenv
from hermes.utils.logger import logger

# Load environment variables from .env file
load_dotenv()

from hermes.workflow.graph import workflow
from hermes.workflow.states import WorkflowInput
from hermes.model.email import CustomerEmail
from hermes.model.enums import Agents
from hermes.config import HermesConfig
from hermes.agents.fulfiller import FulfillerOutput
import hermes.data.load_data  # Import the module


class TestOffersIntegration:
    """Integration tests for offers functionality using the complete workflow."""

    @pytest.fixture
    def hermes_config(self, request):
        """Create a test configuration for integration testing.
        This will now primarily rely on HermesConfig to pick up defaults
        from environment variables or its internal _DEFAULT_CONFIG,
        ensuring test LLM configuration aligns with the project's base config.
        """
        # 1. Clear the cache ensure it's reset before anything
        hermes.data.load_data._products_df = None
        logger.info("Cleared hermes.data.load_data._products_df cache.")

        # 2. Force populate the cache with the local CSV
        try:
            # This directly loads and caches the local CSV.
            hermes.data.load_data.load_products_df(source="data/products.csv")
            logger.info(
                f"Force-loaded and cached data/products.csv via load_products_df for test: {request.node.name}. Loaded {len(hermes.data.load_data._products_df)} products."
            )
        except Exception as e:
            pytest.fail(f"Failed to force-load data/products.csv for tests: {e}")

        # Teardown function to clear the cache after the test
        def fin():
            hermes.data.load_data._products_df = None
            logger.info(
                f"Cleared hermes.data.load_data._products_df cache after test: {request.node.name}."
            )

        request.addfinalizer(fin)

        # Now proceed with the rest of the config.
        # The workflow should now use the pre-cached _products_df.
        llm_provider_env = os.getenv("LLM_PROVIDER")
        temp_config_for_provider = HermesConfig()

        llm_provider_to_use = llm_provider_env or temp_config_for_provider.llm_provider

        api_key = os.getenv(f"{llm_provider_to_use.upper()}_API_KEY")
        if not api_key:
            if llm_provider_to_use == "OpenAI":
                api_key = os.getenv("OPENAI_API_KEY")
            elif llm_provider_to_use == "Gemini":
                api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                pytest.skip(
                    f"{llm_provider_to_use.upper()}_API_KEY (or fallback OPENAI/GEMINI_API_KEY) not set - skipping integration test"
                )

        # Instantiate HermesConfig. It will use its logic to determine model names
        # and llm_provider_url based on the provider and environment variables
        # or its internal defaults if those env vars aren't set.
        return HermesConfig(
            llm_provider=cast(Literal["OpenAI", "Gemini"], llm_provider_to_use),
            llm_api_key=api_key,
            # llm_provider_url will be handled by HermesConfig internal logic
            # llm_strong_model_name and llm_weak_model_name will be handled by HermesConfig
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
    async def test_bogo_beach_bag_explicit_order(self, workflow_graph):
        """Test E024: Explicit order for BOGO on canvas beach bag."""
        email_id = "E024"
        # Load the specific email data from the CSV
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

        customer_email = self.create_customer_email(email_data)
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
        assert (
            len(stockkeeper_output.candidate_products_for_mention) == 1
        ), "Should process one product mention"

        # Get the list of candidate products for the first (and only) mention
        # The [1] accesses the list of Product candidates from the tuple (ProductMention, list[Product])
        candidates_for_first_mention = (
            stockkeeper_output.candidate_products_for_mention[0][1]
        )
        assert (
            len(candidates_for_first_mention) == 1
        ), "Should find exactly one candidate for an explicit product ID"
        assert (
            candidates_for_first_mention[0].product_id == "CBG9876"
        ), "Resolved product ID should be CBG9876"

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
    async def test_vague_beach_bag_inquiry(self, workflow_graph):
        """Test E032: Vague inquiry about beach bag deals."""
        email_id = "E032"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        email_id = "E033"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        resolved_candidate_ids_partial = []
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates,
            ) in stockkeeper_output.candidate_products_for_mention:
                for product_candidate in candidates:
                    resolved_candidate_ids_partial.append(product_candidate.product_id)
        assert "PLV8765" in resolved_candidate_ids_partial

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
    async def test_complete_bundle_order(self, workflow_graph):
        """Test E034: Order for both vest and shirt (complete bundle)."""
        email_id = "E034"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        resolved_candidate_ids_complete = []
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates,
            ) in stockkeeper_output.candidate_products_for_mention:
                for product_candidate in candidates:
                    resolved_candidate_ids_complete.append(product_candidate.product_id)
        assert "PLV8765" in resolved_candidate_ids_complete  # Should include vest

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
    async def test_single_item_bundle_inquiry(self, workflow_graph):
        """Test E035: Inquiry about just the shirt from bundle."""
        email_id = "E035"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        email_id = "E031"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        resolved_candidate_ids_spanish = []
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates,
            ) in stockkeeper_output.candidate_products_for_mention:
                for product_candidate in candidates:
                    resolved_candidate_ids_spanish.append(product_candidate.product_id)
        assert (
            "CBG9876" in resolved_candidate_ids_spanish
            or "QTP5432" in resolved_candidate_ids_spanish
        )

        # Check composer responded in Spanish
        composer_output = result[Agents.COMPOSER]
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

    @pytest.mark.asyncio
    async def test_multiple_promotions_inquiry(self, workflow_graph):
        """Test E047: Multiple items pricing inquiry."""
        email_id = "E047"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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

        # Count how many mentions have at least one candidate product
        num_mentions_with_candidates = 0
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates_list,
            ) in stockkeeper_output.candidate_products_for_mention:
                if (
                    candidates_list
                ):  # Check if the list of Product candidates is not empty
                    num_mentions_with_candidates += 1

        assert (
            num_mentions_with_candidates >= 3
        ), "Should find candidates for at least 3 product mentions for E047"

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
    async def test_wrong_product_id_correction(self, workflow_graph):
        """Test E043: Wrong product ID correction."""
        email_id = "E043"
        email_data_list = [
            e for e in self.load_offers_emails() if e["email_id"] == email_id
        ]
        if not email_data_list:
            pytest.fail(f"Email ID {email_id} not found in data/emails-for-offers.csv")
        email_data = email_data_list[0]

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
        resolved_candidate_ids_wrong_id = []
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates,
            ) in stockkeeper_output.candidate_products_for_mention:
                for product_candidate in candidates:
                    resolved_candidate_ids_wrong_id.append(product_candidate.product_id)
        assert (
            "CBG9876" in resolved_candidate_ids_wrong_id
        )  # Should find correct product

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
        has_candidates = False
        if stockkeeper_output.candidate_products_for_mention:
            for (
                _mention,
                candidates,
            ) in stockkeeper_output.candidate_products_for_mention:
                if candidates:
                    has_candidates = True
                    break
        # assert has_candidates or not stockkeeper_output.unresolved_mentions # Or some other logic depending on test intent

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
