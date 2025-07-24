#!/bin/bash
# Test KB service in remote environments (staging/production)

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
ENVIRONMENT=""
API_KEY=""

function print_usage() {
    echo "Usage: $0 --env {staging|production} --api-key KEY"
    echo ""
    echo "Required Options:"
    echo "  --env staging|production  # Target environment"
    echo "  --api-key KEY            # API key for authentication"
    echo ""
    echo "Examples:"
    echo "  $0 --env staging --api-key YOUR_API_KEY"
    echo "  $0 --env production --api-key YOUR_API_KEY"
}

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

function log_result() {
    if [[ $1 -eq 0 ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
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

# Validate required arguments
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment is required"
    print_usage
    exit 1
fi

if [[ -z "$API_KEY" ]]; then
    log_error "API key is required"
    print_usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Environment must be 'staging' or 'production'"
    exit 1
fi

# Set base URL
BASE_URL="https://gaia-kb-$ENVIRONMENT.fly.dev"

function test_health() {
    log_step "Testing health endpoint..."
    
    local response=$(curl -s "$BASE_URL/health")
    local status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "error")
    local git_initialized=$(echo "$response" | jq -r '.git_initialized' 2>/dev/null || echo "false")
    local file_count=$(echo "$response" | jq -r '.file_count' 2>/dev/null || echo "0")
    
    echo "  Status: $status"
    echo "  Git initialized: $git_initialized"
    echo "  File count: $file_count"
    
    if [[ "$status" == "healthy" && "$git_initialized" == "true" && "$file_count" -gt 0 ]]; then
        log_result 0
        return 0
    else
        log_result 1
        echo "  Response: $response"
        return 1
    fi
}

function test_search() {
    log_step "Testing search functionality..."
    
    local response=$(curl -s -X POST "$BASE_URL/api/v0.2/kb/search" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"message": "Aeonia"}')
    
    local status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "error")
    local results_count=$(echo "$response" | jq -r '.results | length' 2>/dev/null || echo "0")
    
    echo "  Status: $status"
    echo "  Results found: $results_count"
    
    if [[ "$status" == "success" || "$results_count" -gt 0 ]]; then
        log_result 0
        return 0
    else
        log_result 1
        echo "  Response: $response" | head -5
        return 1
    fi
}

function test_read() {
    log_step "Testing file read functionality..."
    
    local response=$(curl -s -X POST "$BASE_URL/api/v0.2/kb/read" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"message": "README.md"}')
    
    local content=$(echo "$response" | jq -r '.response' 2>/dev/null || echo "")
    
    if [[ -n "$content" && "$content" != "null" ]]; then
        echo "  File read successful (${#content} chars)"
        log_result 0
        return 0
    else
        log_result 1
        echo "  Response: $response" | head -5
        return 1
    fi
}

function test_git_status() {
    log_step "Testing Git status endpoint..."
    
    local response=$(curl -s "$BASE_URL/sync/status" \
        -H "X-API-Key: $API_KEY")
    
    local initialized=$(echo "$response" | jq -r '.initialized' 2>/dev/null || echo "false")
    local file_count=$(echo "$response" | jq -r '.file_count' 2>/dev/null || echo "0")
    
    echo "  Initialized: $initialized"
    echo "  File count: $file_count"
    
    if [[ "$initialized" == "true" && "$file_count" -gt 0 ]]; then
        log_result 0
        return 0
    else
        log_result 1
        echo "  Response: $response"
        return 1
    fi
}

function main() {
    log_info "🧪 KB Remote Testing"
    log_info "Environment: $ENVIRONMENT"
    log_info "URL: $BASE_URL"
    echo ""
    
    local total_tests=0
    local passed_tests=0
    
    # Run tests
    if test_health; then ((passed_tests++)); fi
    ((total_tests++))
    
    if test_search; then ((passed_tests++)); fi
    ((total_tests++))
    
    if test_read; then ((passed_tests++)); fi
    ((total_tests++))
    
    if test_git_status; then ((passed_tests++)); fi
    ((total_tests++))
    
    # Summary
    echo ""
    log_info "Test Summary: $passed_tests/$total_tests passed"
    
    if [[ $passed_tests -eq $total_tests ]]; then
        log_info "✅ All tests passed!"
        exit 0
    else
        log_error "❌ Some tests failed"
        exit 1
    fi
}

# Run main function
main "$@"