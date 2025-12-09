#!/bin/bash
# Check what tables exist in Supabase using service key
# This tells us which migrations have been applied

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Load environment
source .env

echo -e "${BLUE}Checking Supabase tables...${NC}"
echo ""

# Query tables using PostgREST meta tables
curl -s "${SUPABASE_URL}/rest/v1/?apikey=${SUPABASE_SERVICE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" | jq -r '.definitions | keys[]' 2>/dev/null || {

    # Alternative: Use pg_meta API if available
    echo -e "${CYAN}Querying database schema...${NC}"
    echo ""

    # Get list of tables via REST API
    TABLES=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/rpc/pg_catalog.pg_tables" \
      -H "apikey: ${SUPABASE_SERVICE_KEY}" \
      -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
      -H "Content-Type: application/json" 2>&1)

    echo -e "${BLUE}Tables found in public schema:${NC}"
    echo ""

    # List known tables from OpenAPI schema
    curl -s "${SUPABASE_URL}/rest/v1/" \
      -H "apikey: ${SUPABASE_SERVICE_KEY}" \
      -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
      -H "Accept: application/openapi+json" | \
      jq -r '.definitions | keys[] | select(. != "")' | sort | while read table; do
        echo -e "  ${GREEN}✓${NC} $table"
      done
}

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Migration Analysis${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

# Store tables in variable
EXISTING_TABLES=$(curl -s "${SUPABASE_URL}/rest/v1/" \
  -H "apikey: ${SUPABASE_SERVICE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
  -H "Accept: application/openapi+json" | \
  jq -r '.definitions | keys[]' 2>/dev/null)

# Check each migration
for migration in migrations/*.sql; do
    [ -e "$migration" ] || continue

    MIGRATION_NAME=$(basename "$migration")

    # Skip supabase internal migrations
    [[ "$MIGRATION_NAME" == supabase_* ]] && continue

    # Extract tables this migration creates
    CREATES=$(grep -i "CREATE TABLE" "$migration" | \
              sed -n 's/.*CREATE TABLE.*IF NOT EXISTS[[:space:]]*\([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/p; s/.*CREATE TABLE[[:space:]]*\([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/p' | \
              grep -v "^IF$" | \
              tr '\n' ',' | sed 's/,$//')

    if [ -n "$CREATES" ]; then
        # Check if all tables exist
        ALL_EXIST=true
        for table in $(echo "$CREATES" | tr ',' ' '); do
            if ! echo "$EXISTING_TABLES" | grep -q "^${table}$"; then
                ALL_EXIST=false
                break
            fi
        done

        if [ "$ALL_EXIST" = true ]; then
            echo -e "  ${GREEN}✓ APPLIED${NC}  $MIGRATION_NAME"
        else
            echo -e "  ${CYAN}? PARTIAL${NC}  $MIGRATION_NAME"
        fi
        echo -e "              Tables: $CREATES"
    else
        echo -e "  ${CYAN}? UNKNOWN${NC}  $MIGRATION_NAME (no tables created)"
    fi
    echo ""
done

echo -e "${CYAN}Done!${NC}"
