#!/usr/bin/env python
"""LLM-as-a-Judge Evaluators for Hermes Workflow.

This module provides sophisticated LLM-based evaluators for assessing
the quality and accuracy of Hermes workflow outputs.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


async def evaluate_classification_with_llm(
    email_content: str, classification: str
) -> dict:
    """Evaluate classification accuracy using LLM as judge.

    Args:
        email_content: Original email content
        classification: Predicted classification

    Returns:
        Evaluation result with score and reasoning
    """
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = f"""
You are evaluating an email classification system for a fashion retailer.

Original Email:
{email_content}

Classification Result: {classification}

Please evaluate whether the classification is accurate based on the email content.
An email should be classified as:
- "order request" if the customer wants to place an order, modify an order, or check order status
- "product inquiry" if the customer is asking questions about products, availability, or specifications

Respond with:
1. A score of 1 if the classification is completely accurate, 0 if incorrect
2. A brief reasoning for your score

Format your response as:
Score: [0 or 1]
Reasoning: [Your explanation]
"""

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        result_text = response.content

        # Parse the response
        lines = result_text.strip().split("\n")
        score = 0
        reasoning = ""

        for line in lines:
            if line.startswith("Score:"):
                try:
                    score = int(line.split(":")[1].strip())
                except:
                    score = 0
            elif line.startswith("Reasoning:"):
                reasoning = line.split(":", 1)[1].strip()

        return {"score": score, "reasoning": reasoning}
    except Exception as e:
        return {"score": 0, "reasoning": f"Error during LLM evaluation: {str(e)}"}


async def evaluate_response_quality_with_llm(
    email_content: str, response_text: str
) -> dict:
    """Evaluate response quality using LLM as judge.

    Args:
        email_content: Original email content
        response_text: Generated response

    Returns:
        Evaluation result with score and reasoning
    """
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = f"""
You are evaluating customer service responses for a high-end fashion retailer.

Original Customer Email:
{email_content}

Generated Response:
{response_text}

Please evaluate the response on these criteria:
1. Helpfulness - Does it address the customer's needs?
2. Professionalism - Is it appropriate for a luxury brand?
3. Completeness - Are all customer questions/concerns addressed?

Rate the overall quality from 0-1 where:
- 1.0 = Excellent response that meets all criteria
- 0.8 = Good response with minor issues
- 0.6 = Adequate response but missing some elements
- 0.4 = Poor response with major issues
- 0.2 = Very poor response
- 0.0 = Completely inadequate or no response

Format your response as:
Score: [0.0 to 1.0]
Reasoning: [Your explanation covering helpfulness, professionalism, and completeness]
"""

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        result_text = response.content

        # Parse the response
        lines = result_text.strip().split("\n")
        score = 0.0
        reasoning = ""

        for line in lines:
            if line.startswith("Score:"):
                try:
                    score = float(line.split(":")[1].strip())
                except:
                    score = 0.0
            elif line.startswith("Reasoning:"):
                reasoning = line.split(":", 1)[1].strip()

        return {"score": score, "reasoning": reasoning}
    except Exception as e:
        return {"score": 0.0, "reasoning": f"Error during LLM evaluation: {str(e)}"}


def create_llm_evaluator_functions():
    """Create LLM evaluator functions for use with LangSmith evaluate().

    Returns:
        List of evaluator functions
    """
    evaluators = []

    # Classification evaluator function
    async def evaluate_classification_llm(run, example) -> dict:
        """LLM-based classification evaluation."""
        try:
            inputs = run.inputs or {}
            outputs = run.outputs or {}

            # Get original email
            subject = inputs.get("subject", "")
            message = inputs.get("message", "")
            email_content = f"Subject: {subject}\n{message}"

            # Get classification result
            email_analysis = outputs.get("email_analysis", {})
            if not email_analysis:
                return {
                    "key": "llm_classification_accuracy",
                    "score": 0,
                    "comment": "No classification output",
                }

            analysis_data = email_analysis.get("email_analysis", {})
            classification = analysis_data.get("primary_intent", "unknown")

            # Run LLM evaluation
            result = await evaluate_classification_with_llm(
                email_content, classification
            )

            return {
                "key": "llm_classification_accuracy",
                "score": result["score"],
                "comment": result["reasoning"],
            }

        except Exception as e:
            return {
                "key": "llm_classification_accuracy",
                "score": 0,
                "comment": f"Error: {str(e)}",
            }

    evaluators.append(evaluate_classification_llm)

    # Response quality evaluator function
    async def evaluate_response_quality_llm(run, example) -> dict:
        """LLM-based response quality evaluation."""
        try:
            inputs = run.inputs or {}
            outputs = run.outputs or {}

            # Get original email
            subject = inputs.get("subject", "")
            message = inputs.get("message", "")
            email_content = f"Subject: {subject}\n{message}"

            # Get final response
            final_response = outputs.get("final_response", {})
            if not final_response:
                return {
                    "key": "llm_response_quality",
                    "score": 0,
                    "comment": "No final response",
                }

            response_text = final_response.get("response_body", "")
            if not response_text:
                return {
                    "key": "llm_response_quality",
                    "score": 0,
                    "comment": "Empty response body",
                }

            # Run LLM evaluation
            result = await evaluate_response_quality_with_llm(
                email_content, response_text
            )

            return {
                "key": "llm_response_quality",
                "score": result["score"],
                "comment": result["reasoning"],
            }

        except Exception as e:
            return {
                "key": "llm_response_quality",
                "score": 0,
                "comment": f"Error: {str(e)}",
            }

    evaluators.append(evaluate_response_quality_llm)

    return evaluators
