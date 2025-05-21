from enum import Enum

# Enum of nodes
class Agents(str, Enum):
    """Names of our Agents (also nodes in the workflow graph)."""

    EMAIL_ANALYZER = "email_analyzer"
    PRODUCT_RESOLVER = "product_resolver"
    ORDER_PROCESSOR = "order_processor"
    INQUIRY_RESPONDER = "inquiry_responder"
    RESPONSE_COMPOSER = "response_composer"

class Nodes(str, Enum):
    """Names of our Nodes (also nodes in the workflow graph)."""

    CLASSIFIER = "classifier"
    STOCKKEEPER = "stockkeeper"
    FULFILLER = "fulfiller"
    ADVISOR = "advisor"
    COMPOSER = "composer"
    
class ProductCategory(str, Enum):
    """Categories of products available in the store."""

    ACCESSORIES = "Accessories"
    BAGS = "Bags"
    KIDS_CLOTHING = "Kid's Clothing"
    LOUNGEWEAR = "Loungewear"
    MENS_ACCESSORIES = "Men's Accessories"
    MENS_CLOTHING = "Men's Clothing"
    MENS_SHOES = "Men's Shoes"
    WOMENS_CLOTHING = "Women's Clothing"
    WOMENS_SHOES = "Women's Shoes"


class Season(str, Enum):
    """Seasons in which a product is available."""

    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter" 