#!/bin/bash
# Smart Local Development Script for Gaia Platform
# Handles port conflicts, clean starts, and common operations

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services (handles port conflicts)"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  clean     Stop and remove all data (fresh start)"
    echo "  status    Show service status"
    echo "  logs      Show logs (follow mode)"
    echo "  test      Run basic health tests"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start cluster, handling conflicts"
    echo "  $0 clean          # Complete fresh start"
    echo "  $0 logs gateway   # Show gateway logs"
    exit 1
}

# Check for port conflicts
check_port_conflicts() {
    local conflicts=false
    
    # Check PostgreSQL port 5432
    if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port 5432 in use. Checking for conflicting containers...${NC}"
        local pg_container=$(docker ps --filter "publish=5432" --format "{{.Names}}" | grep -v gaia-db || true)
        if [[ -n "$pg_container" ]]; then
            echo -e "${YELLOW}Found PostgreSQL container: $pg_container${NC}"
            echo -n "Stop it? (y/n): "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                docker stop "$pg_container"
                echo -e "${GREEN}Stopped $pg_container${NC}"
            else
                conflicts=true
            fi
        fi
    fi
    
    # Check Gateway port 8666
    if lsof -Pi :8666 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port 8666 in use. Checking for conflicting containers...${NC}"
        local gateway_container=$(docker ps --filter "publish=8666" --format "{{.Names}}" | grep -v gaia-gateway || true)
        if [[ -n "$gateway_container" ]]; then
            echo -e "${YELLOW}Found container using port 8666: $gateway_container${NC}"
            echo -n "Stop it? (y/n): "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                docker stop "$gateway_container"
                echo -e "${GREEN}Stopped $gateway_container${NC}"
            else
                conflicts=true
            fi
        fi
    fi
    
    if [[ "$conflicts" == true ]]; then
        echo -e "${RED}Port conflicts remain. Please resolve before starting.${NC}"
        exit 1
    fi
}

# Start services
start_services() {
    echo -e "${BLUE}Starting Gaia Platform locally...${NC}"
    
    # Check for port conflicts
    check_port_conflicts
    
    # Start services
    echo -e "${YELLOW}Starting Docker Compose services...${NC}"
    docker compose up -d
    
    # Wait for services to be healthy
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 5
    
    # Show status
    show_status
    
    # Run basic health check
    echo -e "${BLUE}Running health check...${NC}"
    if curl -s http://localhost:8666/health | grep -q "healthy"; then
        echo -e "${GREEN}✅ Gateway is healthy!${NC}"
        echo ""
        echo -e "${GREEN}🚀 Gaia Platform is running!${NC}"
        echo -e "${BLUE}Gateway URL:${NC} http://localhost:8666"
        echo -e "${BLUE}API Key:${NC} Check .env file or use: docker compose exec gateway cat /app/.env | grep API_KEY"
        echo -e "${BLUE}User:${NC} dev@gaia.local"
        echo ""
        echo -e "${YELLOW}Test with:${NC} ./scripts/test.sh --local providers"
    else
        echo -e "${RED}❌ Gateway health check failed${NC}"
        echo "Check logs with: $0 logs gateway"
    fi
}

# Stop services
stop_services() {
    echo -e "${BLUE}Stopping Gaia Platform...${NC}"
    docker compose down
    echo -e "${GREEN}✅ All services stopped${NC}"
}

# Clean everything
clean_all() {
    echo -e "${RED}⚠️  This will remove all data and start fresh!${NC}"
    echo -n "Are you sure? (y/n): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cleaning up...${NC}"
        docker compose down -v
        echo -e "${GREEN}✅ Clean complete. Ready for fresh start.${NC}"
    else
        echo "Cancelled."
    fi
}

# Show status
show_status() {
    echo -e "${BLUE}=== Gaia Platform Status ===${NC}"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Service}}"
}

# Show logs
show_logs() {
    local service="$1"
    if [[ -z "$service" ]]; then
        docker compose logs -f
    else
        docker compose logs -f "$service"
    fi
}

# Run tests
run_tests() {
    echo -e "${BLUE}Running basic tests...${NC}"
    
    # Health check
    echo -n "Gateway health: "
    if curl -s http://localhost:8666/health | grep -q "healthy"; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
    
    # Provider test with auth
    echo -n "Provider API (authenticated): "
    # Get API key from environment or .env file
    API_KEY="${API_KEY:-$(grep API_KEY .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")}"
    if [ -z "$API_KEY" ]; then
        echo -e "${YELLOW}⚠️  SKIP${NC} (API_KEY not found)"
    elif curl -s -H "X-API-Key: $API_KEY" \
         http://localhost:8666/api/v0.2/providers | grep -q "claude"; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
    
    # Database check
    echo -n "Database connection: "
    if docker exec gaia-db-1 pg_isready -q; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
}

# Main command handling
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        echo ""
        start_services
        ;;
    clean)
        clean_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    test)
        run_tests
        ;;
    *)
        usage
        ;;
esac