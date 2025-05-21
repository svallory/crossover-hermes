"""Tests for the product deduplication functionality."""

from src.hermes.agents.classifier.models import (
    EmailAnalysis,
    ProductMention,
    Segment,
)
from src.hermes.data_processing.product_deduplication import (
    deduplicate_product_mentions,
    get_product_mention_stats,
)

def create_test_analysis_result() -> EmailAnalysis:
    """Create a sample EmailAnalysisResult with duplicate products for testing."""
    # Create a product that appears in multiple segments
    duplicate_product = ProductMention(
        product_id="ABC1234",
        product_name="Alpine Explorer",
        product_category="Bags",
        product_type="Backpack",
        confidence=0.95,
    )

    # Create a variant of the same product with a different confidence
    duplicate_variant = ProductMention(
        product_id="ABC1234",
        product_name="Alpine Explorer",
        product_category="Bags",
        product_type="Backpack",
        confidence=0.85,  # Lower confidence
    )

    # Create another product that's identified by name+category
    name_product1 = ProductMention(
        product_id=None,
        product_name="Sunset Breeze",
        product_category="Women's Clothing",
        product_type="T-shirt",
        confidence=0.9,
    )

    # Create a duplicate of the name-based product
    name_product2 = ProductMention(
        product_id=None,
        product_name="Sunset Breeze",
        product_category="Women's Clothing",
        product_type="T-shirt",
        confidence=0.7,
    )

    # Create a unique product
    unique_product = ProductMention(
        product_id="XYZ5678",
        product_name="Urban Nomad",
        product_category="Men's Shoes",
        product_type="Sneakers",
        confidence=1.0,
    )

    # Create a generic product without enough identifying information
    generic_product = ProductMention(
        product_id=None,
        product_name=None,
        product_category="Accessories",
        product_type="Hat",
        confidence=0.6,
    )

    # Create segments with these products
    segments = [
        Segment(
            segment_type="order",
            main_sentence="I want to buy an Alpine Explorer backpack.",
            related_sentences=["Is it available in black?"],
            product_mentions=[duplicate_product, name_product1],
        ),
        Segment(
            segment_type="inquiry",
            main_sentence="Also, can you tell me more about the Sunset Breeze t-shirt?",
            related_sentences=[],
            product_mentions=[name_product2],
        ),
        Segment(
            segment_type="order",
            main_sentence="I'd also like to purchase the Urban Nomad sneakers.",
            related_sentences=["I need them in size 10."],
            product_mentions=[unique_product, duplicate_variant],
        ),
        Segment(
            segment_type="personal_statement",
            main_sentence="I'm looking for a hat as well.",
            related_sentences=["Something stylish."],
            product_mentions=[generic_product],
        ),
    ]

    return EmailAnalysis(
        language="english",
        primary_intent="order request",
        customer_pii={},
        segments=segments,
    )


def test_deduplicate_product_mentions():
    """Test that product mentions are properly deduplicated."""
    analysis_result = create_test_analysis_result()

    # Get the total number of product mentions before deduplication
    total_mentions = sum(len(segment.product_mentions) for segment in analysis_result.segments)
    assert total_mentions == 6, "Expected 6 total product mentions"

    # Deduplicate
    _, unique_products = deduplicate_product_mentions(analysis_result)

    # We should have 4 unique products (Alpine Explorer, Sunset Breeze, Urban Nomad, and the generic hat)
    assert len(unique_products) == 4, f"Expected 4 unique products but got {len(unique_products)}"

    # Check that we kept the highest confidence version of duplicate products
    alpine_explorer = next((p for p in unique_products if p.product_name == "Alpine Explorer"), None)
    assert alpine_explorer is not None, "Alpine Explorer product not found"
    assert alpine_explorer.confidence == 0.95, "Expected highest confidence value (0.95) for Alpine Explorer"

    sunset_breeze = next((p for p in unique_products if p.product_name == "Sunset Breeze"), None)
    assert sunset_breeze is not None, "Sunset Breeze product not found"
    assert sunset_breeze.confidence == 0.9, "Expected highest confidence value (0.9) for Sunset Breeze"


def test_get_product_mention_stats():
    """Test that product mention statistics are correctly calculated."""
    analysis_result = create_test_analysis_result()

    stats = get_product_mention_stats(analysis_result)

    assert stats["total_mentions"] == 6, "Expected 6 total mentions"
    assert stats["unique_products"] == 4, "Expected 4 unique products"
    assert stats["segments_with_products"] == 4, "Expected 4 segments with products"


def test_empty_analysis_result():
    """Test deduplication with an empty analysis result."""
    empty_result = EmailAnalysis(
        language="english",
        primary_intent="product inquiry",
        customer_pii={},
        segments=[],
    )

    _, unique_products = deduplicate_product_mentions(empty_result)
    assert len(unique_products) == 0, "Expected 0 unique products for empty result"

    stats = get_product_mention_stats(empty_result)
    assert stats["total_mentions"] == 0
    assert stats["unique_products"] == 0
    assert stats["segments_with_products"] == 0
