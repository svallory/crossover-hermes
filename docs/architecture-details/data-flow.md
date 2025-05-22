# Hermes Data Flow

This document provides a detailed view of the data flow through the Hermes system, focusing on the input and output formats of each agent.

## System Input

The initial input to the Hermes system is a `ClassifierInput` object containing:
- `email_id`: Unique identifier for the email
- `subject`: Email subject line
- `message`: Email body content

## Classifier (Email Analyzer)

**Input**: `ClassifierInput`
```python
class ClassifierInput(BaseModel):
    email_id: str
    subject: str
    message: str
```

**Output**: `ClassifierOutput`
```python
class ClassifierOutput(BaseModel):
    email_analysis: EmailAnalysis
```

**EmailAnalysis Details**:
```python
class EmailAnalysis(BaseModel):
    email_id: str
    language: str
    primary_intent: str  # "inquiry", "order", etc.
    customer_pii: dict[str, str] = Field(default_factory=dict)
    segments: list[Segment] = Field(default_factory=list)
    
    def has_order(self) -> bool: ...
    def has_inquiry(self) -> bool: ...
```

**Segment Details**:
```python
class SegmentType(str, Enum):
    ORDER = "order"
    INQUIRY = "inquiry"
    PERSONAL = "personal_statement"
    OTHER = "other"

class Segment(BaseModel):
    segment_type: SegmentType
    content: str
    product_mentions: list[ProductMention] = Field(default_factory=list)
```

**ProductMention Details**:
```python
class ProductMention(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    product_description: Optional[str] = None
    confidence: float = 0.0
    quantity: Optional[int] = None
```

## Stockkeeper (Product Resolver)

**Input**: `StockkeeperInput`
```python
class StockkeeperInput(BaseModel):
    classifier: ClassifierOutput
```

**Output**: `StockkeeperOutput`
```python
class StockkeeperOutput(BaseModel):
    resolved_products: list[Product] = Field(default_factory=list)
    unresolved_mentions: list[ProductMention] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    @property
    def resolution_rate(self) -> float: ...
```

**Product Details**:
```python
class Product(BaseModel):
    product_id: str
    name: str
    description: str
    category: ProductCategory
    product_type: str
    seasons: list[Season] = Field(default_factory=list)
    base_price: float
    stock: int = 0
    promotion: Optional[str] = None
    promotion_description: Optional[str] = None
```

## Advisor (Inquiry Responder)

**Input**: `AdvisorInput`
```python
class AdvisorInput(BaseModel):
    classifier_output: ClassifierOutput
    stockkeeper_output: Optional[StockkeeperOutput] = None
```

**Output**: `AdvisorOutput`
```python
class AdvisorOutput(BaseModel):
    inquiry_answers: InquiryAnswers
```

**InquiryAnswers Details**:
```python
class InquiryAnswers(BaseModel):
    answered_questions: list[QuestionAnswer] = Field(default_factory=list)
    unanswered_questions: list[ExtractedQuestion] = Field(default_factory=list)
    primary_products: list[str] = Field(default_factory=list)
    related_products: list[str] = Field(default_factory=list)
    unsuccessful_references: list[str] = Field(default_factory=list)
```

**QuestionAnswer Details**:
```python
class ExtractedQuestion(BaseModel):
    question_text: str
    referenced_product_ids: list[str] = Field(default_factory=list)

class QuestionAnswer(BaseModel):
    question: ExtractedQuestion
    answer: str
```

## Fulfiller (Order Processor)

**Input**: `FulfillerInput`
```python
class FulfillerInput(ClassifierInput):
    classifier: ClassifierOutput
```

**Output**: `FulfillerOutput`
```python
class FulfillerOutput(BaseModel):
    order_result: Order
```

**Order Details**:
```python
class OrderLineStatus(str, Enum):
    CREATED = "created"
    OUT_OF_STOCK = "out_of_stock"

class OrderLine(BaseModel):
    product_id: str
    description: str
    quantity: int = 1
    base_price: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0
    status: OrderLineStatus = OrderLineStatus.CREATED
    stock: int = 0
    alternatives: list[AlternativeProduct] = Field(default_factory=list)
    promotion_applied: bool = False
    promotion_description: Optional[str] = None
    promotion: Optional[PromotionSpec] = None

class Order(BaseModel):
    email_id: str
    overall_status: str = "created"  # created, out_of_stock, partially_fulfilled
    lines: list[OrderLine] = Field(default_factory=list)
    total_price: float = 0.0
    total_discount: float = 0.0
    stock_updated: bool = False
```

## Composer (Response Generator)

**Input**: `ComposerInput`
```python
class ComposerInput(ClassifierInput):
    classifier: Optional[ClassifierOutput] = None
    advisor: Optional[AdvisorOutput] = None
    fulfiller: Optional[FulfillerOutput] = None
```

**Output**: `ComposerOutput`
```python
class ComposerOutput(BaseModel):
    composed_response: ComposedResponse
```

**ComposedResponse Details**:
```python
class ResponseTone(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    APOLOGETIC = "apologetic"
    ENTHUSIASTIC = "enthusiastic"

class ResponsePoint(BaseModel):
    type: str  # greeting, inquiry_answer, order_confirmation, etc.
    content: str
    priority: int
    product_id: Optional[str] = None

class ComposedResponse(BaseModel):
    email_id: str
    subject: str
    response_body: str
    language: str
    tone: ResponseTone
    response_points: list[ResponsePoint] = Field(default_factory=list)
```

## Workflow State

Throughout the workflow, the system maintains an `OverallState` object:

```python
class OverallState(BaseModel):
    email_id: str
    subject: str
    message: str
    classifier: Optional[ClassifierOutput] = None
    stockkeeper: Optional[StockkeeperOutput] = None
    fulfiller: Optional[FulfillerOutput] = None
    advisor: Optional[AdvisorOutput] = None
    composer: Optional[ComposerOutput] = None
    errors: dict[str, Error] = Field(default_factory=dict)
```

This state object is updated as each agent completes its processing and is ultimately returned by the `run_workflow` function with all intermediate and final results. 