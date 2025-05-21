from typing import (
    Dict,
    Optional,
    Annotated,
    List,
    Any,
    Union,
)
from src.hermes.model.error import Error
from pydantic import Field, BaseModel, create_model
from typing_extensions import Hashable

from src.hermes.agents.classifier.models import EmailAnalyzerOutput
from src.hermes.agents.product_resolver.models import ResolvedProductsOutput
from src.hermes.agents.advisor.models import InquiryResponderOutput
from hermes.agents.fulfiller.models.agent import OrderProcessorOutput
from src.hermes.agents.response_composer.models import ResponseComposerOutput
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
    email_analyzer: Optional[EmailAnalyzerOutput] = None
    product_resolver: Optional[ResolvedProductsOutput] = None
    order_processor: Optional[OrderProcessorOutput] = None
    inquiry_responder: Optional[InquiryResponderOutput] = None
    response_composer: Optional[ResponseComposerOutput] = None
    errors: Annotated[Dict[Agents, Error], merge_errors] = Field(default_factory=dict)

# Update forward references for Pydantic model
OverallState.model_rebuild()