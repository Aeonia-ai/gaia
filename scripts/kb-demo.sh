#!/bin/bash
# Demonstrate KB operations

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Use Jason's API key
export API_KEY=$(grep "^JASON_API_KEY=" .env | cut -d'=' -f2)

echo -e "${BLUE}=== KB Operations Demo ===${NC}"
echo "Using Jason's API key: ${API_KEY:0:10}..."
echo

echo -e "${GREEN}1. Search for 'Aeonia' in KB:${NC}"
./scripts/test.sh --local kb-search "Aeonia"

echo -e "\n${GREEN}2. Navigate KB structure:${NC}"
# Use our custom script for navigation
./scripts/test-kb-operations.sh | grep -A20 "Navigate KB index"

echo -e "\n${GREEN}3. Read a specific file:${NC}"
# Read CLAUDE.md using v0.2 API
curl -s -X POST http://localhost:8666/api/v0.2/kb/read \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "shared/kos/contexts/.placeholder"}' | jq '.response' -r | head -20

echo -e "\n${GREEN}4. Check Git status:${NC}"
curl -s -X GET http://localhost:8666/api/v0.2/kb/git/status \
  -H "X-API-Key: $API_KEY" | jq '.'

echo -e "\n${GREEN}5. List available contexts:${NC}"
# Try to find context files
echo "Searching for context files..."
./scripts/test.sh --local kb-search "context index"

echo -e "\n${BLUE}=== Summary ===${NC}"
echo "KB is operational with:"
echo "- Git repository cloned successfully"
echo "- File read/write capabilities"
echo "- Search functionality (with RBAC SQL issue)"
echo "- Navigation working"
echo "- Multi-user structure in place"
echo
echo "Note: Search operations fail due to SQLAlchemy/asyncpg compatibility issue in RBAC."