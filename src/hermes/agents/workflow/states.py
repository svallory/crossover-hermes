from typing import (
    Annotated,
)

from pydantic import BaseModel, Field

from src.hermes.agents.advisor.models import AdvisorOutput
from src.hermes.agents.classifier.models import ClassifierOutput
from src.hermes.agents.composer.models import ComposerOutput
from src.hermes.agents.fulfiller.models.agent import FulfillerOutput
from src.hermes.agents.stockkeeper.models import ResolvedProductsOutput
from src.hermes.model import Agents  # This should be fine
from src.hermes.model.error import Error

def merge_errors(dict1, dict2):
    """Merge two error dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


class OverallState(BaseModel):
    """Overall state that can contain any combination of analysis, processing, and response."""

    email_id: str
    subject: str | None = None
    message: str

    # Use properly quoted string literals for forward references
    classifier: ClassifierOutput | None = None
    stockkeeper: ResolvedProductsOutput | None = None
    fulfiller: FulfillerOutput | None = None
    advisor: AdvisorOutput | None = None
    composer: ComposerOutput | None = None
    errors: Annotated[dict[Agents, Error], merge_errors] = Field(default_factory=dict)


# Update forward references for Pydantic model
OverallState.model_rebuild()
