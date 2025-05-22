# Summary of src/hermes/agents/classifier/models.py

**File Link:** [`src/hermes/agents/classifier/models.py`](/src/hermes/agents/classifier/models.py)

This file defines the Pydantic data models used for the input and output of the Classifier agent, as well as the detailed structure of the email analysis results.

**Purpose and Responsibilities:**

-   **Data Structuring:** Defines the schema for representing the incoming email (`ClassifierInput`) and the structured output of the classification process (`ClassifierOutput`).
-   **Email Analysis Representation:** Includes models like `ProductMention`, `SegmentType` (enum for segment types like 'order', 'inquiry'), and `Segment` to capture fine-grained details about the email content, including product references and logical sections.
-   **Aggregated Analysis:** The core `EmailAnalysis` model aggregates all the extracted information: email ID, language, primary intent, customer PII, and a list of `Segment` objects. It also provides utility methods to check for the presence of specific segment types (`has_order`, `has_inquiry`).
-   **Type Safety:** Using Pydantic models ensures data validation and provides clear type hints for the data flowing into and out of the Classifier agent, improving code readability and maintainability.

In summary, `models.py` establishes the standardized format for the data used and produced by the Classifier agent, which is essential for the seamless integration and information flow within the broader Hermes workflow. 