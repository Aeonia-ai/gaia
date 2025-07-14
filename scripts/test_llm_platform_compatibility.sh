#!/bin/bash
# LLM Platform Compatibility Test Suite
# Tests Gaia Platform against LLM Platform API expectations

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
BASE_URL="https://gaia-gateway-dev.fly.dev"
API_KEY=""
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to display usage
usage() {
    echo "Usage: $0 [--url <base_url>] [--api-key <key>] [--no-auth]"
    echo "  --url         Base URL (default: https://gaia-gateway-dev.fly.dev)"
    echo "  --api-key     API key for authentication"
    echo "  --no-auth     Skip API key authentication"
    echo ""
    echo "Examples:"
    echo "  $0                                      # Test dev with no auth"
    echo "  $0 --url https://gaia-gateway-staging.fly.dev"
    echo "  $0 --api-key your-key-here"
    exit 1
}

# Parse command line arguments
USE_AUTH=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --no-auth)
            USE_AUTH=false
            shift
            ;;
        *)
            usage
            ;;
    esac
done

# Remove trailing slash from URL
BASE_URL=${BASE_URL%/}

# Set up authentication headers
if [[ "$USE_AUTH" == true ]]; then
    if [[ -z "$API_KEY" ]]; then
        API_KEY=$(grep '^API_KEY=' .env 2>/dev/null | cut -d'=' -f2 || echo "")
    fi
    
    if [[ -n "$API_KEY" ]]; then
        AUTH_HEADER="-H X-API-Key:$API_KEY"
        echo -e "${BLUE}Using API key authentication${NC}"
    else
        echo -e "${YELLOW}No API key provided, testing without authentication${NC}"
        AUTH_HEADER=""
    fi
else
    AUTH_HEADER=""
    echo -e "${YELLOW}Skipping authentication as requested${NC}"
fi

# Function to make HTTP request
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local url="${BASE_URL}${endpoint}"
    
    if [[ -n "$data" ]]; then
        curl -s -w "HTTPSTATUS:%{http_code}" -X "$method" "$url" $AUTH_HEADER \
             -H "Content-Type: application/json" \
             -d "$data"
    else
        curl -s -w "HTTPSTATUS:%{http_code}" -X "$method" "$url" $AUTH_HEADER
    fi
}

# Function to run a test
run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Running $test_name... "
    
    local response=$(make_request "$method" "$endpoint" "$data")
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    local status=$(echo "$response" | sed -E 's/.*HTTPSTATUS:([0-9]{3})$/\1/')
    
    if [[ "$status" == "$expected_status" ]]; then
        echo -e "${GREEN}✅ PASS (${status})${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL (${status}, expected ${expected_status})${NC}"
        echo -e "${RED}   Response: ${body}${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to run test with JSON validation
run_json_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    local expected_field="$6"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Running $test_name... "
    
    local response=$(make_request "$method" "$endpoint" "$data")
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    local status=$(echo "$response" | sed -E 's/.*HTTPSTATUS:([0-9]{3})$/\1/')
    
    if [[ "$status" == "$expected_status" ]]; then
        # Validate JSON contains expected field
        if echo "$body" | grep -q "\"$expected_field\""; then
            echo -e "${GREEN}✅ PASS (${status}, contains ${expected_field})${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "${RED}❌ FAIL (${status} but missing field: ${expected_field})${NC}"
            echo -e "${RED}   Response: ${body}${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        echo -e "${RED}❌ FAIL (${status}, expected ${expected_status})${NC}"
        echo -e "${RED}   Response: ${body}${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo -e "${BLUE}🚀 Starting LLM Platform Compatibility Tests${NC}"
echo -e "${BLUE}Target: ${BASE_URL}${NC}"
echo "=" * 60

# Test 1: Health Check
run_test "Health Check" "GET" "/health" "" "200"

# Test 2: v0.2 Providers API (LLM Platform compatibility)
run_json_test "v0.2 Providers API" "GET" "/api/v0.2/providers" "" "200" "providers"

# Test 3: v0.2 Models API (LLM Platform compatibility)
run_json_test "v0.2 Models API" "GET" "/api/v0.2/models" "" "200" "models"

# Test 4: v1 Chat API (if available)
chat_payload='{"message": "Hello, this is a compatibility test", "stream": false}'
run_test "v1 Chat API" "POST" "/api/v1/chat" "$chat_payload" "200"

# Test 5: v0.2 Chat API
run_test "v0.2 Chat API" "POST" "/api/v0.2/chat" "$chat_payload" "200"

# Test 6: Asset Generation API (if available)
asset_payload='{"prompt": "Test asset generation", "type": "image", "style": "digital_art"}'
run_test "Asset Generation API" "POST" "/api/v1/assets/generate" "$asset_payload" "200"

# Test 7: Providers Info v1 (if available)
run_test "Providers Info v1" "GET" "/api/v1/providers/" "" "200"

# Test 8: Personas API (if available)
run_test "Personas API" "GET" "/api/v1/personas/" "" "200"

# Test 9: Filesystem API (if available)
run_test "Filesystem API" "GET" "/api/v1/filesystem/files?path=/" "" "200"

echo ""
echo "=" * 60
echo -e "${BLUE}📊 LLM PLATFORM COMPATIBILITY TEST SUMMARY${NC}"
echo "=" * 60

echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS ✅${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS ❌${NC}"

if [[ $TOTAL_TESTS -gt 0 ]]; then
    success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
    echo "Success Rate: ${success_rate}%"
fi

echo ""
if [[ $PASSED_TESTS -eq $TOTAL_TESTS ]]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! Gaia Platform is fully LLM Platform compatible! 🎉${NC}"
    exit 0
elif [[ $PASSED_TESTS -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  PARTIAL COMPATIBILITY: Some LLM Platform APIs are working${NC}"
    echo -e "${BLUE}This may be expected if Gaia Platform implements a subset of LLM Platform features${NC}"
    exit 1
else
    echo -e "${RED}❌ NO COMPATIBILITY: No LLM Platform APIs are working${NC}"
    exit 2
fi