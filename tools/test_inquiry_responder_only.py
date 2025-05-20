#!/usr/bin/env python
"""
Test script to run the inquiry responder in isolation.
This script initializes the vector store and directly calls the respond_to_inquiry function.
"""

import asyncio
import os
from dotenv import load_dotenv

from src.hermes.agents.email_analyzer.models import EmailAnalysis, Segment, SegmentType, ProductMention
from src.hermes.agents.inquiry_responder.respond_to_inquiry import respond_to_inquiry, search_vector_store
from src.hermes.agents.inquiry_responder.models import InquiryResponderInput, EmailAnalyzerOutput
from src.hermes.config import HermesConfig
from src.hermes.data_processing.vector_store import VectorStore
from src.hermes.model import ProductCategory, Agents


async def test_vector_store_search():
    """Test the search_vector_store function directly"""
    # Load environment variables
    load_dotenv()
    
    # Create HermesConfig for the search
    hermes_config = HermesConfig()
    
    # Initialize the vector store
    print("Initializing vector store...")
    vector_store = VectorStore(hermes_config=hermes_config)
    
    # Test search with specific queries
    queries = [
        "What messenger bags do you sell?",
        "Do you have leather briefcases?",
        "I need a small bag for work"
    ]
    
    # Run the search - search_vector_store is not async
    print("\nRunning vector store search with queries:", queries)
    result = search_vector_store(queries, hermes_config)
    
    # Print the results
    print("\nSearch Results:")
    print(result)
    print("\nSearch completed. Result length:", len(result), "characters")


async def test_inquiry_responder():
    """Test the full inquiry_responder function"""
    # Load environment variables
    load_dotenv()
    
    # Create HermesConfig
    hermes_config = HermesConfig()
    
    # Initialize the vector store
    print("Initializing vector store...")
    vector_store = VectorStore(hermes_config=hermes_config)
    
    # Create a fake email analysis with inquiries about bags
    email_analysis = EmailAnalysis(
        email_id="TEST-001",
        primary_intent="product inquiry",
        segments=[
            Segment(
                segment_type=SegmentType.INQUIRY,
                main_sentence="What messenger bags do you sell?",
                related_sentences=["Do you have any in leather?"],
                product_mentions=[
                    ProductMention(
                        product_name="messenger bag",
                        product_type="bag",
                        product_category=ProductCategory.BAGS
                    )
                ]
            )
        ]
    )
    
    # Create the EmailAnalyzerOutput object with the required format
    email_analyzer_output = EmailAnalyzerOutput(
        email_analysis=email_analysis,
        unique_products=[]  # Empty list for this test
    )
    
    # Create the inquiry responder input
    input_state = InquiryResponderInput(
        email_analyzer=email_analyzer_output
    )
    
    # Call the respond_to_inquiry function
    print("\nCalling respond_to_inquiry...")
    result = await respond_to_inquiry(
        state=input_state,
        runnable_config={"configurable": {"hermes_config": hermes_config}}
    )
    
    # Process and display results
    # Check if we have a success response or an error
    if Agents.INQUIRY_RESPONDER in result:
        # Success case
        output = result[Agents.INQUIRY_RESPONDER]
        inquiry_answers = output.inquiry_answers
        print(f"\nSuccessfully generated answers for email {inquiry_answers.email_id}")
        
        print(f"\nAnswered Questions ({len(inquiry_answers.answered_questions)}):")
        for i, answer in enumerate(inquiry_answers.answered_questions, 1):
            print(f"{i}. Q: {answer.question}")
            print(f"   A: {answer.answer}")
        
        print(f"\nPrimary Products ({len(inquiry_answers.primary_products)}):")
        for i, prod in enumerate(inquiry_answers.primary_products, 1):
            print(f"{i}. {prod}")
        
        print(f"\nRelated Products ({len(inquiry_answers.related_products)}):")
        for i, prod in enumerate(inquiry_answers.related_products, 1):
            print(f"{i}. {prod}")
        
        print(f"\nUnanswered Questions ({len(inquiry_answers.unanswered_questions)}):")
        for i, q in enumerate(inquiry_answers.unanswered_questions, 1):
            print(f"{i}. {q}")
    elif "errors" in result:
        # Error case
        print("ERROR: Agent returned an error:")
        error = result["errors"].get(Agents.INQUIRY_RESPONDER)
        if error:
            print(f"Message: {error.message}")
            if error.details:
                print(f"Details: {error.details}")
    else:
        print("ERROR: Unexpected result format!")
        print("Result:", result)


async def main():
    """Run the tests"""
    print("TESTING INQUIRY RESPONDER COMPONENTS\n" + "-" * 40)
    
    # First test just the vector store search
    print("\n1. Testing vector store search...")
    await test_vector_store_search()
    
    # Then test the full inquiry responder
    print("\n\n2. Testing full inquiry responder...")
    await test_inquiry_responder()


if __name__ == "__main__":
    asyncio.run(main()) 