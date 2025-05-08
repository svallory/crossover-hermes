# Hermes: Human-like Email Responses for Magically Empathic Sales

## Overview

Hermes is a proof-of-concept application for intelligently processing customer emails for a fashion store. The system categorizes emails as either product inquiries or order requests and generates appropriate responses using the product catalog information and current stock status.

## Key Features

- **Email Classification**: Accurately categorizes incoming emails as either product inquiries or order requests
- **Order Processing**: Verifies product availability, creates orders, and updates stock levels
- **Inquiry Handling**: Uses Retrieval-Augmented Generation (RAG) to find relevant products and provide helpful responses
- **Scalable Design**: Handles large product catalogs efficiently using vector embeddings

## Technical Approach

The solution leverages advanced AI techniques:

1. **LLM Integration**: Uses GPT-4o to understand email content and generate human-like responses
2. **RAG Implementation**: Implements vector-based retrieval to efficiently find relevant products without exceeding token limits
3. **Stock Management**: Tracks inventory changes as orders are processed
4. **Tone Adaptation**: Adjusts response tone based on the context of the request

## Project Structure

- `hermes_solution.md`: Detailed walkthrough of the solution with code and explanations
- `hermes_simplified.py`: Self-contained Python script implementing the complete solution
- `README.md`: Project overview and instructions (this file)

## Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages:
  - pandas
  - numpy
  - openai
  - scikit-learn

## Setup and Usage

1. Clone the repository or extract the files
2. Install required packages:
   ```
   pip install pandas numpy openai scikit-learn
   ```
3. Update the OpenAI API key in the script
4. Run the solution:
   ```
   python hermes_simplified.py
   ```

## Output Format

The system generates four output datasets:

1. **email-classification**: Email ID and classification category
2. **order-status**: Email ID, product ID, quantity, and status (created/out of stock)
3. **order-response**: Email ID and generated response for order requests
4. **inquiry-response**: Email ID and generated response for product inquiries

## Implementation Notes

- The default OpenAI API key in the code should be replaced with your own
- In a production environment, the final solution would write results to Google Sheets as specified in the assignment
- For large product catalogs, embedding generation should be optimized or done as a batch process 