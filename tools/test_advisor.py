#!/usr/bin/env python
"""
Test script for the Inquiry Responder agent in isolation.

This script initializes the vector store, creates a test inquiry, and runs
the respond_to_inquiry function to verify it works correctly.
"""

import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# Add the project root to the path so we can import the modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import modules after adding project root to path to avoid circular imports
# or importing modules that don't exist in the Python path
from src.hermes.agents.classifier.models import EmailAnalysis, Segment, SegmentType, ProductMention  # noqa: E402
from src.hermes.agents.advisor.agent import respond_to_inquiry  # noqa: E402
from src.hermes.agents.advisor.models import AdvisorInput, ClassifierOutput  # noqa: E402
from src.hermes.config import HermesConfig  # noqa: E402
from src.hermes.data_processing.vector_store import VectorStore  # noqa: E402
from src.hermes.model import ProductCategory, Agents  # noqa: E402


async def main():
    """Test the inquiry responder independently."""
    print("\n==== Testing Inquiry Responder ====\n")

    # Create a hermes config
    hermes_config = HermesConfig()

    # Initialize vector store
    print("Initializing vector store...")
    VectorStore(hermes_config=hermes_config)

    # Load environment variables
    load_dotenv()
    print("Testing the Inquiry Responder agent in isolation")

    # Step 2: Create a test email analysis with a product inquiry
    print("\nStep 2: Creating test inquiry...")
    email_analysis = EmailAnalysis(
        email_id="test-123",
        primary_intent="product inquiry",
        segments=[
            Segment(
                segment_type=SegmentType.INQUIRY,
                main_sentence="What messenger bags do you sell?",
                related_sentences=[
                    "I'm looking for a leather bag for work",
                    "What's your price range for messenger bags?",
                ],
                product_mentions=[
                    ProductMention(
                        product_name="messenger bag", product_type="bag", product_category=ProductCategory.BAGS
                    )
                ],
            )
        ],
    )

    # Step 3: Create input state for the inquiry responder
    input_state = AdvisorInput(
        # Create a proper ClassifierOutput instance
        classifier=ClassifierOutput(
            email_analysis=email_analysis,
            unique_products=[],  # No specific unique products needed for this test
        )
    )

    # Step 4: Call the respond_to_inquiry function
    print("\nStep 3: Calling respond_to_inquiry...")
    result = await respond_to_inquiry(
        state=input_state, runnable_config={"configurable": {"hermes_config": hermes_config}}
    )

    # Step 6: Process and display results
    print("\nStep 4: Results:")
    # Check if we have a success response or an error
    if Agents.ADVISOR in result:
        # Success case - we have an AdvisorOutput
        output = result[Agents.ADVISOR]
        inquiry_answers = output.inquiry_answers
        print(f"\nSuccessfully generated answers for email {inquiry_answers.email_id}")
        print(f"\nAnswered Questions ({len(inquiry_answers.answered_questions)}):")
        for i, answer in enumerate(inquiry_answers.answered_questions, 1):
            print(f"{i}. Q: {answer.question}")
            print(f"   A: {answer.answer}")

        print(f"\nPrimary Products ({len(inquiry_answers.primary_products)}):")
        for i, prod in enumerate(inquiry_answers.primary_products, 1):
            print(f"{i}. {prod}")

        print(f"\nRelated Products ({len(inquiry_answers.related_products)}):")
        for i, prod in enumerate(inquiry_answers.related_products, 1):
            print(f"{i}. {prod}")

        print(f"\nUnanswered Questions ({len(inquiry_answers.unanswered_questions)}):")
        for i, q in enumerate(inquiry_answers.unanswered_questions, 1):
            print(f"{i}. {q}")
    elif "errors" in result:
        # Error case
        print("ERROR: Agent returned an error:")
        error = result["errors"].get(Agents.ADVISOR)
        if error:
            print(f"Message: {error.message}")
            if error.details:
                print(f"Details: {error.details}")
    else:
        print("ERROR: Unexpected result format!")
        print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
