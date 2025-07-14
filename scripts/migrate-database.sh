#!/bin/bash
# Database Migration Script for Gaia Platform
# Applies schema changes across environments safely

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 --env <environment> --migration <migration_file> [--provider <provider>] [--dry-run]"
    echo "  --env         Environment: dev, staging, or prod"
    echo "  --migration   Path to SQL migration file"
    echo "  --provider    Database provider: fly (default), aws, gcp, local"
    echo "  --dry-run     Show what would be executed without applying changes"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev --migration migrations/001_add_user_preferences.sql"
    echo "  $0 --env prod --migration migrations/002_add_indexes.sql --dry-run"
    exit 1
}

# Parse command line arguments
ENVIRONMENT=""
MIGRATION_FILE=""
PROVIDER="fly"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --migration)
            MIGRATION_FILE="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENVIRONMENT" || -z "$MIGRATION_FILE" ]]; then
    echo -e "${RED}Error: Missing required parameters${NC}"
    usage
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment. Must be dev, staging, or prod${NC}"
    exit 1
fi

# Check migration file exists
if [[ ! -f "$MIGRATION_FILE" ]]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Set up database command based on provider
case $PROVIDER in
    fly)
        DATABASE_CMD="fly postgres connect -a gaia-db-${ENVIRONMENT}"
        echo -e "${BLUE}Using Fly.io PostgreSQL for ${ENVIRONMENT}${NC}"
        ;;
    aws)
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

# Create migration tracking table if it doesn't exist
echo -e "${YELLOW}Setting up migration tracking...${NC}"
cat > /tmp/setup_migrations.sql << EOF
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_schema_migrations_name ON schema_migrations(migration_name);
EOF

cat /tmp/setup_migrations.sql | $DATABASE_CMD
rm -f /tmp/setup_migrations.sql

# Get migration name from file
MIGRATION_NAME=$(basename "$MIGRATION_FILE")

# Check if migration already applied
echo -e "${YELLOW}Checking migration status...${NC}"
ALREADY_APPLIED=$(echo "SELECT COUNT(*) FROM schema_migrations WHERE migration_name = '$MIGRATION_NAME';" | $DATABASE_CMD -t | tr -d ' ')

if [[ "$ALREADY_APPLIED" -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Migration $MIGRATION_NAME already applied to $ENVIRONMENT${NC}"
    echo "Use --force to reapply (not recommended for production)"
    exit 0
fi

# Calculate checksum of migration file
CHECKSUM=$(sha256sum "$MIGRATION_FILE" | cut -d' ' -f1)

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}=== DRY RUN MODE ===${NC}"
    echo -e "${BLUE}Would execute the following migration:${NC}"
    echo ""
    cat "$MIGRATION_FILE"
    echo ""
    echo -e "${BLUE}Migration name:${NC} $MIGRATION_NAME"
    echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
    echo -e "${BLUE}Checksum:${NC} $CHECKSUM"
    echo ""
    echo -e "${YELLOW}No changes applied. Use without --dry-run to execute.${NC}"
    exit 0
fi

# Production safety check
if [[ "$ENVIRONMENT" == "prod" ]]; then
    echo -e "${RED}⚠️  PRODUCTION MIGRATION WARNING ⚠️${NC}"
    echo "You are about to apply a migration to the PRODUCTION database."
    echo "Migration: $MIGRATION_NAME"
    echo "Environment: $ENVIRONMENT"
    echo ""
    echo "Please confirm by typing 'APPLY PRODUCTION MIGRATION':"
    read -r confirmation
    
    if [[ "$confirmation" != "APPLY PRODUCTION MIGRATION" ]]; then
        echo -e "${RED}Migration cancelled.${NC}"
        exit 1
    fi
fi

# Create the migration execution script
echo -e "${YELLOW}Preparing migration execution...${NC}"
cat > /tmp/execute_migration.sql << EOF
-- Migration: $MIGRATION_NAME
-- Environment: $ENVIRONMENT
-- Applied: $(date)
-- Checksum: $CHECKSUM

BEGIN;

-- Record migration start
INSERT INTO schema_migrations (migration_name, checksum) 
VALUES ('$MIGRATION_NAME', '$CHECKSUM');

-- Execute the migration
$(cat "$MIGRATION_FILE")

-- Update execution time
UPDATE schema_migrations 
SET execution_time_ms = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - applied_at)) * 1000
WHERE migration_name = '$MIGRATION_NAME';

COMMIT;

-- Verification
SELECT 'Migration applied successfully:' as result, migration_name, applied_at 
FROM schema_migrations 
WHERE migration_name = '$MIGRATION_NAME';
EOF

# Execute the migration
echo -e "${YELLOW}Executing migration...${NC}"
START_TIME=$(date +%s)

if cat /tmp/execute_migration.sql | $DATABASE_CMD; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo -e "${GREEN}✅ Migration applied successfully!${NC}"
    echo -e "${BLUE}Migration:${NC} $MIGRATION_NAME"
    echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
    echo -e "${BLUE}Duration:${NC} ${DURATION}s"
    echo -e "${BLUE}Checksum:${NC} $CHECKSUM"
    
    # Clean up
    rm -f /tmp/execute_migration.sql
    
    # Show current migration status
    echo ""
    echo -e "${BLUE}Current migration status:${NC}"
    echo "SELECT migration_name, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 5;" | $DATABASE_CMD
    
else
    echo -e "${RED}❌ Migration failed!${NC}"
    rm -f /tmp/execute_migration.sql
    exit 1
fi

echo ""
echo -e "${GREEN}Migration complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Test the changes with: ./scripts/test.sh --url https://gaia-gateway-${ENVIRONMENT}.fly.dev health"
echo "2. Deploy updated services if needed: ./scripts/deploy.sh --env ${ENVIRONMENT} --services all"