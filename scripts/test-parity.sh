#!/bin/bash
# Test local vs remote parity
# Usage: ./scripts/test-parity.sh [dev|staging|prod]

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-dev}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="test-results/${TIMESTAMP}"

echo -e "${BLUE}=== Local vs Remote Parity Testing ===${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}Results will be saved to: ${RESULTS_DIR}${NC}"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to run tests and save results
run_test_suite() {
    local env_type=$1  # local or remote
    local base_url=$2
    local output_prefix="${RESULTS_DIR}/${env_type}"
    
    echo -e "${BLUE}Running tests for ${env_type} environment...${NC}"
    
    # Core functionality tests
    ./scripts/test.sh --url "$base_url" health > "${output_prefix}_health.txt" 2>&1
    ./scripts/test.sh --url "$base_url" providers > "${output_prefix}_providers.txt" 2>&1
    ./scripts/test.sh --url "$base_url" models > "${output_prefix}_models.txt" 2>&1
    
    # Authentication tests
    ./scripts/test.sh --url "$base_url" auth-register "test_${TIMESTAMP}@example.com" "testpass123" > "${output_prefix}_auth_register.txt" 2>&1
    
    # Asset tests
    ./scripts/test.sh --url "$base_url" assets-test > "${output_prefix}_assets_test.txt" 2>&1
    ./scripts/test.sh --url "$base_url" assets-generate-image > "${output_prefix}_assets_generate.txt" 2>&1
    
    # Chat tests
    ./scripts/test.sh --url "$base_url" chat "Hello, how are you?" > "${output_prefix}_chat.txt" 2>&1
    
    echo -e "${GREEN}✓ ${env_type} tests complete${NC}"
}

# Step 1: Ensure local environment is running
echo -e "${BLUE}Step 1: Starting local environment...${NC}"
docker compose up -d
sleep 10  # Wait for services to be ready

# Step 2: Run local tests
run_test_suite "local" "http://localhost:8666"

# Step 3: Run remote tests
case $ENVIRONMENT in
    dev)
        run_test_suite "remote" "https://gaia-gateway-dev.fly.dev"
        ;;
    staging)
        run_test_suite "remote" "https://gaia-gateway-staging.fly.dev"
        ;;
    prod)
        run_test_suite "remote" "https://gaia-gateway-prod.fly.dev"
        ;;
esac

# Step 4: Compare results
echo ""
echo -e "${BLUE}=== Comparing Results ===${NC}"

compare_test() {
    local test_name=$1
    local local_file="${RESULTS_DIR}/local_${test_name}.txt"
    local remote_file="${RESULTS_DIR}/remote_${test_name}.txt"
    
    # Extract status codes
    local local_status=$(grep -E "Status: [0-9]+" "$local_file" | head -1 | grep -o "[0-9]\+" || echo "0")
    local remote_status=$(grep -E "Status: [0-9]+" "$remote_file" | head -1 | grep -o "[0-9]\+" || echo "0")
    
    if [ "$local_status" == "$remote_status" ] && [ "$local_status" != "0" ]; then
        echo -e "  ${GREEN}✓ ${test_name}: Both returned $local_status${NC}"
    else
        echo -e "  ${RED}✗ ${test_name}: Local=$local_status, Remote=$remote_status${NC}"
        
        # Show error details if different
        if [ "$local_status" != "$remote_status" ]; then
            echo "    Local error:"
            grep -A2 "Status:" "$local_file" | head -3 | sed 's/^/      /'
            echo "    Remote error:"
            grep -A2 "Status:" "$remote_file" | head -3 | sed 's/^/      /'
        fi
    fi
}

# Compare each test
compare_test "health"
compare_test "providers"
compare_test "models"
compare_test "auth_register"
compare_test "assets_test"
compare_test "assets_generate"
compare_test "chat"

# Step 5: Generate summary report
echo ""
echo -e "${BLUE}=== Summary Report ===${NC}"
{
    echo "Local vs Remote Parity Test Report"
    echo "================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $TIMESTAMP"
    echo ""
    echo "Test Results:"
    echo "-------------"
    
    for test in health providers models auth_register assets_test assets_generate chat; do
        local local_status=$(grep -E "Status: [0-9]+" "${RESULTS_DIR}/local_${test}.txt" | head -1 | grep -o "[0-9]\+" || echo "0")
        local remote_status=$(grep -E "Status: [0-9]+" "${RESULTS_DIR}/remote_${test}.txt" | head -1 | grep -o "[0-9]\+" || echo "0")
        
        if [ "$local_status" == "$remote_status" ]; then
            echo "✓ $test: MATCH (Status $local_status)"
        else
            echo "✗ $test: MISMATCH (Local=$local_status, Remote=$remote_status)"
        fi
    done
} > "${RESULTS_DIR}/summary.txt"

cat "${RESULTS_DIR}/summary.txt"

echo ""
echo -e "${GREEN}Full results saved to: ${RESULTS_DIR}${NC}"

# Check if all tests matched
if grep -q "MISMATCH" "${RESULTS_DIR}/summary.txt"; then
    echo -e "${RED}⚠️  Parity issues detected! Review the results.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests show parity between local and remote!${NC}"
    exit 0
fi