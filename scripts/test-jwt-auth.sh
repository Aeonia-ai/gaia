#!/bin/bash
# Test JWT authentication alongside API key authentication
# Part of Phase 1: Add JWT support while maintaining API_KEY compatibility

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="local"
BASE_URL="http://localhost:8666"
API_KEY=${API_KEY:-""}

function print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --env ENV      Environment (local|dev|staging|prod)"
    echo "  --url URL      Base URL (default: http://localhost:8666)"
    echo "  --api-key KEY  API key for testing"
    echo "  --help         Show this help"
}

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

function log_result() {
    if [[ $1 -eq 0 ]]; then
        echo -e "${GREEN}✅ PASS${NC} $2"
    else
        echo -e "${RED}❌ FAIL${NC} $2"
        return 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Load API key from .env if not provided
if [[ -z "$API_KEY" ]] && [[ -f ".env" ]]; then
    API_KEY=$(grep "^API_KEY=" .env | cut -d'=' -f2 | tr -d '"')
fi

# Validate prerequisites
if [[ -z "$API_KEY" ]]; then
    log_error "API_KEY not found. Set via --api-key or in .env file"
    exit 1
fi

log_info "Testing JWT authentication on $BASE_URL"
echo ""

# Test 1: Health check (no auth required)
log_test "Gateway health check"
RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$RESPONSE" | grep -q "healthy\|degraded"; then
    log_result 0 "Gateway health check"
else
    log_result 1 "Gateway health check"
fi

# Test 2: API key authentication (existing functionality)
log_test "API key authentication"
RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/v1/providers")
if echo "$RESPONSE" | grep -q "providers\|error"; then
    if echo "$RESPONSE" | grep -q "error"; then
        log_error "API key auth failed: $RESPONSE"
        log_result 1 "API key authentication"
    else
        log_result 0 "API key authentication"
    fi
else
    log_result 1 "API key authentication - unexpected response"
fi

# Test 3: Generate service JWT token
log_test "Generate service JWT token"
if [[ "$ENVIRONMENT" == "local" ]]; then
    AUTH_URL="http://localhost:8001"
else
    AUTH_URL=$(echo "$BASE_URL" | sed 's/gateway/auth/')
fi

JWT_RESPONSE=$(curl -s -X POST "$AUTH_URL/internal/service-token" \
    -H "Content-Type: application/json" \
    -d '{"service_name": "gateway"}' 2>/dev/null || echo '{"error": "Failed to connect"}')

if echo "$JWT_RESPONSE" | grep -q "token"; then
    SERVICE_JWT=$(echo "$JWT_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    log_result 0 "Service JWT generation"
    log_info "Service JWT obtained (first 50 chars): ${SERVICE_JWT:0:50}..."
else
    log_error "Failed to generate service JWT: $JWT_RESPONSE"
    log_result 1 "Service JWT generation"
    SERVICE_JWT=""
fi

# Test 4: Validate service JWT
if [[ -n "$SERVICE_JWT" ]]; then
    log_test "Service JWT validation"
    VALIDATE_RESPONSE=$(curl -s -X POST "$AUTH_URL/auth/validate" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"$SERVICE_JWT\"}")
    
    if echo "$VALIDATE_RESPONSE" | grep -q '"valid":true.*"auth_type":"service_jwt"'; then
        log_result 0 "Service JWT validation"
    else
        log_error "JWT validation failed: $VALIDATE_RESPONSE"
        log_result 1 "Service JWT validation"
    fi
fi

# Test 5: Use service JWT for API request
if [[ -n "$SERVICE_JWT" ]]; then
    log_test "API request with service JWT"
    JWT_API_RESPONSE=$(curl -s -H "Authorization: Bearer $SERVICE_JWT" "$BASE_URL/v1/providers")
    
    if echo "$JWT_API_RESPONSE" | grep -q "providers"; then
        log_result 0 "API request with service JWT"
    else
        log_error "JWT API request failed: $JWT_API_RESPONSE"
        log_result 1 "API request with service JWT"
    fi
fi

# Test 6: Verify both auth methods work simultaneously
log_test "Simultaneous API key and JWT auth"
ERRORS=0

# Make parallel requests with different auth methods
API_KEY_RESP=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/v1/providers" &)
if [[ -n "$SERVICE_JWT" ]]; then
    JWT_RESP=$(curl -s -H "Authorization: Bearer $SERVICE_JWT" "$BASE_URL/v1/providers" &)
fi
wait

# Both should succeed
if ! echo "$API_KEY_RESP" | grep -q "providers"; then
    ((ERRORS++))
fi
if [[ -n "$SERVICE_JWT" ]] && ! echo "$JWT_RESP" | grep -q "providers"; then
    ((ERRORS++))
fi

log_result $((ERRORS == 0 ? 0 : 1)) "Simultaneous auth methods"

# Summary
echo ""
log_info "🎉 JWT authentication test complete!"
log_info "Phase 1 Goal: ✅ JWT works alongside API_KEY authentication"