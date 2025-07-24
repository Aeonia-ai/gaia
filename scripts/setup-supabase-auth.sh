#!/bin/bash
# Setup Supabase authentication tables

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Setting up Supabase authentication...${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure Supabase settings"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}Supabase URL: $SUPABASE_URL${NC}"
echo ""

# Instructions for manual setup
echo -e "${YELLOW}Manual Setup Instructions:${NC}"
echo ""
echo "1. Go to your Supabase project dashboard"
echo "2. Navigate to SQL Editor"
echo "3. Create a new query"
echo "4. Copy and paste the contents of: migrations/supabase_api_keys.sql"
echo "5. Run the query"
echo ""
echo "Or use the Supabase CLI:"
echo "  supabase db push --db-url \"$SUPABASE_URL\""
echo ""
echo -e "${BLUE}After running the migration:${NC}"
echo ""
echo "1. Enable Supabase authentication in your .env:"
echo "   AUTH_BACKEND=supabase"
echo "   SUPABASE_AUTH_ENABLED=true"
echo ""
echo "2. Test with Jason's API key locally:"
echo "   ./scripts/test.sh --local kb-search \"test\""
echo ""
echo "3. Test on remote deployment:"
echo "   API_KEY=hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev kb-search \"test\""
echo ""
echo -e "${GREEN}The same API key will now work across all environments!${NC}"