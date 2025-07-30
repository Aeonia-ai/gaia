#!/bin/bash
# Comprehensive test suite aggregating all test functionality

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# Default to local environment
ENVIRONMENT="${1:-local}"
BASE_URL="${BASE_URL:-http://localhost:8666}"

# Set base URL based on environment
case $ENVIRONMENT in
    "dev")
        BASE_URL="https://gaia-gateway-dev.fly.dev"
        API_KEY="${DEV_API_KEY:-$API_KEY}"
        ;;
    "staging")
        BASE_URL="https://gaia-gateway-staging.fly.dev"
        API_KEY="${STAGING_API_KEY:-$API_KEY}"
        ;;
    "prod")
        BASE_URL="https://gaia-gateway-prod.fly.dev"
        API_KEY="${PROD_API_KEY:-$API_KEY}"
        ;;
esac

# Use Jason's API key if available, otherwise default
API_KEY="${API_KEY}"

# Function to print section headers
print_section() {
    echo
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    local expected_status=${5:-200}
    
    echo -e "${YELLOW}► Testing: $description${NC}"
    echo -e "  ${CYAN}$method $endpoint${NC}"
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint" 2>/dev/null)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE \
            -H "X-API-Key: $API_KEY" \
            "$BASE_URL$endpoint" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" -X GET \
            -H "X-API-Key: $API_KEY" \
            "$BASE_URL$endpoint" 2>/dev/null)
    fi
    
    # Split response and status code
    body=$(echo "$response" | sed '$d')
    status=$(echo "$response" | tail -n1)
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "  ${GREEN}✓ Status: $status${NC}"
        if command -v jq &> /dev/null; then
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        else
            echo "$body"
        fi
    else
        echo -e "  ${RED}✗ Status: $status (expected $expected_status)${NC}"
        if command -v jq &> /dev/null; then
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        else
            echo "$body"
        fi
    fi
    echo
}

# Function to check service health
check_service_health() {
    local service=$1
    local url=$2
    
    echo -e "${YELLOW}► Checking $service health...${NC}"
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url/health" -H "X-API-Key: $API_KEY")
    
    if [ "$response" = "200" ]; then
        echo -e "  ${GREEN}✓ $service is healthy${NC}"
        return 0
    else
        echo -e "  ${RED}✗ $service is unhealthy (status: $response)${NC}"
        return 1
    fi
}

# Function to test database connectivity
test_database() {
    echo -e "${YELLOW}► Testing database connectivity...${NC}"
    
    # Check if database is accessible
    if docker compose exec -T db psql -U postgres -d llm_platform -c "SELECT 1" &>/dev/null; then
        echo -e "  ${GREEN}✓ Database is accessible${NC}"
        
        # Check user count
        user_count=$(docker compose exec -T db psql -U postgres -d llm_platform -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | tr -d ' ')
        echo -e "  ${GREEN}✓ Users in database: $user_count${NC}"
        
        # Check Jason's account
        jason_exists=$(docker compose exec -T db psql -U postgres -d llm_platform -t -c "SELECT COUNT(*) FROM users WHERE email='jason@aeonia.ai'" 2>/dev/null | tr -d ' ')
        if [ "$jason_exists" = "1" ]; then
            echo -e "  ${GREEN}✓ Jason's account exists${NC}"
        else
            echo -e "  ${YELLOW}⚠ Jason's account not found${NC}"
        fi
    else
        echo -e "  ${RED}✗ Database is not accessible${NC}"
    fi
}

# Main test execution
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     GAIA PLATFORM COMPREHENSIVE TEST SUITE                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}Environment: $ENVIRONMENT${NC}"
echo -e "${GREEN}Base URL: $BASE_URL${NC}"
echo -e "${GREEN}API Key: ${API_KEY:0:10}...${NC}"

# 1. Infrastructure Health Checks
print_section "1. INFRASTRUCTURE HEALTH CHECKS"

if [ "$ENVIRONMENT" = "local" ]; then
    test_database
    echo
fi

check_service_health "Gateway" "$BASE_URL"
test_endpoint "GET" "/health" "" "Gateway detailed health"

# 2. Authentication Tests
print_section "2. AUTHENTICATION TESTS"

test_endpoint "GET" "/api/v1/providers" "" "List providers (API key auth)"
test_endpoint "GET" "/api/v1/auth/verify" "" "Verify authentication"

# 3. KB Operations Tests
print_section "3. KNOWLEDGE BASE (KB) OPERATIONS"

test_endpoint "GET" "/api/v0.2/kb/health" "" "KB service health"
test_endpoint "GET" "/api/v0.2/kb/git/status" "" "KB Git repository status"
test_endpoint "GET" "/api/v0.2/kb/cache/stats" "" "KB cache statistics"
test_endpoint "POST" "/api/v0.2/kb/read" '{"message": "CLAUDE.md"}' "Read KB file"
test_endpoint "POST" "/api/v0.2/kb/list" '{"message": "/"}' "List KB directory"
test_endpoint "POST" "/api/v0.2/kb/navigate" '{"message": "/"}' "Navigate KB structure"
test_endpoint "POST" "/api/v0.2/kb/search" '{"message": "test"}' "Search KB with RBAC"

# 4. Chat Operations Tests
print_section "4. CHAT OPERATIONS"

test_endpoint "POST" "/api/v1/chat" '{"provider": "openai", "model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}], "stream": false}' "Chat completion (non-streaming)"

# 5. Asset Operations Tests (if enabled)
print_section "5. ASSET OPERATIONS"

test_endpoint "GET" "/api/v1/assets" "" "List assets"

# 6. User Management Tests
print_section "6. USER MANAGEMENT"

# Check if we can create/manage users
if [ "$ENVIRONMENT" = "local" ]; then
    echo -e "${YELLOW}► Checking local user management...${NC}"
    echo -e "  ${CYAN}Users can be created with: docker compose exec db psql -U postgres -d llm_platform${NC}"
    echo -e "  ${CYAN}API keys stored in database with proper hashing${NC}"
fi

# 7. Performance Checks
print_section "7. PERFORMANCE CHECKS"

echo -e "${YELLOW}► Testing response times...${NC}"
start_time=$(date +%s%N)
curl -s -o /dev/null "$BASE_URL/health" -H "X-API-Key: $API_KEY"
end_time=$(date +%s%N)
response_time=$((($end_time - $start_time) / 1000000))
echo -e "  Health check response time: ${response_time}ms"

# Summary
print_section "TEST SUMMARY"

echo -e "${GREEN}Test suite completed!${NC}"
echo
echo -e "${CYAN}Key Features Tested:${NC}"
echo "  • Infrastructure health and connectivity"
echo "  • Authentication (API keys + JWT support)"
echo "  • Knowledge Base operations with RBAC"
echo "  • Chat completions"
echo "  • Asset management"
echo "  • Performance baseline"
echo
echo -e "${CYAN}Next Steps:${NC}"
echo "  • Run './scripts/test-kb-operations.sh' for detailed KB tests"
echo "  • Run './scripts/test.sh --local all' for legacy test suite"
echo "  • Check './scripts/layout-check.sh' for UI layout validation"
echo