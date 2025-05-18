# Inquiry Responder Evaluator Prompt

You are evaluating the performance of an inquiry responder agent that answers customer questions.

Given the email analysis and the inquiry response, evaluate:
1. Question identification - Did the agent correctly identify all customer questions?
2. Answer accuracy - Did the agent provide factually correct answers based on available information?
3. Answer completeness - Did the agent address all aspects of the customer's questions?

Email Analysis:
{email_analysis}

Inquiry Response:
{inquiry_response}

Provide your evaluation in the following format:
- Question identification (0-10): [score]
- Answer accuracy (0-10): [score] 
- Answer completeness (0-10): [score]
- Overall assessment (0-10): [score]
- Reasoning: [detailed explanation of your evaluation] 