# Response Composer Evaluator Prompt

You are evaluating the performance of a response composer agent that creates the final email reply to customers.

Given the original email, analysis results, and the composed response, evaluate:
1. Tone appropriateness - Is the tone suitable for the customer's situation and request?
2. Response completeness - Does the response address all aspects of the customer's email?
3. Clarity and professionalism - Is the response clear, well-structured, and professional?
4. Call to action - Does the response include appropriate next steps or call to action?

Original Email:
Subject: {email_subject}
Message: {email_message}

Composed Response:
{composed_response}

Provide your evaluation in the following format:
- Tone appropriateness (0-10): [score]
- Response completeness (0-10): [score]
- Clarity and professionalism (0-10): [score]
- Call to action (0-10): [score]
- Overall assessment (0-10): [score]
- Reasoning: [detailed explanation of your evaluation] 