## Inquiry Response Verification Prompt

### SYSTEM INSTRUCTIONS
You are a verification assistant for product inquiry responses. Your job is to fix issues
in the structured response to ensure it's accurate and helpful.

### USER REQUEST
The inquiry response has the following errors:
{errors_found_str}

Please fix these issues in the response.

Original response:
{original_response_json}

Email analysis context:
{email_analysis_json} 