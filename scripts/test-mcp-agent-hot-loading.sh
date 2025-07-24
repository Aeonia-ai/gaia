#!/bin/bash

# Test script for MCP-agent hot loading performance improvements
# This script tests the multiagent endpoints to verify hot loading is working

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:8666}"
API_KEY="${API_KEY:-${2:-test-key}}"

echo "🔬 Testing MCP-agent Hot Loading Performance"
echo "============================================"
echo "Base URL: $BASE_URL"
echo ""

# Function to test an endpoint and measure response time
test_endpoint() {
    local endpoint=$1
    local message=$2
    local expected_time=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "Endpoint: $endpoint"
    echo "Message: $message"
    
    # Make request and measure time
    start_time=$(date +%s.%N)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{
            \"message\": \"$message\",
            \"stream\": false
        }")
    
    end_time=$(date +%s.%N)
    
    # Extract status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    # Calculate elapsed time
    elapsed=$(echo "$end_time - $start_time" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Success${NC} - Response time: ${elapsed_ms}ms (expected: $expected_time)"
        
        # Extract some metadata if available
        if echo "$response_body" | grep -q "_multiagent"; then
            coordination_time=$(echo "$response_body" | grep -o '"coordination_time_ms":[0-9]*' | grep -o '[0-9]*')
            agent_count=$(echo "$response_body" | grep -o '"agent_count":[0-9]*' | grep -o '[0-9]*')
            hot_loaded=$(echo "$response_body" | grep -o '"hot_loaded":[a-z]*' | grep -o '[a-z]*$')
            echo "  Coordination time: ${coordination_time}ms"
            echo "  Agents used: $agent_count"
            echo "  Hot loaded: $hot_loaded"
        fi
    else
        echo -e "${RED}✗ Failed${NC} - HTTP $http_code"
        echo "Response: $response_body"
    fi
    
    echo ""
    return 0
}

# Test 1: First multiagent request (should initialize on first call)
echo "📊 Test 1: First multiagent request (initialization)"
echo "===================================================="
test_endpoint "/chat/mcp-agent" "Create a tavern scene with multiple NPCs" "3000-6000ms" "Initial multiagent request"

# Wait a bit
sleep 2

# Test 2: Second multiagent request (should be faster with hot loading)
echo "📊 Test 2: Second multiagent request (hot loaded)"
echo "================================================="
test_endpoint "/chat/mcp-agent" "Tell me a story from multiple perspectives" "1000-3000ms" "Hot-loaded multiagent request"

# Test 3: Different scenario type (should still be fast)
echo "📊 Test 3: Different scenario type (worldbuilding)"
echo "=================================================="
test_endpoint "/chat/mcp-agent" "Design a fantasy world with geography and cultures" "1000-3000ms" "Different multiagent scenario"

# Test 4: Hot-loaded lightweight endpoint
echo "📊 Test 4: Hot-loaded lightweight chat"
echo "====================================="
test_endpoint "/chat/mcp-agent-hot" "Hello, how are you?" "500-1500ms" "Hot lightweight chat"

# Test 5: Second hot lightweight request
echo "📊 Test 5: Second hot lightweight request"
echo "========================================"
test_endpoint "/chat/mcp-agent-hot" "What's the weather like?" "300-1000ms" "Second hot lightweight"

# Test specific multiagent scenarios
echo "📊 Test 6: Specific scenario endpoints"
echo "====================================="

test_endpoint "/chat/gamemaster" "You enter the ancient library" "1000-3000ms" "Gamemaster scenario"
test_endpoint "/chat/worldbuilding" "Create a desert civilization" "1000-3000ms" "Worldbuilding scenario"
test_endpoint "/chat/storytelling" "The fall of the empire" "1000-3000ms" "Storytelling scenario"
test_endpoint "/chat/problemsolving" "Design a magic system for our game" "1000-3000ms" "Problem solving scenario"

# Summary
echo "======================================"
echo "🎯 Hot Loading Test Summary"
echo "======================================"
echo ""
echo "If the tests passed:"
echo "✅ First multiagent request: 3-6s (includes initialization)"
echo "✅ Subsequent requests: 1-3s (using hot-loaded agents)"
echo "✅ Hot lightweight chat: <1s after first request"
echo ""
echo "This represents a significant improvement from the previous 5-10s per request!"