#!/bin/bash
# 🤖 CLAUDE CODE TEST RUNNER - Use this instead of pytest!
# 
# IMPORTANT FOR FUTURE CLAUDES: When you want to run tests, use THIS script!
# This is THE ONLY WAY to run all tests without hitting Claude Code's 2-minute timeout!
# 
# ✅ DO: 
#   ./scripts/pytest-for-claude.sh                                        # All tests
#   ./scripts/pytest-for-claude.sh tests/integration                      # Integration tests
#   ./scripts/pytest-for-claude.sh tests/e2e                              # Browser tests
#   ./scripts/pytest-for-claude.sh tests/unit                             # Unit tests
#   ./scripts/pytest-for-claude.sh tests/integration/test_v03_api.py      # Single file
#   ./scripts/pytest-for-claude.sh "tests/integration -k test_health"     # Pattern matching
#   ./scripts/pytest-for-claude.sh "--lf"                                 # Last failed only
#   ./scripts/pytest-for-claude.sh "--ff"                                 # Failed first
# 
# ❌ DON'T use these (they will timeout):
#   - pytest
#   - docker compose run test
#   - docker compose exec test pytest
#   - python -m pytest
# 
# This script runs tests asynchronously in Docker to avoid timeouts.

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if Docker services are running
check_docker_services() {
    local services_needed=($@)
    local all_running=true
    
    echo -e "${CYAN}🔍 Checking required services...${NC}"
    
    for service in "${services_needed[@]}"; do
        # Check if container exists and is running
        if docker compose ps --status running | grep -q "gaia-${service}-1"; then
            echo -e "  ${GREEN}✓${NC} ${service} is running"
        else
            echo -e "  ${RED}✗${NC} ${service} is not running"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        echo -e "\n${RED}❌ Required services are not running!${NC}"
        echo -e "${YELLOW}Please start services with: docker compose up -d${NC}"
        return 1
    fi
    
    return 0
}

# Function to check service health endpoints
check_service_health() {
    echo -e "\n${CYAN}🏥 Checking service health...${NC}"
    
    # Check gateway health (which checks all other services)
    if curl -s -f http://localhost:8666/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Gateway health check passed"
        
        # Get detailed health status
        local health_json=$(curl -s http://localhost:8666/health)
        
        # Check individual service health from gateway response
        if echo "$health_json" | grep -q '"auth".*"status".*"healthy"'; then
            echo -e "  ${GREEN}✓${NC} Auth service is healthy"
        else
            echo -e "  ${YELLOW}⚠${NC} Auth service may have issues"
        fi
        
        if echo "$health_json" | grep -q '"chat".*"status".*"healthy"'; then
            echo -e "  ${GREEN}✓${NC} Chat service is healthy"
        else
            echo -e "  ${YELLOW}⚠${NC} Chat service may have issues"
        fi
        
        if echo "$health_json" | grep -q '"database".*"status".*"healthy"'; then
            echo -e "  ${GREEN}✓${NC} Database is healthy"
        else
            echo -e "  ${YELLOW}⚠${NC} Database may have issues"
        fi
        
        return 0
    else
        echo -e "  ${RED}✗${NC} Gateway health check failed"
        echo -e "  ${YELLOW}Services may still be starting up...${NC}"
        return 1
    fi
}

# Function to determine which services are needed based on test type
get_required_services() {
    local test_args="$1"
    
    # Unit tests don't need any services
    if [[ "$test_args" == *"tests/unit"* ]]; then
        echo ""
        return
    fi
    
    # E2E and web tests need all services including web
    if [[ "$test_args" == *"tests/e2e"* ]] || [[ "$test_args" == *"tests/web"* ]]; then
        echo "db redis nats auth-service chat-service kb-service asset-service gateway web-service"
        return
    fi
    
    # Integration tests need core services
    if [[ "$test_args" == *"tests/integration"* ]] || [[ "$test_args" == "tests/"* ]]; then
        echo "db redis nats auth-service chat-service kb-service asset-service gateway"
        return
    fi
    
    # Default: assume integration tests need core services
    echo "db redis nats auth-service chat-service kb-service asset-service gateway"
}

# Create log directory if it doesn't exist
LOG_DIR="logs/tests/pytest"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/test-run-$(date +%Y%m%d-%H%M%S).log"
PID_FILE=".test-run.pid"

# Check if a test is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${RED}❌ Tests already running (PID: $OLD_PID)${NC}"
        echo "Check status with: ./scripts/check-test-progress.sh"
        exit 1
    fi
fi

# Get all command line arguments (default to all tests)
if [ $# -eq 0 ]; then
    TEST_ARGS="tests/"
else
    TEST_ARGS="$@"
fi

# Determine which services are needed
REQUIRED_SERVICES=$(get_required_services "$TEST_ARGS")

# Check services if needed
if [ -n "$REQUIRED_SERVICES" ]; then
    echo -e "${MAGENTA}🐳 Test type detected: $(echo $TEST_ARGS | grep -oE 'tests/[^/]+' | head -1 || echo 'mixed')${NC}"
    
    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running!${NC}"
        echo -e "${YELLOW}Please start Docker Desktop and try again.${NC}"
        exit 1
    fi
    
    # Check if required services are running
    if ! check_docker_services $REQUIRED_SERVICES; then
        # Services not running - try to start them
        echo -e "\n${BLUE}Starting services automatically...${NC}"
        docker compose up -d
        echo -e "${YELLOW}Waiting 15 seconds for services to be ready...${NC}"
        sleep 15
        
        # Check health after starting
        if ! check_service_health; then
            echo -e "${YELLOW}⚠️  Services are starting up. Proceeding with tests anyway...${NC}"
            echo -e "${YELLOW}Some tests may fail if services aren't fully ready.${NC}"
        fi
    else
        # Services are running, check their health
        if ! check_service_health; then
            echo -e "\n${YELLOW}⚠️  Services are running but may not be fully healthy.${NC}"
            echo -e "${YELLOW}Proceeding anyway - some tests may fail.${NC}"
        fi
    fi
else
    echo -e "${MAGENTA}🧪 Running unit tests - no services required${NC}"
fi

echo -e "\n${BLUE}🚀 Starting async test run...${NC}"
echo "📝 Logging to: $LOG_FILE"
echo "📂 Test args: $TEST_ARGS"

# Start the test in background
{
    echo "=== Test run started at $(date) ===" 
    echo "Running pytest sequentially (no parallel execution)..."
    echo "Test arguments: $TEST_ARGS"
    
    # Run ALL tests sequentially - override pytest.ini to remove -n auto
    echo "Running all tests sequentially..."
    docker compose run --rm test bash -c "PYTHONPATH=/app pytest --override-ini='addopts=-v --tb=short --strict-markers --disable-warnings' $TEST_ARGS" 2>&1
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "\n${RED}❌ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
    fi
    
    echo "=== Test run completed at $(date) ==="
    
    # Clean up PID file
    rm -f "$PID_FILE"
} > "$LOG_FILE" 2>&1 &

TEST_PID=$!
echo $TEST_PID > "$PID_FILE"

echo -e "${GREEN}✅ Tests started in background (PID: $TEST_PID)${NC}"
echo ""
echo "Monitor progress with:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Check status with:"
echo "  ./scripts/check-test-progress.sh"
echo ""
echo -e "${YELLOW}Note: Tests will run sequentially (no parallel execution)${NC}"