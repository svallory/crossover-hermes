# Interview Assignment: Solve Business Problems with AI

## Objective

Develop a proof-of-concept application to intelligently process email order requests and customer inquiries for a fashion store. The system should accurately categorize emails as either product inquiries or order requests and generate appropriate responses using the product catalog information and current stock status.

You are encouraged to use AI assistants (like ChatGPT or Claude) and any IDE of your choice to develop your solution. Many modern IDEs (such as PyCharm, or Cursor) can work with Jupiter files directly.

### Submission Deadline:

You have 2 days to complete the assignment

## Task Description

### Inputs

Google Spreadsheet **[Document](https://docs.google.com/spreadsheets/d/14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U)** containing:

- **Products**: List of products with fields including product ID, name, category, stock amount, detailed description, and season.

- **Emails**: Sequential list of emails with fields such as email ID, subject, and body.

### Instructions

- Implement all requirements using advanced Large Language Models (LLMs) to handle complex tasks, process extensive data, and generate accurate outputs effectively.
- Use Retrieval-Augmented Generation (RAG) and vector store techniques where applicable to retrieve relevant information and generate responses.
- You are provided with a temporary OpenAI API key granting access to GPT-4o, which has a token quota. Use it wisely or use your own key if preferred.
- Address the requirements in the order listed. Review them in advance to develop a general implementation plan before starting.
- Your deliverables should include:
   - Code developed within this notebook.
   - A single spreadsheet containing results, organized across separate sheets.
   - Comments detailing your thought process.
- You may use additional libraries (e.g., langchain) to streamline the solution. Use libraries appropriately to align with best practices for AI and LLM tools.
- Use the most suitable AI techniques for each task. Note that solving tasks with traditional programming methods will not earn points, as this assessment evaluates your knowledge of LLM tools and best practices.

### Requirements

#### 1. Classify emails
    
Classify each email as either a _**"product inquiry"**_ or an _**"order request"**_. Ensure that the classification accurately reflects the intent of the email.

**Output**: Populate the **email-classification** sheet with columns: email ID, category.

#### 2. Process order requests
1.   Process orders
  - For each order request, verify product availability in stock.
  - If the order can be fulfilled, create a new order line with the status “created”.
  - If the order cannot be fulfilled due to insufficient stock, create a line with the status “out of stock” and include the requested quantity.
  - Update stock levels after processing each order.
  - Record each product request from the email.
  - **Output**: Populate the **order-status** sheet with columns: email ID, product ID, quantity, status (**_"created"_**, **_"out of stock"_**).

2.   Generate responses
  - Create response emails based on the order processing results:
      - If the order is fully processed, inform the customer and provide product details.
      - If the order cannot be fulfilled or is only partially fulfilled, explain the situation, specify the out-of-stock items, and suggest alternatives or options (e.g., waiting for restock).
  - Ensure the email tone is professional and production-ready.
  - **Output**: Populate the **order-response** sheet with columns: email ID, response.

#### 3. Handle product inquiry

Customers may ask general open questions.
  - Respond to product inquiries using relevant information from the product catalog.
  - Ensure your solution scales to handle a full catalog of over 100,000 products without exceeding token limits. Avoid including the entire catalog in the prompt.
  - **Output**: Populate the **inquiry-response** sheet with columns: email ID, response.

## Evaluation Criteria
- **Advanced AI Techniques**: The system should use Retrieval-Augmented Generation (RAG) and vector store techniques to retrieve relevant information from data sources and use it to respond to customer inquiries.
- **Tone Adaptation**: The AI should adapt its tone appropriately based on the context of the customer's inquiry. Responses should be informative and enhance the customer experience.
- **Code Completeness**: All functionalities outlined in the requirements must be fully implemented and operational as described.
- **Code Quality and Clarity**: The code should be well-organized, with clear logic and a structured approach. It should be easy to understand and maintain.
- **Presence of Expected Outputs**: All specified outputs must be correctly generated and saved in the appropriate sheets of the output spreadsheet. Ensure the format of each output matches the requirements—do not add extra columns or sheets.
- **Accuracy of Outputs**: The accuracy of the generated outputs is crucial and will significantly impact the evaluation of your submission.

We look forward to seeing your solution and your approach to solving real-world problems with AI technologies.

# Environment

~~~python
INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'
~~~

# Prerequisites

### Configure OpenAI API Key.

~~~python
# Install the OpenAI Python package.
%pip install openai httpx==0.27.2
~~~

**IMPORTANT: If you are going to use our custom API Key then make sure that you also use custom base URL as in example below. Otherwise it will not work.**

~~~python
# Code example of OpenAI communication

from openai import OpenAI

client = OpenAI(
    # In order to use provided API key, make sure that models you create point to this custom base URL.
    base_url='https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/',
    # The temporary API key giving access to ChatGPT 4o model. Quotas apply: you have 500'000 input and 500'000 output tokens, use them wisely ;)
    api_key='<OPENAI API KEY: Use one provided by Crossover or your own>'
)

completion = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message)
~~~

~~~python
# Code example of reading input data

import pandas as pd
from IPython.display import display

def read_data_frame(document_id, sheet_name):
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return  pd.read_csv(export_link)

document_id = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'
products_df = read_data_frame(document_id, 'products')
emails_df = read_data_frame(document_id, 'emails')

# Display first 3 rows of each DataFrame
display(products_df.head(3))
display(emails_df.head(3))
~~~

~~~python
# Code example of generating output document

# Creates a new shared Google Worksheet every invocation with the proper structure
# Note: This code should be executed from the google colab once you are ready, it will not work locally
from google.colab import auth
import gspread
from google.auth import default
from gspread_dataframe import set_with_dataframe

# IMPORTANT: You need to authenticate the user to be able to create new worksheet
# Insert the authentication snippet from the official documentation to create a google client:
# https://colab.research.google.com/notebooks/io.ipynb#scrollTo=qzi9VsEqzI-o

# This code goes after creating google client
output_document = gc.create('Solving Business Problems with AI - Output')

# Create 'email-classification' sheet
email_classification_sheet = output_document.add_worksheet(title="email-classification", rows=50, cols=2)
email_classification_sheet.update([['email ID', 'category']], 'A1:B1')

# Example of writing the data into the sheet
# Assuming you have your classification in the email_classification_df DataFrame
# set_with_dataframe(email_classification_sheet, email_classification_df)
# Or directly update cells: https://docs.gspread.org/en/latest/user-guide.html#updating-cells

# Create 'order-status' sheet
order_status_sheet = output_document.add_worksheet(title="order-status", rows=50, cols=4)
order_status_sheet.update([['email ID', 'product ID', 'quantity', 'status']], 'A1:D1')

# Create 'order-response' sheet
order_response_sheet = output_document.add_worksheet(title="order-response", rows=50, cols=2)
order_response_sheet.update([['email ID', 'response']], 'A1:B1')

# Create 'inquiry-response' sheet
inquiry_response_sheet = output_document.add_worksheet(title="inquiry-response", rows=50, cols=2)
inquiry_response_sheet.update([['email ID', 'response']], 'A1:B1')

# Share the spreadsheet publicly
output_document.share('', perm_type='anyone', role='reader')

# This is the solution output link, paste it into the submission form
print(f"Shareable link: https://docs.google.com/spreadsheets/d/{output_document.id}")
~~~

# Task 1. Classify emails

# Task 2. Process order requests

# Task 3. Handle product inquiry

