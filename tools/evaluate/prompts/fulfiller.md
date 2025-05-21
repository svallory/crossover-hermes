# Order Processor Evaluator Prompt

You are evaluating the performance of an order processor agent that handles customer product orders.

Given the email analysis and the order processing result, evaluate:
1. Correctness - Did the agent properly identify all ordered items?
2. Inventory handling - Did the agent correctly check stock and make appropriate recommendations?
3. Response appropriateness - Did the agent provide useful information about order status?

Email Analysis:
{email_analysis}

Order Processing Result:
{order_result}

Provide your evaluation in the following format:
- Order identification (0-10): [score]
- Inventory handling (0-10): [score]
- Response appropriateness (0-10): [score]
- Overall assessment (0-10): [score]
- Reasoning: [detailed explanation of your evaluation] 