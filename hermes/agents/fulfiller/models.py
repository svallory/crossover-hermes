"""Pydantic models for the order processor agent."""

from pydantic import BaseModel, Field

from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from ...model.email import CustomerEmail
from hermes.model.order import Order


class FulfillerInput(BaseModel):
    """Input data for the order processor function."""

    email: CustomerEmail = Field(description="The customer email being processed")
    classifier: ClassifierOutput = Field(description="The output of the email analyzer")
    stockkeeper: StockkeeperOutput = Field(
        description="The output of the stockkeeper agent"
    )


class FulfillerOutput(BaseModel):
    """Output data for the order processor function."""

    order_result: Order = Field(
        description="The complete result of processing the order request"
    )
