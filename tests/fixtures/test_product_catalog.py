"""Test product catalog data for testing."""

import os
import pandas as pd
from typing import Dict, Any, Optional, List
from hermes.model.enums import ProductCategory, Season
from hermes.model.product import Product

def get_csv_path(filename: str) -> str:
    """Get the absolute path to a CSV file in the data directory."""
    return os.path.join("/work/crossover/hermes/data", filename)

def map_category(category_str: str) -> ProductCategory:
    """Map a category string to a ProductCategory enum."""
    if "Men's" in category_str:
        if "Clothing" in category_str:
            return ProductCategory.MENS_CLOTHING
        elif "Shoes" in category_str:
            return ProductCategory.MENS_SHOES
        elif "Accessories" in category_str:
            return ProductCategory.MENS_ACCESSORIES
        else:
            return ProductCategory.MENS_CLOTHING
    elif "Women's" in category_str:
        if "Clothing" in category_str:
            return ProductCategory.WOMENS_CLOTHING
        elif "Shoes" in category_str:
            return ProductCategory.WOMENS_SHOES
        else:
            return ProductCategory.WOMENS_CLOTHING
    elif "Kids'" in category_str or "Kid's" in category_str:
        return ProductCategory.KIDS_CLOTHING
    elif "Bags" in category_str:
        return ProductCategory.BAGS
    elif "Accessories" in category_str:
        return ProductCategory.ACCESSORIES
    elif "Loungewear" in category_str:
        return ProductCategory.LOUNGEWEAR
    else:
        return ProductCategory.ACCESSORIES

def parse_seasons(seasons_str: str) -> List[Season]:
    """Parse a seasons string into a list of Season enums."""
    seasons = []
    
    # Handle "All seasons" case
    if "All seasons" in seasons_str:
        return [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
    
    # Parse individual seasons
    for s in seasons_str.split(','):
        season_name = s.strip()
        try:
            # Map common alternate names to proper enum values
            if season_name == "Fall":
                seasons.append(Season.AUTUMN)
            else:
                seasons.append(Season(season_name))
        except ValueError:
            pass  # Skip invalid season values
    
    # Default if no valid seasons
    if not seasons:
        seasons = [Season.SPRING]
        
    return seasons

def get_test_products_df() -> pd.DataFrame:
    """Return a DataFrame loaded from the test product catalog CSV."""
    csv_path = get_csv_path("products.csv")
    df = pd.read_csv(csv_path)
    
    # Add 'season' column for backward compatibility if tests expect it
    # The CSV uses 'seasons' but some code might expect 'season'
    if 'seasons' in df.columns and 'season' not in df.columns:
        df['season'] = df['seasons']
    
    return df

def get_product_by_id(product_id: str) -> Product:
    """Get a specific product by ID from the test data."""
    df = get_test_products_df()
    row = df[df['product_id'] == product_id].iloc[0]
    
    # Get seasons from the appropriate column
    seasons_str = str(row.get('seasons', row.get('season', 'Spring')))
    seasons = parse_seasons(seasons_str)
    
    # Map category string to enum
    category = map_category(str(row['category']))
    
    return Product(
        product_id=str(row['product_id']),
        name=str(row['name']),
        description=str(row['description']),
        category=category,
        seasons=seasons,
        stock=int(row['stock']),
        price=float(row['price']),
        product_type="apparel",
        metadata=None
    )

def get_products_matching_description(query: str, limit: int = 3) -> List[Product]:
    """Get products matching a description query from the test data."""
    df = get_test_products_df()
    
    matches = []
    for _, row in df.iterrows():
        if query.lower() in str(row['description']).lower():
            # Get seasons from the appropriate column
            seasons_str = str(row.get('seasons', row.get('season', 'Spring')))
            seasons = parse_seasons(seasons_str)
            
            # Map category string to enum
            category = map_category(str(row['category']))
            
            product = Product(
                product_id=str(row['product_id']),
                name=str(row['name']),
                description=str(row['description']),
                category=category,
                seasons=seasons,
                stock=int(row['stock']),
                price=float(row['price']),
                product_type="apparel",
                metadata=None
            )
            matches.append(product)
    
    return matches[:limit]

def vector_store_search(query: str, n_results: int = 3, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Product]:
    """Mock the behavior of a vector store search using test product data."""
    return get_products_matching_description(query, n_results) 