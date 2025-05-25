"""Test product catalog fixtures for testing critical scenarios from emails.csv."""

import pandas as pd
from hermes.model.product import Product, ProductCategory, Season


def get_test_products_df() -> pd.DataFrame:
    """Get a test products DataFrame with realistic data matching the email scenarios."""
    test_products_data = [
        # CHN0987 - Chunky Knit Beanie (for E009 Spanish scenario)
        {
            "product_id": "CHN0987",
            "name": "Chunky Knit Beanie",
            "description": "Keep your head toasty with our chunky knit beanie",
            "category": "Accessories",
            "stock": 2,
            "price": 22.0,
            "season": "Fall, Winter",
            "type": ""
        },
        # CBT8901 - Chelsea Boots (for E019 spaces scenario)
        {
            "product_id": "CBT8901",
            "name": "Chelsea Boots",
            "description": "Classic leather Chelsea boots with elastic side panels",
            "category": "Men's Shoes",
            "stock": 4,
            "price": 89.99,
            "season": "Fall, Winter",
            "type": ""
        },
        # RSG8901 - Retro Sunglasses (for case sensitivity testing)
        {
            "product_id": "RSG8901",
            "name": "Retro Sunglasses",
            "description": "Classic retro-style sunglasses with UV protection",
            "category": "Accessories",
            "stock": 8,
            "price": 25.99,
            "season": "Spring, Summer",
            "type": ""
        },
        # LTH0976 - Leather Bifold Wallet
        {
            "product_id": "LTH0976",
            "name": "Leather Bifold Wallet",
            "description": "Premium leather bifold wallet with multiple card slots",
            "category": "Accessories",
            "stock": 4,
            "price": 21.0,
            "season": "All seasons",
            "type": ""
        },
        # SWL2345 - Sleek Wallet (for E014 scenario)
        {
            "product_id": "SWL2345",
            "name": "Sleek Wallet",
            "description": "Sleek minimalist wallet with RFID protection",
            "category": "Accessories",
            "stock": 5,
            "price": 30.0,
            "season": "All seasons",
            "type": ""
        },
        # VSC6789 - Versatile Scarf (for E008 scenario)
        {
            "product_id": "VSC6789",
            "name": "Versatile Scarf",
            "description": "Soft versatile scarf perfect for any season",
            "category": "Accessories",
            "stock": 12,
            "price": 18.50,
            "season": "All seasons",
            "type": ""
        },
        # SDE2345 - Saddle Bag (for E020 scenario)
        {
            "product_id": "SDE2345",
            "name": "Saddle Bag",
            "description": "Classic saddle bag with adjustable strap",
            "category": "Bags",
            "stock": 3,
            "price": 65.0,
            "season": "All seasons",
            "type": ""
        },
        # SLD7654 - Slide Sandals (for E013 scenario)
        {
            "product_id": "SLD7654",
            "name": "Slide Sandals",
            "description": "Casual slide sandals for men with comfortable footbed",
            "category": "Men's Shoes",
            "stock": 3,
            "price": 22.0,
            "season": "Spring, Summer",
            "type": ""
        },
        # LTH2109 - Leather Messenger Bag (for E012 scenario)
        {
            "product_id": "LTH2109",
            "name": "Leather Messenger Bag",
            "description": "Professional leather messenger bag for work and travel",
            "category": "Bags",
            "stock": 6,
            "price": 120.0,
            "season": "All seasons",
            "type": ""
        },
        # LTH1098 - Leather Backpack (for laptop bag searches)
        {
            "product_id": "LTH1098",
            "name": "Leather Backpack",
            "description": "Leather backpack with padded laptop sleeve and multiple compartments",
            "category": "Bags",
            "stock": 7,
            "price": 95.99,
            "season": "All seasons",
            "type": ""
        },
        # Additional products for testing variety
        {
            "product_id": "CSH1098",
            "name": "Casual Shirt",
            "description": "Comfortable casual shirt for everyday wear",
            "category": "Shirts",
            "stock": 15,
            "price": 32.99,
            "season": "Spring, Summer",
            "type": ""
        },
        {
            "product_id": "WNT4567",
            "name": "Winter Jacket",
            "description": "Warm winter jacket with water-resistant coating",
            "category": "Outerwear",
            "stock": 8,
            "price": 149.99,
            "season": "Fall, Winter",
            "type": ""
        },
    ]

    return pd.DataFrame(test_products_data)


def get_product_by_id(product_id: str) -> Product | None:
    """Get a specific product by ID from test data."""
    df = get_test_products_df()
    product_data = df[df["product_id"] == product_id]

    if product_data.empty:
        return None

    row = product_data.iloc[0]

    # Process seasons
    seasons = []
    seasons_str = str(row.get("season", "Spring"))
    for s in seasons_str.split(","):
        s = s.strip()
        if s:
            if s == "Fall":
                seasons.append(Season.AUTUMN)
            else:
                try:
                    seasons.append(Season(s))
                except ValueError:
                    seasons.append(Season.SPRING)

    if not seasons:
        seasons = [Season.SPRING]

    return Product(
        product_id=str(row["product_id"]),
        name=str(row["name"]),
        category=ProductCategory(str(row["category"])),
        stock=int(row["stock"]),
        description=str(row["description"]),
        product_type=str(row.get("type", "")),
        price=float(row["price"]),
        seasons=seasons,
        metadata=None,
    )


def get_products_matching_description(description: str, limit: int = 5) -> list[Product]:
    """Get products matching a description for testing."""
    df = get_test_products_df()

    # Simple text matching for testing
    description_lower = description.lower()
    matching_products = []

    for _, row in df.iterrows():
        if (description_lower in row["name"].lower() or
            description_lower in row["description"].lower()):

            # Process seasons
            seasons = []
            seasons_str = str(row.get("season", "Spring"))
            for s in seasons_str.split(","):
                s = s.strip()
                if s:
                    if s == "Fall":
                        seasons.append(Season.AUTUMN)
                    else:
                        try:
                            seasons.append(Season(s))
                        except ValueError:
                            seasons.append(Season.SPRING)

            if not seasons:
                seasons = [Season.SPRING]

            product = Product(
                product_id=str(row["product_id"]),
                name=str(row["name"]),
                category=ProductCategory(str(row["category"])),
                stock=int(row["stock"]),
                description=str(row["description"]),
                product_type=str(row.get("type", "")),
                price=float(row["price"]),
                seasons=seasons,
                metadata=None,
            )
            matching_products.append(product)

            if len(matching_products) >= limit:
                break

    return matching_products


def get_products_by_category(category: str, limit: int = 5) -> list[Product]:
    """Get products by category for testing."""
    df = get_test_products_df()
    category_products = df[df["category"].str.lower() == category.lower()]

    products = []
    for _, row in category_products.head(limit).iterrows():
        # Process seasons
        seasons = []
        seasons_str = str(row.get("season", "Spring"))
        for s in seasons_str.split(","):
            s = s.strip()
            if s:
                if s == "Fall":
                    seasons.append(Season.AUTUMN)
                else:
                    try:
                        seasons.append(Season(s))
                    except ValueError:
                        seasons.append(Season.SPRING)

        if not seasons:
            seasons = [Season.SPRING]

        product = Product(
            product_id=str(row["product_id"]),
            name=str(row["name"]),
            category=ProductCategory(str(row["category"])),
            stock=int(row["stock"]),
            description=str(row["description"]),
            product_type=str(row.get("type", "")),
            price=float(row["price"]),
            seasons=seasons,
            metadata=None,
        )
        products.append(product)

    return products