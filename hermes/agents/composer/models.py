"""Pydantic models for the response composer agent."""

from pydantic import BaseModel, Field

from hermes.agents.advisor.models import AdvisorOutput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.fulfiller.models import FulfillerOutput
from ...model.email import CustomerEmail


class ResponsePoint(BaseModel):
    """A structured point to include in the response.

    This is used internally by the LLM for step-by-step thinking and response planning.
    It helps the LLM organize its thoughts but is not used elsewhere in the system.
    """

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
    related_to: str | None = Field(
        default=None, description="Product ID or question this point relates to, if any"
    )


class ComposerInput(BaseModel):
    """Input model for the response composer function.

    Contains outputs from previous agents in the pipeline.
    """

    email: CustomerEmail = Field(description="The customer email being processed")

    classifier: ClassifierOutput = Field(
        description="Complete EmailAnalysisResult from the analyzer"
    )

    advisor: AdvisorOutput | None = Field(
        default=None, description="Results from the Advisor agent, if applicable"
    )

    fulfiller: FulfillerOutput | None = Field(
        default=None, description="Results from the Fulfiller agent, if applicable"
    )


class ComposerOutput(BaseModel):
    """Output model for the response composer function.

    Contains the final composed response to be sent to the customer.
    """

    email_id: str = Field(description="The ID of the email being responded to")
    subject: str = Field(description="Subject line for the response email")
    response_body: str = Field(description="Full text of the response")
    tone: str = Field(
        description="The tone used in the response (e.g., professional, friendly, enthusiastic)"
    )
    response_points: list[ResponsePoint] = Field(
        default_factory=list,
        description="Structured breakdown of response elements (used internally for LLM reasoning)",
    )
