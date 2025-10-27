#!/bin/bash
# Audit Supabase Database - Check which migrations have been applied
#
# This script compares:
# 1. Tables that exist in Supabase
# 2. Migration files in migrations/
# 3. Reports which migrations appear to be applied

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Supabase Migration Audit Tool                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load environment variables
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

source .env

# Check required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env${NC}"
    exit 1
fi

# Extract project reference from URL
PROJECT_REF=$(echo "$SUPABASE_URL" | sed -n 's/.*https:\/\/\([^.]*\).*/\1/p')
echo -e "${CYAN}Project:${NC} $PROJECT_REF"
echo -e "${CYAN}URL:${NC} $SUPABASE_URL"
echo ""

# Check for database password in environment
if [ -z "$SUPABASE_DB_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️  SUPABASE_DB_PASSWORD not found in .env${NC}"
    echo -e "${YELLOW}   To get direct SQL access, you need the database password.${NC}"
    echo ""
    echo -e "${BLUE}To get your database password:${NC}"
    echo "   1. Go to: https://supabase.com/dashboard/project/$PROJECT_REF/settings/database"
    echo "   2. Look for 'Database password' section"
    echo "   3. Copy the password and add to .env:"
    echo "      SUPABASE_DB_PASSWORD=your_password_here"
    echo ""
    echo -e "${CYAN}For now, using REST API to check tables...${NC}"
    USE_API=true
else
    echo -e "${GREEN}✓ Database password found${NC}"
    USE_API=false
fi
echo ""

# Function to query Supabase tables via REST API
get_tables_via_api() {
    echo -e "${YELLOW}Fetching tables via Supabase REST API...${NC}"

    # Query information_schema via PostgREST
    RESPONSE=$(curl -s -X GET \
        "${SUPABASE_URL}/rest/v1/rpc/get_tables" \
        -H "apikey: ${SUPABASE_SERVICE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" 2>&1)

    # If RPC function doesn't exist, try direct metadata query
    if echo "$RESPONSE" | grep -q "function.*does not exist\|Could not find"; then
        echo -e "${YELLOW}   Note: Cannot query via API. Listing known tables from migrations...${NC}"
        return 1
    fi

    echo "$RESPONSE"
    return 0
}

# Function to query Supabase via direct SQL
get_tables_via_sql() {
    echo -e "${YELLOW}Fetching tables via direct SQL connection...${NC}"

    DB_URL="postgresql://postgres:${SUPABASE_DB_PASSWORD}@db.${PROJECT_REF}.supabase.co:5432/postgres"

    TABLES=$(psql "$DB_URL" -t -c "
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    " 2>&1)

    if [ $? -ne 0 ]; then
        echo -e "${RED}Error connecting to database:${NC}"
        echo "$TABLES"
        return 1
    fi

    echo "$TABLES"
    return 0
}

# Get list of existing tables
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 1: Checking existing tables in Supabase${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$USE_API" = true ]; then
    TABLES=$(get_tables_via_api)
    if [ $? -ne 0 ]; then
        # Fallback: infer from migration files
        echo -e "${YELLOW}Using inference from migration files...${NC}"
        TABLES=""
    fi
else
    TABLES=$(get_tables_via_sql)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Connected to Supabase PostgreSQL${NC}"
        echo ""
        echo -e "${BLUE}Existing tables:${NC}"
        echo "$TABLES" | grep -v "^$" | sed 's/^/  • /'
        echo ""
    else
        echo -e "${RED}Failed to connect via SQL${NC}"
        exit 1
    fi
fi

# Analyze migration files
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 2: Analyzing migration files${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

MIGRATIONS_DIR="migrations"
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: migrations/ directory not found${NC}"
    exit 1
fi

# Count migration files
MIGRATION_COUNT=$(find "$MIGRATIONS_DIR" -name "*.sql" ! -name "supabase_*" | wc -l | tr -d ' ')
echo -e "${BLUE}Found ${MIGRATION_COUNT} migration files:${NC}"
echo ""

# Analyze each migration
declare -A MIGRATION_STATUS
declare -A MIGRATION_TABLES

for migration in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | grep -v "supabase_" | sort); do
    MIGRATION_NAME=$(basename "$migration")

    # Extract table names created in this migration
    CREATED_TABLES=$(grep -i "CREATE TABLE" "$migration" | sed -n 's/.*CREATE TABLE[^a-zA-Z_]*\([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/p' | tr '\n' ',' | sed 's/,$//')

    MIGRATION_TABLES[$MIGRATION_NAME]="$CREATED_TABLES"

    # Check if tables exist
    if [ -n "$TABLES" ] && [ -n "$CREATED_TABLES" ]; then
        ALL_EXIST=true
        for table in $(echo "$CREATED_TABLES" | tr ',' ' '); do
            if ! echo "$TABLES" | grep -q "$table"; then
                ALL_EXIST=false
                break
            fi
        done

        if [ "$ALL_EXIST" = true ]; then
            MIGRATION_STATUS[$MIGRATION_NAME]="APPLIED"
        else
            MIGRATION_STATUS[$MIGRATION_NAME]="PARTIAL"
        fi
    else
        MIGRATION_STATUS[$MIGRATION_NAME]="UNKNOWN"
    fi
done

# Display results
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 3: Migration Status Report${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

for migration in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | grep -v "supabase_" | sort); do
    MIGRATION_NAME=$(basename "$migration")
    STATUS="${MIGRATION_STATUS[$MIGRATION_NAME]}"
    TABLES_CREATED="${MIGRATION_TABLES[$MIGRATION_NAME]}"

    case $STATUS in
        APPLIED)
            echo -e "  ${GREEN}✓ APPLIED${NC}   $MIGRATION_NAME"
            ;;
        PARTIAL)
            echo -e "  ${YELLOW}⚠ PARTIAL${NC}   $MIGRATION_NAME"
            ;;
        UNKNOWN)
            echo -e "  ${CYAN}? UNKNOWN${NC}   $MIGRATION_NAME"
            ;;
        *)
            echo -e "  ${RED}✗ MISSING${NC}   $MIGRATION_NAME"
            ;;
    esac

    if [ -n "$TABLES_CREATED" ]; then
        echo -e "               ${BLUE}Tables:${NC} $TABLES_CREATED"
    fi
    echo ""
done

# Summary
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Summary${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

APPLIED_COUNT=$(echo "${MIGRATION_STATUS[@]}" | tr ' ' '\n' | grep -c "APPLIED" || echo "0")
PARTIAL_COUNT=$(echo "${MIGRATION_STATUS[@]}" | tr ' ' '\n' | grep -c "PARTIAL" || echo "0")
UNKNOWN_COUNT=$(echo "${MIGRATION_STATUS[@]}" | tr ' ' '\n' | grep -c "UNKNOWN" || echo "0")

echo -e "${GREEN}Applied:${NC}  $APPLIED_COUNT"
echo -e "${YELLOW}Partial:${NC}  $PARTIAL_COUNT"
echo -e "${CYAN}Unknown:${NC}  $UNKNOWN_COUNT"
echo ""

# Check for schema_migrations table
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Migration Tracking Status${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

if echo "$TABLES" | grep -q "schema_migrations"; then
    echo -e "${GREEN}✓ schema_migrations table exists${NC}"
    echo ""

    if [ "$USE_API" = false ]; then
        echo -e "${BLUE}Recorded migrations:${NC}"
        DB_URL="postgresql://postgres:${SUPABASE_DB_PASSWORD}@db.${PROJECT_REF}.supabase.co:5432/postgres"
        psql "$DB_URL" -c "SELECT migration_name, applied_at FROM schema_migrations ORDER BY migration_name;" 2>&1
    fi
else
    echo -e "${YELLOW}⚠️  schema_migrations table NOT found${NC}"
    echo ""
    echo -e "${BLUE}Migration tracking is not set up yet.${NC}"
    echo ""
    echo -e "${CYAN}To set up tracking:${NC}"
    echo "   1. Run: ./scripts/create-migration-baseline.sh"
    echo "   2. Or use: ./scripts/migrate-database.sh --env dev --migration <file>"
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Next Steps${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$USE_API" = true ]; then
    echo -e "${YELLOW}For accurate migration tracking:${NC}"
    echo "   1. Add SUPABASE_DB_PASSWORD to .env"
    echo "   2. Re-run this script"
    echo ""
fi

if ! echo "$TABLES" | grep -q "schema_migrations"; then
    echo -e "${BLUE}To enable migration tracking:${NC}"
    echo "   1. Create baseline: ./scripts/create-migration-baseline.sh"
    echo "   2. Future migrations: ./scripts/migrate-database.sh --env dev --migration <file>"
    echo ""
fi

echo -e "${BLUE}To apply a new migration:${NC}"
echo "   ./scripts/migrate-database.sh --env dev --migration migrations/008_new_feature.sql"
echo ""

echo -e "${GREEN}Audit complete!${NC}"
