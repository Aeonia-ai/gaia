#!/bin/bash
# Simple script to setup remote authentication

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <environment> <email>"
    echo "Example: $0 dev jason@aeonia.ai"
    exit 1
fi

ENVIRONMENT=$1
EMAIL=$2

# Generate API key
API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
API_KEY_HASH=$(echo -n "$API_KEY" | sha256sum | cut -d' ' -f1)

echo -e "${BLUE}Setting up user $EMAIL in $ENVIRONMENT environment${NC}"
echo -e "${GREEN}Generated API key: $API_KEY${NC}"
echo -e "${GREEN}API key hash: $API_KEY_HASH${NC}"

# Get database app name
case "$ENVIRONMENT" in
    "dev")
        DB_APP="gaia-db-dev"
        ;;
    "staging")
        DB_APP="gaia-db-staging"
        ;;
    "production")
        DB_APP="gaia-db-production"
        ;;
    *)
        echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
        exit 1
        ;;
esac

# Create temporary SQL file
TEMP_SQL=$(mktemp)
cat > "$TEMP_SQL" <<EOF
-- Setup user for $ENVIRONMENT
BEGIN;

-- Create user
INSERT INTO users (email, name) 
VALUES ('$EMAIL', 'User $EMAIL')
ON CONFLICT (email) DO UPDATE SET updated_at = NOW();

-- Create API key
INSERT INTO api_keys (user_id, key_hash, name, permissions, is_active)
SELECT 
    id as user_id,
    '$API_KEY_HASH' as key_hash,
    '$ENVIRONMENT API Key' as name,
    '{"environment": "$ENVIRONMENT"}'::jsonb as permissions,
    true as is_active
FROM users WHERE email = '$EMAIL'
ON CONFLICT (key_hash) DO UPDATE SET is_active = true;

-- Verify
SELECT u.email, ak.name, ak.is_active 
FROM users u 
JOIN api_keys ak ON u.id = ak.user_id 
WHERE u.email = '$EMAIL' AND ak.key_hash = '$API_KEY_HASH';

COMMIT;
EOF

echo -e "${BLUE}Connecting to $DB_APP...${NC}"

# Try to connect and run SQL
if fly postgres connect -a "$DB_APP" < "$TEMP_SQL" 2>/dev/null; then
    echo -e "${GREEN}✅ Success!${NC}"
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}SAVE THIS API KEY:${NC}"
    echo -e "${GREEN}$API_KEY${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${BLUE}Test with:${NC}"
    echo "API_KEY=$API_KEY ./scripts/test.sh --url https://gaia-gateway-$ENVIRONMENT.fly.dev kb-search \"test\""
else
    echo -e "${RED}Failed to connect to database${NC}"
    echo "You can manually run this SQL:"
    cat "$TEMP_SQL"
fi

# Cleanup
rm -f "$TEMP_SQL"