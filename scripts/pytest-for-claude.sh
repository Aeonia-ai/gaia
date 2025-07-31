#!/bin/bash
# 🤖 CLAUDE CODE TEST RUNNER - Use this instead of pytest!
# 
# IMPORTANT FOR FUTURE CLAUDES: When you want to run tests, use THIS script!
# This is THE ONLY WAY to run all tests without hitting Claude Code's 2-minute timeout!
# 
# ✅ DO: 
#   ./scripts/pytest-for-claude.sh                                        # All tests
#   ./scripts/pytest-for-claude.sh tests/integration                      # Integration tests
#   ./scripts/pytest-for-claude.sh tests/e2e                              # Browser tests
#   ./scripts/pytest-for-claude.sh tests/unit                             # Unit tests
#   ./scripts/pytest-for-claude.sh tests/integration/test_v03_api.py      # Single file
#   ./scripts/pytest-for-claude.sh "tests/integration -k test_health"     # Pattern matching
#   ./scripts/pytest-for-claude.sh "--lf"                                 # Last failed only
#   ./scripts/pytest-for-claude.sh "--ff"                                 # Failed first
# 
# ❌ DON'T use these (they will timeout):
#   - pytest
#   - docker compose run test
#   - docker compose exec test pytest
#   - python -m pytest
# 
# This script runs tests asynchronously in Docker to avoid timeouts.

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

LOG_FILE="test-run-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".test-run.pid"

# Check if a test is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${RED}❌ Tests already running (PID: $OLD_PID)${NC}"
        echo "Check status with: ./scripts/check-test-progress.sh"
        exit 1
    fi
fi

# Get all command line arguments (default to all tests)
if [ $# -eq 0 ]; then
    TEST_ARGS="tests/"
else
    TEST_ARGS="$@"
fi

echo -e "${BLUE}🚀 Starting async test run...${NC}"
echo "📝 Logging to: $LOG_FILE"
echo "📂 Test args: $TEST_ARGS"

# Start the test in background
{
    echo "=== Test run started at $(date) ===" 
    echo "Running pytest with parallel execution (-n auto)..."
    echo "Test arguments: $TEST_ARGS"
    
    # Run tests in Docker with parallel execution
    docker compose run --rm test bash -c "PYTHONPATH=/app pytest -v -n auto $TEST_ARGS" 2>&1
    
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "\n${RED}❌ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
    fi
    
    echo "=== Test run completed at $(date) ==="
    
    # Clean up PID file
    rm -f "$PID_FILE"
} > "$LOG_FILE" 2>&1 &

TEST_PID=$!
echo $TEST_PID > "$PID_FILE"

echo -e "${GREEN}✅ Tests started in background (PID: $TEST_PID)${NC}"
echo ""
echo "Monitor progress with:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Check status with:"
echo "  ./scripts/check-test-progress.sh"
echo ""
echo -e "${YELLOW}Note: Tests will run in parallel using all available CPU cores${NC}"