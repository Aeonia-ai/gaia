#!/bin/bash
# Secret Validation and Synchronization Script
# Helps prevent and diagnose secret management issues

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ENVIRONMENT=""
COMPARE_ENV=""
FIX_MODE=false
CHECK_ONLY=false

function print_usage() {
    echo "Usage: $0 --env {dev|staging|production} [options]"
    echo ""
    echo "Options:"
    echo "  --env ENVIRONMENT           # Target environment to validate"
    echo "  --compare ENV2              # Compare secrets with another environment"
    echo "  --fix                       # Automatically fix detected issues"
    echo "  --check-only                # Only check, don't fix (for production)"
    echo "  --help                      # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev                # Validate dev environment secrets"
    echo "  $0 --env dev --fix          # Validate and fix dev environment"
    echo "  $0 --compare dev staging    # Compare secrets between environments"
    echo "  $0 --env production --check-only  # Check production (no fixes)"
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
        --compare)
            COMPARE_ENV="$2"
            shift 2
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
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

# Validate arguments
if [[ -z "$ENVIRONMENT" && -z "$COMPARE_ENV" ]]; then
    log_error "Environment is required"
    print_usage
    exit 1
fi

if [[ "$CHECK_ONLY" == "true" && "$FIX_MODE" == "true" ]]; then
    log_error "Cannot use --check-only and --fix together"
    exit 1
fi

function check_prerequisites() {
    log_step "Checking prerequisites..."
    
    if ! command -v fly &> /dev/null; then
        log_error "Fly CLI is not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed (required for JSON parsing)"
        exit 1
    fi
    
    if [[ ! -f ".env" ]]; then
        log_error ".env file not found in current directory"
        exit 1
    fi
    
    log_info "✅ Prerequisites met"
}

function get_local_secret() {
    local secret_name=$1
    grep "^${secret_name}=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo ""
}

function get_deployed_secret_info() {
    local app_name=$1
    local secret_name=$2
    
    # Get secret list with timestamps
    fly secrets list -a "$app_name" --json 2>/dev/null | jq -r ".[] | select(.name == \"$secret_name\") | .created_at" || echo ""
}

function validate_environment_secrets() {
    local env=$1
    local fix_mode=$2
    
    log_step "Validating $env environment secrets..."
    
    local auth_app="gaia-auth-$env"
    local web_app="gaia-web-$env"
    
    # Check if apps exist
    if ! fly apps list | grep -q "$auth_app"; then
        log_error "Auth app $auth_app does not exist"
        return 1
    fi
    
    local issues_found=0
    local fixes_applied=0
    
    # Required secrets for auth service
    local auth_secrets=("SUPABASE_URL" "SUPABASE_ANON_KEY" "SUPABASE_JWT_SECRET")
    
    for secret in "${auth_secrets[@]}"; do
        local local_value=$(get_local_secret "$secret")
        local deployed_timestamp=$(get_deployed_secret_info "$auth_app" "$secret")
        
        if [[ -z "$local_value" ]]; then
            log_error "❌ $secret not found in .env file"
            ((issues_found++))
            continue
        fi
        
        if [[ -z "$deployed_timestamp" ]]; then
            log_error "❌ $secret not deployed to $auth_app"
            ((issues_found++))
            
            if [[ "$fix_mode" == "true" ]]; then
                log_info "🔧 Deploying $secret to $auth_app..."
                echo "$local_value" | fly secrets set "${secret}=-" -a "$auth_app" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    log_info "✅ Fixed: $secret deployed to $auth_app"
                    ((fixes_applied++))
                else
                    log_error "❌ Failed to deploy $secret to $auth_app"
                fi
            fi
        else
            # Check if secret is recent (within 7 days)
            local secret_age_days=$(( ($(date +%s) - $(date -d "$deployed_timestamp" +%s)) / 86400 ))
            if [[ $secret_age_days -gt 7 ]]; then
                log_warn "⚠️  $secret in $auth_app is $secret_age_days days old"
            else
                log_info "✅ $secret in $auth_app is current ($secret_age_days days old)"
            fi
        fi
    done
    
    # Check web service API_KEY
    if fly apps list | grep -q "$web_app"; then
        local api_key=$(get_local_secret "API_KEY")
        local web_api_timestamp=$(get_deployed_secret_info "$web_app" "API_KEY")
        
        if [[ -z "$api_key" ]]; then
            log_error "❌ API_KEY not found in .env file"
            ((issues_found++))
        elif [[ -z "$web_api_timestamp" ]]; then
            log_error "❌ API_KEY not deployed to $web_app"
            ((issues_found++))
            
            if [[ "$fix_mode" == "true" ]]; then
                log_info "🔧 Deploying API_KEY to $web_app..."
                echo "$api_key" | fly secrets set "API_KEY=-" -a "$web_app" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    log_info "✅ Fixed: API_KEY deployed to $web_app"
                    ((fixes_applied++))
                else
                    log_error "❌ Failed to deploy API_KEY to $web_app"
                fi
            fi
        else
            log_info "✅ API_KEY in $web_app is deployed"
        fi
    fi
    
    # Check auth service health for secret validation
    log_step "Checking auth service secrets health..."
    local health_url="https://$auth_app.fly.dev/health"
    local health_response=$(curl -s "$health_url" 2>/dev/null)
    
    if [[ -n "$health_response" ]]; then
        local secrets_status=$(echo "$health_response" | jq -r '.secrets.status // "unknown"' 2>/dev/null)
        
        case "$secrets_status" in
            "healthy")
                log_info "✅ Auth service reports secrets as healthy"
                ;;
            "warning")
                log_warn "⚠️  Auth service reports secrets warnings:"
                echo "$health_response" | jq '.secrets.warnings[]?' 2>/dev/null || true
                ((issues_found++))
                ;;
            "unhealthy")
                log_error "❌ Auth service reports secrets as unhealthy:"
                echo "$health_response" | jq '.secrets.error?' 2>/dev/null || true
                ((issues_found++))
                ;;
            "unknown")
                log_warn "⚠️  Unable to determine secrets health (service may be old version)"
                ;;
        esac
    else
        log_error "❌ Unable to reach auth service health endpoint"
        ((issues_found++))
    fi
    
    # Summary
    echo ""
    if [[ $issues_found -eq 0 ]]; then
        log_info "🎉 All secrets validated successfully for $env environment"
    else
        log_warn "⚠️  Found $issues_found issues in $env environment"
        
        if [[ "$fix_mode" == "true" ]]; then
            log_info "🔧 Applied $fixes_applied fixes"
            if [[ $fixes_applied -gt 0 ]]; then
                log_info "💤 Waiting 30 seconds for services to restart..."
                sleep 30
                
                # Re-check health
                log_step "Re-checking auth service health after fixes..."
                health_response=$(curl -s "$health_url" 2>/dev/null)
                if [[ -n "$health_response" ]]; then
                    secrets_status=$(echo "$health_response" | jq -r '.secrets.status // "unknown"' 2>/dev/null)
                    if [[ "$secrets_status" == "healthy" ]]; then
                        log_info "✅ Auth service now reports secrets as healthy"
                    else
                        log_warn "⚠️  Auth service still reports issues - may need manual intervention"
                    fi
                fi
            fi
        elif [[ "$CHECK_ONLY" != "true" ]]; then
            log_info "💡 Run with --fix to automatically resolve issues"
        fi
    fi
    
    return $issues_found
}

function compare_environments() {
    local env1=$1
    local env2=$2
    
    log_step "Comparing secrets between $env1 and $env2..."
    
    local auth_app1="gaia-auth-$env1"
    local auth_app2="gaia-auth-$env2"
    
    # Check SUPABASE_URL (should be the same across environments)
    local url1_timestamp=$(get_deployed_secret_info "$auth_app1" "SUPABASE_URL")
    local url2_timestamp=$(get_deployed_secret_info "$auth_app2" "SUPABASE_URL")
    
    if [[ -n "$url1_timestamp" && -n "$url2_timestamp" ]]; then
        local url1_age=$(( ($(date +%s) - $(date -d "$url1_timestamp" +%s)) / 86400 ))
        local url2_age=$(( ($(date +%s) - $(date -d "$url2_timestamp" +%s)) / 86400 ))
        local age_diff=$((url1_age - url2_age))
        
        if [[ ${age_diff#-} -gt 1 ]]; then  # Absolute difference > 1 day
            log_warn "⚠️  SUPABASE_URL age differs significantly:"
            log_warn "   $env1: $url1_age days old"
            log_warn "   $env2: $url2_age days old"
        else
            log_info "✅ SUPABASE_URL timestamps are similar between environments"
        fi
    fi
    
    # Compare other secrets similarly
    for secret in "SUPABASE_ANON_KEY" "SUPABASE_JWT_SECRET"; do
        local ts1=$(get_deployed_secret_info "$auth_app1" "$secret")
        local ts2=$(get_deployed_secret_info "$auth_app2" "$secret")
        
        if [[ -n "$ts1" && -n "$ts2" ]]; then
            local age1=$(( ($(date +%s) - $(date -d "$ts1" +%s)) / 86400 ))
            local age2=$(( ($(date +%s) - $(date -d "$ts2" +%s)) / 86400 ))
            
            log_info "$secret ages: $env1=$age1 days, $env2=$age2 days"
        else
            log_warn "⚠️  $secret missing in one or both environments"
        fi
    done
}

function main() {
    log_info "🔐 Secret Validation Tool"
    echo ""
    
    check_prerequisites
    
    if [[ -n "$COMPARE_ENV" ]]; then
        if [[ -z "$ENVIRONMENT" ]]; then
            log_error "Must specify --env when using --compare"
            exit 1
        fi
        compare_environments "$ENVIRONMENT" "$COMPARE_ENV"
    else
        local fix_flag=false
        if [[ "$FIX_MODE" == "true" && "$CHECK_ONLY" != "true" ]]; then
            fix_flag=true
        fi
        
        validate_environment_secrets "$ENVIRONMENT" "$fix_flag"
    fi
}

# Run main function
main "$@"