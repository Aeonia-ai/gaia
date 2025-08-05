#!/bin/bash
# Deployment Environment Validation Script
# Validates that all critical secrets and configurations are properly set

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-"local"}
FIX_MODE=${2:-""}

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNING_CHECKS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

check_secret() {
    local secret_name="$1"
    local description="$2"
    local required="${3:-true}"
    local format_check="${4:-}"
    
    ((TOTAL_CHECKS++))
    
    if [ "$ENVIRONMENT" = "local" ]; then
        # Check .env file
        if grep -q "^${secret_name}=" "$PROJECT_ROOT/.env" 2>/dev/null; then
            local value=$(grep "^${secret_name}=" "$PROJECT_ROOT/.env" | cut -d'=' -f2- | tr -d '"')
            if [ -n "$value" ] && [ "$value" != "undefined" ] && [ "$value" != "null" ]; then
                # Format validation if provided
                if [ -n "$format_check" ]; then
                    case "$format_check" in
                        "jwt")
                            if [[ "$value" =~ ^eyJ ]]; then
                                log_success "$secret_name: $description ✓"
                            else
                                log_warning "$secret_name: $description (invalid JWT format)"
                            fi
                            ;;
                        "url")
                            if [[ "$value" =~ ^https?:// ]]; then
                                log_success "$secret_name: $description ✓"
                            else
                                log_warning "$secret_name: $description (invalid URL format)"
                            fi
                            ;;
                        "uuid")
                            if [[ "$value" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
                                log_success "$secret_name: $description ✓"
                            else
                                log_warning "$secret_name: $description (invalid UUID format)"
                            fi
                            ;;
                        *)
                            log_success "$secret_name: $description ✓"
                            ;;
                    esac
                else
                    log_success "$secret_name: $description ✓"
                fi
            else
                if [ "$required" = "true" ]; then
                    log_error "$secret_name: $description (missing or empty)"
                else
                    log_warning "$secret_name: $description (optional, not set)"
                fi
            fi
        else
            if [ "$required" = "true" ]; then
                log_error "$secret_name: $description (not found in .env)"
            else
                log_warning "$secret_name: $description (optional, not found)"
            fi
        fi
    else
        # Check Fly.io secrets
        if command -v fly >/dev/null 2>&1; then
            local app_name="gaia-${ENVIRONMENT}"
            if fly secrets list -a "$app_name" 2>/dev/null | grep -q "^${secret_name}"; then
                log_success "$secret_name: $description ✓ (Fly.io)"
            else
                if [ "$required" = "true" ]; then
                    log_error "$secret_name: $description (missing from Fly.io secrets)"
                    if [ "$FIX_MODE" = "--fix" ]; then
                        log_info "Fix command: fly secrets set $secret_name=\"<value>\" -a $app_name"
                    fi
                else
                    log_warning "$secret_name: $description (optional, not in Fly.io)"
                fi
            fi
        else
            log_warning "fly CLI not available, cannot check remote secrets"
        fi
    fi
}

check_service_health() {
    local service_name="$1"
    local port="$2"
    
    ((TOTAL_CHECKS++))
    
    if [ "$ENVIRONMENT" = "local" ]; then
        local url="http://localhost:$port/health"
        if curl -s "$url" >/dev/null 2>&1; then
            log_success "Service health: $service_name ✓"
        else
            log_error "Service health: $service_name (not responding on port $port)"
        fi
    else
        local url="https://gaia-${service_name}-${ENVIRONMENT}.fly.dev/health"
        if curl -s "$url" >/dev/null 2>&1; then
            log_success "Service health: $service_name ✓ (remote)"
        else
            log_error "Service health: $service_name (not responding remotely)"
        fi
    fi
}

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Gaia Platform Deployment Validation${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
    echo -e "Timestamp: $(date)"
    echo ""
}

print_summary() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Validation Summary${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo -e "Total checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✅ All critical checks passed!${NC}"
        if [ $WARNING_CHECKS -gt 0 ]; then
            echo -e "${YELLOW}⚠️  Some warnings detected - review optional configurations${NC}"
        fi
        exit 0
    else
        echo -e "${RED}❌ $FAILED_CHECKS critical checks failed${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Fix the failed checks above"
        echo "2. Run this script again with --fix for suggested commands"
        echo "3. Verify fixes with: ./scripts/test.sh --env $ENVIRONMENT health"
        exit 1
    fi
}

main() {
    print_header
    
    log_info "Checking critical authentication secrets..."
    
    # Supabase Configuration
    check_secret "SUPABASE_URL" "Supabase project URL" true "url"
    check_secret "SUPABASE_ANON_KEY" "Supabase anonymous key" true "jwt"
    check_secret "SUPABASE_JWT_SECRET" "Supabase JWT secret" true
    check_secret "SUPABASE_SERVICE_KEY" "Supabase service role key" false "jwt"
    
    # API Provider Keys
    check_secret "ANTHROPIC_API_KEY" "Claude API key" true
    check_secret "OPENAI_API_KEY" "OpenAI API key" false
    
    # Application Configuration
    check_secret "AUTH_BACKEND" "Authentication backend" true
    check_secret "ENVIRONMENT" "Environment identifier" true
    
    # Database Configuration (if not using Supabase exclusively)
    if [ "$ENVIRONMENT" = "local" ]; then
        check_secret "DATABASE_URL" "PostgreSQL connection" false "url"
        check_secret "REDIS_URL" "Redis connection" false "url"
    fi
    
    # Git Integration (if KB service is used)
    check_secret "KB_GIT_REPO_URL" "Knowledge base Git repository" false "url"
    check_secret "KB_GIT_AUTH_TOKEN" "Git authentication token" false
    
    # Service Discovery
    check_secret "NATS_URL" "NATS messaging URL" false "url"
    
    log_info "Checking service health..."
    
    if [ "$ENVIRONMENT" = "local" ]; then
        # Check Docker services
        if command -v docker >/dev/null 2>&1; then
            if docker compose ps | grep -q "Up"; then
                check_service_health "gateway" "8666"
                check_service_health "auth" "8001"
                check_service_health "chat" "8002"
                check_service_health "kb" "8003"
                check_service_health "asset" "8004"
                
                # Check detailed auth health if service is up
                ((TOTAL_CHECKS++))
                if curl -s "http://auth-service:8000/auth/health" >/dev/null 2>&1; then
                    local auth_health=$(curl -s "http://auth-service:8000/auth/health" | grep -o '"overall_status":"[^"]*"' | cut -d'"' -f4)
                    if [ "$auth_health" = "healthy" ]; then
                        log_success "Auth system health: All authentication components ✓"
                    else
                        log_warning "Auth system health: $auth_health (check auth service logs)"
                    fi
                else
                    log_error "Auth system health: Auth health endpoint not responding"
                fi
            else
                log_warning "Docker services not running - start with 'docker compose up'"
            fi
        else
            log_warning "Docker not available, skipping service health checks"
        fi
    else
        # Check remote services
        check_service_health "gateway" ""
        check_service_health "auth" ""
        check_service_health "chat" ""
        check_service_health "kb" ""
        check_service_health "asset" ""
        
        # Check detailed auth health for remote
        ((TOTAL_CHECKS++))
        local auth_health_url="https://gaia-auth-${ENVIRONMENT}.fly.dev/auth/health"
        if curl -s "$auth_health_url" >/dev/null 2>&1; then
            local auth_health=$(curl -s "$auth_health_url" | grep -o '"overall_status":"[^"]*"' | cut -d'"' -f4)
            if [ "$auth_health" = "healthy" ]; then
                log_success "Auth system health: All authentication components ✓ (remote)"
            else
                log_warning "Auth system health: $auth_health (check remote auth service)"
            fi
        else
            log_error "Auth system health: Remote auth health endpoint not responding"
        fi
    fi
    
    log_info "Checking environment consistency..."
    
    ((TOTAL_CHECKS++))
    if [ "$ENVIRONMENT" = "local" ]; then
        if grep -q "AUTH_BACKEND=supabase" "$PROJECT_ROOT/.env" 2>/dev/null; then
            log_success "AUTH_BACKEND configured for Supabase ✓"
        else
            log_warning "AUTH_BACKEND not set to supabase (may use PostgreSQL fallback)"
        fi
    fi
    
    print_summary
}

# Usage information
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [ENVIRONMENT] [--fix]"
    echo ""
    echo "ENVIRONMENT:"
    echo "  local    - Validate local development environment (default)"
    echo "  dev      - Validate development deployment"
    echo "  staging  - Validate staging deployment"
    echo "  prod     - Validate production deployment"
    echo ""
    echo "OPTIONS:"
    echo "  --fix    - Show fix commands for failed checks"
    echo "  --help   - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Validate local environment"
    echo "  $0 dev               # Validate dev environment"
    echo "  $0 dev --fix         # Validate dev and show fix commands"
    exit 0
fi

# Validate environment parameter
case "$ENVIRONMENT" in
    local|dev|staging|prod)
        ;;
    *)
        echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
        echo "Valid environments: local, dev, staging, prod"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

main