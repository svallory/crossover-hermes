"""Tests for catalog_tools.py."""

from unittest.mock import patch, MagicMock

from hermes.tools.catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    search_products_by_description,
    find_complementary_products,
    search_products_with_filters,
    find_products_for_occasion,
)
from hermes.data.vector_store import metadata_to_product

# import hermes.data.vector_store # No longer needed for patch.object
from hermes.model.product import Product, ProductCategory, Season
from hermes.model.errors import ProductNotFound

from tests.fixtures.mock_product_catalog import (
    get_mock_products_df,
)
from tests.fixtures.test_product_catalog import (
    get_test_products_df,
)


class TestCatalogTools:
    """Tests for the catalog_tools module using mock data."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_valid(self, mock_load_df):
        """Test finding a product by a valid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_id.invoke({"product_id": "TST001"})

        # Verify result
        assert isinstance(result, Product)
        assert result.product_id == "TST001"
        assert result.name == "Test Shirt"
        assert result.category == ProductCategory.SHIRTS

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid(self, mock_load_df):
        """Test finding a product with invalid ID."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_id.invoke({"product_id": "NONEXISTENT"})

        # Verify result
        assert isinstance(result, ProductNotFound)
        assert "No product found" in result.message

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_invalid_input(self, mock_load_df):
        """Test finding a product with invalid input."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke with empty string
        result = find_product_by_id.invoke({"product_id": ""})

        # Verify result
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_valid(self, mock_load_df):
        """Test finding a product by name with valid match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke
        result = find_product_by_name.invoke(
            {"product_name": "Test Shirt", "threshold": None, "top_n": None}
        )

        # Verify result - should match both "Test Shirt" products in mock data
        assert isinstance(result, list)
        # Both "Test Shirt" and "Test Shirt Blue" will match "Test Shirt"
        assert len(result) >= 1
        assert result[0].matched_product.name == "Test Shirt"
        assert result[0].similarity_score > 0.9

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_name_no_match(self, mock_load_df):
        """Test finding a product by name with no match."""
        # Setup mock
        mock_load_df.return_value = get_mock_products_df()

        # Call @tool function using invoke with high threshold to force no matches
        result = find_product_by_name.invoke(
            {"product_name": "Nonexistent Product", "threshold": 0.99, "top_n": None}
        )

        # Verify result
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.load_products_df")
    @patch("hermes.tools.catalog_tools.find_product_by_id")
    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_valid(
        self,
        mock_create_vector_store_func,
        mock_find_product_by_id_tool,
        mock_load_df_unused,
    ):
        """Test searching products by description with valid query."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value

        # Mock find_product_by_id to return a live product for TST001
        mock_live_product_tst001 = Product(
            product_id="TST001",
            name="Live Test Shirt",
            category=ProductCategory.SHIRTS,
            stock=10,  # Ensure positive stock
            price=29.99,
            seasons=[Season.SPRING],
            description="Live description.",
            product_type="live_type",
        )
        # Configure mock for specific input "TST001"
        mock_find_product_by_id_tool.invoke.side_effect = (
            lambda args: mock_live_product_tst001
            if args.get("product_id") == "TST001"
            else ProductNotFound(
                message="Generic mock error", query_product_id=args.get("product_id")
            )
        )

        # Mock similarity search results from vector store
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Test Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "",
            "description": "A comfortable cotton test shirt for any occasion.",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]

        result = search_products_by_description.invoke(
            {"query": "comfortable", "top_k": 2}
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"
        assert result[0].stock == 10

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_no_match(
        self, mock_create_vector_store_func
    ):
        """Test searching products by description with no matches."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value
        mock_vector_store_instance.similarity_search_with_score.return_value = []

        result = search_products_by_description.invoke({"query": "nonexistent term"})
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_complementary_products_valid(
        self, mock_load_df, mock_create_vector_store_func
    ):
        """Test finding complementary products with valid product ID."""
        mock_load_df.return_value = get_mock_products_df()
        mock_vector_store_instance = mock_create_vector_store_func.return_value

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST002",
            "name": "Another Shirt",
            "category": "Shirts",
            "stock": 5,
            "price": 25.99,
            "season": "Spring",
            "type": "",
            "description": "Another test shirt",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]

        result = find_complementary_products.invoke(
            {"product_id": "TST005", "limit": 2}
        )
        assert isinstance(result, (list, ProductNotFound))

    @patch("hermes.tools.catalog_tools.get_vector_store")
    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_complementary_products_invalid_product(
        self, mock_load_df, mock_create_vector_store_func
    ):
        """Test finding complementary products with invalid product ID."""
        mock_load_df.return_value = get_mock_products_df()

        result = find_complementary_products.invoke(
            {"product_id": "NONEXISTENT", "limit": 2}
        )
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_valid(self, mock_create_vector_store_func):
        """Test searching products with filters."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Test Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 29.99,
            "season": "Spring",
            "type": "",
            "description": "A comfortable cotton test shirt for any occasion.",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]

        result = search_products_with_filters.invoke(
            {
                "query": "comfortable shirt",
                "category": "Shirts",
                "season": None,
                "min_price": 20.0,
                "max_price": 50.0,
                "min_stock": None,
                "top_k": 3,
            }
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_no_match(self, mock_create_vector_store_func):
        """Test searching products with filters that don't match."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value
        mock_vector_store_instance.similarity_search_with_score.return_value = []

        result = search_products_with_filters.invoke(
            {
                "query": "nonexistent product",
                "category": "Shirts",
                "season": None,
                "min_price": None,
                "max_price": None,
                "min_stock": None,
                "top_k": None,
            }
        )
        assert isinstance(result, ProductNotFound)

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_products_for_occasion_valid(
        self, mock_create_vector_store_func, mock_find_product_by_id_tool
    ):
        """Test finding products for a specific occasion."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value

        mock_live_product_tst001 = Product(
            product_id="TST001",
            name="Live Formal Shirt",
            category=ProductCategory.SHIRTS,
            stock=5,
            price=49.99,
            seasons=[Season.SPRING],
            description="Live formal description.",
            product_type="live_formal_type",
        )
        mock_find_product_by_id_tool.invoke.side_effect = (
            lambda args: mock_live_product_tst001
            if args.get("product_id") == "TST001"
            else ProductNotFound(
                message="Generic mock error", query_product_id=args.get("product_id")
            )
        )

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "TST001",
            "name": "Formal Shirt",
            "category": "Shirts",
            "stock": 10,
            "price": 49.99,
            "season": "Spring",
            "type": "",
            "description": "A formal dress shirt perfect for business meetings.",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]

        result = find_products_for_occasion.invoke(
            {"occasion": "business meeting", "limit": 3}
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "TST001"
        assert result[0].stock == 5

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_find_products_for_occasion_no_match(self, mock_create_vector_store_func):
        """Test finding products for occasion with no matches."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value
        mock_vector_store_instance.similarity_search_with_score.return_value = []

        result = find_products_for_occasion.invoke(
            {"occasion": "space travel", "limit": 3}
        )
        assert isinstance(result, ProductNotFound)


class TestCatalogToolsCriticalScenarios:
    """Tests for critical real-world scenarios from email analysis."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_case_insensitive_product_id(self, mock_load_df):
        """Test case insensitive product ID matching."""
        mock_df = get_test_products_df()
        mock_load_df.return_value = mock_df

        # Test lowercase product ID
        result = find_product_by_id.invoke({"product_id": "rsg8901"})

        assert isinstance(result, Product)
        assert result.product_id == "RSG8901"
        assert result.name == "Retro Sunglasses"


class TestMetadataConversion:
    """Test the metadata_to_product conversion function."""

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_metadata_to_product_basic(self, mock_find_product_by_id_tool):
        """Test basic metadata to product conversion."""
        mock_live_product = Product(
            product_id="TST001",
            name="Live Test Product",
            category=ProductCategory.ACCESSORIES,
            stock=5,
            price=30.00,
            seasons=[Season.SPRING],
            description="Live description.",
            product_type="live_test",
        )
        mock_find_product_by_id_tool.invoke.return_value = mock_live_product

        metadata = {
            "product_id": "TST001",
            "name": "Test Product",
            "category": "Accessories",
            "price": 29.99,
            "season": "Spring,Summer",
            "type": "test",
            "description": "A test product",
        }

        product = metadata_to_product(metadata)

        assert isinstance(product, Product)
        assert product.product_id == "TST001"
        assert product.name == "Test Product"
        assert product.description == "A test product"
        assert product.product_type == "test"
        assert product.stock == 5
        assert product.price == 30.00
        assert product.category == ProductCategory.ACCESSORIES
        assert product.seasons == [Season.SPRING, Season.SUMMER]

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_metadata_to_product_season_handling(self, mock_find_product_by_id_tool):
        """Test season handling in metadata conversion."""
        mock_live_product = Product(
            product_id="TST001",
            name="Live Test Product",
            category=ProductCategory.ACCESSORIES,
            stock=10,
            price=29.99,
            seasons=[Season.FALL],
            description="Live description",
            product_type="live_type",
        )
        mock_find_product_by_id_tool.invoke.return_value = mock_live_product

        metadata = {
            "product_id": "TST001",
            "name": "Test Product",
            "category": "Accessories",
            "season": "Fall,Winter",
            "type": "",
            "description": "A test product",
            "price": 29.99,
        }

        product = metadata_to_product(metadata)

        assert isinstance(product, Product)
        assert product.seasons == [Season.FALL, Season.WINTER]

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_metadata_to_product_not_found_in_live_catalog(
        self, mock_find_product_by_id_tool
    ):
        """Test metadata_to_product when product ID from metadata is not in live catalog."""
        mock_find_product_by_id_tool.invoke.return_value = ProductNotFound(
            message="Not found", query_product_id="TST002"
        )

        metadata = {
            "product_id": "TST002",
            "name": "Fallback Product",
            "category": "Shirts",
            "price": 19.99,
            "season": "Summer",
            "type": "fallback_type",
            "description": "A product description from metadata.",
        }

        product = metadata_to_product(metadata)

        assert isinstance(product, Product)
        assert product.product_id == "TST002"
        assert product.name == "Fallback Product"
        assert product.category == ProductCategory.SHIRTS
        assert product.stock == 0
        assert product.price == 19.99
        assert product.seasons == [Season.SUMMER]
        assert product.product_type == "fallback_type"
        assert product.description == "A product description from metadata."
        assert product.metadata is not None and (
            "Fallback: Original product ID 'TST002' not found in live catalog."
            in product.metadata
        )

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_metadata_to_product_invalid_category_in_metadata(
        self, mock_find_product_by_id_tool
    ):
        """Test metadata_to_product with an invalid category string in metadata when live product is found."""
        mock_live_product = Product(
            product_id="TST003",
            name="Live Product Name",
            category=ProductCategory.MENS_SHOES,
            stock=15,
            price=75.00,
            seasons=[Season.ALL_SEASONS],
            description="Live description",
            product_type="live_type",
        )
        mock_find_product_by_id_tool.invoke.return_value = mock_live_product

        metadata = {
            "product_id": "TST003",
            "name": "Product from Metadata",
            "category": "InvalidCategoryValue",
            "price": 70.00,
            "season": "Spring",
            "type": "meta_type",
            "description": "Meta description",
        }
        product = metadata_to_product(metadata)
        assert isinstance(product, Product)
        assert product.category == ProductCategory.MENS_SHOES

    @patch("hermes.tools.catalog_tools.find_product_by_id")
    def test_metadata_to_product_invalid_season_in_metadata(
        self, mock_find_product_by_id_tool
    ):
        """Test metadata_to_product with an invalid season string in metadata when live product is found."""
        mock_live_product = Product(
            product_id="TST004",
            name="Live Product Name",
            category=ProductCategory.BAGS,
            stock=20,
            price=120.00,
            seasons=[Season.FALL, Season.WINTER],
            description="Live description",
            product_type="live_type",
        )
        mock_find_product_by_id_tool.invoke.return_value = mock_live_product

        metadata = {
            "product_id": "TST004",
            "name": "Product from Metadata",
            "category": "Bags",
            "price": 110.00,
            "season": "InvalidSeason,Spring",
            "type": "meta_type",
            "description": "Meta description",
        }
        product = metadata_to_product(metadata)
        assert isinstance(product, Product)
        assert product.seasons == [Season.FALL, Season.WINTER]


class TestCatalogToolsWithTestData:
    """Tests for catalog_tools using test product data from CSV."""

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_with_test_data(self, mock_load_df):
        """Test finding a product by ID with test product data."""
        mock_load_df.return_value = get_test_products_df()
        test_product_id = "RSG8901"
        result = find_product_by_id.invoke({"product_id": test_product_id})
        assert isinstance(result, Product)
        assert result.product_id == test_product_id
        assert result.name == "Retro Sunglasses"
        assert result.category == ProductCategory.ACCESSORIES

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_with_spanish_name_test_data(self, mock_load_df):
        """Test finding a product by ID when mention has a Spanish name, using test data."""
        mock_load_df.return_value = get_test_products_df()
        product_id_to_find = "CHN0987"
        expected_name = "Chunky Knit Beanie"
        result = find_product_by_id.invoke({"product_id": product_id_to_find})
        assert isinstance(result, Product)
        assert result.product_id == product_id_to_find
        assert result.name == expected_name
        assert result.category == ProductCategory.ACCESSORIES

    @patch("hermes.tools.catalog_tools.load_products_df")
    def test_find_product_by_id_not_found_with_test_data(self, mock_load_df):
        """Test finding a product with invalid ID using test data."""
        mock_load_df.return_value = get_test_products_df()
        result = find_product_by_id.invoke({"product_id": "NONEXISTENT"})
        assert isinstance(result, ProductNotFound)
        assert "No product found" in result.message

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_by_description_with_test_data(
        self, mock_create_vector_store_func
    ):
        """Test searching products by description using test data."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Wallet",
            "category": "Accessories",
            "stock": 25,
            "price": 45.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather wallet with multiple card slots",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]
        result = search_products_with_filters.invoke(
            {
                "query": "leather",
                "category": None,
                "season": None,
                "min_price": None,
                "max_price": None,
                "min_stock": None,
                "top_k": None,
            }
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "LTH0976"

    @patch("hermes.tools.catalog_tools.get_vector_store")
    def test_search_products_with_filters_with_test_data(
        self, mock_create_vector_store_func
    ):
        """Test searching products with filters using test data."""
        mock_vector_store_instance = mock_create_vector_store_func.return_value
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "product_id": "LTH0976",
            "name": "Leather Wallet",
            "category": "Accessories",
            "stock": 25,
            "price": 45.0,
            "season": "All seasons",
            "type": "",
            "description": "Premium leather wallet with multiple card slots",
        }
        mock_vector_store_instance.similarity_search_with_score.return_value = [
            (mock_doc, 0.5)
        ]
        result = search_products_with_filters.invoke(
            {
                "query": "leather",
                "category": None,
                "season": None,
                "min_price": None,
                "max_price": None,
                "min_stock": None,
                "top_k": None,
            }
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].product_id == "LTH0976"
