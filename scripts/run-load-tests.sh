#!/bin/bash
#
# Run load tests separately from regular test suite
# These tests consume API quotas and test concurrent behavior
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Running Load Tests ===${NC}"
echo "⚠️  WARNING: Load tests consume API quotas and may trigger rate limits"
echo ""

# Check if we should run with custom configuration
if [ -n "$1" ]; then
    echo "Using custom configuration:"
    echo "  LOAD_TEST_CONCURRENT_REQUESTS=${LOAD_TEST_CONCURRENT_REQUESTS:-5}"
    echo "  LOAD_TEST_CONCURRENT_USERS=${LOAD_TEST_CONCURRENT_USERS:-3}"
    echo "  LOAD_TEST_BURST_SIZE=${LOAD_TEST_BURST_SIZE:-10}"
    echo ""
fi

# Ensure we have required environment variables
if [ -z "$API_KEY" ] && [ -z "$TEST_API_KEY" ]; then
    echo -e "${RED}ERROR: No API key found. Set API_KEY or TEST_API_KEY environment variable${NC}"
    exit 1
fi

# Run load tests explicitly
echo "Running load tests..."
./scripts/pytest-for-claude.sh tests/load/ -v -m load --no-header

echo ""
echo -e "${GREEN}Load tests completed!${NC}"
echo ""
echo "To run with different parameters:"
echo "  LOAD_TEST_CONCURRENT_REQUESTS=10 ./scripts/run-load-tests.sh"
echo "  LOAD_TEST_BURST_SIZE=20 ./scripts/run-load-tests.sh"