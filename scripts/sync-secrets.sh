#!/bin/bash
# Sync secrets from local .env to Fly.io services
# Usage: ./scripts/sync-secrets.sh --env dev --services "gateway auth asset chat"

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
ENVIRONMENT=""
SERVICES=""
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --env [dev|staging|prod] --services \"service1 service2\" [--dry-run]"
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$ENVIRONMENT" ]; then
    echo -e "${RED}Error: --env is required${NC}"
    exit 1
fi

if [ -z "$SERVICES" ]; then
    echo -e "${YELLOW}No services specified, defaulting to all services${NC}"
    SERVICES="gateway auth asset chat"
fi

# Load .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

echo -e "${BLUE}=== Fly.io Secret Sync ===${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}Services: ${SERVICES}${NC}"
echo ""

# Define required secrets per service
get_service_secrets() {
    local service=$1
    case $service in
        gateway)
            echo "SUPABASE_URL SUPABASE_ANON_KEY SUPABASE_JWT_SECRET DATABASE_URL API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY"
            ;;
        auth)
            echo "SUPABASE_URL SUPABASE_ANON_KEY SUPABASE_JWT_SECRET DATABASE_URL"
            ;;
        asset)
            echo "DATABASE_URL OPENAI_API_KEY MESHY_API_KEY STABILITY_API_KEY MUBERT_API_KEY MIDJOURNEY_API_KEY FREESOUND_API_KEY SUPABASE_URL SUPABASE_JWT_SECRET"
            ;;
        chat)
            echo "DATABASE_URL OPENAI_API_KEY ANTHROPIC_API_KEY SUPABASE_URL SUPABASE_JWT_SECRET"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to get secret value from .env
get_secret_value() {
    local key=$1
    grep "^${key}=" .env | head -1 | cut -d'=' -f2- | sed 's/^"//' | sed 's/"$//'
}

# Function to set secrets for a service
set_service_secrets() {
    local service=$1
    local app_name="gaia-${service}-${ENVIRONMENT}"
    
    echo -e "${BLUE}Setting secrets for ${app_name}...${NC}"
    
    # Get required secrets for this service
    local secrets=$(get_service_secrets "$service")
    if [ -z "$secrets" ]; then
        echo -e "${YELLOW}Warning: No secrets defined for service ${service}${NC}"
        return
    fi
    
    # Build the fly secrets set command
    local cmd="fly secrets set"
    local has_secrets=false
    
    for secret in $secrets; do
        local value=$(get_secret_value "$secret")
        if [ -n "$value" ]; then
            # Escape special characters
            value=$(printf '%q' "$value")
            cmd="$cmd ${secret}=${value}"
            has_secrets=true
            echo -e "  ${GREEN}✓${NC} ${secret}"
        else
            echo -e "  ${YELLOW}⚠${NC} ${secret} (not found in .env)"
        fi
    done
    
    cmd="$cmd -a ${app_name}"
    
    if [ "$has_secrets" = true ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}DRY RUN: Would execute:${NC}"
            echo "$cmd" | sed 's/=.*/=<redacted>/'
        else
            echo -e "${GREEN}Executing secrets update...${NC}"
            eval "$cmd"
        fi
    else
        echo -e "${RED}No secrets to set for ${app_name}${NC}"
    fi
    
    echo ""
}

# Process each service
for service in $SERVICES; do
    set_service_secrets "$service"
done

echo -e "${GREEN}Secret sync complete!${NC}"

# Show verification commands
echo -e "${BLUE}To verify secrets were set:${NC}"
for service in $SERVICES; do
    echo "  fly secrets list -a gaia-${service}-${ENVIRONMENT}"
done