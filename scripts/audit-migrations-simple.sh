#!/bin/bash
# Simple Migration Audit - Analyzes migration files without database access
#
# This script:
# 1. Lists all migration files
# 2. Extracts what tables each creates
# 3. Shows duplicate migration numbers
# 4. Provides recommendations

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Migration File Analysis Tool                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

MIGRATIONS_DIR="migrations"

if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: migrations/ directory not found${NC}"
    exit 1
fi

# Count migration files
MIGRATION_COUNT=$(find "$MIGRATIONS_DIR" -name "*.sql" ! -name "_*" | wc -l | tr -d ' ')
echo -e "${CYAN}Found ${MIGRATION_COUNT} migration files${NC}"
echo ""

# Analyze each migration
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Migration File Details${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

declare -A SEEN_NUMBERS

for migration in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
    MIGRATION_NAME=$(basename "$migration")

    # Extract migration number
    MIGRATION_NUM=$(echo "$MIGRATION_NAME" | grep -o "^[0-9]*")

    # Check for duplicates
    if [ -n "$MIGRATION_NUM" ]; then
        if [ -n "${SEEN_NUMBERS[$MIGRATION_NUM]}" ]; then
            echo -e "${RED}⚠️  DUPLICATE #${MIGRATION_NUM}${NC}"
        fi
        SEEN_NUMBERS[$MIGRATION_NUM]="$MIGRATION_NAME"
    fi

    # Extract table names
    CREATED_TABLES=$(grep -i "CREATE TABLE" "$migration" | sed -n 's/.*CREATE TABLE[^a-zA-Z_]*\([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/p' | tr '\n' ', ' | sed 's/,$//')

    # File size
    SIZE=$(du -h "$migration" | cut -f1)

    # Print migration info
    if [ -n "$MIGRATION_NUM" ]; then
        echo -e "${BLUE}#${MIGRATION_NUM}${NC} ${MIGRATION_NAME}"
    else
        echo -e "${YELLOW}   ${MIGRATION_NAME}${NC}"
    fi

    echo -e "     ${CYAN}Size:${NC} $SIZE"

    if [ -n "$CREATED_TABLES" ]; then
        echo -e "     ${CYAN}Creates:${NC} $CREATED_TABLES"
    else
        echo -e "     ${CYAN}Creates:${NC} ${YELLOW}(no tables, or schema modification)${NC}"
    fi

    echo ""
done

# Check for duplicate numbers
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Duplicate Migration Numbers${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

DUPLICATES_FOUND=false

for num in "${!SEEN_NUMBERS[@]}"; do
    COUNT=$(ls "$MIGRATIONS_DIR"/${num}_*.sql "$MIGRATIONS_DIR"/${num}*.sql 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 1 ]; then
        DUPLICATES_FOUND=true
        echo -e "${RED}⚠️  Migration #${num} appears ${COUNT} times:${NC}"
        ls "$MIGRATIONS_DIR"/${num}_*.sql "$MIGRATIONS_DIR"/${num}*.sql 2>/dev/null | while read file; do
            echo -e "     • $(basename "$file")"
        done
        echo ""
    fi
done

if [ "$DUPLICATES_FOUND" = false ]; then
    echo -e "${GREEN}✓ No duplicate migration numbers found${NC}"
    echo ""
fi

# Recommendations
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Recommendations${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DUPLICATES_FOUND" = true ]; then
    echo -e "${YELLOW}1. Fix duplicate migration numbers${NC}"
    echo "   Run: ./scripts/rename-migrations-timestamp.sh"
    echo ""
fi

echo -e "${BLUE}2. To check what's actually applied to Supabase:${NC}"
echo "   Option A: Add SUPABASE_DB_PASSWORD to .env, then run:"
echo "             ./scripts/audit-supabase-migrations.sh"
echo ""
echo "   Option B: Check Supabase Dashboard:"
echo "             https://supabase.com/dashboard/project/lbaohvnusingoztdzlmj/editor"
echo "             Look at Tables list in left sidebar"
echo ""

echo -e "${BLUE}3. To apply a new migration:${NC}"
echo "   ./scripts/migrate-database.sh --env dev --migration migrations/XXX.sql"
echo ""

echo -e "${BLUE}4. To set up migration tracking:${NC}"
echo "   Create schema_migrations table in Supabase (via SQL Editor):"
cat << 'SQL'

   CREATE TABLE IF NOT EXISTS schema_migrations (
       id SERIAL PRIMARY KEY,
       migration_name VARCHAR(255) UNIQUE NOT NULL,
       applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       checksum VARCHAR(64),
       execution_time_ms INTEGER
   );
SQL
echo ""

echo -e "${GREEN}Analysis complete!${NC}"
