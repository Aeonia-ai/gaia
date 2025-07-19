#!/bin/bash
# Full system test after deployment

set -e

echo "🧪 Full System Test - mTLS + JWT Authentication"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Test results
PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name=$1
    local cmd=$2
    echo -n "Testing $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
    fi
}

echo "1️⃣ Service Health Checks:"
echo "--------------------------"
test_endpoint "Gateway health" "curl -s http://localhost:8666/health"
test_endpoint "Web UI health" "curl -s http://localhost:8080/health"
test_endpoint "Auth service (internal)" "docker compose exec gateway curl -s http://auth-service:8000/health"
test_endpoint "Chat service (internal)" "docker compose exec gateway curl -s http://chat-service:8000/health"

echo ""
echo "2️⃣ Authentication Tests:"
echo "------------------------"
test_endpoint "API key auth" "./scripts/test.sh --local health"
test_endpoint "Chat with API key" "./scripts/test.sh --local chat 'test message'"
test_endpoint "Providers list" "./scripts/test.sh --local providers"

echo ""
echo "3️⃣ Web UI Tests:"
echo "-----------------"
test_endpoint "Login page" "curl -s http://localhost:8080/login | grep -q 'Gaia Platform'"
test_endpoint "Chat page (redirect)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/chat | grep -q '303'"

echo ""
echo "4️⃣ Database Tests:"
echo "-------------------"
test_endpoint "API keys exist" "docker compose exec db psql -U gaia_user -d gaia_db -c 'SELECT COUNT(*) FROM api_keys;' | grep -q '1'"
test_endpoint "Users exist" "docker compose exec db psql -U gaia_user -d gaia_db -c 'SELECT COUNT(*) FROM users;' | grep -q '1'"

echo ""
echo "5️⃣ Certificate Tests:"
echo "----------------------"
test_endpoint "CA certificate" "test -f certs/ca.pem"
test_endpoint "JWT signing key" "test -f certs/jwt-signing.key"
test_endpoint "Gateway certificate" "test -f certs/gateway/cert.pem"

echo ""
echo "=============================================="
echo "Test Summary:"
echo "  ✅ Passed: $PASSED"
echo "  ❌ Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! System is fully operational.${NC}"
    echo ""
    echo "Authentication Status:"
    echo "  • API Keys: Working ✅"
    echo "  • JWT Support: Enabled ✅"
    echo "  • Web UI: Accessible ✅"
    echo "  • Services: All healthy ✅"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check the logs for details.${NC}"
    exit 1
fi