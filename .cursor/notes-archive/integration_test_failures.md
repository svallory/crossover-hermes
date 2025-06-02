# Integration Test Failures

All previously listed integration test failures have been resolved.

---

**Successfully Resolved Issues (Recap from this session):**

*   **`tests/integration/test_offers_integration.py::TestOffersIntegration::test_single_item_bundle_inquiry`**
    *   Original Status: FAILED (New)
    *   Original Error: `RuntimeError: Stockkeeper: Error during candidate provision for email E035` (due to `ValueError: "Kids' Clothing" is not a valid ProductCategory`)
    *   Fix: Added direct, robust category string normalization (handling typographic apostrophes and ensuring correct mapping for "Kids' Clothing") within `hermes/tools/catalog_tools.py::_create_product_from_row` as a safeguard, supplementing the primary normalization in `hermes/data/load_data.py`.
    *   Current Status: PASSED

*   **`tests/integration/test_stockkeeper_integration.py::TestStockkeeperIntegration::test_nonexistent_product_id`**
    *   Original Status: FAILED (Regression)
    *   Original Error: `AssertionError: assert 1 == 0` (Stockkeeper found candidates for a non-existent ID).
    *   Fix: Corrected logic in `hermes/tools/catalog_tools.py::resolve_product_mention` to ensure it immediately returns `ProductNotFound` if an explicit `product_id` is provided but not found by `find_product_by_id`, without falling back to name-based searches. Updated the corresponding unit test `tests/unit/test_resolve_product_mention.py::TestResolveProductMention::test_resolve_product_mention_nonexistent` to align with this corrected behavior.
    *   Current Status: PASSED

*   **`tests/integration/test_advisor_integration.py::TestAdvisorIntegration::test_bag_comparison_inquiry_e003`** (Resolved earlier in session)
    *   Original Status: MARKED XFAIL
    *   New Status: PASSED

*   **`tests/integration/test_offers_integration.py::TestOffersIntegration::test_no_promotion_for_standard_order`** (Resolved earlier in session)
    *   Original Status: FAILED (Persistent)
    *   New Status: PASSED

**Other Previously Resolved Issues (from initial file state):**

*   **`tests/integration/test_composer_integration.py::TestComposerIntegration::test_composer_order_confirmation_e001`**
    *   Original Error: `pydantic_core._pydantic_core.ValidationError: 1 validation error for OrderLine`
    *   Status: PASSED (Fix: Ensured `OrderLine` in test helpers receives both `name` and `description` fields).

*   **`tests/integration/test_fulfiller_promotions.py::TestFulfillerPromotionDetection::test_canvas_beach_bag_bogo_promotion`**
    *   Original Error: `assert 0 == 1` (due to product not being identified correctly by Fulfiller)
    *   Status: PASSED (Fix: Updated `StockkeeperOutput` mock in the test to use the correct `candidate_products_for_mention` structure, ensuring the Fulfiller agent receives the product context correctly).