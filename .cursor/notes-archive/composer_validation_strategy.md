# Composer Integration Test Validation Strategy

## Overview

The composer integration tests use a **hybrid validation approach** that combines multiple validation methods to comprehensively assess both concrete facts and subjective quality aspects of generated responses.

## Validation Layers

### 1. **Concrete Facts Validation** (String Matching)
Used for verifying factual accuracy and specific details:

```python
# Product IDs and names
assert "lth0976" in response_lower or "leather bifold wallet" in response_lower

# Pricing information
assert "$84" in composer_output.response_body or "84.00" in composer_output.response_body

# Quantities
assert "4" in composer_output.response_body or "four" in response_lower

# Customer names
assert "david" in response_lower
```

**Pros**: Fast, deterministic, catches concrete errors
**Cons**: Brittle to rephrasing, misses semantic equivalence

### 2. **Structural Validation** (Type & Format Checking)
Ensures response structure and basic quality:

```python
# Type checking
assert isinstance(composer_output.response_body, str)
assert isinstance(composer_output.tone, str)

# Minimum quality thresholds
assert len(composer_output.response_body) > 100  # Substantial response
assert composer_output.language in ["English", "Spanish", "French", "German"]

# Required elements
assert "hermes" in response_lower  # Brand signature
```

**Pros**: Catches structural issues, ensures data integrity
**Cons**: Doesn't assess content quality or appropriateness

### 3. **Categorical Validation** (Predefined Lists)
Validates responses against expected categories:

```python
# Tone appropriateness
assert composer_output.tone in [
    "professional", "professional and warm", "friendly and professional"
]

# Content inclusion checks
assert ("compartment" in response_lower or
        "pocket" in response_lower or
        "organization" in response_lower)
```

**Pros**: Good for known classification tasks
**Cons**: Limited flexibility, may miss valid alternatives

### 4. **LLM-as-a-Judge Validation** (Advanced Quality Assessment)
Uses a separate LLM to evaluate response quality across multiple criteria:

```python
# Custom validation for specific test scenarios
llm_validation = await self.validate_composer_response_with_llm(
    email, composer_output,
    validation_criteria={
        "order_confirmation": "Does the response clearly confirm order details?",
        "business_tone": "Is the tone appropriately professional for a business customer?",
        "personalization": "Does the response feel personalized rather than templated?",
    }
)
```

**Validation Criteria Categories**:
- **Personalization**: Name usage, customer-specific context
- **Tone Consistency**: Matching customer communication style
- **Completeness**: Addressing all customer concerns
- **Professionalism**: Brand-appropriate language and structure
- **Accuracy**: Factual correctness of product/order details
- **Clarity**: Clear, well-structured communication
- **Brand Voice**: Signature inclusion, company voice

## Validation Strengths by Approach

### String Matching - Best For:
- Product IDs and codes
- Specific pricing information
- Quantities and measurements
- Customer names
- Required signatures/brand elements

### Type/Structure Checking - Best For:
- Data format validation
- Minimum quality thresholds
- Language detection
- Response completeness

### Categorical Validation - Best For:
- Tone classification
- Intent validation
- Binary yes/no assessments
- Known enumeration checks

### LLM-as-a-Judge - Best For:
- Subjective quality assessment
- Contextual appropriateness
- Tone adaptation evaluation
- Personalization assessment
- Overall coherence and helpfulness
- Complex multi-criteria evaluation

## Implementation Pattern

```python
@pytest.mark.asyncio
async def test_composer_scenario(self, mock_runnable_config):
    # 1. Set up test scenario
    email = self.create_customer_email(...)
    composer_input = ComposerInput(...)

    # 2. Run composer agent
    result = await run_composer(composer_input, mock_runnable_config)
    composer_output = result[Agents.COMPOSER]

    # 3. Structural validation (required)
    assert isinstance(composer_output, ComposerOutput)
    assert composer_output.email_id == "expected_id"

    # 4. Concrete facts validation (scenario-specific)
    response_lower = composer_output.response_body.lower()
    assert "expected_product" in response_lower
    assert "expected_price" in composer_output.response_body

    # 5. Categorical validation (scenario-specific)
    assert composer_output.tone in ["expected", "tone", "categories"]

    # 6. LLM validation (optional, for quality assessment)
    llm_validation = await self.validate_composer_response_with_llm(
        email, composer_output, scenario_specific_criteria
    )

    # Use for debugging or quality monitoring
    if llm_validation["overall_score"] < 0.7:
        print(f"⚠️  Quality warning: {llm_validation['overall_reasoning']}")
```

## Test Scenarios Coverage

The integration tests cover diverse scenarios to validate composer adaptability:

1. **E001 (Order Confirmation)**: Business customer, bulk order, professional tone
2. **E003 (Product Inquiry)**: Personal customer, comparison questions, helpful tone
3. **E016 (Mixed Intent)**: Multiple topics, wedding context, warm tone
4. **E022 (Unclear Reference)**: Vague product description, enthusiastic customer
5. **E009 (Spanish Language)**: Non-English communication, respectful tone
6. **E012 (Rambling Customer)**: Unfocused input, staying on topic
7. **Structure Validation**: Complete response validation, all fields

## Quality Thresholds

### Acceptable Response Criteria:
- **Length**: Minimum 50-100 characters for substantial responses
- **Structure**: All required fields present and properly typed
- **Brand Elements**: Hermes signature included
- **Language**: Correct language detection and response
- **Tone**: Appropriate for customer and scenario

### LLM Validation Scoring:
- **0.9-1.0**: Excellent response, exceeds expectations
- **0.7-0.8**: Good response, meets requirements with minor issues
- **0.5-0.6**: Adequate response, basic requirements met
- **Below 0.5**: Poor response, requires investigation

## Benefits of Hybrid Approach

1. **Comprehensive Coverage**: Catches both objective errors and subjective quality issues
2. **Fast Feedback**: String matching provides immediate error detection
3. **Quality Assurance**: LLM evaluation catches nuanced quality problems
4. **Debugging Support**: Multiple validation layers help isolate issues
5. **Maintainability**: Concrete validations remain stable, LLM validation adapts
6. **Cost Efficiency**: Use expensive LLM validation selectively for complex scenarios

## Best Practices

1. **Layer Appropriately**: Use string matching for facts, LLM for quality
2. **Threshold Setting**: Set appropriate acceptance thresholds for different scenarios
3. **Error Reporting**: Provide clear feedback for different validation failures
4. **Selective LLM Use**: Use LLM validation for complex scenarios, not all tests
5. **Criteria Customization**: Tailor LLM validation criteria to specific test scenarios
6. **Quality Monitoring**: Use LLM scores for quality trends and improvements

This hybrid approach ensures both the correctness and quality of composer responses while maintaining test efficiency and reliability.