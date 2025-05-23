# Tests for Hermes Tools

This directory contains tests for the Hermes system tools.

## Structure

- `fixtures/`: Test fixtures and data helpers
  - `mock_product_catalog.py`: Mock product data for unit testing
  - `test_product_catalog.py`: Test data helpers using products.csv
- `test_catalog_tools.py`: Tests for catalog search and retrieval tools
- `test_order_tools.py`: Tests for order processing and stock management tools
- `test_promotion_tools.py`: Tests for promotion and discount application tools

## Running Tests

You can run the tests in several ways:

### Running All Tests

```bash
# From the project root
poe test

# Or with specific verbosity
poe test -v
```

### Running Specific Test Files

```bash
# Run tests for catalog tools
poe test tests/test_catalog_tools.py

# Run tests for order tools
poe test tests/test_order_tools.py

# Run tests for promotion tools
poe test tests/test_promotion_tools.py
```

### Running Individual Test Classes

```bash
# Run mock data tests for catalog tools
poe test tests/test_catalog_tools.py::TestCatalogTools

# Run test data tests for catalog tools
poe test tests/test_catalog_tools.py::TestCatalogToolsWithTestData

# Run specific test method
poe test tests/test_catalog_tools.py::TestCatalogTools::test_find_product_by_id_valid
```

## Test Structure

Each test file contains two test classes:

1. **Mock Data Tests**: Use synthetic mock data for isolated unit testing
   - Fast execution
   - Predictable data
   - Isolated from external dependencies

2. **Test Data Tests**: Use data from `data/products.csv` and `data/emails.csv`
   - More realistic testing scenarios
   - Test with actual product catalog structure
   - Validate integration with CSV data format

## Test Fixtures

The fixtures directory contains:

- `mock_product_catalog.py`: Provides synthetic product data for unit tests
- `test_product_catalog.py`: Provides helpers to work with test CSV data

## Adding New Tests

To add new tests:

1. Add test methods to the appropriate test class in the relevant test file
2. Use descriptive test method names that clearly indicate what is being tested
3. Include both positive and negative test cases
4. Add fixtures or test data helpers as needed in the `fixtures/` directory

## Test Data vs Integration Tests

- **Test Data**: The CSV files in `data/` directory are for testing the system with realistic but controlled data
- **Integration Tests**: True integration tests would connect to the actual Google Spreadsheet mentioned in the assignment instructions
- Currently, all tests use local test data for fast, reliable testing 