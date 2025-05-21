"""Pydantic models for the email analyzer agent."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.hermes.model.enums import ProductCategory

class SegmentType(str, Enum):
    """Types of segments in an email analysis."""

    ORDER = "order"
    INQUIRY = "inquiry"
    PERSONAL_STATEMENT = "personal_statement"


class ProductMention(BaseModel):
    """A mention of a product in a customer email."""

    product_id: str | None = None
    product_name: str | None = None
    product_description: str | None = None
    product_category: ProductCategory | None = None
    product_type: str | None = Field(default=None, description="Fundamental product type in the general category")
    quantity: int | None = Field(default=1, ge=1)
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level in this product mention",
    )


class Segment(BaseModel):
    """A segment of a customer email with specific intent."""

    segment_type: SegmentType
    main_sentence: str
    related_sentences: list[str] = Field(default_factory=list)
    product_mentions: list[ProductMention] = Field(default_factory=list)


class EmailAnalysis(BaseModel):
    """Complete analysis of a customer email."""

    email_id: str = Field(default="", description="The unique identifier for the email")
    language: str = Field(default="English", description="The language of the email")

    primary_intent: Literal["order request", "product inquiry"] = Field(
        description="The main purpose of the customer's email"
    )

    customer_pii: dict[str, Any] = Field(
        default_factory=dict,
        description="Personal identifiable information like name, email, phone, etc.",
    )

    segments: list[Segment] = Field(default_factory=list)

    def has_order(self) -> bool:
        """Determine if the email contains an order segment."""
        if not self.segments:
            return False
        return any(seg.segment_type == "order" for seg in self.segments)

    def has_inquiry(self) -> bool:
        """Determine if the email contains an inquiry segment."""
        if not self.segments:
            return False
        return any(seg.segment_type == "inquiry" for seg in self.segments)


class ClassifierInput(BaseModel):
    """Input model for the email analyzer."""

    email_id: str = Field(description="The unique identifier for the email")

    subject: str | None = Field(description="The subject of the email")

    message: str = Field(description="The body of the email")


class ClassifierOutput(BaseModel):
    """Output model for the email analyzer function."""

    email_analysis: EmailAnalysis = Field(description="The initial email analysis result")
