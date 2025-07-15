#!/bin/bash
# Version Check Script for Gaia Platform Services
# Checks deployment versions before testing to avoid outdated code

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function usage() {
    echo "Usage: $0 [environment]"
    echo ""
    echo "Environments:"
    echo "  dev        Check dev environment versions"
    echo "  staging    Check staging environment versions" 
    echo "  prod       Check production environment versions"
    echo "  local      Check local Docker versions"
    echo ""
    echo "Examples:"
    echo "  $0 dev     # Check dev deployment versions"
    echo "  $0 local   # Check local Docker versions"
    exit 1
}

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

function check_fly_service() {
    local service=$1
    local env=$2
    local app_name="gaia-${service}-${env}"
    
    echo -n "  ${service}: "
    
    if ! fly status -a "$app_name" >/dev/null 2>&1; then
        echo -e "${RED}❌ Not deployed${NC}"
        return 1
    fi
    
    # Extract version info from fly status
    local version_info=$(fly status -a "$app_name" 2>/dev/null | grep -E "(Image|VERSION)" || echo "")
    local updated_info=$(fly status -a "$app_name" 2>/dev/null | grep -A5 "LAST UPDATED" | head -1 || echo "")
    
    if [[ -n "$version_info" ]]; then
        local deployment_id=$(echo "$version_info" | grep -o "deployment-[A-Z0-9]*" || echo "unknown")
        local updated_time=$(echo "$updated_info" | awk '{print $NF}' || echo "unknown")
        echo -e "${GREEN}✅ $deployment_id${NC} (${updated_time})"
    else
        echo -e "${YELLOW}⚠️  Version info unavailable${NC}"
    fi
}

function check_local_service() {
    local service=$1
    
    echo -n "  ${service}: "
    
    if ! docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "gaia-${service}"; then
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
    
    # Get container info
    local container_id=$(docker ps -q --filter "name=gaia-${service}")
    local image_info=$(docker inspect "$container_id" --format "{{.Config.Image}}" 2>/dev/null || echo "unknown")
    local created_time=$(docker inspect "$container_id" --format "{{.Created}}" 2>/dev/null | cut -d'T' -f1 || echo "unknown")
    
    echo -e "${GREEN}✅ $image_info${NC} (${created_time})"
}

function check_environment() {
    local env=$1
    
    log_step "Checking $env environment versions..."
    echo ""
    
    if [[ "$env" == "local" ]]; then
        check_local_service "gateway"
        check_local_service "auth-service" 
        check_local_service "asset-service"
        check_local_service "chat-service"
        check_local_service "db"
        check_local_service "nats"
    else
        check_fly_service "gateway" "$env"
        check_fly_service "auth" "$env"
        check_fly_service "asset" "$env"
        check_fly_service "chat" "$env"
        check_fly_service "db" "$env"
        check_fly_service "nats" "$env"
    fi
}

function get_current_git_info() {
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local git_status=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    
    echo ""
    log_step "Current Git State:"
    echo "  Branch: $git_branch"
    echo "  Commit: $git_commit"
    if [[ "$git_status" -gt 0 ]]; then
        echo -e "  Status: ${YELLOW}$git_status uncommitted changes${NC}"
    else
        echo -e "  Status: ${GREEN}Clean working directory${NC}"
    fi
}

function assess_freshness() {
    local env=$1
    
    echo ""
    log_step "Deployment Freshness Assessment:"
    
    case "$env" in
        "local")
            echo -e "  ${GREEN}✅ Local development:${NC} Always current with your changes"
            ;;
        "dev"|"staging"|"prod")
            echo -e "  ${YELLOW}⚠️  Cloud deployment:${NC} May need updates if you've made recent changes"
            echo "  💡 To update: ./scripts/deploy.sh --env $env --services all"
            echo "  💡 Quick update gateway only: ./scripts/deploy.sh --env $env --services gateway"
            ;;
    esac
}

function recommend_testing_order() {
    local env=$1
    
    echo ""
    log_step "Recommended Testing Approach:"
    
    case "$env" in
        "local")
            echo "  1. ✅ Test locally first (you're here)"
            echo "  2. 📤 Deploy to dev: ./scripts/deploy.sh --env dev"  
            echo "  3. 🧪 Test dev: ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev assets-generate-image"
            ;;
        "dev")
            echo "  1. ✅ Test local first: ./scripts/test.sh --local assets-generate-image"
            echo "  2. 📤 Update dev if needed: ./scripts/deploy.sh --env dev"
            echo "  3. 🧪 Test dev (you're here)"
            ;;
        "staging"|"prod")
            echo "  1. ✅ Test local: ./scripts/test.sh --local assets-generate-image"
            echo "  2. ✅ Test dev: ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev assets-generate-image"
            echo "  3. 📤 Deploy to $env: ./scripts/deploy.sh --env $env"
            echo "  4. 🧪 Test $env (you're here)"
            ;;
    esac
}

# Main execution
if [[ $# -ne 1 ]]; then
    usage
fi

ENV="$1"

case "$ENV" in
    "local"|"dev"|"staging"|"prod")
        ;;
    *)
        log_error "Invalid environment: $ENV"
        usage
        ;;
esac

log_info "🔍 Gaia Platform Version Check"
log_info "Environment: $ENV"

# Check prerequisites for cloud environments
if [[ "$ENV" != "local" ]]; then
    if ! command -v fly &> /dev/null; then
        log_error "Fly CLI not found. Please install: https://fly.io/docs/hands-on/install-flyctl/"
        exit 1
    fi
    
    if ! fly auth whoami &> /dev/null; then
        log_error "Not logged in to Fly.io. Please run: fly auth login"
        exit 1
    fi
fi

# Check Docker for local environment
if [[ "$ENV" == "local" ]]; then
    if ! docker info &> /dev/null; then
        log_error "Docker not running. Please start Docker Desktop."
        exit 1
    fi
fi

# Perform checks
get_current_git_info
check_environment "$ENV"
assess_freshness "$ENV"
recommend_testing_order "$ENV"

echo ""
log_info "✅ Version check complete!"
echo ""
echo "💡 Pro tip: Run this before testing to catch outdated deployments early"
echo "💡 Add to your workflow: ./scripts/check-versions.sh dev && ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev assets-generate-image"