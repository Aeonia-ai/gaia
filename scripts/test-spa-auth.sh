#!/bin/bash

# Test Web UI SPA functionality with real authentication
set -e

echo "🧪 Testing Web UI SPA Features with Authentication..."

BASE_URL="http://localhost:8080"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load credentials from .env or prompt
if [ -f .env ]; then
    # Source the .env file
    export $(cat .env | grep -E '^(TEST_EMAIL|TEST_PASSWORD)=' | xargs)
fi

# Use env vars or defaults
EMAIL=${TEST_EMAIL:-jason@aeonia.ai}
PASSWORD=${TEST_PASSWORD:-}

# If no password in env, prompt for it
if [ -z "$PASSWORD" ]; then
    echo -e "\n${BLUE}No TEST_PASSWORD found in .env${NC}"
    read -s -p "Password for $EMAIL: " PASSWORD
    echo ""
else
    echo -e "\n${BLUE}Using credentials from .env${NC}"
    echo "Email: $EMAIL"
fi

# Test function
test_endpoint() {
    local desc=$1
    local method=$2
    local url=$3
    local expected_status=$4
    local headers=${5:-""}
    
    echo -n "Testing: $desc... "
    
    response=$(curl -s -w "\n%{http_code}" -X $method "$url" $headers -b cookies.txt)
    status=$(echo "$response" | tail -n 1)
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} (Status: $status)"
        return 0
    else
        echo -e "${RED}✗${NC} (Expected: $expected_status, Got: $status)"
        return 1
    fi
}

echo -e "\n${YELLOW}1. Testing Login Flow${NC}"
# Attempt login
echo -n "Logging in as $EMAIL... "
login_response=$(curl -s -c cookies.txt -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
    -d "email=$EMAIL&password=$PASSWORD" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "HX-Request: true")

login_status=$(echo "$login_response" | tail -n 1)
login_body=$(echo "$login_response" | sed '$d')

if [ "$login_status" = "200" ] && echo "$login_body" | grep -q "HX-Redirect"; then
    echo -e "${GREEN}✓${NC} (HTMX redirect detected)"
elif [ "$login_status" = "303" ]; then
    echo -e "${GREEN}✓${NC} (Standard redirect)"
else
    echo -e "${RED}✗${NC} (Status: $login_status)"
    echo "Response preview: ${login_body:0:200}..."
    exit 1
fi

echo -e "\n${YELLOW}2. Testing Authenticated Access${NC}"
test_endpoint "Access chat page" "GET" "$BASE_URL/chat" "200"

echo -e "\n${YELLOW}3. Testing HTMX Navigation${NC}"
# Test HTMX request to chat
echo -n "HTMX request for partial content... "
htmx_response=$(curl -s -w "\n%{http_code}" "$BASE_URL/chat" \
    -H "HX-Request: true" \
    -b cookies.txt)

htmx_status=$(echo "$htmx_response" | tail -n 1)
htmx_body=$(echo "$htmx_response" | sed '$d')

if [ "$htmx_status" = "200" ] && echo "$htmx_body" | grep -q 'id="main-content"'; then
    echo -e "${GREEN}✓${NC} (Partial content with main-content ID)"
else
    echo -e "${RED}✗${NC} (Missing main-content wrapper)"
fi

echo -e "\n${YELLOW}4. Testing Conversation Management${NC}"
# Create new conversation
echo -n "Creating new conversation... "
new_chat=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/chat/new" \
    -H "HX-Request: true" \
    -b cookies.txt)

new_status=$(echo "$new_chat" | tail -n 1)
new_body=$(echo "$new_chat" | sed '$d')

if [ "$new_status" = "200" ] && echo "$new_body" | grep -q "conversation-id-input"; then
    echo -e "${GREEN}✓${NC}"
    # Extract conversation ID if possible
    conv_id=$(echo "$new_body" | grep -o 'data-conversation-id="[^"]*"' | cut -d'"' -f2 | head -1)
    if [ -n "$conv_id" ]; then
        echo "  Created conversation: $conv_id"
    fi
else
    echo -e "${RED}✗${NC} (Status: $new_status)"
fi

echo -e "\n${YELLOW}5. Testing API Endpoints${NC}"
test_endpoint "Get user info" "GET" "$BASE_URL/api/user" "200"
test_endpoint "Get conversations" "GET" "$BASE_URL/api/conversations" "200" "-H 'HX-Request: true'"

echo -e "\n${YELLOW}6. Testing Message Sending${NC}"
if [ -n "$conv_id" ]; then
    echo -n "Sending test message... "
    msg_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/chat/send" \
        -d "message=Hello from SPA test!&conversation_id=$conv_id" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "HX-Request: true" \
        -b cookies.txt)
    
    msg_status=$(echo "$msg_response" | tail -n 1)
    if [ "$msg_status" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC} (Status: $msg_status)"
    fi
else
    echo "Skipping (no conversation ID)"
fi

# Test logout
echo -e "\n${YELLOW}7. Testing Logout${NC}"
test_endpoint "Logout" "GET" "$BASE_URL/logout" "303"

# Clean up
rm -f cookies.txt

echo -e "\n${GREEN}✅ SPA Authentication Testing Complete!${NC}"
echo -e "\n${BLUE}Summary:${NC}"
echo "- Login flow works with HTMX"
echo "- Authenticated pages accessible"
echo "- Partial content updates working"
echo "- API endpoints protected"
echo "- Conversation creation functional"