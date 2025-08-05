#!/bin/bash
# Check status of async test run

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PID_FILE=".test-run.pid"
LOG_DIR="logs/tests/pytest"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}No test run in progress${NC}"
    
    # Check for recent log files
    LATEST_LOG=$(ls -t "$LOG_DIR"/test-run-*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo "Latest test log: $LATEST_LOG"
        echo -e "${BLUE}Last 20 lines:${NC}"
        tail -20 "$LATEST_LOG"
        
        # Check if tests passed or failed
        if grep -q "All tests passed" "$LATEST_LOG"; then
            echo -e "\n${GREEN}✅ Last run: PASSED${NC}"
        elif grep -q "Some tests failed" "$LATEST_LOG"; then
            echo -e "\n${RED}❌ Last run: FAILED${NC}"
        fi
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${BLUE}🔄 Tests are running (PID: $PID)${NC}"
    
    # Find the log file
    CURRENT_LOG=$(ls -t "$LOG_DIR"/test-run-*.log 2>/dev/null | head -1)
    if [ -n "$CURRENT_LOG" ]; then
        echo "📝 Log file: $CURRENT_LOG"
        echo ""
        
        # Show test progress
        TOTAL_TESTS=$(grep -c "PASSED\|FAILED\|SKIPPED" "$CURRENT_LOG" 2>/dev/null || echo "0")
        PASSED_TESTS=$(grep -c "PASSED" "$CURRENT_LOG" 2>/dev/null || echo "0")
        FAILED_TESTS=$(grep -c "FAILED" "$CURRENT_LOG" 2>/dev/null || echo "0")
        
        echo -e "${GREEN}Passed: $PASSED_TESTS${NC} | ${RED}Failed: $FAILED_TESTS${NC} | Total: $TOTAL_TESTS"
        echo ""
        echo -e "${BLUE}Recent output:${NC}"
        tail -10 "$CURRENT_LOG"
    fi
else
    echo -e "${RED}Test process (PID: $PID) is no longer running${NC}"
    rm -f "$PID_FILE"
    
    # Show final results from log
    LATEST_LOG=$(ls -t "$LOG_DIR"/test-run-*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo "Log file: $LATEST_LOG"
        echo -e "${BLUE}Final results:${NC}"
        tail -30 "$LATEST_LOG" | grep -E "(passed|failed|error|warnings|Test run completed)"
    fi
fi