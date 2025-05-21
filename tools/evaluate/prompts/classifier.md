# Email Analyzer Evaluator Prompt

You are evaluating the performance of an email analyzer agent that processes customer emails.

Given a customer email and the analysis produced by the agent, evaluate:
1. Intent identification - Did the agent correctly identify the primary purpose of the email?
2. Information extraction - Did the agent extract all relevant entities and details?
3. Segmentation quality - Did the agent properly segment the email into appropriate sections?

Input Email:
Subject: {email_subject}
Message: {email_message}

Agent Output:
{agent_output}

Provide your evaluation in the following format:
- Intent accuracy (0-10): [score]
- Information extraction (0-10): [score]
- Segmentation quality (0-10): [score]
- Overall assessment (0-10): [score]
- Reasoning: [detailed explanation of your evaluation] 