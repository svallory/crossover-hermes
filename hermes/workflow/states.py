from typing import (
    Annotated,
)

from pydantic import BaseModel, Field

from hermes.agents.advisor.models import AdvisorOutput
from hermes.agents.classifier.models import ClassifierOutput
from hermes.agents.composer.models import ComposerOutput
from hermes.agents.fulfiller.models import FulfillerOutput
from hermes.agents.stockkeeper.models import StockkeeperOutput
from hermes.model.email import CustomerEmail
from hermes.model.enums import Agents  # This should be fine
from hermes.model.errors import Error


def merge_errors(dict1, dict2):
    """Merge two error dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


class WorkflowInput(BaseModel):
    """Input of the workflow."""

    email: CustomerEmail


class WorkflowOutput(BaseModel):
    """Output of the workflow."""

    email: CustomerEmail
    classifier: ClassifierOutput
    stockkeeper: StockkeeperOutput
    fulfiller: FulfillerOutput | None = None
    advisor: AdvisorOutput | None = None
    composer: ComposerOutput

    errors: None | Annotated[dict[Agents, Error], merge_errors] = Field(
        default_factory=dict
    )


class OverallState(BaseModel):
    """Overall state that can contain any combination of analysis, processing, and response."""

    email: CustomerEmail

    # Use properly quoted string literals for forward references
    classifier: ClassifierOutput | None = None
    stockkeeper: StockkeeperOutput | None = None
    fulfiller: FulfillerOutput | None = None
    advisor: AdvisorOutput | None = None
    composer: ComposerOutput | None = None
    errors: Annotated[dict[Agents, Error], merge_errors] = Field(default_factory=dict)


# Update forward references for Pydantic model
OverallState.model_rebuild()
