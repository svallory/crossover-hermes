from enum import Enum

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