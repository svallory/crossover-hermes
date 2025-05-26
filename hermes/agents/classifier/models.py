"""Pydantic models for the classifier agent."""

from pydantic import BaseModel, Field

from hermes.model.email import CustomerEmail, EmailAnalysis


class ClassifierInput(BaseModel):
    """Input model for the email analyzer.

    Contains a CustomerEmail object with the email data to be analyzed.
    """

    email: CustomerEmail = Field(description="The customer email to be analyzed")


class ClassifierOutput(BaseModel):
    """Output model for the email analyzer function."""

    email_analysis: EmailAnalysis = Field(
        description="The initial email analysis result"
    )
