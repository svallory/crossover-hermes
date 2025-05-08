#!/bin/bash

# Run Hermes tests with proper configuration
# Usage: ./run_tests.sh [test_pattern]
#
# Examples: 
#   ./run_tests.sh               # Run all tests
#   ./run_tests.sh classifier    # Run only classifier tests
#   ./run_tests.sh integration   # Run only integration tests

# Default values
API_KEY=${OPENAI_API_KEY:-""}
BASE_URL=${OPENAI_BASE_URL:-"https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/"}
TEST_PATTERN=$1

# Ensure we're in the right directory
cd "$(dirname "$0")"
ROOT_DIR="$(cd .. && pwd)"

echo "Using project root: $ROOT_DIR"

# Check if OpenAI API key is provided
if [ -z "$API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable not set"
    echo "Using default test key. Some tests might fail if API requests are made."
else
    echo "Using provided OpenAI API key"
fi

# Export variables to be used by tests
export OPENAI_API_KEY="$API_KEY"
export OPENAI_BASE_URL="$BASE_URL"

# Run the tests using Poetry
cd "$ROOT_DIR"

if [ -z "$TEST_PATTERN" ]; then
    # Run all tests
    echo "Running all tests"
    poetry run python -m unittest discover -s tests -p "test_*.py" -v
else
    # Run specific test file
    echo "Running tests matching pattern: $TEST_PATTERN"
    if [[ "$TEST_PATTERN" == test_* ]]; then
        poetry run python -m unittest "tests/$TEST_PATTERN"
    else
        poetry run python -m unittest "tests/test_$TEST_PATTERN.py"
    fi
fi

# Return status
exit $? 