#!/bin/bash

# Supabase Multi-Environment Setup Script
# Usage: ./scripts/setup-supabase-env.sh [environment] [action]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Function to display usage
usage() {
    echo "Usage: $0 [environment] [action]"
    echo ""
    echo "Environments:"
    echo "  local     - Local development (uses dev Supabase project)"
    echo "  dev       - Cloud development"
    echo "  staging   - Staging deployment"
    echo "  prod      - Production deployment"
    echo ""
    echo "Actions:"
    echo "  info      - Show configuration info for environment"
    echo "  setup     - Interactive setup for environment"
    echo "  validate  - Validate current configuration"
    echo "  urls      - Show expected URLs for Supabase configuration"
    echo ""
    echo "Examples:"
    echo "  $0 local setup    - Set up local development"
    echo "  $0 staging info   - Show staging configuration"
    echo "  $0 prod validate  - Validate production setup"
    exit 1
}

# Function to get environment URLs
get_environment_urls() {
    local env=$1
    
    case $env in
        "local")
            SITE_URL="http://localhost:8080"
            FLY_APP=""
            ;;
        "dev")
            SITE_URL="https://gaia-web-dev.fly.dev"
            FLY_APP="gaia-web-dev"
            ;;
        "staging")
            SITE_URL="https://gaia-web-staging.fly.dev"
            FLY_APP="gaia-web-staging"
            ;;
        "prod")
            SITE_URL="https://gaia-web-production.fly.dev"
            FLY_APP="gaia-web-production"
            ;;
        *)
            print_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Function to show configuration info
show_info() {
    local env=$1
    get_environment_urls $env
    
    print_info "Configuration for $env environment:"
    echo ""
    echo "Supabase Project Name: gaia-$env"
    echo "Site URL: $SITE_URL"
    echo "Redirect URLs:"
    echo "  - $SITE_URL/auth/confirm"
    echo "  - $SITE_URL/auth/callback"
    echo "  - $SITE_URL/"
    
    if [ "$env" = "local" ]; then
        echo ""
        print_warning "Local development uses the dev Supabase project"
        echo "Also add localhost URLs to dev project:"
        echo "  - http://localhost:8080/auth/confirm"
        echo "  - http://localhost:8080/auth/callback"
        echo "  - http://localhost:8080/"
    fi
    
    if [ -n "$FLY_APP" ]; then
        echo ""
        echo "Fly.io App: $FLY_APP"
        echo "Set secrets with:"
        echo "  fly secrets set -a $FLY_APP \\"
        echo "    \"SUPABASE_URL=https://[project-id].supabase.co\" \\"
        echo "    \"SUPABASE_ANON_KEY=[anon-key]\" \\"
        echo "    \"SUPABASE_JWT_SECRET=[jwt-secret]\""
    fi
}

# Function to show URLs for Supabase configuration
show_urls() {
    local env=$1
    get_environment_urls $env
    
    print_info "URLs to configure in Supabase dashboard for $env:"
    echo ""
    echo "🌐 Site URL:"
    echo "$SITE_URL"
    echo ""
    echo "🔗 Redirect URLs (add all of these):"
    echo "$SITE_URL/auth/confirm"
    echo "$SITE_URL/auth/callback"
    echo "$SITE_URL/"
    
    if [ "$env" = "local" ]; then
        echo ""
        print_warning "For local development, also add these to the dev project:"
        echo "http://localhost:8080/auth/confirm"
        echo "http://localhost:8080/auth/callback"
        echo "http://localhost:8080/"
    fi
}

# Function for interactive setup
interactive_setup() {
    local env=$1
    get_environment_urls $env
    
    print_info "Setting up $env environment..."
    echo ""
    
    # Show what needs to be configured
    print_info "Step 1: Create Supabase project 'gaia-$env'"
    echo "Go to: https://supabase.com/dashboard"
    echo "Create new project with name: gaia-$env"
    echo ""
    
    print_info "Step 2: Configure authentication settings"
    show_urls $env
    echo ""
    print_warning "Configure these URLs in Supabase Authentication → Settings"
    echo ""
    
    # Get credentials from user
    print_info "Step 3: Enter Supabase credentials"
    echo ""
    
    read -p "Project URL (https://[project-id].supabase.co): " SUPABASE_URL
    read -p "Anon/Public Key: " SUPABASE_ANON_KEY
    read -p "JWT Secret: " SUPABASE_JWT_SECRET
    
    # Validate inputs
    if [[ ! $SUPABASE_URL =~ ^https://.*\.supabase\.co$ ]]; then
        print_error "Invalid Supabase URL format"
        exit 1
    fi
    
    if [ ${#SUPABASE_ANON_KEY} -lt 100 ]; then
        print_error "Anon key seems too short"
        exit 1
    fi
    
    if [ ${#SUPABASE_JWT_SECRET} -lt 32 ]; then
        print_error "JWT secret seems too short"
        exit 1
    fi
    
    # Apply configuration
    if [ "$env" = "local" ]; then
        print_info "Updating local .env file..."
        
        # Backup existing .env
        if [ -f "$PROJECT_ROOT/.env" ]; then
            cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.backup.$(date +%s)"
        fi
        
        # Update .env file
        if [ -f "$PROJECT_ROOT/.env" ]; then
            # Update existing values
            sed -i.bak "s|^SUPABASE_URL=.*|SUPABASE_URL=$SUPABASE_URL|" "$PROJECT_ROOT/.env"
            sed -i.bak "s|^SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|" "$PROJECT_ROOT/.env"
            sed -i.bak "s|^SUPABASE_JWT_SECRET=.*|SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET|" "$PROJECT_ROOT/.env"
            rm "$PROJECT_ROOT/.env.bak"
        else
            print_error ".env file not found"
            exit 1
        fi
        
        print_success "Local configuration updated!"
        print_info "Restart services: docker compose restart"
        
    else
        print_info "Setting Fly.io secrets for $FLY_APP..."
        
        fly secrets set -a "$FLY_APP" \
            "ENVIRONMENT=$env" \
            "SUPABASE_URL=$SUPABASE_URL" \
            "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
            "SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET"
        
        print_success "Fly.io secrets set for $env environment!"
        print_info "Deploy the app: fly deploy -a $FLY_APP"
    fi
    
    echo ""
    print_success "Setup complete for $env environment!"
    print_info "Test with: $0 $env validate"
}

# Function to validate configuration
validate_config() {
    local env=$1
    get_environment_urls $env
    
    print_info "Validating $env environment configuration..."
    
    if [ "$env" = "local" ]; then
        # Check local .env file
        if [ ! -f "$PROJECT_ROOT/.env" ]; then
            print_error ".env file not found"
            exit 1
        fi
        
        source "$PROJECT_ROOT/.env"
        
        if [ -z "$SUPABASE_URL" ]; then
            print_error "SUPABASE_URL not set in .env"
            exit 1
        fi
        
        if [ -z "$SUPABASE_ANON_KEY" ]; then
            print_error "SUPABASE_ANON_KEY not set in .env"
            exit 1
        fi
        
        if [ -z "$SUPABASE_JWT_SECRET" ]; then
            print_error "SUPABASE_JWT_SECRET not set in .env"
            exit 1
        fi
        
        print_success "Local configuration is valid"
        
        # Test local service
        print_info "Testing local service..."
        if curl -s -f http://localhost:8080/health >/dev/null; then
            print_success "Local service is responding"
        else
            print_warning "Local service not responding (may not be running)"
        fi
        
    else
        # Check Fly.io app exists
        if ! fly apps list | grep -q "$FLY_APP"; then
            print_error "Fly.io app $FLY_APP not found"
            exit 1
        fi
        
        print_success "Fly.io app $FLY_APP exists"
        
        # Test remote service
        print_info "Testing remote service..."
        if curl -s -f "$SITE_URL/health" >/dev/null; then
            print_success "Remote service is responding"
        else
            print_warning "Remote service not responding"
        fi
    fi
    
    print_success "Validation complete for $env environment"
}

# Main script logic
if [ $# -ne 2 ]; then
    usage
fi

ENVIRONMENT=$1
ACTION=$2

# Validate environment
case $ENVIRONMENT in
    local|dev|staging|prod) ;;
    *) print_error "Invalid environment: $ENVIRONMENT"; usage ;;
esac

# Validate action
case $ACTION in
    info|setup|validate|urls) ;;
    *) print_error "Invalid action: $ACTION"; usage ;;
esac

# Execute action
case $ACTION in
    "info")
        show_info $ENVIRONMENT
        ;;
    "setup")
        interactive_setup $ENVIRONMENT
        ;;
    "validate")
        validate_config $ENVIRONMENT
        ;;
    "urls")
        show_urls $ENVIRONMENT
        ;;
esac