"""
Pydantic models for the response composer agent.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from src.hermes.agents.classifier.models import ClassifierInput, ClassifierOutput
from src.hermes.agents.advisor.models import AdvisorOutput
from src.hermes.agents.fulfiller.models.agent import (
    FulfillerOutput,
)


class ResponseTone(str, Enum):
    """Tone options for customer responses."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    APOLOGETIC = "apologetic"
    ENTHUSIASTIC = "enthusiastic"


class ResponsePoint(BaseModel):
    """A structured point to include in the response."""

    content_type: str = Field(
        description="Type of content (greeting, product_info, answer, alternative, closing, etc.)"
    )
    content: str = Field(description="The actual content to include")
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority of this point (1-10, 10 being highest)",
    )
    related_to: Optional[str] = Field(default=None, description="Product ID or question this point relates to, if any")


class ComposerInput(ClassifierInput):
    """
    Input model for the response composer function.

    Contains outputs from previous agents in the pipeline.
    """

    classifier: ClassifierOutput = Field(description="Complete EmailAnalysisResult from the analyzer")
    advisor: Optional[AdvisorOutput] = Field(
        default=None, description="Results from the Inquiry Responder, if applicable"
    )
    fulfiller: Optional[FulfillerOutput] = Field(
        default=None, description="Results from the Order Processor, if applicable"
    )


class ComposedResponse(BaseModel):
    """
    The final composed response to be sent to the customer.
    """

    email_id: str = Field(description="The ID of the email being responded to")
    subject: str = Field(description="Subject line for the response email")
    response_body: str = Field(description="Full text of the response")
    language: str = Field(description="Language code of the response (should match customer's language)")
    tone: ResponseTone = Field(description="Detected tone used in the response")
    response_points: List[ResponsePoint] = Field(
        default_factory=list, description="Structured breakdown of response elements"
    )


class ComposerOutput(BaseModel):
    """
    Output model for the response composer function.
    """

    composed_response: ComposedResponse = Field(description="The final composed response to send to the customer")
