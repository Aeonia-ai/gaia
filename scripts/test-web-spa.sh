#!/bin/bash

# Test Web UI SPA functionality
set -e

echo "🧪 Testing Web UI SPA Features..."

BASE_URL="http://localhost:8080"
EMAIL="dev@gaia.local"
PASSWORD="test"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local desc=$1
    local method=$2
    local url=$3
    local data=$4
    local expected_status=$5
    local headers=${6:-""}
    
    echo -n "Testing: $desc... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$url" -d "$data" -H "Content-Type: application/x-www-form-urlencoded" $headers)
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$url" $headers)
    fi
    
    status=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} (Status: $status)"
        return 0
    else
        echo -e "${RED}✗${NC} (Expected: $expected_status, Got: $status)"
        echo "Response: $body"
        return 1
    fi
}

echo -e "\n${YELLOW}1. Testing Authentication Redirects${NC}"
test_endpoint "Root redirects to login" "GET" "$BASE_URL/" "" "303"
test_endpoint "Chat redirects to login" "GET" "$BASE_URL/chat" "" "303"

echo -e "\n${YELLOW}2. Testing Login Flow${NC}"
# For now, skip login test since we need real Supabase credentials
echo "Skipping login test (requires Supabase account)"

# Create a mock session for testing
mkdir -p /tmp/gaia-test
echo "mock-session" > /tmp/gaia-test/session.txt

echo -e "\n${YELLOW}3. Testing Authenticated Access${NC}"
test_endpoint "Access chat with auth" "GET" "$BASE_URL/chat" "" "200" "-b cookies.txt"

echo -e "\n${YELLOW}4. Testing HTMX Navigation${NC}"
# Test HTMX request to chat
htmx_response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/chat" \
    -H "HX-Request: true" \
    -b cookies.txt)

htmx_status=$(echo "$htmx_response" | tail -n 1)
htmx_body=$(echo "$htmx_response" | sed '$d')

echo -n "HTMX request returns partial content... "
if [ "$htmx_status" = "200" ] && echo "$htmx_body" | grep -q "main-content"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -e "\n${YELLOW}5. Testing Conversation Creation${NC}"
new_chat_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/new" \
    -H "HX-Request: true" \
    -b cookies.txt)

new_chat_status=$(echo "$new_chat_response" | tail -n 1)
echo -n "Create new conversation... "
if [ "$new_chat_status" = "200" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC} (Status: $new_chat_status)"
fi

echo -e "\n${YELLOW}6. Testing API Endpoints${NC}"
test_endpoint "Get conversations list" "GET" "$BASE_URL/api/conversations" "" "200" "-b cookies.txt -H 'HX-Request: true'"
test_endpoint "Get user info" "GET" "$BASE_URL/api/user" "" "200" "-b cookies.txt"

# Clean up
rm -f cookies.txt

echo -e "\n${GREEN}✅ SPA Testing Complete!${NC}"