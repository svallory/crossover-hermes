"""
Pydantic models for the inquiry responder agent.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

from src.hermes.agents.classifier.models import EmailAnalysis, EmailAnalyzerOutput
from src.hermes.agents.product_resolver.models import ResolvedProductsOutput
from src.hermes.model.product import Product


class ExtractedQuestion(BaseModel):
    """A question extracted from a customer inquiry segment."""

    question_text: str = Field(description="The original question text from the customer")
    question_type: str = Field(
        description="Type/category of the question (e.g., availability, features, sizing, compatibility)"
    )
    related_product_ids: List[str] = Field(
        default_factory=list,
        description="Product IDs this question might be related to",
    )


class QuestionAnswer(BaseModel):
    """An answer to a customer question."""

    question: str = Field(description="Original question from the customer")
    answer: str = Field(description="Factual, objective answer to the question")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level in this answer")
    reference_product_ids: List[str] = Field(default_factory=list, description="Product IDs referenced in this answer")
    answer_type: str = Field(
        default="factual",
        description="Type of answer (factual, speculative, unavailable)",
    )


class ProductInformation(BaseModel):
    """Detailed product information for customer response."""

    product: Product
    is_available: bool = Field(description="Whether the product is in stock")
    stock_amount: int = Field(description="Current stock level")
    has_promotion: bool = Field(default=False, description="Whether the product has an active promotion")
    promotion_text: Optional[str] = Field(default=None, description="Description of the active promotion if any")


class InquiryAnswers(BaseModel):
    """Objective factual response to a customer inquiry."""

    email_id: str = Field(description="The unique identifier for the email")
    primary_products: List[ProductInformation] = Field(
        default_factory=list, description="Products directly mentioned by the customer"
    )
    answered_questions: List[QuestionAnswer] = Field(
        default_factory=list,
        description="Questions from the customer with factual answers",
    )
    unanswered_questions: List[str] = Field(
        default_factory=list,
        description="Questions that couldn't be answered with available information",
    )
    related_products: List[ProductInformation] = Field(
        default_factory=list,
        description="Objectively related products based on customer inquiries",
    )
    unsuccessful_references: List[str] = Field(
        default_factory=list, description="Product references that couldn't be resolved"
    )


class InquiryResponderInput(BaseModel):
    """
    Input model for the inquiry responder.
    """

    email_analyzer: EmailAnalyzerOutput = Field(description="Complete EmailAnalysisResult from the analyzer")
    product_resolver: Optional[ResolvedProductsOutput] = Field(
        default=None, 
        description="Resolved products from the product resolver"
    )


class InquiryResponderOutput(BaseModel):
    """
    Output model for the inquiry responder function.
    """

    inquiry_answers: InquiryAnswers = Field(description="The factual response to the customer inquiry")
