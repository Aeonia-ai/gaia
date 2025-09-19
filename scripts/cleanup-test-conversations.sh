#!/bin/bash
# Clean up test conversations from development database

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🧹 CLEANING UP TEST CONVERSATIONS${NC}"
echo "========================================"

# Load environment variables
if [ -f .env ]; then
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# Check what we're about to delete
echo -e "${BLUE}📊 Analyzing test conversations...${NC}"

QUERY="
SELECT 'Test conversations to delete:' as action, count(*) as conversations
FROM conversations
WHERE title ILIKE '%test%'
   OR title ILIKE '%investigation%'
   OR title ILIKE '%reload%'
   OR title ILIKE '%diagnostic%'
   OR title ILIKE '%demo%'
   OR title = '';
"

docker compose exec db psql -U postgres -d llm_platform -c "$QUERY"

# Ask for confirmation
echo -e "\n${YELLOW}⚠️  Are you sure you want to delete these test conversations?${NC}"
echo -e "${YELLOW}This action cannot be undone.${NC}"
read -p "Type 'yes' to confirm: " -r
echo

if [[ $REPLY == "yes" ]]; then
    echo -e "${BLUE}🗑️ Deleting test conversations...${NC}"

    DELETE_QUERY="
    DELETE FROM conversations
    WHERE title ILIKE '%test%'
       OR title ILIKE '%investigation%'
       OR title ILIKE '%reload%'
       OR title ILIKE '%diagnostic%'
       OR title ILIKE '%demo%'
       OR title = '';

    SELECT COUNT(*) as remaining_conversations FROM conversations;
    "

    docker compose exec db psql -U postgres -d llm_platform -c "$DELETE_QUERY"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Test conversations cleaned up successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to clean up test conversations${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}🚫 Cleanup cancelled${NC}"
    exit 0
fi

echo -e "\n${GREEN}🎯 CLEANUP COMPLETE${NC}"