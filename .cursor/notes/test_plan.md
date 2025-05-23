## Test Plan for Email Processing Application

This test plan covers the requirements outlined in `docs/assignment/assignment-instructions.md`.

### Overall Objective

Verify that the application correctly classifies emails, processes order requests (checking stock, updating stock, generating statuses and responses), and handles product inquiries (generating responses using product catalog information).

### Test Cases

Each test case should use a specific set of input emails and a predefined state of the product catalog (stock levels). The expected outputs for each sheet (`email-classification`, `order-status`, `order-response`, `inquiry-response`) should be documented for each test case.

#### Test Case 1: Mixed Emails (Order Request and Product Inquiry)

*   **Input:**
    *   Emails with a mix of clear order requests for available products and clear product inquiries.
    *   Product catalog with sufficient stock for the requested items.
*   **Expected Output:**
    *   `email-classification.csv`: Correct classification for each email.
    *   `order-status.csv`: "created" status for all requested items in order emails, with correct product IDs and quantities. Stock levels in the product catalog should be updated accordingly.
    *   `order-response.csv`: Professional responses confirming successful order processing.
    *   `inquiry-response.csv`: Relevant responses based on the product catalog for inquiry emails.

#### Test Case 2: Order Request - Insufficient Stock

*   **Input:**
    *   Email containing an order request for one or more items with insufficient stock.
    *   Product catalog with low/zero stock for specific items.
*   **Expected Output:**
    *   `email-classification.csv`: Correct classification as "order request".
    *   `order-status.csv`: "out of stock" status for items with insufficient stock, including the requested quantity. "created" status for available items. Stock levels should be updated for available items.
    *   `order-response.csv`: Professional response explaining which items are out of stock, mentioning the requested quantity, and suggesting alternatives or waiting for restock.
    *   `inquiry-response.csv`: Empty or no entry for this email ID.

#### Test Case 3: Product Inquiry - Detailed Question

*   **Input:**
    *   Email with a detailed product inquiry requiring information from the product description.
    *   Product catalog with detailed descriptions for the queried product.
*   **Expected Output:**
    *   `email-classification.csv`: Correct classification as "product inquiry".
    *   `order-status.csv`: Empty or no entry for this email ID.
    *   `order-response.csv`: Empty or no entry for this email ID.
    *   `inquiry-response.csv`: Relevant response containing details from the product catalog description.

#### Test Case 4: Product Inquiry - General Question (requiring RAG)

*   **Input:**
    *   Email with a general question about product categories or seasons that requires retrieving information from the overall product catalog.
    *   Product catalog with various categories and seasons.
*   **Expected Output:**
    *   `email-classification.csv`: Correct classification as "product inquiry".
    *   `order-status.csv`: Empty or no entry for this email ID.
    *   `order-response.csv`: Empty or no entry for this email ID.
    *   `inquiry-response.csv`: Relevant response based on retrieved information from the product catalog (demonstrating RAG). The response should maintain an appropriate tone.

#### Test Case 5: Edge Cases / Ambiguous Emails

*   **Input:**
    *   Emails with ambiguous intent (e.g., asking about a product and also mentioning a desire to buy it without a clear order format).
*   **Expected Output:**
    *   Verify that the classification is reasonable based on the dominant intent.
    *   Verify that subsequent processing (order or inquiry) handles the ambiguity gracefully and produces a relevant output.

### Test Execution Steps

1.  Prepare input data (emails and product catalog) for each test case, saving them in a format loadable by the application (e.g., a local copy of the spreadsheet or CSVs).
2.  Run the application (`main.py`) with the prepared input data for a specific test case.
3.  Collect the generated output files (`email-classification.csv`, `order-status.csv`, `order-response.csv`, `inquiry-response.csv`) from the `output` directory.
4.  Compare the actual output files with the documented expected outputs for the test case.
5.  Verify that stock levels in the product catalog are updated correctly after processing order requests.
6.  Repeat for all test cases.

### Evaluation Criteria

*   Accuracy of email classification.
*   Correctness of order processing logic (stock check, status, quantity).
*   Accuracy and relevance of generated responses for both order requests and product inquiries.
*   Correctness of output file formats and column names.
*   Demonstration of RAG techniques for product inquiries.
*   Appropriate tone adaptation in generated responses. 