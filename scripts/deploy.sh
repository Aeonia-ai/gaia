#!/bin/bash
# Smart Deployment Script for Gaia Platform
# Handles different deployment patterns based on lessons learned

set -e  # Exit on any error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
REGION="lax"  # Default to LAX for better latency
FORCE_REBUILD=false
DEPLOY_SERVICES="gateway"  # Default to gateway only
DATABASE_TYPE="fly"  # fly or supabase
DRY_RUN=false

function print_usage() {
    echo "Usage: $0 --env {dev|staging|production} [options]"
    echo ""
    echo "Required Options:"
    echo "  --env dev|staging|production # Target environment"
    echo ""
    echo "Optional Options:"
    echo "  --region REGION             # Fly.io region (default: lax)"
    echo "  --services SERVICE_LIST     # Services to deploy (default: all for dev, gateway for staging/prod)"
    echo "                              # Options: gateway, auth, asset, chat, web, all"
    echo "  --database fly|supabase     # Database type (default: fly)"
    echo "  --rebuild                   # Force rebuild containers"
    echo "  --dry-run                   # Show what would be deployed without deploying"
    echo "  --help                      # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev                               # Deploy all services to dev"
    echo "  $0 --env staging                           # Deploy gateway to staging"
    echo "  $0 --env production --services all         # Deploy all services to prod"
    echo "  $0 --env dev --region sjc --rebuild        # Deploy to SJC with rebuild"
    echo "  $0 --env dev --dry-run                     # Show what would be deployed to dev"
    echo ""
    echo "Deployment Patterns (Based on Lessons Learned):"
    echo "  🚀 Gateway-Only: Fast deployment, embedded services, NATS disabled"
    echo "  🏗️  Full Microservices: All services separate, NATS enabled, service mesh"
    echo "  🌎 Co-located Database: Fly.io Postgres in same region for <1ms latency"
    echo "  🔄 Smart Health Checks: Account for service startup dependencies"
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

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --services)
            DEPLOY_SERVICES="$2"
            shift 2
            ;;
        --database)
            DATABASE_TYPE="$2"
            shift 2
            ;;
        --rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment is required. Use --env dev, --env staging, or --env production"
    print_usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Environment must be 'dev', 'staging', or 'production'"
    exit 1
fi

# Set default services for dev environment
if [[ "$ENVIRONMENT" == "dev" && "$DEPLOY_SERVICES" == "gateway" ]]; then
    DEPLOY_SERVICES="all"
    log_info "Dev environment: defaulting to deploy all services"
fi

# Validate services
case "$DEPLOY_SERVICES" in
    "gateway"|"auth"|"asset"|"chat"|"web")
        ;;
    "all")
        DEPLOY_SERVICES="gateway auth asset chat web"
        ;;
    *)
        log_error "Invalid services: $DEPLOY_SERVICES"
        log_error "Valid options: gateway, auth, asset, chat, web, all"
        exit 1
        ;;
esac

function check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check if fly CLI is installed
    if ! command -v fly &> /dev/null; then
        log_error "Fly CLI is not installed. Please install it first:"
        log_error "https://fly.io/docs/hands-on/install-flyctl/"
        exit 1
    fi
    
    # Check if logged in to Fly.io
    if ! fly auth whoami &> /dev/null; then
        log_error "Not logged in to Fly.io. Please run: fly auth login"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    log_info "✅ All prerequisites met"
}

function create_database() {
    local env=$1
    local region=$2
    
    if [[ "$DATABASE_TYPE" == "fly" ]]; then
        log_step "Setting up Fly.io Managed Postgres..."
        
        local db_name="gaia-db-$env"
        
        # Check if database already exists using new mpg command
        log_info "Checking for existing database..."
        if fly mpg list 2>/dev/null | grep -q "$db_name" || fly postgres list 2>/dev/null | grep -q "$db_name"; then
            log_info "Database $db_name already exists"
        else
            log_info "Creating new Postgres database: $db_name"
            log_info "Organization: aeonia-dev"
            fly postgres create \
                --name "$db_name" \
                --region "$region" \
                --vm-size shared-cpu-1x \
                --volume-size 10 \
                --initial-cluster-size 1 \
                --org aeonia-dev
        fi
        
        # Get connection string
        local db_url=$(fly postgres connect -a "$db_name" --command "echo \\$DATABASE_URL" 2>/dev/null || echo "")
        if [[ -z "$db_url" ]]; then
            log_warn "Could not automatically retrieve database URL"
            log_warn "Please get it manually with: fly postgres connect -a $db_name"
            log_warn "Then update your fly.$env.toml file"
        else
            log_info "Database URL retrieved successfully"
        fi
        
    else
        log_info "Using Supabase database (configured via environment variables)"
    fi
}

function deploy_service() {
    local service=$1
    local env=$2
    local region=$3
    
    log_step "Deploying $service service to $env..."
    
    local app_name="gaia-$service-$env"
    local config_file="fly.$service.$env.toml"
    
    # Handle gateway special case (uses different config names)
    if [[ "$service" == "gateway" ]]; then
        if [[ "$DEPLOY_SERVICES" == "gateway" ]]; then
            # Gateway-only deployment (legacy pattern)
            if [[ "$env" == "staging" ]]; then
                config_file="fly.staging.toml"
            elif [[ "$env" == "production" ]]; then
                config_file="fly.production.toml"
            fi
            app_name="gaia-gateway-$env"
        else
            # Full microservices deployment
            config_file="fly.gateway.$env.toml"
        fi
    fi
    
    # Check if config file exists
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file $config_file not found"
        log_error "Available configs:"
        ls -la fly.*.toml 2>/dev/null || log_error "No fly.*.toml files found"
        exit 1
    fi
    
    # Update region in config if needed
    if [[ "$region" != "lax" ]]; then
        log_info "Updating region to $region in $config_file"
        sed -i.bak "s/primary_region = '[^']*'/primary_region = '$region'/" "$config_file"
    fi
    
    # Build arguments
    local deploy_args=("--config" "$config_file")
    
    if [[ "$FORCE_REBUILD" == "true" ]]; then
        deploy_args+=("--no-cache")
    fi
    
    # Deploy based on service deployment pattern
    if [[ "$DEPLOY_SERVICES" == "gateway" ]]; then
        log_info "🚀 Gateway-Only Deployment Pattern:"
        log_info "  - All services embedded in gateway"
        log_info "  - NATS disabled for cloud"
        log_info "  - Database co-located for latency"
    else
        log_info "🏗️  Full Microservices Deployment Pattern:"
        log_info "  - Independent service scaling"
        log_info "  - NATS enabled for coordination"
        log_info "  - Service mesh communication"
    fi
    
    # Deploy the service
    log_info "Running: fly deploy ${deploy_args[*]}"
    if fly deploy "${deploy_args[@]}"; then
        log_info "✅ Successfully deployed $service"
        
        # Test the deployment
        log_step "Testing deployed service..."
        local app_url="https://$app_name.fly.dev"
        if curl -s "$app_url/health" | grep -q "healthy\|degraded"; then
            log_info "✅ Health check passed for $app_url"
            
            # For auth service, also validate secrets configuration
            if [[ "$service" == "auth" ]]; then
                log_step "Validating auth service secrets configuration..."
                local health_response=$(curl -s "$app_url/health")
                
                # Check if secrets health is included and validate
                if echo "$health_response" | grep -q '"secrets"'; then
                    local secrets_status=$(echo "$health_response" | grep -o '"secrets":[^}]*}' | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
                    
                    if [[ "$secrets_status" == "healthy" ]]; then
                        log_info "✅ Secrets configuration validated"
                    elif [[ "$secrets_status" == "warning" ]]; then
                        log_warn "⚠️  Secrets configuration has warnings"
                        echo "$health_response" | grep -o '"warnings":\[[^\]]*\]' || true
                    else
                        log_error "❌ Secrets configuration is unhealthy"
                        echo "$health_response" | grep -o '"error":"[^"]*"' || true
                    fi
                else
                    log_warn "⚠️  Unable to validate secrets configuration (old auth service version?)"
                fi
            fi
        else
            log_warn "⚠️  Health check failed or service not ready yet"
            log_warn "Service may still be starting up..."
        fi
    else
        log_error "❌ Failed to deploy $service"
        return 1
    fi
    
    # Restore original config if we modified it
    if [[ -f "$config_file.bak" ]]; then
        mv "$config_file.bak" "$config_file"
    fi
}

function setup_secrets() {
    local env=$1
    local service=$2
    
    log_step "Setting up secrets for $service..."
    
    local app_name="gaia-$service-$env"
    if [[ "$service" == "gateway" && "$DEPLOY_SERVICES" == "gateway" ]]; then
        app_name="gaia-gateway-$env"
    fi
    
    # Load secrets from .env file
    if [[ -f ".env" ]]; then
        log_info "Loading secrets from .env file..."
        
        # Common secrets for all services (API_KEY removed - now user-associated in database)
        local secrets=()
        
        # Service-specific secrets
        case "$service" in
            "gateway"|"chat")
                secrets+=("OPENAI_API_KEY" "ANTHROPIC_API_KEY")
                ;;
            "asset")
                secrets+=("STABILITY_API_KEY" "MESHY_API_KEY" "REPLICATE_API_TOKEN")
                ;;
            "auth")
                secrets+=("SUPABASE_URL" "SUPABASE_ANON_KEY" "SUPABASE_JWT_SECRET")
                ;;
            "web")
                secrets+=("API_KEY")
                ;;
        esac
        
        # Deploy secrets that exist in .env
        for secret in "${secrets[@]}"; do
            local value=$(grep "^$secret=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo "")
            if [[ -n "$value" ]]; then
                log_info "Setting secret: $secret"
                echo "$value" | fly secrets set "$secret=-" -a "$app_name" >/dev/null
            else
                log_warn "Secret $secret not found in .env file"
            fi
        done
        
    else
        log_warn ".env file not found - secrets must be set manually"
        log_warn "Use: fly secrets set SECRET_NAME=value -a $app_name"
    fi
}

function main() {
    log_info "🚀 Gaia Platform Smart Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $REGION"
    log_info "Services: $DEPLOY_SERVICES"
    log_info "Database: $DATABASE_TYPE"
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Mode: DRY RUN (no actual deployment)"
    fi
    echo ""
    
    check_prerequisites
    
    # Create database if using Fly.io
    if [[ "$DATABASE_TYPE" == "fly" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would create database: gaia-db-$ENVIRONMENT"
        else
            create_database "$ENVIRONMENT" "$REGION"
        fi
    fi
    
    # Deploy each service
    for service in $DEPLOY_SERVICES; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would setup secrets for: gaia-$service-$ENVIRONMENT"
            log_info "[DRY RUN] Would deploy service: $service to $ENVIRONMENT"
        else
            setup_secrets "$ENVIRONMENT" "$service"
            deploy_service "$service" "$ENVIRONMENT" "$REGION"
        fi
        echo ""
    done
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🎉 Dry run complete!"
        log_info ""
        log_info "To deploy for real, run:"
        log_info "  $0 --env $ENVIRONMENT --services \"$DEPLOY_SERVICES\""
    else
        log_info "🎉 Deployment complete!"
        log_info ""
        log_info "Next steps:"
        log_info "1. Test the deployment: ./scripts/test.sh --$ENVIRONMENT all"
        log_info "2. Monitor logs: fly logs -a gaia-gateway-$ENVIRONMENT"
        log_info "3. Check status: fly status -a gaia-gateway-$ENVIRONMENT"
    fi
    
    if [[ "$DEPLOY_SERVICES" != "gateway" ]]; then
        log_info "4. Configure service discovery between microservices"
        log_info "5. Set up NATS clustering for production"
    fi
}

# Run main function
main "$@"