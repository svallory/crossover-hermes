# Hermes Master Evaluator Implementation Plan

## Current Analysis

After examining the Hermes codebase, I've confirmed:

1. **Workflow State Management**
   - `workflow.py` properly stores all agent outputs in the workflow state
   - Each task function updates the state with its component's output
   - Final state contains all intermediate results needed for evaluation

2. **Current Evaluation System**
   - Separate evaluators for each component (email_analyzer, order_processor, etc.)
   - Each evaluator requires 3-4 API calls to evaluate one email processing flow
   - Results are successfully uploaded to LangSmith

## Master Evaluator Concept

The goal is to create a single "master evaluator" that:
- Evaluates all agent outputs in a single pass (1 API call instead of 5)
- Maintains the quality of individual evaluations
- Formats results in a way compatible with existing reporting

## Implementation Steps

### 1. Create Master Evaluator Prompt

Create a comprehensive prompt with multiple evaluation tasks:

```markdown
# Master Evaluator Prompt

You are evaluating the performance of a comprehensive email processing system for a high-end fashion retailer called "Luxe Fashions". You will evaluate all components of the system in a single pass.

## System Components to Evaluate:
1. Email Analyzer - Classifies and extracts information from customer emails
2. Order Processor - Handles order-related segments (if applicable)
3. Inquiry Responder - Addresses customer questions (if applicable)
4. Response Composer - Creates the final email response
5. End-to-End Performance - Overall system effectiveness

## Original Customer Email:
Subject: {email_subject}
Message: {email_message}

## Component 1: Email Analyzer Output
```json
{email_analysis}
```

## Component 2: Order Processor Output
Order processing applicable: {has_order_processing}
```json
{order_result}
```

## Component 3: Inquiry Responder Output
Inquiry response applicable: {has_inquiry_response}
```json
{inquiry_response}
```

## Component 4: Response Composer Output (Final Response)
Subject: {response_subject}
Body: {response_body}

## Evaluation Tasks

### Task 1: Evaluate Email Analyzer
[Task details...]

### Task 2: Evaluate Order Processor (if applicable)
[Task details...]

### Task 3: Evaluate Inquiry Responder (if applicable)
[Task details...]

### Task 4: Evaluate Response Composer
[Task details...]

### Task 5: Evaluate End-to-End Performance
[Task details...]
```

### 2. Create Master Evaluator Function

```python
async def evaluate_master(
    client, 
    experiment_name: str, 
    email_id: str,
    workflow_state: Dict[str, Any],
    model
) -> Dict[str, Any]:
    """
    Comprehensive evaluator that evaluates all agent outputs in a single pass.
    """
    # Extract all relevant data from workflow state
    email_subject = workflow_state.get("email_subject", "")
    email_message = workflow_state.get("email_message", "")
    email_analyzer_output = workflow_state.get("email_analysis", {})
    order_processor_output = workflow_state.get("order_result", {})
    inquiry_responder_output = workflow_state.get("inquiry_response", {})
    response_composer_output = workflow_state.get("final_response", {})
    
    # Determine which components were executed
    has_order_processing = order_processor_output is not None
    has_inquiry_response = inquiry_responder_output is not None
    
    # Create evaluator with all criteria
    criteria = {
        # Email Analyzer criteria
        "email_analyzer_intent": "...",
        # Order Processor criteria
        "order_processor_identification": "...",
        # Inquiry Responder criteria
        "inquiry_responder_questions": "...",
        # Response Composer criteria 
        "response_composer_tone": "...",
        # End-to-End criteria
        "end_to_end_understanding": "..."
    }
    
    # Run evaluation, only one LLM call
    eval_result = run_evaluator(...)
    
    # Format results to match existing structure
    organized_results = {
        "email_analyzer": {...},
        "order_processor": {...},
        "inquiry_responder": {...},
        "response_composer": {...},
        "end_to_end": {...}
    }
    
    return organized_results
```

### 3. Modify run_evaluation Function

Update `run_evaluation` in `tools/evaluate/main.py` to use the master evaluator:

```python
async def run_evaluation(
    results: List[Dict[str, Any]],
    experiment_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    auto_upload: bool = True,
    dataset_name: Optional[str] = None,
    use_master_evaluator: bool = True  # New parameter
) -> Dict[str, Any]:
    # [...]
    
    # Process each result
    for result in results:
        email_id = result.get("input", {}).get("email_id", "unknown")
        
        # Extract workflow state
        workflow_state = {
            "email_id": email_id,
            "email_subject": email_input.get("email_subject", ""),
            "email_message": email_input.get("email_message", ""),
            "email_analysis": outputs.get("email-analyzer", {}),
            "order_result": outputs.get("order-processor", {}),
            "inquiry_response": outputs.get("inquiry-responder", {}),
            "final_response": outputs.get("response-composer", {})
        }
        
        if use_master_evaluator:
            # Use the master evaluator
            eval_results = await evaluate_master(
                client, 
                experiment_name, 
                email_id, 
                workflow_state,
                model
            )
            
            # Store results in the appropriate structure
            if eval_results.get("email_analyzer"):
                all_scores["email_analyzer"].append(eval_results["email_analyzer"])
            if eval_results.get("order_processor"):
                all_scores["order_processor"].append(eval_results["order_processor"])
            if eval_results.get("inquiry_responder"):
                all_scores["inquiry_responder"].append(eval_results["inquiry_responder"])
            if eval_results.get("response_composer"):
                all_scores["response_composer"].append(eval_results["response_composer"])
            if eval_results.get("end_to_end"):
                all_scores["end_to_end"].append(eval_results["end_to_end"])
        else:
            # Use individual evaluators (original approach)
            # [original evaluation code...]
        
    # [rest of the function...]
```

### 4. Add New Prompt File

Create a new file `tools/evaluate/prompts/master_evaluator.md` with the master evaluator prompt.

### 5. Testing

Test the master evaluator against individual evaluators:
- Compare scores for consistency
- Measure token usage and API call reduction
- Verify performance improvement

## Benefits

1. **Efficiency**
   - Reduces API calls by ~80% (1 call vs 5 calls per email)
   - Decreases token usage by eliminating redundant context

2. **Quality**
   - Provides evaluator with comprehensive view of entire workflow
   - Enables assessment of cross-component interactions

3. **Flexibility**
   - Conditional evaluation based on what agents were executed
   - Maintains backward compatibility with existing reporting

## Implementation Timeline

1. **Phase 1 (1-2 days)**
   - Create master evaluator prompt
   - Implement evaluate_master function
   - Add unit tests

2. **Phase 2 (1 day)**
   - Modify run_evaluation to use master evaluator
   - Test with sample workflow results
   - Document changes

3. **Phase 3 (1-2 days)**
   - Compare results with original evaluators
   - Optimize prompt and function
   - Update documentation

## Risks and Mitigations

1. **Context Window Limits**
   - Risk: Combined prompt may exceed context limits
   - Mitigation: Optimize JSON formatting, use truncation if needed

2. **Evaluation Quality**
   - Risk: Combined evaluation may not be as thorough
   - Mitigation: Explicitly structure prompt as multiple tasks

3. **Backward Compatibility**
   - Risk: New format may break existing reporting
   - Mitigation: Transform results to match original structure 