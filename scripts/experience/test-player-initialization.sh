#!/bin/bash
# Test Player Initialization Pattern
#
# Validates ensure_player_initialized() is called at all entry points.
# Prevents regression of "Player view not found" bug.
#
# Usage: ./scripts/experience/test-player-initialization.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
}

check_pattern() {
    local file=$1
    local pattern=$2
    local description=$3

    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $description"
        echo "    File: $file"
        echo "    Missing: $pattern"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

print_header "PLAYER INITIALIZATION PATTERN VALIDATION"

echo "Checking that ensure_player_initialized() is called at all entry points..."
echo ""

# Test 1: WebSocket handler calls ensure_player_initialized
check_pattern \
    "$ROOT_DIR/app/services/kb/websocket_experience.py" \
    "ensure_player_initialized" \
    "WebSocket handler calls ensure_player_initialized()"

# Test 2: Chat endpoint calls ensure_player_initialized
check_pattern \
    "$ROOT_DIR/app/services/kb/experience_endpoints.py" \
    "ensure_player_initialized" \
    "Chat endpoint calls ensure_player_initialized()"

# Test 3: ensure_player_initialized method exists
check_pattern \
    "$ROOT_DIR/app/services/kb/unified_state_manager.py" \
    "async def ensure_player_initialized" \
    "ensure_player_initialized() method exists in UnifiedStateManager"

# Test 4: get_player_view assumes file exists (no auto-bootstrap)
check_pattern \
    "$ROOT_DIR/app/services/kb/unified_state_manager.py" \
    "Call ensure_player_initialized() first" \
    "get_player_view() has clear error message about initialization"

# Test 5: update_player_view assumes file exists
if grep -q "async def update_player_view" "$ROOT_DIR/app/services/kb/unified_state_manager.py"; then
    if grep -A 10 "async def update_player_view" "$ROOT_DIR/app/services/kb/unified_state_manager.py" | grep -q "ASSUMES.*ensure_player_initialized"; then
        TESTS_RUN=$((TESTS_RUN + 1))
        echo -e "${GREEN}✅ PASS${NC}: update_player_view() documents initialization assumption"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        TESTS_RUN=$((TESTS_RUN + 1))
        echo -e "${YELLOW}⚠️  WARN${NC}: update_player_view() should document ASSUMES in docstring"
    fi
fi

print_header "SUMMARY"

echo "Total tests: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL PATTERN CHECKS PASSED${NC}"
    echo ""
    echo "Player initialization pattern is correctly implemented:"
    echo "  ✓ ensure_player_initialized() exists in UnifiedStateManager"
    echo "  ✓ WebSocket handler calls it before state operations"
    echo "  ✓ Chat endpoint calls it before state operations"
    echo "  ✓ State methods document initialization requirement"
    echo ""
    echo "This prevents the 'Player view not found' bug from recurring."
    exit 0
else
    echo -e "${RED}❌ PATTERN VALIDATION FAILED${NC}"
    echo ""
    echo "Fix the issues above to prevent regression."
    echo ""
    echo "Pattern requirements:"
    echo "  1. Add ensure_player_initialized() to UnifiedStateManager"
    echo "  2. Call it at all entry points (WebSocket, chat, etc.)"
    echo "  3. Remove auto-bootstrap from get_player_view()"
    echo "  4. Document ASSUMES in state method docstrings"
    exit 1
fi
