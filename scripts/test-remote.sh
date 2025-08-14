#!/bin/bash
#
# Run tests against remote environments (dev, staging, production)
#
# Usage:
#   ./scripts/test-remote.sh [environment] [test-suite]
#
# Examples:
#   ./scripts/test-remote.sh dev smoke
#   ./scripts/test-remote.sh staging all
#   ./scripts/test-remote.sh production monitoring
#
# Environment variables:
#   API_KEY - API key for authentication
#   TEST_API_KEY - Alternative API key variable
#   TEST_ENV - Override environment (instead of first argument)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
ENV=${1:-${TEST_ENV:-dev}}
SUITE=${2:-smoke}

# Validate environment
case $ENV in
    local|dev|staging|production)
        ;;
    *)
        echo -e "${RED}❌ Invalid environment: $ENV${NC}"
        echo "Valid environments: local, dev, staging, production"
        exit 1
        ;;
esac

# Set TEST_ENV for pytest
export TEST_ENV=$ENV

# Check for API key
if [ -z "$API_KEY" ] && [ -z "$TEST_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  No API key found. Set API_KEY or TEST_API_KEY${NC}"
    echo "Some tests may be skipped."
fi

# Get environment URLs for display
case $ENV in
    local)
        GATEWAY_URL="http://localhost:8666"
        ;;
    dev)
        GATEWAY_URL="https://gaia-gateway-dev.fly.dev"
        ;;
    staging)
        GATEWAY_URL="https://gaia-gateway-staging.fly.dev"
        ;;
    production)
        GATEWAY_URL="https://gaia-gateway-production.fly.dev"
        ;;
esac

echo -e "${BLUE}🌍 Remote Testing Configuration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Environment: ${GREEN}$ENV${NC}"
echo -e "Gateway URL: ${GREEN}$GATEWAY_URL${NC}"
echo -e "Test Suite:  ${GREEN}$SUITE${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Production warning
if [ "$ENV" = "production" ]; then
    echo -e "${YELLOW}⚠️  WARNING: Testing against PRODUCTION${NC}"
    echo "Only read-only tests will be executed."
    echo "Destructive tests will be automatically skipped."
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Function to run tests
run_tests() {
    local markers=$1
    local test_path=${2:-"tests/remote/"}
    
    echo -e "${BLUE}Running: pytest $test_path -v -m \"$markers\"${NC}"
    
    if [ -d "$test_path" ]; then
        # Run pytest directly for remote tests (not in Docker)
        python -m pytest "$test_path" -v -m "$markers" --tb=short
    else
        echo -e "${RED}❌ Test directory not found: $test_path${NC}"
        echo "Have you created the remote test structure?"
        echo "See: docs/remote-testing-strategy.md"
        exit 1
    fi
}

# Run appropriate test suite
case $SUITE in
    smoke)
        echo -e "${GREEN}🔥 Running smoke tests...${NC}"
        run_tests "remote and smoke" "tests/remote/smoke/"
        ;;
    
    contract)
        echo -e "${GREEN}📋 Running API contract tests...${NC}"
        run_tests "remote and contract" "tests/remote/contract/"
        ;;
    
    performance)
        echo -e "${GREEN}⚡ Running performance tests...${NC}"
        run_tests "remote and performance" "tests/remote/performance/"
        ;;
    
    monitoring)
        echo -e "${GREEN}👁️  Running monitoring tests...${NC}"
        run_tests "remote and monitoring" "tests/remote/monitoring/"
        ;;
    
    auth)
        echo -e "${GREEN}🔐 Running authentication tests...${NC}"
        run_tests "remote and smoke" "tests/remote/smoke/test_auth_flow.py"
        ;;
    
    health)
        echo -e "${GREEN}💚 Running health checks...${NC}"
        run_tests "remote and smoke" "tests/remote/smoke/test_basic_health.py"
        ;;
    
    all)
        echo -e "${GREEN}🧪 Running all remote tests...${NC}"
        run_tests "remote" "tests/remote/"
        ;;
    
    *)
        echo -e "${RED}❌ Unknown test suite: $SUITE${NC}"
        echo "Valid suites: smoke, contract, performance, monitoring, auth, health, all"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Remote testing completed!${NC}"

# Show next steps
echo ""
echo "Next steps:"
echo "  • View full logs: Check the pytest output above"
echo "  • Run specific test: ./scripts/test-remote.sh $ENV health"
echo "  • Test other environment: ./scripts/test-remote.sh staging smoke"

# Performance tip for production
if [ "$ENV" = "production" ]; then
    echo ""
    echo -e "${YELLOW}💡 Tip: For continuous monitoring, consider setting up a GitHub Action${NC}"
    echo "See: .github/workflows/remote-monitoring.yml (example in docs)"
fi