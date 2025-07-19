#!/bin/bash
# Test KB editing functionality

# Default to local development
BASE_URL="http://localhost:8666"
ENVIRONMENT="local"

# Parse command line arguments for environment
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            BASE_URL="http://localhost:8666"
            ENVIRONMENT="local"
            shift
            ;;
        --staging)
            BASE_URL="https://gaia-gateway-staging.fly.dev"
            ENVIRONMENT="staging"
            shift
            ;;
        --prod)
            BASE_URL="https://gaia-gateway-prod.fly.dev"
            ENVIRONMENT="production"
            shift
            ;;
        --url)
            BASE_URL="$2"
            ENVIRONMENT="custom"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Load API key from .env file
if [ -f ".env" ]; then
    export $(grep -E '^API_KEY=' .env | head -1 | xargs)
fi

# Fallback API key if not in .env
API_KEY="${API_KEY:-FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

function print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

function test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local description=$4
    
    print_header "$description"
    
    local response
    local status_code
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}${path}" \
            -H "x-api-key: ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    # Extract status code (last line) and body (everything else)
    status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
        echo -e "${GREEN}✅ Status: $status_code${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Status: $status_code${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
    fi
    
    echo ""
}

echo -e "${YELLOW}Testing KB Editing Functionality${NC}"
echo "================================"
echo -e "${GREEN}🌍 Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}🔗 Base URL: ${BASE_URL}${NC}"
echo -e "${GREEN}🔑 API Key: ${API_KEY:0:8}...${NC}"

# Test 1: Check git status
test_endpoint "GET" "/api/v0.2/kb/git/status" "" "Check Git status"

# Test 2: Write a new test file
WRITE_DATA='{
  "path": "tests/kb-edit-test.md",
  "content": "# KB Edit Test\n\nThis is a test file created by the KB editing API.\n\n## Test Content\n\n- Created at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'\n- API test successful\n\n## Tags\n\n#test #api #kb-edit",
  "message": "Test KB write endpoint",
  "validate_content": true
}'
test_endpoint "POST" "/api/v0.2/kb/write" "$WRITE_DATA" "Write new test file"

# Test 3: Read the file back
READ_DATA='{
  "message": "tests/kb-edit-test.md"
}'
test_endpoint "POST" "/api/v0.2/kb/read" "$READ_DATA" "Read file back"

# Test 4: Update the file
UPDATE_DATA='{
  "path": "tests/kb-edit-test.md",
  "content": "# KB Edit Test (Updated)\n\nThis is a test file created by the KB editing API.\n\n## Test Content\n\n- Created at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'\n- Updated at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'\n- API test successful\n- Update test successful\n\n## Tags\n\n#test #api #kb-edit #updated",
  "message": "Update KB test file",
  "validate_content": true
}'
test_endpoint "POST" "/api/v0.2/kb/write" "$UPDATE_DATA" "Update existing file"

# Test 5: Move the file
MOVE_DATA='{
  "old_path": "tests/kb-edit-test.md",
  "new_path": "tests/kb-edit-test-moved.md",
  "message": "Test KB move endpoint"
}'
test_endpoint "POST" "/api/v0.2/kb/move" "$MOVE_DATA" "Move file"

# Test 6: Check git status again
test_endpoint "GET" "/api/v0.2/kb/git/status" "" "Check Git status after changes"

# Test 7: Delete the test file
DELETE_DATA='{
  "path": "tests/kb-edit-test-moved.md",
  "message": "Clean up KB test file"
}'
test_endpoint "DELETE" "/api/v0.2/kb/delete" "$DELETE_DATA" "Delete test file"

# Test 8: Final git status
test_endpoint "GET" "/api/v0.2/kb/git/status" "" "Final Git status"

echo -e "\n${GREEN}KB Edit Testing Complete!${NC}"
echo "========================="
echo -e "${YELLOW}Note:${NC} Check the KB repository for Git history to verify commits were created."