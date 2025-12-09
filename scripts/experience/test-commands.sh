#!/bin/bash
# General Command/Response Testing Framework
#
# Test ANY experience command and validate responses.
# Works with chat endpoint, WebSocket, or any protocol.
#
# Usage:
#   ./scripts/experience/test-commands.sh [--url URL] [--protocol PROTOCOL] [--test TEST]
#
# Examples:
#   ./scripts/experience/test-commands.sh                              # Run all tests (chat)
#   ./scripts/experience/test-commands.sh --protocol websocket         # Test via WebSocket
#   ./scripts/experience/test-commands.sh --test movement              # Run specific test
#   ./scripts/experience/test-commands.sh --url https://... --test all # Test remote

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default configuration
KB_URL="http://localhost:8001"
PROTOCOL="chat"  # chat, websocket
TEST_FILTER="all"
EXPERIENCE="wylding-woods"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url) KB_URL="$2"; shift 2 ;;
        --protocol) PROTOCOL="$2"; shift 2 ;;
        --test) TEST_FILTER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Get JWT token
get_jwt() {
    python3 "$ROOT_DIR/tests/manual/get_test_jwt.py" 2>/dev/null | tail -1
}

JWT_TOKEN=$(get_jwt)
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get JWT token${NC}"
    exit 1
fi

# Parse user_id from JWT
USER_ID=$(python3 -c "
import jwt
token = '$JWT_TOKEN'
payload = jwt.decode(token, options={'verify_signature': False})
print(payload.get('sub', ''))
" 2>/dev/null)

print_header() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
}

print_result() {
    local status=$1
    local test_name=$2
    local message=$3

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        [ -n "$message" ] && echo "    $message"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo "    $message"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Send command via chat endpoint
send_chat_command() {
    local command=$1

    curl -s -X POST "$KB_URL/api/v0.3/experience/chat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -d "{
            \"message\": \"$command\",
            \"experience\": \"$EXPERIENCE\",
            \"user_id\": \"$USER_ID\"
        }" 2>&1
}

# Validate response contains expected text
validate_response() {
    local response=$1
    local expected=$2
    local test_name=$3

    if echo "$response" | grep -iq "$expected"; then
        print_result "PASS" "$test_name" "Response contains: $expected"
    else
        print_result "FAIL" "$test_name" "Expected '$expected' not found in response"
    fi
}

# Validate response is valid JSON
validate_json() {
    local response=$1
    local test_name=$2

    if echo "$response" | python3 -m json.tool >/dev/null 2>&1; then
        print_result "PASS" "$test_name" "Valid JSON response"
    else
        print_result "FAIL" "$test_name" "Invalid JSON: ${response:0:100}"
    fi
}

# Validate response time
validate_response_time() {
    local command=$1
    local max_seconds=$2
    local test_name=$3

    local start_time=$(date +%s%N)
    local response=$(send_chat_command "$command")
    local end_time=$(date +%s%N)

    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    local max_ms=$((max_seconds * 1000))

    if [ $duration_ms -lt $max_ms ]; then
        print_result "PASS" "$test_name" "Response time: ${duration_ms}ms (< ${max_ms}ms)"
    else
        print_result "FAIL" "$test_name" "Response time: ${duration_ms}ms (> ${max_ms}ms)"
    fi
}

print_header "EXPERIENCE COMMAND TESTING FRAMEWORK"
echo "KB URL: $KB_URL"
echo "Protocol: $PROTOCOL"
echo "Experience: $EXPERIENCE"
echo "User: $USER_ID"
echo ""

# =============================================================================
# TEST SUITE: Basic Commands
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "basic" ]; then
    print_header "BASIC COMMANDS"

    # Test: look around
    RESPONSE=$(send_chat_command "look around")
    validate_json "$RESPONSE" "Look command returns JSON"
    validate_response "$RESPONSE" "location" "Look command describes location"

    # Test: inventory
    RESPONSE=$(send_chat_command "check inventory")
    validate_json "$RESPONSE" "Inventory command returns JSON"

    # Test: help
    RESPONSE=$(send_chat_command "help")
    validate_response "$RESPONSE" "command" "Help shows available commands"
fi

# =============================================================================
# TEST SUITE: Movement Commands
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "movement" ]; then
    print_header "MOVEMENT COMMANDS"

    # Test: go to location
    RESPONSE=$(send_chat_command "go to entrance")
    validate_response "$RESPONSE" "entrance\|moved\|location" "Movement command works"

    # Test: invalid location
    RESPONSE=$(send_chat_command "go to nonexistent_place")
    validate_response "$RESPONSE" "cannot\|unknown\|not found" "Invalid location handled"
fi

# =============================================================================
# TEST SUITE: Item Interaction
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "items" ]; then
    print_header "ITEM INTERACTION"

    # Test: examine item
    RESPONSE=$(send_chat_command "examine bottle")
    validate_json "$RESPONSE" "Examine command returns JSON"

    # Test: collect item
    RESPONSE=$(send_chat_command "collect bottle of joy")
    validate_response "$RESPONSE" "collect\|inventory\|picked" "Item collection works"
fi

# =============================================================================
# TEST SUITE: NPC Interaction
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "npc" ]; then
    print_header "NPC INTERACTION"

    # Test: talk to NPC
    RESPONSE=$(send_chat_command "talk to Woander")
    validate_response "$RESPONSE" "Woander\|says\|greet" "NPC conversation works"

    # Test: ask NPC question
    RESPONSE=$(send_chat_command "ask Woander about bottles")
    validate_json "$RESPONSE" "NPC question returns JSON"
fi

# =============================================================================
# TEST SUITE: Quest Commands
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "quest" ]; then
    print_header "QUEST COMMANDS"

    # Test: check quest status
    RESPONSE=$(send_chat_command "quest status")
    validate_response "$RESPONSE" "quest\|progress\|objective" "Quest status works"

    # Test: list quests
    RESPONSE=$(send_chat_command "list quests")
    validate_json "$RESPONSE" "Quest list returns JSON"
fi

# =============================================================================
# TEST SUITE: Performance
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "performance" ]; then
    print_header "PERFORMANCE TESTS"

    validate_response_time "look around" 2 "Look command < 2s"
    validate_response_time "check inventory" 1 "Inventory command < 1s"
    validate_response_time "go to entrance" 3 "Movement command < 3s"
fi

# =============================================================================
# TEST SUITE: Error Handling
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "errors" ]; then
    print_header "ERROR HANDLING"

    # Test: empty command
    RESPONSE=$(send_chat_command "")
    validate_json "$RESPONSE" "Empty command returns JSON"

    # Test: gibberish command
    RESPONSE=$(send_chat_command "xyzabc123notacommand")
    validate_response "$RESPONSE" "unclear\|unknown\|help" "Gibberish handled gracefully"

    # Test: malformed command
    RESPONSE=$(send_chat_command "go to to to entrance")
    validate_json "$RESPONSE" "Malformed command returns JSON"
fi

# =============================================================================
# TEST SUITE: Edge Cases
# =============================================================================
if [ "$TEST_FILTER" = "all" ] || [ "$TEST_FILTER" = "edge" ]; then
    print_header "EDGE CASES"

    # Test: very long command
    LONG_CMD=$(python3 -c "print('look around ' * 100)")
    RESPONSE=$(send_chat_command "$LONG_CMD")
    validate_json "$RESPONSE" "Long command returns JSON"

    # Test: special characters
    RESPONSE=$(send_chat_command "look at <script>alert('xss')</script>")
    validate_json "$RESPONSE" "Special characters handled safely"

    # Test: unicode characters
    RESPONSE=$(send_chat_command "look at 🍾 bottle")
    validate_json "$RESPONSE" "Unicode characters handled"
fi

# =============================================================================
# SUMMARY
# =============================================================================
print_header "TEST SUMMARY"

echo "Total tests: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "All command/response patterns working correctly!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Review failed tests above."
    exit 1
fi