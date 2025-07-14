#!/bin/bash
# Database Initialization Script for Gaia Platform
# Creates users and associates API keys with them

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

function print_usage() {
    echo "Usage: $0 --env {local|dev|staging|production} [options]"
    echo ""
    echo "Options:"
    echo "  --env ENVIRONMENT    # Target environment database"
    echo "  --user EMAIL         # User email (default: admin@gaia.dev)"
    echo "  --api-key KEY        # API key to associate (default: from .env)"
    echo "  --help               # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev                                    # Initialize dev with default user/key"
    echo "  $0 --env staging --user admin@company.com      # Custom user email"
    echo "  $0 --env production --user prod@company.com    # Production user"
}

# Default values
ENVIRONMENT=""
USER_EMAIL="admin@gaia.dev"
USER_NAME="Gaia Admin"
API_KEY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --user)
            USER_EMAIL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
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
    log_error "Environment is required. Use --env local|dev|staging|production"
    print_usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "local" && "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Environment must be 'local', 'dev', 'staging', or 'production'"
    exit 1
fi

# Get API key from .env if not provided
if [[ -z "$API_KEY" ]]; then
    if [ -f ".env" ]; then
        API_KEY=$(grep -E '^API_KEY=' .env | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    fi
    
    if [[ -z "$API_KEY" ]]; then
        log_error "API_KEY not found. Provide --api-key or set API_KEY in .env file"
        exit 1
    fi
fi

log_step "Initializing $ENVIRONMENT database with user authentication"
log_info "User: $USER_EMAIL"
log_info "API Key: ${API_KEY:0:8}..."

# Create initialization SQL
cat > /tmp/init_gaia_db.sql << EOF
-- Gaia Platform Database Initialization
-- Creates user and associates API key following new authentication pattern

-- Create tables if they don't exist (based on security.py expectations)
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Insert user (if not exists)
INSERT INTO users (id, email, name, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    '$USER_EMAIL',
    '$USER_NAME',
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING;

-- Get user ID for API key association
WITH user_data AS (
    SELECT id FROM users WHERE email = '$USER_EMAIL'
)
-- Insert API key associated with user (if not exists)
-- Note: Using SHA256 hash as expected by security.py
INSERT INTO api_keys (id, user_id, key_hash, name, permissions, created_at, updated_at, is_active)
SELECT 
    gen_random_uuid(),
    user_data.id,
    encode(sha256('$API_KEY'::bytea), 'hex'),  -- Hash the API key
    'Default API Key',
    '{}',
    NOW(),
    NOW(),
    true
FROM user_data
ON CONFLICT (key_hash) DO NOTHING;

-- Verify the setup
SELECT 
    u.email,
    u.name,
    ak.name as api_key_name,
    ak.is_active,
    ak.created_at,
    'API Key: $API_KEY (first 8 chars)' as note
FROM users u
JOIN api_keys ak ON u.id = ak.user_id
WHERE u.email = '$USER_EMAIL';
EOF

# Execute based on environment
case $ENVIRONMENT in
    "local")
        log_info "Connecting to local database..."
        if docker compose ps db | grep -q "Up"; then
            docker compose exec db psql -U postgres -d postgres -f /tmp/init_gaia_db.sql
        else
            log_error "Local database not running. Start with: docker compose up db"
            exit 1
        fi
        ;;
    "dev")
        log_info "Connecting to dev database..."
        log_info "Executing SQL initialization via fly postgres connect..."
        
        # Use fly postgres connect with stdin input
        if cat /tmp/init_gaia_db.sql | fly postgres connect -a gaia-db-dev; then
            log_info "✅ Dev database initialized successfully"
        else
            log_error "Failed to initialize dev database"
            exit 1
        fi
        ;;
    "staging")
        log_info "Connecting to staging database..."
        # Note: Staging might use the shared database, need to check connection string
        log_error "Staging database initialization not implemented yet"
        log_error "Need to determine staging database connection method"
        exit 1
        ;;
    "production")
        log_info "Connecting to production database..."
        log_error "Production database initialization requires manual verification"
        log_error "Use staging database initialization as reference"
        exit 1
        ;;
esac

# Cleanup
rm -f /tmp/init_gaia_db.sql

log_info "🎉 Database initialization complete!"
log_info "User '$USER_EMAIL' can now authenticate with API key: ${API_KEY:0:8}..."
log_info ""
log_info "Test the setup:"
log_info "  ./scripts/test.sh --$ENVIRONMENT providers"