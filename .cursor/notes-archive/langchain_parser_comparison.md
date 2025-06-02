# LangChain Parser vs Current Approach - Code Comparison

## Target: Classifier Agent (Most Complex Case)

The classifier agent is our most complex case since it outputs the `EmailAnalysis` model that has the `customer_pii` field causing issues.

## Current Approach Code

### Current Validation Code Required
```python
# hermes/utils/validation.py (185 lines)
# + Local copies in 3 model files (30+ lines each)
# + Field validators in models (5-10 lines each)
```

**Total: ~250+ lines of validation code**

### Current Agent Code (No Changes Needed)
```python
# hermes/agents/classifier/agent.py - UNCHANGED
async def run_classifier(state: ClassifierInput, runnable_config: RunnableConfig) -> dict:
    # ... existing logic works fine
    response = await llm.ainvoke(prompt_value)

    # Pydantic automatically uses field validators
    email_analysis = EmailAnalysis.model_validate_json(response.content)

    return create_node_response(Agents.CLASSIFIER, classifier_output)
```

---

## LangChain PydanticOutputParser Approach

### NEW: Parser-Based Agent Code
```python
# hermes/agents/classifier/agent.py - MAJOR CHANGES
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import OutputParserException

async def run_classifier(state: ClassifierInput, runnable_config: RunnableConfig) -> dict:
    config = HermesConfig.from_runnable_config(runnable_config)
    llm = get_llm(config, "strong")

    # NEW: Create parser
    parser = PydanticOutputParser(pydantic_object=EmailAnalysis)

    # NEW: Modify prompt to include format instructions
    format_instructions = parser.get_format_instructions()

    # UPDATE: Prompt template needs modification
    updated_prompt = f"""
    {CLASSIFIER_PROMPT}

    {format_instructions}
    """

    try:
        # NEW: Use parser instead of manual JSON parsing
        response = await llm.ainvoke(updated_prompt)
        email_analysis = parser.parse(response.content)

        classifier_output = ClassifierOutput(email_analysis=email_analysis)
        return create_node_response(Agents.CLASSIFIER, classifier_output)

    except OutputParserException as e:
        # NEW: Handle parser-specific errors
        return create_node_response(
            Agents.CLASSIFIER,
            Exception(f"Failed to parse classifier output: {e}")
        )
```

### NEW: Updated Prompt Template
```python
# hermes/agents/classifier/prompts.py - REQUIRES UPDATES
# Remove current JSON examples, let parser handle format instructions

CLASSIFIER_PROMPT = """
Analyze the customer email and extract structured information.

Email: {email_message}

IMPORTANT: Focus on accuracy over completeness. Use null/empty values if information is not present.
"""

# The parser automatically adds JSON schema instructions
```

### Model Changes (SIMPLIFIED)
```python
# hermes/model/email.py - REMOVE VALIDATORS
class EmailAnalysis(BaseModel):
    """Complete analysis of a customer email."""

    customer_pii: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Personal identifiable information like name, email, phone, etc.",
    )

    # REMOVE: All @field_validator decorators
    # REMOVE: parse_customer_pii method
    # REMOVE: All validation imports
```

---

## Code Change Summary

### Current Approach (What We Have)
- ✅ **Models**: 4-5 field validators across multiple models
- ✅ **Utils**: 185 lines of validation utilities
- ✅ **Agents**: No changes needed
- ✅ **Prompts**: No changes needed
- ✅ **Graph**: No changes needed

**Total Impact**: Isolated to models + utils

### LangChain Parser Approach
- 🔄 **Models**: Remove all field validators (SIMPLER)
- ❌ **Utils**: Remove validation utilities entirely
- 🔄 **Agents**: Rewrite all agent functions to use parsers
- 🔄 **Prompts**: Update all prompts to work with parser format instructions
- 🔄 **Graph**: Potentially update error handling

**Total Impact**: Changes to every layer of the system

---

## Specific Graph Changes Needed

### Current Graph (No Changes)
```python
# hermes/workflow/graph.py - UNCHANGED
async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    classifier_input = ClassifierInput(email=email)
    result = await run_classifier(state=classifier_input, runnable_config=config)
    return result
```

### LangChain Graph (Error Handling Updates)
```python
# hermes/workflow/graph.py - MINOR UPDATES
from langchain.schema import OutputParserException

async def analyze_email_node(state: OverallState, config: RunnableConfig) -> dict:
    try:
        classifier_input = ClassifierInput(email=email)
        result = await run_classifier(state=classifier_input, runnable_config=config)
        return result
    except OutputParserException as e:
        # NEW: Handle LangChain parser errors specifically
        from hermes.model.enums import Agents
        from hermes.utils.response import create_node_response
        return create_node_response(Agents.CLASSIFIER, e)
```

---

## Lines of Code Comparison

### Current Approach
- **New Code**: ~50 lines (centralized utils)
- **Modified Files**: 4 model files
- **Risk**: Low (isolated changes)

### LangChain Approach
- **Modified Code**: ~200-300 lines across multiple files
- **Modified Files**: All agents + prompts + models + graph
- **Risk**: High (system-wide changes)

---

## Verdict

**Current approach wins on simplicity**:
- ✅ Surgical fix for exact problem
- ✅ Minimal code changes
- ✅ No architectural disruption
- ✅ Easy to test and verify

**LangChain approach benefits**:
- ✅ Cleaner models (no validators)
- ✅ Standard LangChain patterns
- ❌ Requires system-wide changes
- ❌ Risk of breaking existing functionality

**Recommendation**: Stick with current approach for immediate fix, consider LangChain for future green-field development.