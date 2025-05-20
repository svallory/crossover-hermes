from enum import Enum

class SignalCategory(str, Enum):
    """Customer signal categories, aligned with prompt examples."""

    PURCHASE_INTENT = "Purchase Intent"  # Example: I'd like to order
    CUSTOMER_CONTEXT = "Customer Context"  # General context
    COMMUNICATION_STYLE = "Communication Style"  # Tone, formality
    EMOTION_AND_TONE = "Emotion and Tone"  # Sentiment, specific emotions
    OBJECTION = "Objection"  # Concerns or reasons not to buy
    TIMING = "Timing"  # e.g., urgency for a trip
    PURCHASE_STAGE = "Purchase Stage"  # e.g. clear intent, pre-finalization question
    PRODUCT_FEATURES = "Product Features"  # e.g. wondering about material
    USAGE_INFORMATION = "Usage Information"  # e.g. care instructions
    DECISION_FACTOR = "Decision Factor"  # e.g. health concern, suitability for skin
    PURCHASE_CONTEXT = "Purchase Context"  # e.g. gift purpose
    # Adding other categories from the prompt example for Customer Signals
    PRODUCT_INTEREST = "Product Interest"
    URGENCY = "Urgency"
    SENTIMENT_POSITIVE = "Sentiment Positive"
    SENTIMENT_NEGATIVE = "Sentiment Negative"
    BUDGET_MENTION = "Budget Mention"
    OCCASION_MENTION = "Occasion Mention"
    NEW_CUSTOMER_INDICATOR = "New Customer Indicator"
    LOYALTY_MENTION = "Loyalty Mention"
    COMPARISON_SHOPPING = "Comparison Shopping"
    FEATURE_REQUEST = "Feature Request"
    PROBLEM_REPORT = "Problem Report"

