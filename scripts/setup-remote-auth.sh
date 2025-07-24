#!/bin/bash
# Setup authentication for remote environments
# This creates test users and API keys in remote PostgreSQL databases

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
ENVIRONMENT=""
EMAIL=""
CREATE_API_KEY=true

function print_usage() {
    echo "Usage: $0 --env {dev|staging|production} --email <email> [options]"
    echo ""
    echo "Required Options:"
    echo "  --env dev|staging|production  # Target environment"
    echo "  --email EMAIL                 # User email to create"
    echo ""
    echo "Optional Options:"
    echo "  --no-api-key                  # Don't create API key (JWT only)"
    echo "  --help                        # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev --email jason@aeonia.ai"
    echo "  $0 --env staging --email test@example.com --no-api-key"
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

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --no-api-key)
            CREATE_API_KEY=false
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
    log_error "Environment is required"
    print_usage
    exit 1
fi

if [[ -z "$EMAIL" ]]; then
    log_error "Email is required"
    print_usage
    exit 1
fi

# Get database connection info based on environment
case "$ENVIRONMENT" in
    "dev")
        DB_APP="gaia-db-dev"
        API_KEY_NAME="Dev API Key"
        ;;
    "staging")
        DB_APP="gaia-db-staging"
        API_KEY_NAME="Staging API Key"
        ;;
    "production")
        DB_APP="gaia-db-production"
        API_KEY_NAME="Production API Key"
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

function setup_user() {
    log_step "Setting up user $EMAIL in $ENVIRONMENT environment"
    
    # Generate a random API key
    API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    API_KEY_HASH=$(echo -n "$API_KEY" | sha256sum | cut -d' ' -f1)
    
    log_info "Generated API key: $API_KEY"
    log_info "API key hash: $API_KEY_HASH"
    
    # Create SQL script
    SQL_SCRIPT=$(cat <<'SQLEOF'
-- Setup user for environment
BEGIN;

-- Create user if not exists
INSERT INTO users (email, name, created_at) 
VALUES ('EMAIL_PLACEHOLDER', 'User for EMAIL_PLACEHOLDER', NOW())
ON CONFLICT (email) DO UPDATE
SET updated_at = NOW();

-- Get user ID
DO $$
DECLARE
    user_id_var UUID;
BEGIN
    SELECT id INTO user_id_var FROM users WHERE email = 'EMAIL_PLACEHOLDER';
    
    -- Create API key if requested
    API_KEY_SECTION
    
    -- Grant KB access (if permissions table exists)
    -- This will fail gracefully if the table doesn't exist yet
    BEGIN
        INSERT INTO user_permissions (user_id, permission_name)
        VALUES (user_id_var, 'kb_access')
        ON CONFLICT DO NOTHING;
    EXCEPTION
        WHEN undefined_table THEN
            RAISE NOTICE 'user_permissions table does not exist yet';
    END;
END$$;

COMMIT;

-- Verify setup
SELECT u.email, u.id, ak.name as api_key_name, ak.is_active
FROM users u
LEFT JOIN api_keys ak ON u.id = ak.user_id
WHERE u.email = 'EMAIL_PLACEHOLDER';
SQLEOF
)
    
    # Replace placeholders
    SQL_SCRIPT="${SQL_SCRIPT//EMAIL_PLACEHOLDER/$EMAIL}"
    
    # Add API key section if needed
    if $CREATE_API_KEY; then
        API_KEY_INSERT=$(cat <<APIEOF
INSERT INTO api_keys (user_id, key_hash, name, permissions, is_active)
    VALUES (
        user_id_var,
        '${API_KEY_HASH}',
        '${API_KEY_NAME}',
        '{"environment": "${ENVIRONMENT}"}'::jsonb,
        true
    )
    ON CONFLICT (key_hash) DO UPDATE
    SET is_active = true,
        updated_at = NOW();
APIEOF
)
        SQL_SCRIPT="${SQL_SCRIPT//API_KEY_SECTION/$API_KEY_INSERT}"
    else
        SQL_SCRIPT="${SQL_SCRIPT//API_KEY_SECTION/-- No API key created (JWT only mode)}"
    fi
    
    # Execute SQL on remote database
    log_step "Connecting to remote database..."
    
    # Try to execute the SQL
    if fly postgres connect -a "$DB_APP" <<< "$SQL_SCRIPT" 2>/dev/null; then
        log_info "✅ User setup completed successfully!"
        
        if $CREATE_API_KEY; then
            echo ""
            log_info "======================================"
            log_info "SAVE THIS API KEY (shown only once):"
            log_info "$API_KEY"
            log_info "======================================"
            echo ""
            log_info "Test with:"
            log_info "curl -H \"X-API-Key: $API_KEY\" https://gaia-gateway-$ENVIRONMENT.fly.dev/health"
        else
            log_info "User created for JWT authentication only"
            log_info "Use Supabase auth to get a JWT token"
        fi
    else
        log_error "Failed to setup user in database"
        log_warn "This might be due to:"
        log_warn "1. Database connection issues"
        log_warn "2. Missing database password"
        log_warn "3. Network connectivity"
        echo ""
        log_info "Manual setup instructions:"
        log_info "1. Connect to database: fly postgres connect -a $DB_APP"
        log_info "2. Run the following SQL:"
        echo "$SQL_SCRIPT"
    fi
}

function main() {
    log_info "🔐 Remote Authentication Setup"
    log_info "Environment: $ENVIRONMENT"
    log_info "Email: $EMAIL"
    log_info "Create API Key: $CREATE_API_KEY"
    echo ""
    
    # Check if fly CLI is available
    if ! command -v fly &> /dev/null; then
        log_error "Fly CLI is not installed"
        log_info "Install from: https://fly.io/docs/hands-on/install-flyctl/"
        exit 1
    fi
    
    # Setup the user
    setup_user
    
    echo ""
    log_info "🎉 Setup process completed!"
    
    if $CREATE_API_KEY; then
        log_info "Next steps:"
        log_info "1. Save the API key shown above"
        log_info "2. Test authentication:"
        log_info "   ./scripts/test.sh --url https://gaia-gateway-$ENVIRONMENT.fly.dev kb-search \"test\""
    else
        log_info "Next steps:"
        log_info "1. Login via Supabase to get JWT"
        log_info "2. Use JWT for authentication"
    fi
}

# Run main function
main