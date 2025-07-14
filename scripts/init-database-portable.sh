#!/bin/bash
# Portable Database Initialization Script
# Supports multiple cloud providers and environments

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 --env <environment> --user <admin_email> [--provider <provider>]"
    echo "  --env         Environment: dev, staging, or prod"
    echo "  --user        Admin user email"
    echo "  --provider    Database provider: fly (default), aws, gcp, local"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev --user admin@gaia.dev"
    echo "  $0 --env staging --user admin@gaia.com --provider aws"
    exit 1
}

# Parse command line arguments
ENVIRONMENT=""
ADMIN_EMAIL=""
PROVIDER="fly"

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --user)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENVIRONMENT" || -z "$ADMIN_EMAIL" ]]; then
    echo -e "${RED}Error: Missing required parameters${NC}"
    usage
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment. Must be dev, staging, or prod${NC}"
    exit 1
fi

# Set up database command based on provider
case $PROVIDER in
    fly)
        DATABASE_CMD="fly postgres connect -a gaia-db-${ENVIRONMENT}"
        echo -e "${BLUE}Using Fly.io PostgreSQL for ${ENVIRONMENT}${NC}"
        ;;
    aws)
        # Requires DATABASE_URL to be set
        if [[ -z "$DATABASE_URL" ]]; then
            echo -e "${RED}Error: DATABASE_URL must be set for AWS RDS${NC}"
            exit 1
        fi
        DATABASE_CMD="psql $DATABASE_URL"
        echo -e "${BLUE}Using AWS RDS for ${ENVIRONMENT}${NC}"
        ;;
    gcp)
        DATABASE_CMD="gcloud sql connect gaia-${ENVIRONMENT} --user=postgres"
        echo -e "${BLUE}Using Google Cloud SQL for ${ENVIRONMENT}${NC}"
        ;;
    local)
        DATABASE_CMD="psql postgresql://postgres:postgres@localhost:5432/gaia_${ENVIRONMENT}"
        echo -e "${BLUE}Using local PostgreSQL for ${ENVIRONMENT}${NC}"
        ;;
    *)
        echo -e "${RED}Error: Unknown provider ${PROVIDER}${NC}"
        exit 1
        ;;
esac

# Generate a secure API key for the admin user
ADMIN_API_KEY="gaia-${ENVIRONMENT}-$(openssl rand -hex 32)"
API_KEY_HASH=$(echo -n "$ADMIN_API_KEY" | openssl dgst -sha256 -binary | xxd -p -c 256)

echo -e "${YELLOW}Initializing database for ${ENVIRONMENT} environment...${NC}"

# Create the SQL initialization script
cat > /tmp/init_gaia_portable.sql << EOF
-- Gaia Platform Database Initialization
-- Environment: ${ENVIRONMENT}
-- Provider: ${PROVIDER}
-- Generated: $(date)

BEGIN;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- Create chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(100),
    provider VARCHAR(50),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- Create assets table
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url TEXT,
    metadata JSONB DEFAULT '{}',
    generation_params JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at);

-- Insert admin user if not exists
INSERT INTO users (email, name) 
VALUES ('${ADMIN_EMAIL}', 'Administrator')
ON CONFLICT (email) DO NOTHING;

-- Get the admin user ID
DO \$\$
DECLARE
    admin_user_id UUID;
BEGIN
    SELECT id INTO admin_user_id FROM users WHERE email = '${ADMIN_EMAIL}';
    
    -- Insert API key for admin user
    INSERT INTO api_keys (user_id, key_hash, name, permissions, is_active)
    VALUES (
        admin_user_id,
        '${API_KEY_HASH}',
        'Admin API Key - ${ENVIRONMENT}',
        '{"admin": true, "environment": "${ENVIRONMENT}"}'::jsonb,
        true
    )
    ON CONFLICT (key_hash) DO UPDATE
    SET updated_at = CURRENT_TIMESTAMP,
        is_active = true;
END\$\$;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
\$\$ language 'plpgsql';

-- Apply update trigger to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Environment-specific configurations
$(if [[ "$ENVIRONMENT" == "prod" ]]; then
    echo "-- Production-specific settings"
    echo "ALTER SYSTEM SET shared_buffers = '4GB';"
    echo "ALTER SYSTEM SET effective_cache_size = '12GB';"
    echo "ALTER SYSTEM SET max_connections = 200;"
elif [[ "$ENVIRONMENT" == "staging" ]]; then
    echo "-- Staging-specific settings"
    echo "ALTER SYSTEM SET shared_buffers = '1GB';"
    echo "ALTER SYSTEM SET effective_cache_size = '3GB';"
    echo "ALTER SYSTEM SET max_connections = 100;"
else
    echo "-- Dev-specific settings"
    echo "ALTER SYSTEM SET log_statement = 'all';"
    echo "ALTER SYSTEM SET log_duration = on;"
fi)

COMMIT;

-- Verification queries
SELECT 'Users created:' as info, COUNT(*) as count FROM users;
SELECT 'API keys created:' as info, COUNT(*) as count FROM api_keys;
SELECT 'Admin user:' as info, email, name FROM users WHERE email = '${ADMIN_EMAIL}';
EOF

# Execute the initialization script
echo -e "${YELLOW}Executing database initialization...${NC}"
if cat /tmp/init_gaia_portable.sql | $DATABASE_CMD; then
    echo -e "${GREEN}✅ Database initialized successfully!${NC}"
    echo ""
    echo -e "${GREEN}=== Important Information ===${NC}"
    echo -e "${BLUE}Environment:${NC} ${ENVIRONMENT}"
    echo -e "${BLUE}Admin Email:${NC} ${ADMIN_EMAIL}"
    echo -e "${BLUE}Admin API Key:${NC} ${ADMIN_API_KEY}"
    echo ""
    echo -e "${YELLOW}⚠️  Save this API key securely! It won't be shown again.${NC}"
    echo -e "${YELLOW}⚠️  Use this key in X-API-Key header for authentication.${NC}"
    
    # Clean up
    rm -f /tmp/init_gaia_portable.sql
    
    # Save key to secure location (optional)
    if [[ -n "$GAIA_KEYS_DIR" ]]; then
        echo "$ADMIN_API_KEY" > "$GAIA_KEYS_DIR/admin-${ENVIRONMENT}.key"
        chmod 600 "$GAIA_KEYS_DIR/admin-${ENVIRONMENT}.key"
        echo -e "${GREEN}API key saved to: $GAIA_KEYS_DIR/admin-${ENVIRONMENT}.key${NC}"
    fi
else
    echo -e "${RED}❌ Database initialization failed!${NC}"
    rm -f /tmp/init_gaia_portable.sql
    exit 1
fi

# Run verification
echo ""
echo -e "${BLUE}Running verification tests...${NC}"

# Test connection and basic queries
cat > /tmp/verify_gaia.sql << EOF
-- Verify tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'api_keys', 'chat_messages', 'assets')
ORDER BY table_name;

-- Verify admin user
SELECT email, name, created_at FROM users WHERE email = '${ADMIN_EMAIL}';

-- Verify API key
SELECT ak.name, ak.permissions, ak.is_active, ak.created_at
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE u.email = '${ADMIN_EMAIL}';
EOF

if cat /tmp/verify_gaia.sql | $DATABASE_CMD; then
    echo -e "${GREEN}✅ Verification passed!${NC}"
else
    echo -e "${RED}❌ Verification failed!${NC}"
fi

rm -f /tmp/verify_gaia.sql

echo ""
echo -e "${GREEN}Database initialization complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Deploy services with: ./scripts/deploy.sh --env ${ENVIRONMENT} --services all"
echo "2. Test with: ./scripts/test.sh --url https://gaia-gateway-${ENVIRONMENT}.fly.dev health"
echo "3. Use API key in X-API-Key header for authenticated requests"