from .catalog_tools import (
    find_product_by_id,
    find_product_by_name,
    find_complementary_products,
    search_products_with_filters,
    find_products_for_occasion,
)


class CatalogToolkit:
    @staticmethod
    def get_tools():
        return [
            find_product_by_id,
            find_product_by_name,
            find_complementary_products,
            search_products_with_filters,
            find_products_for_occasion,
        ]


class OrderToolkit:
    @staticmethod
    def get_tools():
        return []


class PromotionsToolkit:
    @staticmethod
    def get_tools():
        return []
