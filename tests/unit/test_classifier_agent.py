"""Unit tests for the classifier agent."""

from hermes.model.email import EmailAnalysis, CustomerEmail
from hermes.agents.classifier.models import ClassifierInput, ClassifierOutput


class TestClassifierAgent:
    """Test cases for the classifier agent."""

    def test_classifier_input_model(self):
        """Test ClassifierInput model validation."""

        email = CustomerEmail(
            email_id="test_001", subject="Test subject", message="Test message"
        )

        classifier_input = ClassifierInput(email=email)
        assert classifier_input.email.email_id == "test_001"

    def test_classifier_output_model(self):
        """Test ClassifierOutput model validation."""

        email_analysis = EmailAnalysis(
            email_id="test_001",
            language="English",
            primary_intent="order request",
            customer_name="Test User",
            segments=[],
        )

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        assert classifier_output.email_analysis.email_id == "test_001"
        assert isinstance(classifier_output.email_analysis.customer_name, str)
