#!/bin/bash
# Create KB volumes for different environments

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
ENVIRONMENT=""
REGION="lax"
SIZE="3"  # GB

function print_usage() {
    echo "Usage: $0 --env {dev|staging|production} [options]"
    echo ""
    echo "Required Options:"
    echo "  --env dev|staging|production  # Target environment"
    echo ""
    echo "Optional Options:"
    echo "  --region REGION              # Fly.io region (default: lax)"
    echo "  --size SIZE                  # Volume size in GB (default: 3)"
    echo "  --help                       # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --env staging             # Create 3GB volume for staging in LAX"
    echo "  $0 --env production --size 5 # Create 5GB volume for production"
}

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
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
        --size)
            SIZE="$2"
            shift 2
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
    log_error "Environment is required"
    print_usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Environment must be 'dev', 'staging', or 'production'"
    exit 1
fi

# Set app name and volume name based on environment
APP_NAME="gaia-kb-$ENVIRONMENT"
VOLUME_NAME="gaia_kb_${ENVIRONMENT}_${SIZE}gb"

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
    
    log_info "✅ All prerequisites met"
}

function check_existing_volume() {
    log_step "Checking for existing volume..."
    
    if fly volumes list -a "$APP_NAME" 2>/dev/null | grep -q "$VOLUME_NAME"; then
        log_info "Volume $VOLUME_NAME already exists for app $APP_NAME"
        return 0
    else
        return 1
    fi
}

function create_volume() {
    log_step "Creating volume $VOLUME_NAME for app $APP_NAME..."
    
    if fly volumes create "$VOLUME_NAME" \
        --region "$REGION" \
        --size "$SIZE" \
        -a "$APP_NAME"; then
        log_info "✅ Successfully created volume $VOLUME_NAME"
        log_info "  App: $APP_NAME"
        log_info "  Region: $REGION"
        log_info "  Size: ${SIZE}GB"
    else
        log_error "❌ Failed to create volume"
        exit 1
    fi
}

function main() {
    log_info "🗄️ KB Volume Creation Tool"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $REGION"
    log_info "Size: ${SIZE}GB"
    echo ""
    
    check_prerequisites
    
    if check_existing_volume; then
        log_info "Volume already exists. No action needed."
        
        # Show volume details
        log_step "Volume details:"
        fly volumes list -a "$APP_NAME" | grep "$VOLUME_NAME"
    else
        create_volume
        
        log_info ""
        log_info "🎉 Volume creation complete!"
        log_info ""
        log_info "Next steps:"
        log_info "1. Set KB secrets:"
        log_info "   fly secrets set KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git -a $APP_NAME"
        log_info "   fly secrets set KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx -a $APP_NAME"
        log_info ""
        log_info "2. Deploy the KB service:"
        log_info "   ./scripts/deploy.sh --env $ENVIRONMENT --services kb --remote-only"
        log_info ""
        log_info "3. If needed, trigger manual clone:"
        log_info "   curl -X POST https://$APP_NAME.fly.dev/trigger-clone"
    fi
}

# Run main function
main "$@"