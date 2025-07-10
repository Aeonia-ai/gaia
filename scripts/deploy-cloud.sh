#!/bin/bash
set -e

# Gaia Platform Multi-Environment Cloud Deployment Script
# Supports dev, staging, and production deployments to Fly.io

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SUPPORTED_ENVIRONMENTS=("dev" "staging" "prod")
SERVICES=("gateway" "auth" "asset" "chat")

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print functions
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}[DEPLOY]${NC} $1"; }

# Usage information
usage() {
    cat << EOF
Gaia Platform Cloud Deployment Script

Usage: $0 <environment> [service] [options]

Environments:
  dev        - Development environment (auto-sleep, minimal resources)
  staging    - Staging environment (production-like, scheduled scaling)
  prod       - Production environment (high availability, auto-scaling)

Services:
  gateway    - Main API gateway service
  auth       - Authentication service
  asset      - Asset generation service
  chat       - Chat/LLM service
  all        - Deploy all services (default)

Options:
  --dry-run        Show what would be deployed without executing
  --skip-build     Skip Docker build step
  --force          Force deployment even if environment checks fail
  --rollback       Rollback to previous version

Examples:
  $0 dev                    # Deploy all services to dev
  $0 staging gateway        # Deploy only gateway to staging
  $0 prod --dry-run         # Show what would be deployed to prod
  $0 staging --rollback     # Rollback staging deployment

EOF
}

# Validate environment
validate_environment() {
    local env=$1
    if [[ ! " ${SUPPORTED_ENVIRONMENTS[@]} " =~ " ${env} " ]]; then
        print_error "Unsupported environment: $env"
        print_error "Supported environments: ${SUPPORTED_ENVIRONMENTS[*]}"
        exit 1
    fi
}

# Validate service
validate_service() {
    local service=$1
    if [[ "$service" != "all" ]] && [[ ! " ${SERVICES[@]} " =~ " ${service} " ]]; then
        print_error "Unsupported service: $service"
        print_error "Supported services: ${SERVICES[*]} all"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check flyctl
    if ! command -v flyctl &> /dev/null; then
        print_error "flyctl is not installed. Install from: https://fly.io/docs/hands-on/install-flyctl/"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check authentication
    if ! flyctl auth whoami &> /dev/null; then
        print_error "Not authenticated with Fly.io. Run: flyctl auth login"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Set environment variables based on deployment environment
set_environment_config() {
    local env=$1
    print_status "Configuring environment: $env"
    
    case $env in
        "dev")
            export FLY_CONFIG="fly.dev.toml"
            export LOG_LEVEL="DEBUG"
            export AUTO_STOP="stop"
            export MIN_MACHINES="0"
            ;;
        "staging")
            export FLY_CONFIG="fly.staging.toml"
            export LOG_LEVEL="INFO"
            export AUTO_STOP="suspend"
            export MIN_MACHINES="1"
            ;;
        "prod")
            export FLY_CONFIG="fly.prod.toml"
            export LOG_LEVEL="WARNING"
            export AUTO_STOP="false"
            export MIN_MACHINES="2"
            ;;
    esac
}

# Deploy infrastructure services (database, NATS)
deploy_infrastructure() {
    local env=$1
    print_header "Deploying infrastructure for $env environment"
    
    # Deploy PostgreSQL database
    print_status "Deploying PostgreSQL database..."
    if ! flyctl apps list | grep -q "gaia-db-$env"; then
        print_status "Creating new database app: gaia-db-$env"
        flyctl apps create "gaia-db-$env"
        flyctl postgres create --name "gaia-db-$env" --region sjc
    else
        print_status "Database app gaia-db-$env already exists"
    fi
    
    # Deploy NATS message broker
    print_status "Deploying NATS message broker..."
    if ! flyctl apps list | grep -q "gaia-nats-$env"; then
        print_status "Creating new NATS app: gaia-nats-$env"
        flyctl apps create "gaia-nats-$env"
        # Note: NATS deployment would need a custom Dockerfile
        print_warning "NATS deployment not yet implemented - using external NATS service"
    else
        print_status "NATS app gaia-nats-$env already exists"
    fi
}

# Deploy a specific service
deploy_service() {
    local env=$1
    local service=$2
    local app_name="gaia-$service-$env"
    
    print_header "Deploying $service service to $env environment"
    
    # Check if app exists
    if ! flyctl apps list | grep -q "$app_name"; then
        print_status "Creating new app: $app_name"
        flyctl apps create "$app_name"
    fi
    
    # Set secrets for the environment
    print_status "Setting secrets for $app_name..."
    setup_secrets "$app_name" "$env"
    
    # Deploy the service
    print_status "Deploying $app_name..."
    cd "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "DRY RUN: Would deploy $app_name with config $FLY_CONFIG"
        return 0
    fi
    
    if [[ "$SKIP_BUILD" != "true" ]]; then
        flyctl deploy --config "$FLY_CONFIG" --app "$app_name"
    else
        flyctl deploy --config "$FLY_CONFIG" --app "$app_name" --no-build-cache
    fi
    
    # Verify deployment
    print_status "Verifying deployment..."
    if flyctl status --app "$app_name" | grep -q "running"; then
        print_status "✅ $app_name deployed successfully"
        
        # Show app URL
        local app_url=$(flyctl info --app "$app_name" --json | jq -r '.Hostname')
        if [[ "$app_url" != "null" ]]; then
            print_status "🌐 App URL: https://$app_url"
        fi
    else
        print_error "❌ $app_name deployment failed"
        return 1
    fi
}

# Setup secrets for an app
setup_secrets() {
    local app_name=$1
    local env=$2
    
    print_status "Setting up secrets for $app_name..."
    
    # Common secrets for all environments
    if [[ -n "$API_KEY" ]]; then
        flyctl secrets set API_KEY="$API_KEY" --app "$app_name"
    fi
    
    if [[ -n "$OPENAI_API_KEY" ]]; then
        flyctl secrets set OPENAI_API_KEY="$OPENAI_API_KEY" --app "$app_name"
    fi
    
    if [[ -n "$ANTHROPIC_API_KEY" ]]; then
        flyctl secrets set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" --app "$app_name"
    fi
    
    # Environment-specific database URL
    local db_url=$(get_database_url "$env")
    if [[ -n "$db_url" ]]; then
        flyctl secrets set DATABASE_URL="$db_url" --app "$app_name"
    fi
    
    # Environment-specific NATS URL
    local nats_url="nats://gaia-nats-$env.fly.dev:4222"
    flyctl secrets set NATS_URL="$nats_url" --app "$app_name"
}

# Get database URL for environment
get_database_url() {
    local env=$1
    # This would be configured based on your database setup
    echo "postgresql://postgres:password@gaia-db-$env.fly.dev:5432/llm_platform"
}

# Rollback deployment
rollback_deployment() {
    local env=$1
    local service=$2
    local app_name="gaia-$service-$env"
    
    print_header "Rolling back $service in $env environment"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_status "DRY RUN: Would rollback $app_name"
        return 0
    fi
    
    flyctl releases list --app "$app_name" | head -5
    read -p "Enter the release version to rollback to: " release_version
    
    if [[ -n "$release_version" ]]; then
        flyctl releases rollback "$release_version" --app "$app_name"
        print_status "✅ Rolled back $app_name to version $release_version"
    else
        print_warning "No release version specified, skipping rollback"
    fi
}

# Health check after deployment
health_check() {
    local env=$1
    local service=$2
    local app_name="gaia-$service-$env"
    
    print_status "Performing health check for $app_name..."
    
    local app_url=$(flyctl info --app "$app_name" --json | jq -r '.Hostname')
    if [[ "$app_url" != "null" ]]; then
        local health_url="https://$app_url/health"
        print_status "Checking health endpoint: $health_url"
        
        if curl -s -f "$health_url" > /dev/null; then
            print_status "✅ Health check passed for $app_name"
        else
            print_warning "⚠️ Health check failed for $app_name"
        fi
    else
        print_warning "Could not determine app URL for health check"
    fi
}

# Main deployment orchestration
main() {
    local environment=""
    local service="all"
    local dry_run=false
    local skip_build=false
    local force=false
    local rollback=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|staging|prod)
                environment="$1"
                shift
                ;;
            gateway|auth|asset|chat|all)
                service="$1"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --skip-build)
                skip_build=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --rollback)
                rollback=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$environment" ]]; then
        print_error "Environment is required"
        usage
        exit 1
    fi
    
    validate_environment "$environment"
    validate_service "$service"
    
    # Set global variables
    export DRY_RUN="$dry_run"
    export SKIP_BUILD="$skip_build"
    export FORCE="$force"
    
    print_header "Gaia Platform Deployment to $environment"
    print_status "Service(s): $service"
    print_status "Options: dry-run=$dry_run, skip-build=$skip_build, force=$force, rollback=$rollback"
    
    # Check prerequisites
    check_prerequisites
    
    # Set environment configuration
    set_environment_config "$environment"
    
    # Handle rollback
    if [[ "$rollback" == "true" ]]; then
        if [[ "$service" == "all" ]]; then
            for svc in "${SERVICES[@]}"; do
                rollback_deployment "$environment" "$svc"
            done
        else
            rollback_deployment "$environment" "$service"
        fi
        exit 0
    fi
    
    # Deploy infrastructure first
    if [[ "$service" == "all" ]] || [[ "$force" == "true" ]]; then
        deploy_infrastructure "$environment"
    fi
    
    # Deploy services
    if [[ "$service" == "all" ]]; then
        # Deploy services in order (auth first, then others)
        deploy_service "$environment" "auth"
        deploy_service "$environment" "gateway"
        deploy_service "$environment" "asset"
        deploy_service "$environment" "chat"
        
        # Health checks for all services
        for svc in "${SERVICES[@]}"; do
            health_check "$environment" "$svc"
        done
    else
        deploy_service "$environment" "$service"
        health_check "$environment" "$service"
    fi
    
    print_header "🚀 Deployment to $environment environment completed!"
    print_status "Monitor your deployment with: flyctl logs --app gaia-gateway-$environment"
    print_status "Check app status with: flyctl status --app gaia-gateway-$environment"
}

# Execute main function with all arguments
main "$@"