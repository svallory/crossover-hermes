"""Pydantic models for the inquiry responder agent."""


from pydantic import BaseModel, Field

from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.model.product import Product

class ExtractedQuestion(BaseModel):
    """A question extracted from a customer inquiry segment."""

    question_text: str = Field(description="The original question text from the customer")
    question_type: str = Field(
        description="Type/category of the question (e.g., availability, features, sizing, compatibility)"
    )
    related_product_ids: list[str] = Field(
        default_factory=list,
        description="Product IDs this question might be related to",
    )


class QuestionAnswer(BaseModel):
    """An answer to a customer question."""

    question: str = Field(description="Original question from the customer")
    answer: str = Field(description="Factual, objective answer to the question")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level in this answer")
    reference_product_ids: list[str] = Field(default_factory=list, description="Product IDs referenced in this answer")
    answer_type: str = Field(
        default="factual",
        description="Type of answer (factual, speculative, unavailable)",
    )


class InquiryAnswers(BaseModel):
    """Objective factual response to a customer inquiry."""

    email_id: str = Field(description="The unique identifier for the email")
    primary_products: list[Product] = Field(
        default_factory=list, description="Products directly mentioned by the customer"
    )
    answered_questions: list[QuestionAnswer] = Field(
        default_factory=list,
        description="Questions from the customer with factual answers",
    )
    unanswered_questions: list[str] = Field(
        default_factory=list,
        description="Questions that couldn't be answered with available information",
    )
    related_products: list[Product] = Field(
        default_factory=list,
        description="Objectively related products based on customer inquiries",
    )
    unsuccessful_references: list[str] = Field(
        default_factory=list, description="Product references that couldn't be resolved"
    )


class AdvisorInput(BaseModel):
    """Input model for the inquiry responder."""

    classifier: ClassifierOutput = Field(description="Complete EmailAnalysisResult from the analyzer")
    stockkeeper: StockkeeperOutput | None = Field(
        default=None, description="Resolved products from the product resolver"
    )


class AdvisorOutput(BaseModel):
    """Output model for the inquiry responder function."""

    inquiry_answers: InquiryAnswers = Field(description="The factual response to the customer inquiry")
