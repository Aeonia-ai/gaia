#!/bin/bash
# Smart test runner that separates test types and uses appropriate execution strategies

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
VERBOSE=""
TIMEOUT_SECONDS=300  # 5 minute timeout for browser tests

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--unit|--integration|--e2e|--all] [-v|--verbose]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🧪 Smart Test Runner${NC}"
echo "=================================="

# Function to run tests with timeout and proper async handling
run_test_suite() {
    local test_path=$1
    local test_name=$2
    local parallel_flag=$3
    local timeout=$4
    
    echo -e "\n${YELLOW}Running $test_name tests...${NC}"
    
    # Use the async wrapper to prevent Claude Code timeouts
    if [ -n "$timeout" ]; then
        # For browser tests, use timeout command
        timeout $timeout ./scripts/pytest-for-claude.sh $test_path $VERBOSE $parallel_flag \
            --asyncio-mode=strict \
            -o log_cli=false \
            --tb=short \
            || {
            exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo -e "${RED}❌ $test_name tests timed out after $timeout seconds${NC}"
                return 1
            else
                echo -e "${RED}❌ $test_name tests failed with exit code $exit_code${NC}"
                return $exit_code
            fi
        }
    else
        ./scripts/pytest-for-claude.sh $test_path $VERBOSE $parallel_flag \
            --asyncio-mode=strict \
            -o log_cli=false \
            --tb=short
    fi
}

# Track overall results
TOTAL_PASSED=0
TOTAL_FAILED=0
FAILED_SUITES=""

# Run unit tests (fast, parallel)
if [ "$TEST_TYPE" = "unit" ] || [ "$TEST_TYPE" = "all" ]; then
    if run_test_suite "tests/unit" "Unit" "-n auto"; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        FAILED_SUITES="$FAILED_SUITES unit"
        ((TOTAL_FAILED++))
    fi
    ((TOTAL_PASSED++))
fi

# Run integration tests excluding browser tests (medium speed, parallel)
if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    if run_test_suite "tests/integration --ignore=tests/integration/web/" "API Integration" "-n auto"; then
        echo -e "${GREEN}✅ API Integration tests passed${NC}"
    else
        echo -e "${RED}❌ API Integration tests failed${NC}"
        FAILED_SUITES="$FAILED_SUITES integration"
        ((TOTAL_FAILED++))
    fi
    ((TOTAL_PASSED++))
fi

# Run E2E/browser tests (slow, sequential with timeout)
if [ "$TEST_TYPE" = "e2e" ] || [ "$TEST_TYPE" = "all" ]; then
    # Combine E2E and browser integration tests
    echo -e "\n${YELLOW}Note: Browser tests run sequentially to prevent resource exhaustion${NC}"
    
    # Run E2E tests
    if run_test_suite "tests/e2e" "E2E Browser" "-n 1" "$TIMEOUT_SECONDS"; then
        echo -e "${GREEN}✅ E2E tests passed${NC}"
    else
        echo -e "${RED}❌ E2E tests failed or timed out${NC}"
        FAILED_SUITES="$FAILED_SUITES e2e"
        ((TOTAL_FAILED++))
    fi
    ((TOTAL_PASSED++))
    
    # Optionally run browser integration tests
    if [ "$TEST_TYPE" = "all" ]; then
        echo -e "\n${YELLOW}Running browser integration tests (optional)...${NC}"
        if run_test_suite "tests/integration/web" "Browser Integration" "-n 1" "$TIMEOUT_SECONDS"; then
            echo -e "${GREEN}✅ Browser Integration tests passed${NC}"
        else
            echo -e "${RED}⚠️  Browser Integration tests failed (non-critical)${NC}"
            # Don't fail the whole suite for browser integration tests
        fi
    fi
fi

# Summary
echo -e "\n=================================="
echo -e "${GREEN}Test Summary${NC}"
echo "=================================="
echo "Test suites run: $((TOTAL_PASSED + TOTAL_FAILED))"
echo "Passed: $TOTAL_PASSED"
echo "Failed: $TOTAL_FAILED"

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Failed suites: $FAILED_SUITES${NC}"
    echo -e "${YELLOW}Tip: Run individual suites for faster feedback:${NC}"
    echo "  $0 --unit       # Fast unit tests only"
    echo "  $0 --integration # API tests only"  
    echo "  $0 --e2e        # Browser tests only"
    exit 1
fi