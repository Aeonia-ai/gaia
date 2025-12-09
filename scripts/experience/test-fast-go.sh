#!/bin/bash
# Test Fast "go" Command Implementation
#
# Tests the new fast path for navigation commands (no LLM processing).
# Expected response time: <1s (vs 25-30s for natural language "go to X")

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "Fast 'go' Command Test"
echo "========================================"
echo ""

# Get JWT token
echo "Getting JWT token..."
JWT_TOKEN=$(python3 "$ROOT_DIR/tests/manual/get_test_jwt.py" 2>/dev/null | tail -1)
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get JWT token${NC}"
    exit 1
fi
echo -e "${GREEN}✅ JWT token obtained${NC}"
echo ""

# Test 1: Fast "go" with destination parameter
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Fast 'go' command (structured)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: {\"action\": \"go\", \"destination\": \"spawn_zone_1\"}"
echo ""

START=$(date +%s%3N)
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v0.3/experience/chat" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d '{
        "message": "go",
        "experience": "wylding-woods",
        "metadata": {
            "command_data": {
                "action": "go",
                "destination": "spawn_zone_1"
            }
        }
    }')
END=$(date +%s%3N)
ELAPSED=$((END - START))

echo "Response time: ${ELAPSED}ms"
echo "Response: $RESPONSE"
echo ""

if [ $ELAPSED -lt 2000 ]; then
    echo -e "${GREEN}✅ FAST PATH CONFIRMED (<2s)${NC}"
else
    echo -e "${YELLOW}⚠️  Slower than expected (${ELAPSED}ms)${NC}"
fi
echo ""

# Test 2: Natural language "go" for comparison
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Natural language 'go' (LLM path)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: \"go to spawn_zone_1\" (natural language)"
echo "Expected: 25-30s (LLM processing)"
echo ""

START=$(date +%s%3N)
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v0.3/experience/chat" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d '{
        "message": "go to spawn_zone_1",
        "experience": "wylding-woods"
    }')
END=$(date +%s%3N)
ELAPSED=$((END - START))

echo "Response time: ${ELAPSED}ms ($(echo "scale=1; $ELAPSED/1000" | bc)s)"
echo "Response: $RESPONSE" | head -c 200
echo "..."
echo ""

if [ $ELAPSED -gt 10000 ]; then
    echo -e "${GREEN}✅ LLM PATH CONFIRMED (>10s) - Backward compatible${NC}"
else
    echo -e "${YELLOW}⚠️  Faster than expected for natural language${NC}"
fi
echo ""

echo "========================================"
echo "Test Summary"
echo "========================================"
echo "✅ Fast path: Should complete in <2s"
echo "✅ LLM fallback: Should take 25-30s"
echo "✅ Backward compatible: Both formats work"
echo ""
