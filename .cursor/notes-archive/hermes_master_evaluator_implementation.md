# Hermes Master Evaluator Implementation

## Master Evaluator Function

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
    
    Args:
        client: LangSmith client
        experiment_name: Name of the experiment
        email_id: ID of the email
        workflow_state: Complete Hermes workflow state containing all outputs
        model: LLM model for evaluation
        
    Returns:
        Comprehensive evaluation results for all components
    """
    try:
        print(f"  Running comprehensive evaluation for email {email_id}...")
        
        # Extract relevant data from workflow state
        email_subject = workflow_state.get("email_subject", "")
        email_message = workflow_state.get("email_message", "")
        email_analyzer_output = workflow_state.get("email_analysis", {})
        order_processor_output = workflow_state.get("order_result", {})
        inquiry_responder_output = workflow_state.get("inquiry_response", {})
        response_composer_output = workflow_state.get("final_response", {})
        
        # Determine which components were executed
        has_order_processing = order_processor_output is not None
        has_inquiry_response = inquiry_responder_output is not None
        
        # Create comprehensive evaluator with all criteria
        criteria = {
            # Email Analyzer criteria
            "email_analyzer_intent": "Did the agent correctly identify the primary intent of the email?",
            "email_analyzer_extraction": "Did the agent extract all relevant entities and details?",
            "email_analyzer_segmentation": "Did the agent properly segment the email?",
            
            # Order Processor criteria (if applicable)
            "order_processor_identification": "Did the agent correctly identify all ordered items?",
            "order_processor_inventory": "Did the agent correctly handle inventory checks?",
            "order_processor_response": "Did the agent provide appropriate order status info?",
            
            # Inquiry Responder criteria (if applicable)
            "inquiry_responder_questions": "Did the agent correctly identify all customer questions?",
            "inquiry_responder_accuracy": "Are the answers factually correct based on available information?",
            "inquiry_responder_completeness": "Did the agent address all aspects of the questions?",
            
            # Response Composer criteria
            "response_composer_tone": "Is the tone suitable for the customer's situation?",
            "response_composer_completeness": "Does the response address all aspects of the customer's email?",
            "response_composer_clarity": "Is the response clear, well-structured, and professional?",
            "response_composer_cta": "Does it include appropriate next steps?",
            
            # End-to-End criteria
            "end_to_end_understanding": "Did the system understand the customer's request and situation?",
            "end_to_end_accuracy": "Is the response factually correct and appropriate?",
            "end_to_end_helpfulness": "Does the response effectively help the customer?",
            "end_to_end_professionalism": "Is the response professional with an appropriate tone?"
        }
        
        # Load master evaluator prompt
        evaluation_template = read_prompt("master_evaluator")
        
        # Create evaluator
        evaluator = load_evaluator(
            "labeled_criteria",
            criteria=criteria,
            evaluation_template=evaluation_template,
            llm=model
        )
        
        # Format data for the master evaluator
        evaluation_input = {
            "email_subject": email_subject,
            "email_message": email_message,
            "email_analysis": json.dumps(email_analyzer_output, indent=2),
            "has_order_processing": has_order_processing,
            "order_result": json.dumps(order_processor_output, indent=2) if has_order_processing else "Not applicable",
            "has_inquiry_response": has_inquiry_response,
            "inquiry_response": json.dumps(inquiry_responder_output, indent=2) if has_inquiry_response else "Not applicable",
            "response_subject": response_composer_output.get("subject", ""),
            "response_body": response_composer_output.get("response_body", "")
        }
        
        # Run evaluation
        eval_result = evaluator.evaluate_strings(
            prediction=json.dumps(evaluation_input, indent=2),
            input=f"Subject: {email_subject}\nMessage: {email_message}",
            reference=""
        )
        
        # Log to LangSmith
        run = client.create_run(
            project_name=experiment_name,
            name=f"Comprehensive Evaluation - {email_id}",
            inputs={"email": f"Subject: {email_subject}\nMessage: {email_message}"},
            outputs={"workflow_results": json.dumps(workflow_state, indent=2)},
            tags=["master_evaluator", email_id],
            run_type="llm"
        )
        
        # Add evaluation feedback for each component
        for criterion, score in eval_result.items():
            if criterion.endswith("_reasoning"):
                continue
            
            client.create_feedback(
                run.id,
                criterion,
                score=score == "Y" if isinstance(score, str) else score,
                comment=eval_result.get(f"{criterion}_reasoning", "")
            )
        
        # Organize results by component
        organized_results = {
            "email_analyzer": {
                "intent_accuracy": eval_result.get("email_analyzer_intent", 0),
                "information_extraction": eval_result.get("email_analyzer_extraction", 0),
                "segmentation_quality": eval_result.get("email_analyzer_segmentation", 0),
                "reasoning": eval_result.get("email_analyzer_intent_reasoning", "")
            },
            "order_processor": {
                "order_identification": eval_result.get("order_processor_identification", 0),
                "inventory_handling": eval_result.get("order_processor_inventory", 0),
                "response_appropriateness": eval_result.get("order_processor_response", 0),
                "reasoning": eval_result.get("order_processor_identification_reasoning", "")
            } if has_order_processing else None,
            "inquiry_responder": {
                "question_identification": eval_result.get("inquiry_responder_questions", 0),
                "answer_accuracy": eval_result.get("inquiry_responder_accuracy", 0),
                "answer_completeness": eval_result.get("inquiry_responder_completeness", 0),
                "reasoning": eval_result.get("inquiry_responder_questions_reasoning", "")
            } if has_inquiry_response else None,
            "response_composer": {
                "tone_appropriateness": eval_result.get("response_composer_tone", 0),
                "response_completeness": eval_result.get("response_composer_completeness", 0),
                "clarity_professionalism": eval_result.get("response_composer_clarity", 0),
                "call_to_action": eval_result.get("response_composer_cta", 0),
                "reasoning": eval_result.get("response_composer_tone_reasoning", "")
            },
            "end_to_end": {
                "understanding": eval_result.get("end_to_end_understanding", 0),
                "response_accuracy": eval_result.get("end_to_end_accuracy", 0),
                "helpfulness": eval_result.get("end_to_end_helpfulness", 0),
                "tone_professionalism": eval_result.get("end_to_end_professionalism", 0),
                "reasoning": eval_result.get("end_to_end_understanding_reasoning", "")
            }
        }
        
        print(f"    Logged comprehensive evaluation to LangSmith: {run.id}")
        return organized_results
        
    except Exception as e:
        print(f"  Error in comprehensive evaluation: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
```

## Master Evaluator Prompt

Create this file as `tools/evaluate/prompts/master_evaluator.md`:

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
- Email Analyzer Intent (0-10): Did the agent correctly identify the primary intent of the email?
- Email Analyzer Extraction (0-10): Did the agent extract all relevant entities and details?
- Email Analyzer Segmentation (0-10): Did the agent properly segment the email?
- Reasoning: [Explain your evaluation of the Email Analyzer]

### Task 2: Evaluate Order Processor (if applicable)
- Order Processor Identification (0-10): Did the agent correctly identify all ordered items?
- Order Processor Inventory (0-10): Did the agent correctly handle inventory checks?
- Order Processor Response (0-10): Did the agent provide appropriate order status info?
- Reasoning: [Explain your evaluation of the Order Processor]

### Task 3: Evaluate Inquiry Responder (if applicable)
- Inquiry Responder Questions (0-10): Did the agent correctly identify all customer questions?
- Inquiry Responder Accuracy (0-10): Are the answers factually correct based on available information?
- Inquiry Responder Completeness (0-10): Did the agent address all aspects of the questions?
- Reasoning: [Explain your evaluation of the Inquiry Responder]

### Task 4: Evaluate Response Composer
- Response Composer Tone (0-10): Is the tone suitable for the customer's situation?
- Response Composer Completeness (0-10): Does the response address all aspects of the customer's email?
- Response Composer Clarity (0-10): Is the response clear, well-structured, and professional?
- Response Composer CTA (0-10): Does it include appropriate next steps?
- Reasoning: [Explain your evaluation of the Response Composer]

### Task 5: Evaluate End-to-End Performance
- End-to-End Understanding (0-10): Did the system understand the customer's request and situation?
- End-to-End Accuracy (0-10): Is the response factually correct and appropriate?
- End-to-End Helpfulness (0-10): Does the response effectively help the customer?
- End-to-End Professionalism (0-10): Is the response professional with an appropriate tone?
- Reasoning: [Explain your evaluation of the overall system performance]

## Important Instructions:
1. Evaluate each component based solely on their specific responsibilities
2. For components marked as "not applicable", score them as NA
3. Provide detailed reasoning for each evaluation
4. Use the full 0-10 scale for nuanced scoring
5. Consider the context of a high-end fashion retailer when evaluating tone and content
```

## Integration with run_evaluation

To integrate the master evaluator with the existing evaluation system, modify `run_evaluation` in `tools/evaluate/main.py`:

```python
async def run_evaluation(
    results: List[Dict[str, Any]],
    experiment_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    auto_upload: bool = True,
    dataset_name: Optional[str] = None,
    use_master_evaluator: bool = True  # New parameter
) -> Dict[str, Any]:
    """
    Evaluate the results of running the Hermes agent flow.
    
    Args:
        results: Results from running the workflow
        experiment_name: Custom name for the experiment
        output_dir: Directory to save the evaluation report
        auto_upload: Whether to automatically upload results to LangSmith
        dataset_name: Name for the dataset in LangSmith when auto-uploading
        use_master_evaluator: Whether to use the combined master evaluator
        
    Returns:
        Evaluation report
    """
    # ... [existing code] ...
    
    try:
        # ... [existing code] ...
        
        # Process each result
        for result in results:
            email_id = result.get("input", {}).get("email_id", "unknown")
            print(f"Evaluating result for email {email_id}...")
            
            # Skip if there were workflow errors
            if result.get("errors") and any(result["errors"].values()):
                print(f"  Skipping evaluation due to workflow errors: {result['errors']}")
                continue
            
            # Extract input email
            email_input = result.get("input", {})
            email_subject = email_input.get("email_subject", "")
            email_message = email_input.get("email_message", "")
            
            # Extract agent outputs
            outputs = result.get("output", {})
            email_analyzer_output = outputs.get("email-analyzer", {})
            order_processor_output = outputs.get("order-processor", {})
            inquiry_responder_output = outputs.get("inquiry-responder", {})
            response_composer_output = outputs.get("response-composer", {})
            
            # Create workflow state for master evaluator
            workflow_state = {
                "email_id": email_id,
                "email_subject": email_subject,
                "email_message": email_message,
                "email_analysis": email_analyzer_output,
                "order_result": order_processor_output,
                "inquiry_response": inquiry_responder_output,
                "final_response": response_composer_output
            }
            
            if use_master_evaluator:
                # Use the master evaluator for all components at once
                eval_results = await evaluate_master(
                    client, 
                    experiment_name, 
                    email_id, 
                    workflow_state,
                    model
                )
                
                # Store results in the appropriate structure
                if "email_analyzer" in eval_results and eval_results["email_analyzer"]:
                    all_scores["email_analyzer"].append(eval_results["email_analyzer"])
                
                if "order_processor" in eval_results and eval_results["order_processor"]:
                    all_scores["order_processor"].append(eval_results["order_processor"])
                
                if "inquiry_responder" in eval_results and eval_results["inquiry_responder"]:
                    all_scores["inquiry_responder"].append(eval_results["inquiry_responder"])
                
                if "response_composer" in eval_results and eval_results["response_composer"]:
                    all_scores["response_composer"].append(eval_results["response_composer"])
                
                if "end_to_end" in eval_results and eval_results["end_to_end"]:
                    all_scores["end_to_end"].append(eval_results["end_to_end"])
            else:
                # Use individual evaluators as before
                if email_analyzer_output:
                    eval_result = await evaluate_email_analyzer(
                        client, 
                        experiment_name, 
                        email_id, 
                        email_subject, 
                        email_message, 
                        email_analyzer_output, 
                        model
                    )
                    all_scores["email_analyzer"].append(eval_result)
                
                # ... [rest of individual evaluators] ...
        
        # ... [rest of function] ...
    
    except Exception as e:
        # ... [error handling] ...
```

## Command Line Interface Update

Update the CLI to allow selecting between master and individual evaluators:

```python
def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Evaluate Hermes agent flow using LangSmith.")
    
    # ... [existing arguments] ...
    
    parser.add_argument(
        "--use-master-evaluator",
        action="store_true",
        help="Use the master evaluator for more efficient evaluation",
        default=True
    )
    parser.add_argument(
        "--use-individual-evaluators",
        action="store_false",
        dest="use_master_evaluator",
        help="Use individual evaluators for each component"
    )
    
    args = parser.parse_args()
    
    # Run the main async function
    asyncio.run(main_async(
        dataset_id=args.dataset_id,
        experiment_name=args.experiment_name,
        result_dir=args.result_dir,
        auto_upload=args.auto_upload,
        dataset_name=args.dataset_name,
        use_master_evaluator=args.use_master_evaluator
    ))
```

This implementation maintains backward compatibility while enabling significant efficiency improvements. 