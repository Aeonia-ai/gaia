#!/bin/bash
# Verify deployment health and configuration parity
# Usage: ./scripts/verify-deployment.sh --env dev

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-dev}"
if [ "$1" == "--env" ]; then
    ENVIRONMENT="$2"
fi

echo -e "${BLUE}=== Deployment Verification for ${ENVIRONMENT} ===${NC}"
echo ""

# Services to check
SERVICES=("gateway" "auth" "asset" "chat")
FAILED_CHECKS=0

# Check service health
check_service_health() {
    local service=$1
    local app_name="gaia-${service}-${ENVIRONMENT}"
    
    echo -e "${BLUE}Checking ${app_name}...${NC}"
    
    # Check if app exists
    if ! fly apps list | grep -q "$app_name"; then
        echo -e "  ${RED}✗ App not found${NC}"
        ((FAILED_CHECKS++))
        return
    fi
    
    # Check health endpoint
    local url="https://${app_name}.fly.dev/health"
    local response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
    local status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" == "200" ]; then
        echo -e "  ${GREEN}✓ Health check passed${NC}"
        
        # Parse health response
        local body=$(echo "$response" | sed '$d')
        
        # Check database connection
        if echo "$body" | grep -q '"database".*"connected"'; then
            echo -e "  ${GREEN}✓ Database connected${NC}"
        else
            echo -e "  ${YELLOW}⚠ Database disconnected${NC}"
        fi
        
        # Check NATS connection (if applicable)
        if echo "$body" | grep -q '"nats"'; then
            if echo "$body" | grep -q '"nats".*"connected"'; then
                echo -e "  ${GREEN}✓ NATS connected${NC}"
            else
                echo -e "  ${YELLOW}⚠ NATS disconnected${NC}"
            fi
        fi
    else
        echo -e "  ${RED}✗ Health check failed (HTTP $status_code)${NC}"
        ((FAILED_CHECKS++))
    fi
    
    # Check secrets
    echo -e "  ${BLUE}Checking secrets...${NC}"
    local secrets=$(fly secrets list -a "$app_name" 2>/dev/null | grep -E "NAME|^[A-Z_]+" | tail -n +2)
    
    case $service in
        gateway)
            check_secret "$secrets" "SUPABASE_URL"
            check_secret "$secrets" "DATABASE_URL"
            check_secret "$secrets" "API_KEY"
            ;;
        auth)
            check_secret "$secrets" "SUPABASE_URL"
            check_secret "$secrets" "DATABASE_URL"
            ;;
        asset)
            check_secret "$secrets" "OPENAI_API_KEY"
            check_secret "$secrets" "DATABASE_URL"
            ;;
        chat)
            check_secret "$secrets" "OPENAI_API_KEY"
            check_secret "$secrets" "ANTHROPIC_API_KEY"
            ;;
    esac
    
    echo ""
}

check_secret() {
    local secrets="$1"
    local secret_name="$2"
    
    if echo "$secrets" | grep -q "^$secret_name"; then
        echo -e "    ${GREEN}✓ $secret_name${NC}"
    else
        echo -e "    ${RED}✗ $secret_name missing${NC}"
        ((FAILED_CHECKS++))
    fi
}

# Check inter-service communication
check_service_communication() {
    echo -e "${BLUE}=== Inter-Service Communication ===${NC}"
    
    # Test gateway -> auth service
    echo -e "${BLUE}Testing Gateway -> Auth Service...${NC}"
    local auth_test=$(curl -s -X POST "https://gaia-gateway-${ENVIRONMENT}.fly.dev/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"testpass123"}' 2>/dev/null)
    
    if echo "$auth_test" | grep -q "user\|already registered"; then
        echo -e "  ${GREEN}✓ Gateway can reach Auth Service${NC}"
    else
        echo -e "  ${RED}✗ Gateway cannot reach Auth Service${NC}"
        ((FAILED_CHECKS++))
    fi
    
    # Test gateway -> asset service
    echo -e "${BLUE}Testing Gateway -> Asset Service...${NC}"
    local asset_test=$(curl -s "https://gaia-gateway-${ENVIRONMENT}.fly.dev/api/v1/assets/test" 2>/dev/null)
    
    if echo "$asset_test" | grep -q "asset-service"; then
        echo -e "  ${GREEN}✓ Gateway can reach Asset Service${NC}"
    else
        echo -e "  ${RED}✗ Gateway cannot reach Asset Service${NC}"
        ((FAILED_CHECKS++))
    fi
    
    echo ""
}

# Main verification
for service in "${SERVICES[@]}"; do
    check_service_health "$service"
done

check_service_communication

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Deployment is healthy.${NC}"
else
    echo -e "${RED}✗ $FAILED_CHECKS checks failed. Deployment needs attention.${NC}"
fi

# Suggest fixes
if [ $FAILED_CHECKS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Suggested fixes:${NC}"
    echo "1. Run: ./scripts/sync-secrets.sh --env $ENVIRONMENT --services \"gateway auth asset chat\""
    echo "2. Check logs: fly logs -a gaia-[service]-$ENVIRONMENT"
    echo "3. Verify internal DNS configuration in fly.*.toml files"
fi

exit $FAILED_CHECKS