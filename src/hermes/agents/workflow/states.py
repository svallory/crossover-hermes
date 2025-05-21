from typing import (
    Dict,
    Optional,
    Annotated,
)
from src.hermes.model.error import Error
from pydantic import Field, BaseModel

from src.hermes.agents.classifier.models import ClassifierOutput
from src.hermes.agents.stockkeeper.models import ResolvedProductsOutput
from src.hermes.agents.advisor.models import AdvisorOutput
from src.hermes.agents.fulfiller.models.agent import FulfillerOutput
from src.hermes.agents.composer.models import ComposerOutput
from src.hermes.model import Agents  # This should be fine


def merge_errors(dict1, dict2):
    """Merge two error dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


class OverallState(BaseModel):
    """Overall state that can contain any combination of analysis, processing, and response"""

    email_id: str
    subject: Optional[str] = None
    message: str

    # Use properly quoted string literals for forward references
    classifier: Optional[ClassifierOutput] = None
    stockkeeper: Optional[ResolvedProductsOutput] = None
    fulfiller: Optional[FulfillerOutput] = None
    advisor: Optional[AdvisorOutput] = None
    composer: Optional[ComposerOutput] = None
    errors: Annotated[Dict[Agents, Error], merge_errors] = Field(default_factory=dict)


# Update forward references for Pydantic model
OverallState.model_rebuild()
