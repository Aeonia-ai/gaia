#!/bin/bash

# Performance test for intelligent routing with ultra-fast path
# Tests the three-tier routing: ultra-fast, fast, and orchestrated

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:8666}"
API_KEY="${API_KEY:-${2:-test-key}}"

echo "⚡ Testing Intelligent Routing Performance"
echo "========================================"
echo "Base URL: $BASE_URL"
echo ""

# Arrays to store timing data
declare -a ultra_fast_times=()
declare -a fast_times=()
declare -a moderate_times=()
declare -a complex_times=()

# Function to test and collect timing data
test_message() {
    local message=$1
    local category=$2
    
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
    
    # Extract status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    # Calculate elapsed time
    elapsed=$(echo "$end_time - $start_time" | bc)
    elapsed_ms=$(echo "$elapsed * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ]; then
        # Extract routing info
        if echo "$response_body" | grep -q "_intelligent_routing"; then
            endpoint_used=$(echo "$response_body" | grep -o '"endpoint_used":"[^"]*"' | cut -d'"' -f4)
            is_complete=$(echo "$response_body" | grep -o '"is_complete":[a-z]*' | grep -o '[a-z]*$' || echo "false")
            
            # Determine actual path used
            if [ "$endpoint_used" = "DIRECT_RESPONSE" ] || [ "$is_complete" = "true" ]; then
                actual_path="ULTRA-FAST"
                ultra_fast_times+=($elapsed_ms)
            elif [ "$endpoint_used" = "/chat/direct" ]; then
                actual_path="FAST"
                fast_times+=($elapsed_ms)
            elif [ "$endpoint_used" = "/chat/mcp-agent-hot" ]; then
                actual_path="MODERATE"
                moderate_times+=($elapsed_ms)
            else
                actual_path="COMPLEX"
                complex_times+=($elapsed_ms)
            fi
            
            # Color code based on performance
            if [ $elapsed_ms -lt 500 ]; then
                time_color=$GREEN
            elif [ $elapsed_ms -lt 1500 ]; then
                time_color=$YELLOW
            elif [ $elapsed_ms -lt 3000 ]; then
                time_color=$BLUE
            else
                time_color=$RED
            fi
            
            echo -e "[$category] ${time_color}${elapsed_ms}ms${NC} - $actual_path - \"$message\""
        else
            echo -e "[$category] ${elapsed_ms}ms - NO ROUTING INFO - \"$message\""
        fi
    else
        echo -e "${RED}[$category] FAILED${NC} - \"$message\""
    fi
}

# Test ultra-simple messages (should get direct response without routing)
echo -e "${CYAN}Testing Ultra-Simple Messages (Direct Response Expected)${NC}"
echo "========================================================"
test_message "Hello!" "ULTRA"
test_message "Hi there" "ULTRA"
test_message "How are you?" "ULTRA"
test_message "What's your name?" "ULTRA"
test_message "Thanks!" "ULTRA"
test_message "Good morning" "ULTRA"
test_message "Bye" "ULTRA"
echo ""

# Test simple messages (should route to /chat/direct)
echo -e "${CYAN}Testing Simple Messages (Fast Path Expected)${NC}"
echo "==========================================="
test_message "What's the capital of France?" "SIMPLE"
test_message "Explain quantum computing in simple terms" "SIMPLE"
test_message "What are the benefits of exercise?" "SIMPLE"
test_message "Tell me about the history of computers" "SIMPLE"
test_message "What's the difference between HTTP and HTTPS?" "SIMPLE"
echo ""

# Test moderate messages (should route to /chat/mcp-agent-hot)
echo -e "${CYAN}Testing Moderate Messages (Tool Path Expected)${NC}"
echo "============================================="
test_message "Search for the latest news about AI developments" "MODERATE"
test_message "Calculate the area of a circle with radius 15" "MODERATE"
test_message "Find information about Python decorators and explain with examples" "MODERATE"
test_message "Help me debug this code: def factorial(n): return n * factorial(n-1)" "MODERATE"
echo ""

# Test complex messages (should route to /chat/mcp-agent)
echo -e "${CYAN}Testing Complex Messages (Orchestrated Path Expected)${NC}"
echo "==================================================="
test_message "Create a detailed fantasy world with multiple kingdoms, each with unique cultures" "COMPLEX"
test_message "Tell the story of a historic event from three different perspectives" "COMPLEX"
test_message "Design a complete game system with balanced mechanics and progression" "COMPLEX"
test_message "Analyze this business problem from technical, financial, and user perspectives" "COMPLEX"
echo ""

# Calculate and display statistics
calculate_average() {
    local -n arr=$1
    local sum=0
    local count=${#arr[@]}
    
    if [ $count -eq 0 ]; then
        echo "0"
        return
    fi
    
    for time in "${arr[@]}"; do
        sum=$((sum + time))
    done
    
    echo $((sum / count))
}

echo "======================================"
echo "📊 Performance Summary"
echo "======================================"
echo ""

if [ ${#ultra_fast_times[@]} -gt 0 ]; then
    avg_ultra=$(calculate_average ultra_fast_times)
    echo -e "${GREEN}⚡ Ultra-Fast Path:${NC} ${#ultra_fast_times[@]} requests, avg: ${avg_ultra}ms"
fi

if [ ${#fast_times[@]} -gt 0 ]; then
    avg_fast=$(calculate_average fast_times)
    echo -e "${YELLOW}🏃 Fast Path:${NC} ${#fast_times[@]} requests, avg: ${avg_fast}ms"
fi

if [ ${#moderate_times[@]} -gt 0 ]; then
    avg_moderate=$(calculate_average moderate_times)
    echo -e "${BLUE}🔧 Moderate Path:${NC} ${#moderate_times[@]} requests, avg: ${avg_moderate}ms"
fi

if [ ${#complex_times[@]} -gt 0 ]; then
    avg_complex=$(calculate_average complex_times)
    echo -e "${CYAN}🧠 Complex Path:${NC} ${#complex_times[@]} requests, avg: ${avg_complex}ms"
fi

echo ""
echo "Expected Performance Targets:"
echo "✅ Ultra-Fast: <500ms (direct response, no routing)"
echo "✅ Fast: ~1000ms (simple routing + direct LLM)"
echo "✅ Moderate: ~2000ms (routing + hot MCP agent)"
echo "✅ Complex: ~3000ms (routing + orchestration)"