#!/bin/bash
# Test KB operations with various endpoints

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    # Remove comments and empty lines, then export
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# Configuration
API_KEY="${JASON_API_KEY:-${API_KEY}}"
BASE_URL="${BASE_URL:-http://localhost:8666}"

if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: No API key found. Please set JASON_API_KEY or API_KEY in .env file${NC}"
    exit 1
fi

echo -e "${BLUE}=== KB Operations Test Suite ===${NC}"
echo -e "Using API Key: ${API_KEY:0:10}..."
echo -e "Base URL: $BASE_URL"
echo

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo -e "Endpoint: $method $endpoint"
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X GET \
            -H "X-API-Key: $API_KEY" \
            "$BASE_URL$endpoint")
    fi
    
    # Split response and status code
    body=$(echo "$response" | sed '$d')
    status=$(echo "$response" | tail -n1)
    
    if [ "$status" = "200" ]; then
        echo -e "${GREEN}✓ Status: $status${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ Status: $status${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    fi
    echo
}

# Test 1: KB Git Status
test_endpoint "GET" "/api/v0.2/kb/git/status" "" "KB Git Repository Status"

# Test 2: KB Cache Stats
test_endpoint "GET" "/api/v0.2/kb/cache/stats" "" "KB Cache Statistics"

# Test 3: KB Read a file
test_endpoint "POST" "/api/v0.2/kb/read" '{"message": "CLAUDE.md"}' "Read CLAUDE.md file"

# Test 4: KB List directory
test_endpoint "POST" "/api/v0.2/kb/list" '{"message": "/"}' "List root KB directory"

# Test 5: KB Navigate
test_endpoint "POST" "/api/v0.2/kb/navigate" '{"message": "/"}' "Navigate KB index"

# Test 6: KB Context
test_endpoint "POST" "/api/v0.2/kb/context" '{"message": "gaia"}' "Load Gaia context"

# Test 7: KB Search with RBAC
test_endpoint "POST" "/api/v0.2/kb/search" '{"message": "test search"}' "KB Search with RBAC permissions"

# Test 8: Direct KB health check
test_endpoint "GET" "/api/v0.2/kb/health" "" "KB Service Health (if available)"

echo -e "${BLUE}=== Test Summary ===${NC}"
echo "Tests completed. Check output above for any errors."