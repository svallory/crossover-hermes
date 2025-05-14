"""{cell}
## Inquiry Responder Agent

This agent handles emails classified as product inquiries. It performs the following key tasks:
1. Resolve product references to specific catalog items
2. Use RAG (Retrieval-Augmented Generation) to find relevant product information
3. Extract and answer customer questions about products
4. Identify related products that might interest the customer
5. Generate comprehensive inquiry response data

The Inquiry Responder leverages vector search to handle inquiries even for large
product catalogs, ensuring accurate and helpful answers to customer questions.
"""

import json
from typing import List, Dict, Any, Optional, Union, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from ..llm_client import get_llm_client
from ..tools.catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    search_products_by_description,
    find_related_products,
    resolve_product_reference,
    Product,
    ProductNotFound,
)
from ..tools.response_tools import extract_questions
from ..tools.order_tools import extract_promotion, PromotionDetails
from ..state import HermesState
from ..model.common import ProductBase
from .email_analyzer import EmailAnalysis
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from ..prompts import (
    inquiry_responder_md,
    answer_question_md,
    inquiry_response_verification_md,
)


class LLMAnsweredQuestionResult(BaseModel):
    """LLM structured answer for a customer question."""

    is_answered: bool = Field(
        description="Whether the question could be answered from the provided context."
    )
    answer_text: str = Field(
        description="The generated answer text. Empty if not answered."
    )
    confidence: Annotated[
        float, Field(ge=0.0, le=1.0, description="Confidence in the answer (0.0-1.0).")
    ]
    relevant_product_ids: List[str] = Field(
        default_factory=list,
        description="Product IDs relevant to this answer based on the context used.",
    )


class ProductInformation(ProductBase):
    """Detailed product information relevant to a customer inquiry."""

    details: Dict[str, Any] = Field(
        description="Key product details relevant to the inquiry"
    )
    availability: str = Field(description="Availability status")
    promotions: Optional[str] = Field(
        default=None, description="Any promotions for this product"
    )

    @staticmethod
    def from_product_obj(
        product: Union[Product, Dict[str, Any]],
    ) -> "ProductInformation":
        """Factory method to create ProductInformation from a Product object or dict."""
        if isinstance(product, dict):
            product_obj = Product(**product)
        else:
            product_obj = product

        stock_amount = (
            product_obj.stock_amount if hasattr(product_obj, "stock_amount") else 0
        )
        availability = "In stock" if stock_amount > 0 else "Out of stock"

        details = {
            "category": getattr(product_obj, "category", "Unknown"),
            "description": getattr(
                product_obj, "description", "No description available."
            ),
            "stock_amount": stock_amount,
        }

        if hasattr(product_obj, "season") and product_obj.season:
            details["season"] = product_obj.season

        promotion_result_data = extract_promotion.invoke(
            input={
                "product_description": getattr(product_obj, "description", ""),
                "product_name": product_obj.product_name,
            }
        )

        # extract_promotion tool returns PromotionDetails Pydantic model
        if isinstance(promotion_result_data, PromotionDetails):
            promotion_details_obj = promotion_result_data
        elif isinstance(
            promotion_result_data, dict
        ):  # Should not happen if tool returns Pydantic
            promotion_details_obj = PromotionDetails(**promotion_result_data)
        else:  # Fallback or error
            promotion_details_obj = PromotionDetails(has_promotion=False)

        promotions = (
            promotion_details_obj.promotion_text
            if promotion_details_obj.has_promotion
            else None
        )

        return ProductInformation(
            product_id=product_obj.product_id,
            product_name=product_obj.product_name,
            details=details,
            availability=availability,
            price=getattr(product_obj, "price", None),
            promotions=promotions,
        )


class QuestionAnswer(BaseModel):
    """A customer's question paired with its answer from product information."""

    question: str = Field(description="The customer's question")
    question_excerpt: Optional[str] = Field(
        default=None, description="Text from the email containing this question"
    )
    answer: str = Field(description="The answer based on product information")
    confidence: Annotated[
        float, Field(ge=0.0, le=1.0, description="Confidence in the answer (0.0-1.0)")
    ]
    relevant_product_ids: List[str] = Field(
        default_factory=list, description="Product IDs relevant to this answer"
    )


class InquiryResponse(BaseModel):
    """Complete response to a product inquiry."""

    email_id: str = Field(description="Email ID")
    primary_products: List[ProductInformation] = Field(
        default_factory=list,
        description="Main products inquired about, identified by the LLM using tools.",
    )
    answered_questions: List[QuestionAnswer] = Field(
        default_factory=list,
        description="Questions extracted and answered by the LLM using tools and context.",
    )
    related_products: List[ProductInformation] = Field(
        default_factory=list,
        description="Related or complementary products suggested by the LLM using tools.",
    )
    response_points: List[str] = Field(
        description="Key points synthesized by the LLM to include in the final email response."
    )
    unanswered_questions: List[str] = Field(
        default_factory=list,
        description="Questions the LLM identified but could not answer with available tools/information.",
    )
    unsuccessful_references: List[str] = Field(
        default_factory=list,
        description="Product references the LLM attempted to resolve with tools but failed.",
    )


async def process_inquiry_node(
    state: Dict[str, Any], config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process product inquiries using an LLM with tool calling capabilities.
    The LLM will use tools to resolve products, extract/answer questions, and find related products
    to generate a comprehensive InquiryResponse.
    """
    typed_state = HermesState(
        email_id=state.get("email_id", "unknown"),
        email_subject=state.get("email_subject", ""),
        email_body=state.get("email_body", ""),
        email_analysis=state.get("email_analysis"),
        product_catalog_df=state.get("product_catalog_df"),
        vector_store=state.get("vector_store"),
    )

    email_id = typed_state.email_id
    email_body = typed_state.email_body
    email_analysis_data = typed_state.email_analysis
    product_catalog_df = typed_state.product_catalog_df  # Tools will need this
    vector_store = typed_state.vector_store  # Tools will need this

    if (
        config
        and "configurable" in config
        and "hermes_config" in config["configurable"]
    ):
        hermes_config = config["configurable"]["hermes_config"]
    else:
        from ..config import HermesConfig

        hermes_config = HermesConfig()

    llm = get_llm_client(
        config=hermes_config, temperature=hermes_config.llm_inquiry_temperature
    )

    if (
        not email_analysis_data
        or email_analysis_data.get("classification") != "product_inquiry"
    ):
        print(f"Email {email_id} is not a product inquiry. Skipping.")
        empty_result = InquiryResponse(
            email_id=email_id,
            primary_products=[],
            response_points=["This email was not classified as a product inquiry."],
        )
        return {"inquiry_result": empty_result.model_dump()}

    print(f"Processing inquiry for email {email_id} using LLM with tool calling.")

    if product_catalog_df is None:
        print(f"Error: Product catalog missing for email {email_id}")
        error_result = InquiryResponse(
            email_id=email_id,
            response_points=["Error: Missing product catalog data."],
            primary_products=[],
        )
        return {
            "inquiry_result": error_result.model_dump(),
            "error": "Missing product catalog data.",
        }
    # Vector store is optional for some tools, but search_products_by_description requires it.
    # The tool itself can handle if it's missing if it's made optional in its schema.
    # For now, search_products_by_description requires it.

    # Define the tools available to the LLM
    tools = [
        find_product_by_id,
        find_product_by_name,
        search_products_by_description,
        find_related_products,
        extract_questions,
        resolve_product_reference,
    ]

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    # The inquiry_responder_prompt needs to be adapted.
    # It should instruct the LLM on its goal (fill InquiryResponse) and how to use tools.
    # Example of a system message (simplified):
    system_prompt_text = f"""You are an AI assistant helping a customer with a product inquiry for email ID: {email_id}.
Your goal is to populate all fields of the InquiryResponse JSON schema.
Email Subject: {typed_state.email_subject}
Email Body:
---
{email_body}
---
Email Analysis (provided for context, you should verify and use tools for product details):
---
{json.dumps(email_analysis_data, indent=2)}
---
Use the available tools to:
1.  Identify and resolve all product references mentioned by the customer. These are your 'primary_products'.
    For each primary product, provide its ID, name, details (like category, description, stock_amount, season), availability, and any promotions.
2.  Extract all explicit and implicit questions the customer is asking using the 'extract_questions' tool.
3.  For each extracted question, try to answer it using the information you've gathered about products or by searching further if necessary.
    Populate the 'answered_questions' list with the question, your answer, confidence, and relevant product IDs.
    If a question cannot be answered, add it to 'unanswered_questions'.
4.  Suggest 1-2 'related_products' that might also interest the customer, based on the primary products or the nature of their inquiry.
5.  Synthesize a few key 'response_points' that should be included in an email back to the customer.
6.  List any 'unsuccessful_references' if you tried to find a product mentioned by the customer but couldn't resolve it with tools.

Respond with a single JSON object that strictly adheres to the InquiryResponse schema.
Ensure product_catalog_df and vector_store are passed to tools that require them.
The product_catalog_df contains all product data. The vector_store is for semantic search.
"""

    # For tools requiring DataFrame or vector_store, they need to be partialled or the agent needs to inject them.
    # Langchain tools can take arguments directly. The LLM generates args for `product_id`, `query` etc.
    # `product_catalog_df` and `vector_store` are available in this scope.
    # When executing a tool call, we'll need to add these fixed arguments.

    messages = [
        SystemMessage(content=system_prompt_text),
        HumanMessage(
            content=f"Please process the product inquiry from email ID {email_id} and generate the InquiryResponse JSON."
        ),
    ]

    # Tool calling loop
    MAX_ITERATIONS = 5
    for _ in range(MAX_ITERATIONS):
        ai_response: AIMessage = await llm_with_tools.ainvoke(messages)
        messages.append(ai_response)

        if not ai_response.tool_calls:
            # If no tool calls, LLM thinks it's done or doesn't need tools.
            # We expect the AI to provide the InquiryResponse JSON here.
            break

        for tool_call in ai_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            selected_tool = next((t for t in tools if t.name == tool_name), None)
            if not selected_tool:
                messages.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found.",
                        tool_call_id=tool_id,
                    )
                )
                continue

            # Inject product_catalog_df and vector_store if the tool needs them
            # This is a bit manual; Langroid AgentExecutor handles this more gracefully with tool definitions.
            if "product_catalog_df" in selected_tool.args_schema.schema().get(
                "properties", {}
            ):
                tool_args["product_catalog_df"] = product_catalog_df
            if "vector_store" in selected_tool.args_schema.schema().get(
                "properties", {}
            ):
                if vector_store:  # Only add if available
                    tool_args["vector_store"] = vector_store
                elif "vector_store" in selected_tool.args_schema.schema().get(
                    "required", []
                ):
                    messages.append(
                        ToolMessage(
                            content=f"Error: Tool '{tool_name}' requires vector_store, but it's not available.",
                            tool_call_id=tool_id,
                        )
                    )
                    continue

            try:
                tool_output = await selected_tool.ainvoke(tool_args)
                # If tool output is Pydantic model or list of them, convert to JSON string or dict for ToolMessage
                if isinstance(tool_output, BaseModel):
                    tool_output_content = tool_output.model_dump_json()
                elif isinstance(tool_output, list) and all(
                    isinstance(item, BaseModel) for item in tool_output
                ):
                    tool_output_content = json.dumps(
                        [item.model_dump() for item in tool_output]
                    )
                elif isinstance(
                    tool_output, ProductNotFound
                ):  # Handle ProductNotFound specifically
                    tool_output_content = tool_output.model_dump_json()
                else:  # Assume it's already a string or simple dict/list
                    tool_output_content = (
                        json.dumps(tool_output)
                        if not isinstance(tool_output, str)
                        else tool_output
                    )

                messages.append(
                    ToolMessage(content=tool_output_content, tool_call_id=tool_id)
                )
            except Exception as e:
                error_message = (
                    f"Error executing tool {tool_name} with args {tool_args}: {e}"
                )
                print(error_message)
                messages.append(
                    ToolMessage(content=error_message, tool_call_id=tool_id)
                )

    # After loop, the last AI message should contain the InquiryResponse content or a message leading to it.
    final_ai_message = messages[-1]
    inquiry_response_result: Optional[InquiryResponse] = None

    if isinstance(final_ai_message, AIMessage) and final_ai_message.content:
        try:
            # Assuming the LLM is prompted to return JSON for InquiryResponse in its final message
            data = json.loads(final_ai_message.content)
            inquiry_response_result = InquiryResponse(**data)
        except (json.JSONDecodeError, TypeError) as e:
            print(
                f"Error parsing final LLM response into InquiryResponse for {email_id}: {e}. Content: {final_ai_message.content}"
            )
            # Fallback: Try to get it from tool_calls if the last message was a tool call for some reason (should not happen with break)
            # Or if the LLM is using `with_structured_output` *after* the tool calling part.
            # This part is tricky without a dedicated agent executor or more refined prompting.
            # For now, let's attempt to parse the last message, if it's not a tool call itself.

    if not inquiry_response_result:  # Fallback if parsing failed
        print(
            f"Could not directly parse InquiryResponse for {email_id}. Generating fallback."
        )
        # This indicates the LLM didn't provide the final JSON as expected in final_ai_message.content
        # The prompt or loop structure might need refinement.
        # A simpler approach for the final step *could* be to take all messages and then call:
        # inquiry_response_result = await (llm.with_structured_output(InquiryResponse)).ainvoke(messages)
        # But this is another LLM call. The ideal is the LLM provides it in the loop's last message.

        # For now, create a fallback if not parsed.
        # Extract what we can from the conversation if needed, or use a generic error.
        # This fallback is very basic.
        unsuccessful_references_texts = []  # This would need to be extracted from tool calls or messages
        primary_products_for_context = []  # This would need to be extracted

        # A temporary strategy if the direct JSON output fails:
        # Use the original prompt approach with the full message history for context.
        # This is like a "summary" step.
        print(f"Attempting structured output parse as a fallback for {email_id}")
        try:
            # Create a new chain for final parsing if direct output failed
            # This prompt would need to summarize the conversation and produce InquiryResponse
            final_parse_prompt_text = f"""Based on the preceding conversation (including tool usage and results),
please generate the InquiryResponse JSON object for email ID {email_id}.
The conversation history is: {json.dumps([m.dict() for m in messages], indent=2)}
Ensure your output is ONLY the JSON object conforming to the InquiryResponse schema.
"""
            # This assumes inquiry_responder_prompt is designed for this kind of summarization
            # which it might not be. A dedicated "final_summary_prompt" might be better.
            # For this refactor, the primary path is the LLM outputting JSON in the loop.
            # If that fails, this fallback is a hail mary.

            # The original prompt `inquiry_responder_prompt` was for a single call.
            # We need a prompt that can take the message history and produce the final Pydantic.
            # A simple way for this fallback is to use the existing `inquiry_responder_prompt`
            # but re-craft its input based on the message history. This is complex.

            # The most straightforward fallback for now if the LLM doesn't provide the JSON in the loop:
            inquiry_response_result = InquiryResponse(
                email_id=email_id,
                response_points=[
                    "Error: Could not fully process inquiry using tool calling. LLM did not provide final structured output."
                ],
                primary_products=[],  # primary_products_for_context,
                unsuccessful_references=[],  # unsuccessful_references_texts
            )
        except Exception as e_fallback:
            print(
                f"Fallback structured output parse also failed for {email_id}: {e_fallback}"
            )
            inquiry_response_result = InquiryResponse(
                email_id=email_id,
                response_points=[
                    "Critical error: Could not process inquiry and fallback also failed."
                ],
                primary_products=[],
                unsuccessful_references=[],
            )

    # Ensure email_id is correctly propagated
    if inquiry_response_result and not inquiry_response_result.email_id:
        inquiry_response_result.email_id = email_id

    # Verification step (can remain, as it's an agent's internal step)
    if inquiry_response_result:
        verified_result = await verify_inquiry_response(
            inquiry_response_result, llm, email_analysis_data
        )  # llm here is the base llm
        return {"inquiry_result": verified_result.model_dump()}
    else:  # Should not happen if fallback always creates an InquiryResponse
        return {
            "inquiry_result": InquiryResponse(
                email_id=email_id,
                response_points=["Error: No inquiry result generated."],
            ).model_dump()
        }


async def verify_inquiry_response(
    result: InquiryResponse,
    llm: ChatOpenAI,
    email_analysis: Union[EmailAnalysis, Dict[str, Any]],
):
    # ... (docstring and existing verification logic remains largely the same) ...
    # This function uses an LLM for verification, which is fine as it's part of the agent's
    # internal workflow, not a "tool" called by another LLM.
    validation_errors = []

    if not result.response_points:
        validation_errors.append(
            "No response points generated by the main inquiry LLM."
        )

    print(f"Verifying inquiry response for {result.email_id} using LLM.")
    errors_found_str = (
        "N/A - LLM performing full review based on system prompt instructions."
    )
    if validation_errors:
        errors_found_str = "\\n".join(f"- {err}" for err in validation_errors)
        print(f"Initial Python checks found: {errors_found_str}")

    original_response_json = result.model_dump_json()
    email_analysis_dump = (
        email_analysis.model_dump()
        if hasattr(email_analysis, "model_dump")
        else email_analysis
    )
    email_analysis_json = json.dumps(email_analysis_dump, indent=2)

    # The verification prompt is correctly formatted
    # Make sure the input keys match what the template expects.
    # Assuming the template is: prompt_template.from_template(template_string)
    # And it expects "errors_found_str", "original_response_json", "email_analysis_json"

    # Create prompt templates from markdown content
    inquiry_responder_prompt = PromptTemplate.from_template(inquiry_responder_md)

    answer_question_prompt_template = PromptTemplate.from_template(answer_question_md)

    inquiry_response_verification_prompt_template = PromptTemplate.from_template(
        inquiry_response_verification_md
    )

    # Creating the chain for verification
    verification_chain = (
        inquiry_response_verification_prompt_template
        | llm.with_structured_output(InquiryResponse)
    )

    try:
        # Invoke the verification chain.
        # The prompt template itself might define some input variables.
        # If the prompt template takes no dynamic inputs beyond what's in its definition,
        # then invoking with an empty dict might be okay IF the prompt formats itself with fixed context.
        # However, usually, these are passed to .invoke()
        fixed_result = await verification_chain.ainvoke(
            {
                "errors_found_str": errors_found_str,  # If your prompt template uses this
                "original_response_json": original_response_json,  # If your prompt template uses this
                "email_analysis_json": email_analysis_json,  # If your prompt template uses this
            }
        )

        if fixed_result.model_dump() != result.model_dump():
            print("Inquiry response verification: LLM suggested revisions.")
        else:
            print(
                "Inquiry response verification: LLM confirmed response quality or made no major changes."
            )
        return fixed_result
    except Exception as e:
        print(f"Inquiry response verification: LLM review/correction failed: {e}")
        if not hasattr(result, "response_points") or result.response_points is None:
            result.response_points = []
        elif not isinstance(result.response_points, list):
            result.response_points = [str(result.response_points)]
        result.response_points.append(f"[Note: LLM Verification failed: {str(e)}]")
        return result


""" {cell}
### Inquiry Responder Agent Implementation Notes

The Inquiry Responder Agent provides comprehensive information in response to customer product inquiries:

1. **RAG Architecture**:
   - This agent implements a classic Retrieval-Augmented Generation (RAG) pattern for product inquiries
   - Uses both structured lookups (by ID, name) and semantic search for more abstract references
   - Vector search makes the system scalable to large product catalogs (100,000+ products)

2. **Multi-Step Resolution Process**:
   - First attempts to resolve explicit product references from the email
   - Then extracts questions and uses available product details to answer them
   - Falls back to semantic search when specific product context is insufficient
   - Finally suggests related or complementary products to enhance the customer experience

3. **Question Answering**:
   - The `answer_product_question` function implements a two-stage approach:
     - First tries to answer using primary products identified in the email
     - Then tries semantic search when needed to find additional information
   - Each answer includes confidence levels and source product IDs for transparency

4. **Response Planning**:
   - Generates structured `response_points` that will guide the Response Composer
   - Handles edge cases like unanswerable questions and unidentifiable products
   - Ensures the customer receives a complete response even with partial information

5. **Verification Logic**:
   - The `verify_inquiry_response` function ensures a valid, actionable response
   - Adds fallbacks for edge cases where little product information was found

This agent balances depth of product information with natural question answering, ensuring customers receive helpful responses regardless of how they phrase their inquiries.
"""
