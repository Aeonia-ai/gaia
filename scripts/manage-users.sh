#!/bin/bash
# User management helper script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment variables
if [ -f .env ]; then
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# Function to generate secure API key
generate_api_key() {
    # Generate a secure random API key (32 bytes, base64url encoded)
    openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
}

# Function to hash API key
hash_api_key() {
    local api_key=$1
    echo -n "$api_key" | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '='
}

# Command processing
case "$1" in
    "list")
        echo -e "${BLUE}=== User List ===${NC}"
        docker compose exec db psql -U postgres -d llm_platform -c \
            "SELECT id, email, created_at, 
             CASE WHEN api_key_hash IS NOT NULL THEN 'Yes' ELSE 'No' END as has_api_key 
             FROM users ORDER BY created_at DESC;"
        ;;
        
    "create")
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 create <email>${NC}"
            exit 1
        fi
        
        EMAIL="$2"
        API_KEY=$(generate_api_key)
        API_KEY_HASH=$(hash_api_key "$API_KEY")
        USER_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
        
        echo -e "${BLUE}Creating user: $EMAIL${NC}"
        
        # Create user in database
        docker compose exec db psql -U postgres -d llm_platform <<EOF
INSERT INTO users (id, email, api_key_hash, created_at, updated_at)
VALUES ('$USER_ID', '$EMAIL', '$API_KEY_HASH', NOW(), NOW())
ON CONFLICT (email) DO UPDATE SET updated_at = NOW()
RETURNING id;
EOF
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ User created successfully!${NC}"
            echo -e "${GREEN}Email: $EMAIL${NC}"
            echo -e "${GREEN}API Key: $API_KEY${NC}"
            echo -e "${YELLOW}⚠️  Save this API key securely - it cannot be retrieved later${NC}"
            
            # Optionally save to file
            echo "$EMAIL:$API_KEY" >> user_api_keys.txt
            echo -e "${BLUE}API key saved to user_api_keys.txt${NC}"
        else
            echo -e "${RED}✗ Failed to create user${NC}"
        fi
        ;;
        
    "grant-kb")
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 grant-kb <email>${NC}"
            exit 1
        fi
        
        EMAIL="$2"
        echo -e "${BLUE}Granting KB access to: $EMAIL${NC}"
        
        # Grant KB permissions via RBAC
        docker compose exec db psql -U postgres -d llm_platform <<EOF
INSERT INTO resource_permissions (resource_type, resource_id, principal_type, principal_id, permissions)
SELECT 'kb', '/kb', 'user', u.id, '["read", "write", "delete", "admin"]'::jsonb
FROM users u
WHERE u.email = '$EMAIL'
ON CONFLICT DO NOTHING;
EOF
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ KB access granted${NC}"
        else
            echo -e "${RED}✗ Failed to grant KB access${NC}"
        fi
        ;;
        
    "check")
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 check <email>${NC}"
            exit 1
        fi
        
        EMAIL="$2"
        echo -e "${BLUE}=== User Details: $EMAIL ===${NC}"
        
        # Get user details
        docker compose exec db psql -U postgres -d llm_platform -t <<EOF
SELECT 
    'User ID: ' || id || E'\n' ||
    'Email: ' || email || E'\n' ||
    'Has API Key: ' || CASE WHEN api_key_hash IS NOT NULL THEN 'Yes' ELSE 'No' END || E'\n' ||
    'Created: ' || created_at::date
FROM users 
WHERE email = '$EMAIL';
EOF
        
        echo -e "\n${BLUE}KB Permissions:${NC}"
        docker compose exec db psql -U postgres -d llm_platform -t <<EOF
SELECT 
    'Resource: ' || resource_id || ' - Permissions: ' || permissions::text
FROM resource_permissions rp
JOIN users u ON rp.principal_id = u.id
WHERE u.email = '$EMAIL' AND rp.resource_type = 'kb';
EOF
        
        echo -e "\n${BLUE}Team Memberships:${NC}"
        docker compose exec db psql -U postgres -d llm_platform -t <<EOF
SELECT 
    t.name || ' (' || tm.role || ')'
FROM team_members tm
JOIN teams t ON tm.team_id = t.id
JOIN users u ON tm.user_id = u.id
WHERE u.email = '$EMAIL';
EOF
        ;;
        
    "test-api-key")
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 test-api-key <api-key>${NC}"
            exit 1
        fi
        
        API_KEY="$2"
        echo -e "${BLUE}Testing API key...${NC}"
        
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "X-API-Key: $API_KEY" \
            "http://localhost:8666/api/v1/providers")
            
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✓ API key is valid${NC}"
        else
            echo -e "${RED}✗ API key is invalid (status: $response)${NC}"
        fi
        ;;
        
    *)
        echo -e "${BLUE}User Management Script${NC}"
        echo
        echo "Usage: $0 <command> [args]"
        echo
        echo "Commands:"
        echo "  list                    List all users"
        echo "  create <email>          Create a new user with API key"
        echo "  grant-kb <email>        Grant KB access to user"
        echo "  check <email>           Check user details and permissions"
        echo "  test-api-key <key>      Test if an API key is valid"
        echo
        echo "Examples:"
        echo "  $0 create john@example.com"
        echo "  $0 grant-kb john@example.com"
        echo "  $0 check jason@aeonia.ai"
        ;;
esac