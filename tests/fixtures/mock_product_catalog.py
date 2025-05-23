"""Mock product catalog data for testing."""

import pandas as pd
from typing import Dict, Any, Optional, List
from hermes.model.enums import ProductCategory, Season
from hermes.model.product import Product

def get_mock_products_df() -> pd.DataFrame:
    """Return a DataFrame with mock product data for testing."""
    data = {
        'product_id': ['TST001', 'TST002', 'TST003', 'TST004', 'TST005'],
        'name': ['Test Shirt', 'Test Pants', 'Test Winter Jacket', 'Test Shirt Blue', 'Test Dress'],
        'category': ['Shirts', 'Men\'s Clothing', 'Men\'s Clothing', 'Shirts', 'Women\'s Clothing'],
        'description': [
            'A comfortable cotton test shirt for any occasion.',
            'Stylish test pants for casual wear.',
            'Warm winter jacket for cold weather.',
            'A different test shirt in blue color.',
            'Elegant test dress for special occasions.'
        ],
        'stock': [10, 5, 0, 8, 3],
        'price': [29.99, 49.99, 99.99, 34.99, 79.99],
        'seasons': ['Spring,Summer', 'Fall,Winter', 'Winter', 'Spring,Summer', 'Spring,Summer'],
        'season': ['Spring,Summer', 'Fall,Winter', 'Winter', 'Spring,Summer', 'Spring,Summer']
    }
    
    return pd.DataFrame(data)

def create_mock_product(product_id: str, name: str, category: ProductCategory, 
                       description: str, stock: int, price: float,
                       seasons: Optional[List[Season]] = None) -> Product:
    """Create a mock Product object."""
    if seasons is None:
        seasons = [Season.SPRING, Season.SUMMER]
    
    return Product(
        product_id=product_id,
        name=name,
        description=description,
        category=category,
        seasons=seasons,
        stock=stock,
        price=price,
        product_type="apparel",
        metadata=None
    )

def mock_vector_store_search(query: str, n_results: int = 3, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Product]:
    """Mock the behavior of a vector store search using mock product data."""
    df = get_mock_products_df()
    
    # Simulate filtering if criteria provided
    if filter_criteria:
        if 'category' in filter_criteria:
            df = df[df['category'] == filter_criteria['category']]
        if 'season' in filter_criteria:
            df = df[df['seasons'].str.contains(filter_criteria['season'], na=False)]
    
    # Semantic matching - search in description for the query
    matches = []
    for _, row in df.iterrows():
        if query.lower() in str(row['description']).lower():
            # Map category string to enum
            if 'Shirt' in row['category']:
                category = ProductCategory.SHIRTS
            elif "Men's" in row['category']:
                category = ProductCategory.MENS_CLOTHING
            elif "Women's" in row['category']:
                category = ProductCategory.WOMENS_CLOTHING
            else:
                category = ProductCategory.ACCESSORIES
            
            # Parse seasons
            seasons = []
            for s in row['seasons'].split(','):
                try:
                    seasons.append(Season(s.strip()))
                except ValueError:
                    pass
            if not seasons:
                seasons = [Season.SPRING]
            
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
    
    return matches[:n_results] 