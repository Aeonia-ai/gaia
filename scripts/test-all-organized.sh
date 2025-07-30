#!/bin/bash
# Comprehensive test runner that handles all test types appropriately

echo "🧪 Gaia Platform Comprehensive Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Function to run container tests
run_container_tests() {
    echo -e "${YELLOW}📦 Running Container Tests (parallel)...${NC}"
    echo "These tests run inside Docker containers with all dependencies"
    echo ""
    
    if docker compose run test bash -c "pip install pytest-xdist &>/dev/null && python -m pytest tests/ -m 'not host_only' -n auto --tb=short -v"; then
        echo -e "${GREEN}✅ Container tests passed${NC}"
    else
        echo -e "${RED}❌ Container tests failed${NC}"
        ((FAILURES++))
    fi
    echo ""
}

# Function to run web UI tests
run_web_tests() {
    echo -e "${YELLOW}🌐 Running Web UI Tests...${NC}"
    echo "These tests run inside the web-service container"
    echo ""
    
    if ./scripts/test-web.sh; then
        echo -e "${GREEN}✅ Web UI tests passed${NC}"
    else
        echo -e "${RED}❌ Web UI tests failed${NC}"
        ((FAILURES++))
    fi
    echo ""
}

# Function to run host-only tests
run_host_tests() {
    echo -e "${YELLOW}🐳 Running Host-Only Tests...${NC}"
    echo "These tests require Docker access from the host"
    echo ""
    
    # Check if pytest is available on host
    if ! command -v pytest &> /dev/null; then
        echo "⚠️  pytest not installed on host, skipping host-only tests"
        echo "   To run these tests, install: pip install pytest"
    else
        if python -m pytest tests/ -m "host_only" -v; then
            echo -e "${GREEN}✅ Host-only tests passed${NC}"
        else
            echo -e "${RED}❌ Host-only tests failed${NC}"
            ((FAILURES++))
        fi
    fi
    echo ""
}

# Main execution
echo "Starting comprehensive test suite..."
echo ""

# Run tests in appropriate environments
run_container_tests
run_web_tests
run_host_tests

# Summary
echo "========================================"
echo "📊 Test Summary"
echo "========================================"

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILURES test suite(s) failed${NC}"
    exit 1
fi