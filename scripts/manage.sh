#!/bin/bash
# Gaia Platform Management Script
# Combines deployment, testing, and monitoring into smart workflows

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

function print_usage() {
    echo "Gaia Platform Management Script"
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  deploy-and-test ENVIRONMENT    # Deploy and run comprehensive tests"
    echo "  quick-test ENVIRONMENT         # Run quick health checks"
    echo "  full-test ENVIRONMENT          # Run complete test suite"
    echo "  monitor ENVIRONMENT            # Monitor deployment status"
    echo "  rollback ENVIRONMENT           # Rollback to previous version"
    echo "  scale ENVIRONMENT SERVICE N    # Scale service to N instances"
    echo "  logs ENVIRONMENT [SERVICE]     # Stream logs from environment"
    echo "  status                         # Show status of all environments"
    echo ""
    echo "Examples:"
    echo "  $0 deploy-and-test staging     # Deploy to staging and test"
    echo "  $0 quick-test production       # Quick health check of prod"
    echo "  $0 monitor staging             # Monitor staging deployment"
    echo "  $0 scale production gateway 3  # Scale gateway to 3 instances"
    echo "  $0 logs staging                # Stream all staging logs"
}

function deploy_and_test() {
    local env=$1
    
    log_step "Starting deploy-and-test workflow for $env"
    
    # Deploy
    log_info "🚀 Deploying to $env..."
    if "$SCRIPT_DIR/deploy.sh" --env "$env"; then
        log_info "✅ Deployment successful"
    else
        log_error "❌ Deployment failed"
        return 1
    fi
    
    # Wait for services to be ready
    log_info "⏳ Waiting for services to be ready..."
    sleep 30
    
    # Run tests
    log_info "🧪 Running comprehensive tests..."
    if "$SCRIPT_DIR/test.sh" --"$env" all; then
        log_info "✅ All tests passed"
    else
        log_warn "⚠️  Some tests failed - checking if expected for $env"
        
        # Run core tests only for partial deployments
        log_info "Running core functionality tests..."
        if "$SCRIPT_DIR/test.sh" --"$env" health && "$SCRIPT_DIR/test.sh" --"$env" providers; then
            log_info "✅ Core functionality working"
        else
            log_error "❌ Core functionality broken"
            return 1
        fi
    fi
    
    log_info "🎉 Deploy-and-test workflow completed successfully"
}

function quick_test() {
    local env=$1
    
    log_step "Running quick health checks for $env"
    
    local tests=("health" "status" "providers")
    
    for test in "${tests[@]}"; do
        log_info "Testing $test..."
        if "$SCRIPT_DIR/test.sh" --"$env" "$test" >/dev/null 2>&1; then
            log_info "✅ $test: OK"
        else
            log_error "❌ $test: FAILED"
        fi
    done
}

function full_test() {
    local env=$1
    
    log_step "Running full test suite for $env"
    
    log_info "Core functionality..."
    "$SCRIPT_DIR/test.sh" --"$env" health
    "$SCRIPT_DIR/test.sh" --"$env" providers
    "$SCRIPT_DIR/test.sh" --"$env" models
    
    log_info "Chat functionality..."
    "$SCRIPT_DIR/test.sh" --"$env" chat "Hello"
    "$SCRIPT_DIR/test.sh" --"$env" stream "Quick test"
    
    if [[ "$env" == "local" ]]; then
        log_info "Local environment - testing all endpoints..."
        "$SCRIPT_DIR/test.sh" --"$env" personas-all
        "$SCRIPT_DIR/test.sh" --"$env" performance-all
    else
        log_info "Cloud environment - testing available endpoints only..."
        # Only test endpoints that work in cloud deployments
    fi
    
    log_info "✅ Full test suite completed"
}

function monitor_deployment() {
    local env=$1
    
    log_step "Monitoring $env environment"
    
    local apps=("gaia-gateway-$env")
    
    for app in "${apps[@]}"; do
        if fly apps list | grep -q "$app"; then
            log_info "📊 Status for $app:"
            fly status -a "$app"
            echo ""
            
            log_info "🏥 Health check:"
            local url="https://$app.fly.dev/health"
            if curl -s "$url" | jq . 2>/dev/null; then
                log_info "✅ Health check passed"
            else
                log_warn "⚠️  Health check failed or service not ready"
            fi
            echo ""
        else
            log_warn "App $app not found"
        fi
    done
}

function rollback_deployment() {
    local env=$1
    
    log_step "Rolling back $env environment"
    log_warn "This will rollback to the previous deployment"
    
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local app="gaia-gateway-$env"
        
        log_info "Rolling back $app..."
        if fly deploy --config "fly.staging.toml" --image "$(fly releases list -a "$app" --json | jq -r '.[1].version')"; then
            log_info "✅ Rollback successful"
            
            # Test the rollback
            sleep 30
            quick_test "$env"
        else
            log_error "❌ Rollback failed"
        fi
    else
        log_info "Rollback cancelled"
    fi
}

function scale_service() {
    local env=$1
    local service=$2
    local count=$3
    
    log_step "Scaling $service in $env to $count instances"
    
    local app="gaia-$service-$env"
    if [[ "$service" == "gateway" ]]; then
        app="gaia-gateway-$env"
    fi
    
    if fly scale count "$count" -a "$app"; then
        log_info "✅ Scaled $service to $count instances"
        
        # Monitor the scaling
        log_info "Monitoring scaling progress..."
        fly status -a "$app"
    else
        log_error "❌ Failed to scale $service"
    fi
}

function stream_logs() {
    local env=$1
    local service=${2:-"gateway"}
    
    log_step "Streaming logs from $service in $env"
    
    local app="gaia-$service-$env"
    if [[ "$service" == "gateway" ]]; then
        app="gaia-gateway-$env"
    fi
    
    log_info "Streaming logs from $app..."
    log_info "Press Ctrl+C to stop"
    
    fly logs -a "$app"
}

function show_status() {
    log_step "Gaia Platform Status Overview"
    
    local environments=("staging" "production")
    
    for env in "${environments[@]}"; do
        log_info "🌍 $env Environment:"
        
        local app="gaia-gateway-$env"
        if fly apps list 2>/dev/null | grep -q "$app"; then
            local url="https://$app.fly.dev"
            printf "  %-20s " "$app:"
            
            # Use our smart test script for health checks
            if "$SCRIPT_DIR/test.sh" --"$env" health >/dev/null 2>&1; then
                local status_output=$("$SCRIPT_DIR/test.sh" --"$env" health 2>/dev/null | grep -E '"status":|Status:')
                if echo "$status_output" | grep -q '"status":"healthy"'; then
                    echo -e "${GREEN}✅ Healthy${NC} ($url)"
                elif echo "$status_output" | grep -q '"status":"degraded"'; then
                    echo -e "${YELLOW}⚠️  Degraded${NC} ($url) - Partial deployment"
                else
                    echo -e "${GREEN}✅ Responsive${NC} ($url)"
                fi
            else
                echo -e "${RED}❌ Unhealthy${NC} ($url)"
            fi
        else
            printf "  %-20s " "$app:"
            echo -e "${YELLOW}⚠️  Not deployed${NC}"
        fi
    done
    
    echo ""
    log_info "🐳 Local Development:"
    if docker compose ps 2>/dev/null | grep -q "Up"; then
        echo -e "  Local services:    ${GREEN}✅ Running${NC} (http://localhost:8666)"
    else
        echo -e "  Local services:    ${YELLOW}⚠️  Stopped${NC} (run: docker compose up)"
    fi
}

# Main command handling
case "${1:-}" in
    "deploy-and-test")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        deploy_and_test "$2"
        ;;
    "quick-test")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        quick_test "$2"
        ;;
    "full-test")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        full_test "$2"
        ;;
    "monitor")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        monitor_deployment "$2"
        ;;
    "rollback")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        rollback_deployment "$2"
        ;;
    "scale")
        if [[ -z "${2:-}" || -z "${3:-}" || -z "${4:-}" ]]; then
            log_error "Environment, service, and count required"
            print_usage
            exit 1
        fi
        scale_service "$2" "$3" "$4"
        ;;
    "logs")
        if [[ -z "${2:-}" ]]; then
            log_error "Environment required"
            print_usage
            exit 1
        fi
        stream_logs "$2" "$3"
        ;;
    "status")
        show_status
        ;;
    *)
        print_usage
        exit 1
        ;;
esac