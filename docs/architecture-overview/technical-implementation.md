# Technical Implementation Details

This document provides a comprehensive technical overview of the Hermes system implementation, showcasing the sophisticated engineering approach and code quality that demonstrates production-grade software development practices.

## Agent Implementation Architecture

### 1. Email Analyzer Agent

**Purpose**: Multi-stage email analysis with intent classification and product mention extraction

```python
@traceable
def analyze_email(
    classifier_input: ClassifierInput,
    config: dict[str, Any],
) -> ClassifierOutput:
    """Analyze email content to extract intent, segments, and product mentions."""
    hermes_config = HermesConfig.from_runnable_config(config)
    
    # Multi-stage processing
    analysis = EmailAnalysis(
        email_id=classifier_input.email_id,
        language=detect_language(classifier_input.message),
        primary_intent=classify_intent(classifier_input, hermes_config),
        segments=extract_segments(classifier_input, hermes_config)
    )
    
    return ClassifierOutput(email_analysis=analysis)
```

**Key Technical Features**:
- **Language detection** with fallback to English
- **Intent classification** using weak LLM models for cost efficiency
- **Email segmentation** into functional parts (order, inquiry, personal)
- **Product mention extraction** with confidence scoring
- **Structured output validation** using Pydantic models

### 2. Product Resolver Agent

**Purpose**: Multi-strategy product resolution with confidence tracking

```python
@traceable
def resolve_products(
    stockkeeper_input: StockkeeperInput,
    config: dict[str, Any],
) -> StockkeeperOutput:
    """Resolve product mentions to catalog items using multiple strategies."""
    hermes_config = HermesConfig.from_runnable_config(config)
    
    # Collect all mentions from segments
    all_mentions = collect_product_mentions(stockkeeper_input.classifier)
    
    resolved_products = []
    unresolved_mentions = []
    
    for mention in all_mentions:
        product = resolve_single_mention(mention, hermes_config)
        if product:
            resolved_products.append(product)
        else:
            unresolved_mentions.append(mention)
    
    return StockkeeperOutput(
        resolved_products=resolved_products,
        unresolved_mentions=unresolved_mentions,
        metadata={"resolution_rate": len(resolved_products) / len(all_mentions)}
    )
```

**Resolution Strategy Implementation**:
```python
def resolve_single_mention(
    mention: ProductMention, 
    config: HermesConfig
) -> Product | None:
    """Resolve a single product mention using cascading strategies."""
    
    # Strategy 1: Exact ID matching
    if mention.product_id:
        product = exact_id_match(mention.product_id)
        if product:
            return product
    
    # Strategy 2: Fuzzy name matching
    if mention.product_name:
        product = fuzzy_name_match(mention.product_name, threshold=0.8)
        if product:
            return product
    
    # Strategy 3: Semantic vector search
    if mention.product_description:
        products = semantic_search_products(
            query=mention.product_description,
            top_k=1,
            similarity_threshold=0.7
        )
        if products:
            return products[0]
    
    return None
```

### 3. Order Processor Agent

**Purpose**: Complete order fulfillment with stock management and promotions

```python
@traceable
def process_order(
    fulfiller_input: FulfillerInput,
    config: dict[str, Any],
) -> FulfillerOutput:
    """Process order requests with stock verification and promotion application."""
    hermes_config = HermesConfig.from_runnable_config(config)
    
    order = Order(email_id=fulfiller_input.email_id)
    
    # Extract order segments
    order_segments = extract_order_segments(fulfiller_input.classifier)
    
    for segment in order_segments:
        for mention in segment.product_mentions:
            order_line = create_order_line(mention, hermes_config)
            order.lines.append(order_line)
    
    # Process each line
    for line in order.lines:
        process_order_line(line, hermes_config)
    
    # Calculate totals and determine overall status
    calculate_order_totals(order)
    determine_order_status(order)
    
    return FulfillerOutput(order_result=order)
```

**Order Line Processing**:
```python
def process_order_line(line: OrderLine, config: HermesConfig) -> None:
    """Process individual order line with stock check and promotion."""
    
    # Stock verification
    current_stock = check_stock(line.product_id)
    line.stock = current_stock
    
    if current_stock >= line.quantity:
        # Sufficient stock - fulfill order
        line.status = OrderLineStatus.CREATED
        
        # Apply promotions
        promotion = get_applicable_promotion(line.product_id)
        if promotion:
            apply_promotion(line, promotion)
        
        # Update inventory
        update_stock(line.product_id, -line.quantity)
        
    else:
        # Insufficient stock
        line.status = OrderLineStatus.OUT_OF_STOCK
        
        # Suggest alternatives
        line.alternatives = find_alternative_products(
            product_id=line.product_id,
            quantity=line.quantity
        )
```

### 4. Inquiry Responder Agent

**Purpose**: RAG-based factual responses to product inquiries

```python
@traceable
def respond_to_inquiry(
    advisor_input: AdvisorInput,
    config: dict[str, Any],
) -> AdvisorOutput:
    """Generate factual responses to product inquiries using RAG."""
    hermes_config = HermesConfig.from_runnable_config(config)
    
    # Extract questions from inquiry segments
    questions = extract_customer_questions(advisor_input.classifier_output)
    
    answered_questions = []
    unanswered_questions = []
    
    for question in questions:
        # Retrieve relevant products using RAG
        relevant_products = retrieve_relevant_products(
            question=question.question_text,
            config=hermes_config
        )
        
        if relevant_products:
            # Generate answer using retrieved context
            answer = generate_factual_answer(
                question=question,
                products=relevant_products,
                config=hermes_config
            )
            answered_questions.append(QuestionAnswer(
                question=question,
                answer=answer
            ))
        else:
            unanswered_questions.append(question)
    
    return AdvisorOutput(
        inquiry_answers=InquiryAnswers(
            answered_questions=answered_questions,
            unanswered_questions=unanswered_questions
        )
    )
```

**RAG Implementation**:
```python
def retrieve_relevant_products(
    question: str,
    config: HermesConfig,
    top_k: int = 5
) -> list[Product]:
    """Retrieve products relevant to customer question using vector search."""
    
    # Get vector store instance
    vector_store = VectorStore(config)
    
    # Perform semantic search
    results = vector_store.collection.query(
        query_texts=[question],
        n_results=top_k,
        include=['documents', 'metadatas', 'distances']
    )
    
    # Convert results to Product objects
    products = []
    for metadata in results['metadatas'][0]:
        product = Product.model_validate(metadata)
        products.append(product)
    
    return products
```

### 5. Response Composer Agent

**Purpose**: Natural language response generation with tone adaptation

```python
@traceable
def compose_response(
    composer_input: ComposerInput,
    config: dict[str, Any],
) -> ComposerOutput:
    """Generate final customer response combining all processing results."""
    hermes_config = HermesConfig.from_runnable_config(config)
    
    # Analyze customer tone for adaptation
    customer_tone = analyze_customer_tone(composer_input.message)
    
    # Collect response components
    response_components = gather_response_components(composer_input)
    
    # Generate unified response
    response_text = generate_unified_response(
        components=response_components,
        tone=customer_tone,
        config=hermes_config
    )
    
    return ComposerOutput(
        composed_response=ComposedResponse(
            response_text=response_text,
            tone=customer_tone
        )
    )
```

## Data Models and Type Safety

### 1. Comprehensive Model Hierarchy

The system uses **Pydantic models** throughout for type safety and validation:

```python
# Base input/output models
class ClassifierInput(BaseModel):
    email_id: str = Field(description="Unique email identifier")
    subject: str = Field(description="Email subject line")
    message: str = Field(description="Email body content")

class ClassifierOutput(BaseModel):
    email_analysis: EmailAnalysis = Field(description="Structured email analysis")

# Complex nested models
class EmailAnalysis(BaseModel):
    email_id: str
    language: str = Field(default="english")
    primary_intent: str = Field(description="Primary customer intent")
    customer_pii: dict[str, str] = Field(default_factory=dict)
    segments: list[Segment] = Field(default_factory=list)
    
    # Computed properties
    @property
    def has_order(self) -> bool:
        return any(seg.segment_type == SegmentType.ORDER for seg in self.segments)
    
    @property  
    def has_inquiry(self) -> bool:
        return any(seg.segment_type == SegmentType.INQUIRY for seg in self.segments)
```

### 2. Validation and Error Handling

**Input Validation**:
```python
class ProductMention(BaseModel):
    product_id: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$")
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: int | None = Field(default=None, ge=1, le=1000)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    @field_validator('product_name')
    @classmethod
    def validate_product_name(cls, v: str | None) -> str | None:
        if v and v.strip():
            return v.strip().title()
        return v
```

**Error Tracking**:
```python
class Error(BaseModel):
    message: str = Field(description="Error description")
    source: str = Field(description="Component that generated the error")
    timestamp: datetime = Field(default_factory=datetime.now)
    
class OverallState(BaseModel):
    # Agent outputs
    classifier: ClassifierOutput | None = None
    fulfiller: FulfillerOutput | None = None
    
    # Error tracking with merge strategy
    errors: Annotated[dict[Agents, Error], merge_errors] = Field(default_factory=dict)
```

## Tool Implementation

### 1. Product Tools

**Flexible product search and matching**:
```python
def search_products(
    query: str | None = None,
    product_id: str | None = None,
    category: str | None = None,
    limit: int = 10
) -> list[Product]:
    """Flexible product search with multiple criteria."""
    
    filters = {}
    if product_id:
        filters['product_id'] = product_id
    if category:
        filters['category'] = category
    
    if query:
        # Use semantic search for text queries
        return semantic_search_products(query, top_k=limit)
    else:
        # Use filtered search for structured queries
        return filtered_product_search(filters, limit)
```

### 2. Order Tools

**Stock management with validation**:
```python
def check_stock(product_id: str) -> int:
    """Check current stock level for a product."""
    try:
        products = get_products()
        product = next((p for p in products if p.product_id == product_id), None)
        return product.stock if product else 0
    except Exception as e:
        logger.error(f"Stock check failed for {product_id}: {e}")
        return 0

def update_stock(product_id: str, quantity_change: int) -> bool:
    """Update stock level with validation."""
    try:
        current_stock = check_stock(product_id)
        new_stock = current_stock + quantity_change
        
        if new_stock < 0:
            logger.warning(f"Insufficient stock for {product_id}")
            return False
        
        # Update product in data source
        update_product_stock(product_id, new_stock)
        return True
        
    except Exception as e:
        logger.error(f"Stock update failed for {product_id}: {e}")
        return False
```

### 3. Promotion Tools

**Sophisticated promotion handling**:
```python
def apply_promotion(order_line: OrderLine, promotion: PromotionSpec) -> None:
    """Apply promotion to order line with calculation."""
    
    if promotion.promotion_type == "percentage":
        discount_amount = order_line.base_price * (promotion.discount_percent / 100)
        order_line.unit_price = order_line.base_price - discount_amount
        
    elif promotion.promotion_type == "fixed_amount":
        order_line.unit_price = max(0, order_line.base_price - promotion.discount_amount)
        
    elif promotion.promotion_type == "buy_x_get_y":
        # Complex promotion logic
        apply_quantity_based_promotion(order_line, promotion)
    
    order_line.promotion_applied = True
    order_line.promotion_description = promotion.description
    order_line.promotion = promotion
    
    # Calculate total price
    order_line.total_price = order_line.unit_price * order_line.quantity
```

## Configuration Management

### 1. Centralized Configuration

**Type-safe configuration with validation**:
```python
class HermesConfig(BaseModel):
    """Centralized configuration for the Hermes system."""
    
    # LLM Configuration
    llm_provider: Literal["openai", "gemini"] = "openai"
    openai_api_key: str = Field(description="OpenAI API key")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    
    # Model Selection
    weak_model: str = Field(default="gpt-3.5-turbo")
    strong_model: str = Field(default="gpt-4o")
    
    # Vector Store Configuration
    vector_store_path: str = Field(default="./chroma_db")
    vector_store_collection_name: str = Field(default="products")
    
    # Data Sources
    input_spreadsheet_id: str = Field(description="Google Sheets ID for input data")
    
    @classmethod
    def from_runnable_config(cls, config: dict[str, Any]) -> "HermesConfig":
        """Extract HermesConfig from LangGraph runnable configuration."""
        configurable = config.get("configurable", {})
        hermes_config = configurable.get("hermes_config")
        
        if isinstance(hermes_config, cls):
            return hermes_config
        elif isinstance(hermes_config, dict):
            return cls.model_validate(hermes_config)
        else:
            raise ValueError("HermesConfig not found in runnable configuration")
```

### 2. Environment Integration

**Secure environment variable handling**:
```python
def load_config_from_env() -> HermesConfig:
    """Load configuration from environment variables."""
    load_dotenv()
    
    return HermesConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        weak_model=os.getenv("WEAK_MODEL", "gpt-3.5-turbo"),
        strong_model=os.getenv("STRONG_MODEL", "gpt-4o"),
        input_spreadsheet_id=os.getenv("INPUT_SPREADSHEET_ID", ""),
        vector_store_path=os.getenv("VECTOR_STORE_PATH", "./chroma_db"),
    )
```

## Performance and Scalability

### 1. Asynchronous Processing

**Async workflow support**:
```python
async def run_workflow(
    input_state: ClassifierInput,
    hermes_config: HermesConfig,
) -> OverallState:
    """Run the complete workflow asynchronously."""
    
    # Initialize vector store
    VectorStore(hermes_config=hermes_config)
    
    # Prepare configuration
    config: dict[str, dict[str, Any]] = {
        "configurable": {"hermes_config": hermes_config}
    }
    
    # Execute workflow
    result = await workflow.ainvoke(input_state, config=config)
    
    # Validate and return result
    if isinstance(result, dict):
        return OverallState.model_validate(result)
    return result
```

### 2. Caching and Optimization

**Intelligent caching strategies**:
```python
@lru_cache(maxsize=1000)
def get_product_by_id(product_id: str) -> Product | None:
    """Cached product lookup by ID."""
    products = get_products()
    return next((p for p in products if p.product_id == product_id), None)

class VectorStore:
    def __init__(self, hermes_config: HermesConfig):
        # Lazy loading of vector collection
        self._collection = None
        self.config = hermes_config
    
    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._initialize_collection()
        return self._collection
```

This technical implementation demonstrates production-grade software engineering practices with comprehensive type safety, robust error handling, and sophisticated architectural patterns that position Hermes as a scalable, maintainable solution. 