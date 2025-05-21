"""Test fixtures for Hermes tests."""

import os
import sys
from typing import Any, Dict, Tuple

import pandas as pd

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def load_sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the sample data from the CSV files.

    Returns:
        Tuple of (products_df, emails_df)

    """
    # Path to sample data files
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-data"))
    products_path = os.path.join(sample_dir, "products.csv")
    emails_path = os.path.join(sample_dir, "emails.csv")

    # Load data
    products_df = pd.read_csv(products_path)
    emails_df = pd.read_csv(emails_path)

    return products_df, emails_df


def get_test_email(email_id: str) -> dict[str, Any]:
    """Get a specific test email by ID.

    Args:
        email_id: The ID of the email to retrieve (e.g., 'E009')

    Returns:
        Dictionary with email_id, email_subject, and email_body

    """
    _, emails_df = load_sample_data()
    email_row = emails_df[emails_df["email_id"] == email_id]

    if email_row.empty:
        raise ValueError(f"Email ID {email_id} not found in sample data")

    email = email_row.iloc[0]
    return {
        "email_id": email["email_id"],
        "email_subject": email["subject"] if pd.notna(email["subject"]) else "",
        "email_body": email["message"],
    }


def get_test_product(product_id: str) -> dict[str, Any]:
    """Get a specific test product by ID.

    Args:
        product_id: The ID of the product to retrieve (e.g., 'RSG8901')

    Returns:
        Dictionary with product details

    """
    products_df, _ = load_sample_data()
    product_row = products_df[products_df["product_id"] == product_id]

    if product_row.empty:
        raise ValueError(f"Product ID {product_id} not found in sample data")

    product = product_row.iloc[0]
    return product.to_dict()


def get_test_cases() -> dict[str, dict[str, Any]]:
    """Get predefined test cases based on the hidden-evaluation-criteria.md.

    Returns:
        Dictionary mapping test case name to test data

    """
    test_cases = {
        # Email Classifier Test Cases
        "multi_language": get_test_email("E009"),  # Spanish inquiry
        "mixed_intent": get_test_email("E019"),  # Chelsea boots + future sunglasses
        "vague_reference": get_test_email("E017"),  # "that popular item"
        "missing_subject": get_test_email("E006"),  # No subject
        "tangential_info": get_test_email("E012"),  # Lawnmower, reservations
        # Order Processor Test Cases
        "last_item_stock": {
            "email": get_test_email("E010"),  # Order for 1 RSG8901
            "product": get_test_product("RSG8901"),  # Stock = 1
        },
        "exceeds_stock": {
            "email": get_test_email("E018"),  # Order for 2 RSG8901
            "product": get_test_product("RSG8901"),  # Stock = 1
        },
        "complex_format": {
            "email": get_test_email("E019"),  # "[CBT 89 01]"
            "product": get_test_product("CBT8901"),  # Chelsea Boots
        },
        "multiple_items": {
            "email": get_test_email("E007"),  # 5 beanies + 2 slippers
            "products": [
                get_test_product("CLF2109"),  # Cable Knit Beanie
                get_test_product("FZZ1098"),  # Fuzzy Slippers
            ],
        },
        "with_promotion": {
            "email": get_test_email("E022"),  # "those amazing bags"
            "product": get_test_product("CBG9876"),  # Canvas Beach Bag with promotion
        },
        # Inquiry Responder Test Cases
        "seasonal_inquiry": {
            "email": get_test_email("E020"),  # Saddle bag for spring
            "product": get_test_product("SDE2345"),  # Saddle Bag
        },
        "occasion_inquiry": {
            "email": get_test_email("E016"),  # Dress for summer wedding
            "products": [],  # Various dresses could match
        },
        "material_quality": {
            "email": get_test_email("E005"),  # CSH1098 material quality
            "product": get_test_product("CSH1098"),  # Cozy Shawl
        },
        "style_inspiration": {
            "email": get_test_email("E011"),  # Era for RSG8901
            "product": get_test_product("RSG8901"),  # Retro Sunglasses
        },
        # Response Composer Test Cases
        "formal_tone": get_test_email("E005"),  # "Good day,"
        "casual_tone": get_test_email("E002"),  # Chatty with personal details
        "out_of_stock": {
            "email": get_test_email("E018"),  # 2 pairs of RSG8901
            "product": get_test_product("RSG8901"),  # Stock = 1
        },
    }

    return test_cases
