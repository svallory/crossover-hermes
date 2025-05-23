"""Pydantic models for the order processor agent."""

from typing import Literal
from pydantic import BaseModel, Field

from hermes.agents.classifier.models import ClassifierInput, ClassifierOutput
from hermes.model.order import Order


class FulfillerInput(ClassifierInput):
    """Input data for the order processor function."""

    classifier: ClassifierOutput = Field(description="The output of the email analyzer")


class FulfillerOutput(BaseModel):
    """Output data for the order processor function."""

    order_result: Order = Field(
        description="The complete result of processing the order request"
    )
