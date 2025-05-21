import pytest
from dotenv import load_dotenv

from src.hermes.agents.advisor.agent import respond_to_inquiry
from src.hermes.agents.advisor.models import AdvisorInput
from src.hermes.agents.classifier.models import ClassifierOutput, EmailAnalysis, Segment, SegmentType
from src.hermes.config import HermesConfig
from src.hermes.data_processing.vector_store import VectorStore
from src.hermes.model import Agents

@pytest.mark.asyncio
async def test_advisor_with_vector_store():
    """Test that the inquiry responder can answer questions using the vector store."""
    # Load environment variables
    load_dotenv()

    # Create a config with hermes_config
    hermes_config = HermesConfig()

    # First, ensure the vector store is initialized with data
    # This is critical - the search_vector_store function needs actual data
    VectorStore(hermes_config=hermes_config)
    # We don't need to assert success anymore as get_vector_store raises an exception on failure

    # Create a mock email analysis with an inquiry
    email_analysis = EmailAnalysis(
        email_id="test-123",
        primary_intent="product inquiry",  # Use proper Literal value
        segments=[
            Segment(
                segment_type=SegmentType.INQUIRY,
                main_sentence="Do you sell leather messenger bags?",
                related_sentences=["What's the price range for your messenger bags?"],
                product_mentions=[],
            )
        ],
    )

    # Create the ClassifierOutput object
    classifier_output = ClassifierOutput(
        email_analysis=email_analysis,
        unique_products=[],  # No specific unique products for this test
    )

    # Create the input state expected by respond_to_inquiry
    input_state = AdvisorInput(classifier=classifier_output)

    # Call the function
    result = await respond_to_inquiry(
        state=input_state, runnable_config={"configurable": {"hermes_config": hermes_config}}
    )

    # Check that we got a valid response
    assert Agents.ADVISOR in result, "No advisor data in result"
    output = result[Agents.ADVISOR]
    inquiry_answers = output.inquiry_answers

    # Verify we got answers and not errors
    assert len(inquiry_answers.answered_questions) > 0, "No questions were answered"
    assert len(inquiry_answers.primary_products) > 0, "No primary products were identified"

    # Print results for debugging
    print(f"Answered questions: {inquiry_answers.answered_questions}")
    print(f"Primary products: {inquiry_answers.primary_products}")
    print(f"Related products: {inquiry_answers.related_products}")
