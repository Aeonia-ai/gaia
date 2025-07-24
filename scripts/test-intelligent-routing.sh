#!/bin/bash

# Test script for intelligent chat routing
# This script tests various message types to verify routing decisions

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:8666}"
API_KEY="${API_KEY:-${2:-test-key}}"

echo "🧠 Testing Intelligent Chat Routing"
echo "==================================="
echo "Base URL: $BASE_URL"
echo ""

# Function to test intelligent routing
test_intelligent_routing() {
    local message=$1
    local expected_complexity=$2
    local expected_endpoint=$3
    local description=$4
    
    echo -e "${YELLOW}Test: $description${NC}"
    echo "Message: \"$message\""
    echo "Expected: $expected_complexity → $expected_endpoint"
    
    # Make request and measure time
    start_time=$(date +%s.%N)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/intelligent" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{
            \"message\": \"$message\",
            \"stream\": false
        }")
    
    end_time=$(date +%s.%N)
    
    # Extract status code and response
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    # Calculate elapsed time
    elapsed=$(echo "$end_time - $start_time" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ]; then
        # Extract routing metadata
        if echo "$response_body" | grep -q "_intelligent_routing"; then
            complexity=$(echo "$response_body" | grep -o '"complexity":"[^"]*"' | cut -d'"' -f4)
            endpoint_used=$(echo "$response_body" | grep -o '"endpoint_used":"[^"]*"' | cut -d'"' -f4)
            classification_time=$(echo "$response_body" | grep -o '"classification_time_ms":[0-9]*' | grep -o '[0-9]*')
            total_time=$(echo "$response_body" | grep -o '"total_time_ms":[0-9]*' | grep -o '[0-9]*')
            reasoning=$(echo "$response_body" | grep -o '"reasoning":"[^"]*"' | cut -d'"' -f4)
            
            # Check if routing matches expected
            if [ "$complexity" = "$expected_complexity" ]; then
                echo -e "${GREEN}✓ Correct routing${NC}"
            else
                echo -e "${RED}✗ Incorrect routing${NC} (got: $complexity)"
            fi
            
            echo "  Complexity: $complexity"
            echo "  Endpoint: $endpoint_used"
            echo "  Classification time: ${classification_time}ms"
            echo "  Total time: ${total_time}ms"
            echo "  Reasoning: $reasoning"
        else
            echo -e "${GREEN}✓ Success${NC} - Response time: ${elapsed_ms}ms"
            echo -e "${RED}  Warning: No routing metadata found${NC}"
        fi
    else
        echo -e "${RED}✗ Failed${NC} - HTTP $http_code"
        echo "Response: $response_body"
    fi
    
    echo ""
    return 0
}

# Test various message types
echo "📊 Testing Simple Messages (should route to /chat/direct)"
echo "========================================================"
test_intelligent_routing "Hello!" "simple" "/chat/direct" "Basic greeting"
test_intelligent_routing "How are you today?" "simple" "/chat/direct" "Simple question"
test_intelligent_routing "What's your name?" "simple" "/chat/direct" "Basic inquiry"
test_intelligent_routing "Thanks for your help" "simple" "/chat/direct" "Acknowledgment"
test_intelligent_routing "Tell me a joke" "simple" "/chat/direct" "Simple request"

echo "📊 Testing Moderate Messages (should route to /chat/mcp-agent-hot)"
echo "================================================================="
test_intelligent_routing "Search for information about quantum computing" "moderate" "/chat/mcp-agent-hot" "Search request"
test_intelligent_routing "Calculate the compound interest on \$10,000 at 5% for 10 years" "moderate" "/chat/mcp-agent-hot" "Calculation"
test_intelligent_routing "Analyze this code and find potential bugs" "moderate" "/chat/mcp-agent-hot" "Technical analysis"
test_intelligent_routing "Help me debug this Python function" "moderate" "/chat/mcp-agent-hot" "Programming help"

echo "📊 Testing Complex Messages (should route to /chat/mcp-agent)"
echo "==========================================================="
test_intelligent_routing "Create a fantasy world with multiple civilizations, each with unique cultures and histories" "complex" "/chat/mcp-agent" "Worldbuilding"
test_intelligent_routing "I need multiple perspectives on the ethical implications of AI" "complex" "/chat/mcp-agent" "Multi-perspective"
test_intelligent_routing "Design a complete game system with mechanics, balance, and player progression" "complex" "/chat/mcp-agent" "Complex design"
test_intelligent_routing "Tell the story of a battle from the perspectives of a soldier, general, and civilian" "complex" "/chat/mcp-agent" "Multi-narrator story"

# Get routing metrics
echo "📊 Getting Routing Metrics"
echo "========================="
metrics_response=$(curl -s -X GET "$BASE_URL/chat/intelligent/metrics" \
    -H "X-API-Key: $API_KEY")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Metrics retrieved${NC}"
    echo "$metrics_response" | python3 -m json.tool
else
    echo -e "${RED}✗ Failed to get metrics${NC}"
fi

# Summary
echo ""
echo "======================================"
echo "🎯 Intelligent Routing Test Summary"
echo "======================================"
echo ""
echo "Expected behavior:"
echo "✅ Simple messages → /chat/direct (~1s total)"
echo "✅ Moderate messages → /chat/mcp-agent-hot (~2-3s total)"
echo "✅ Complex messages → /chat/mcp-agent (~3-5s total)"
echo "✅ Classification overhead: ~200ms"
echo ""
echo "The routing should correctly identify message complexity and"
echo "send it to the optimal endpoint for best performance."