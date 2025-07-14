#!/bin/bash
# Database Monitoring Script for Gaia Platform
# Provides health metrics and performance insights

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 --env <environment> [--provider <provider>] [--report <type>]"
    echo "  --env         Environment: dev, staging, or prod"
    echo "  --provider    Database provider: fly (default), aws, gcp, local"
    echo "  --report      Report type: health (default), performance, size, activity"
    echo ""
    echo "Examples:"
    echo "  $0 --env dev                          # Health check"
    echo "  $0 --env prod --report performance    # Performance metrics"
    echo "  $0 --env staging --report size        # Database size analysis"
    exit 1
}

# Parse command line arguments
ENVIRONMENT=""
PROVIDER="fly"
REPORT_TYPE="health"

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --report)
            REPORT_TYPE="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENVIRONMENT" ]]; then
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
        echo -e "${BLUE}Monitoring Fly.io PostgreSQL for ${ENVIRONMENT}${NC}"
        ;;
    aws)
        if [[ -z "$DATABASE_URL" ]]; then
            echo -e "${RED}Error: DATABASE_URL must be set for AWS RDS${NC}"
            exit 1
        fi
        DATABASE_CMD="psql $DATABASE_URL"
        echo -e "${BLUE}Monitoring AWS RDS for ${ENVIRONMENT}${NC}"
        ;;
    gcp)
        DATABASE_CMD="gcloud sql connect gaia-${ENVIRONMENT} --user=postgres"
        echo -e "${BLUE}Monitoring Google Cloud SQL for ${ENVIRONMENT}${NC}"
        ;;
    local)
        DATABASE_CMD="psql postgresql://postgres:postgres@localhost:5432/gaia_${ENVIRONMENT}"
        echo -e "${BLUE}Monitoring local PostgreSQL for ${ENVIRONMENT}${NC}"
        ;;
    *)
        echo -e "${RED}Error: Unknown provider ${PROVIDER}${NC}"
        exit 1
        ;;
esac

# Health report
if [[ "$REPORT_TYPE" == "health" ]]; then
    echo -e "${GREEN}=== Database Health Report ===${NC}"
    cat > /tmp/health_report.sql << 'EOF'
-- Database connection status
SELECT 'Connection Status' as metric, 'Connected' as value;

-- Version information
SELECT 'PostgreSQL Version' as metric, version() as value;

-- Database size
SELECT 'Database Size' as metric, 
       pg_size_pretty(pg_database_size(current_database())) as value;

-- Active connections
SELECT 'Active Connections' as metric, 
       count(*)::text as value
FROM pg_stat_activity 
WHERE state = 'active';

-- Table count
SELECT 'Tables Count' as metric, 
       count(*)::text as value
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Last backup (if backup info is available)
SELECT 'Uptime' as metric,
       EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))::int || ' seconds' as value;
EOF

    echo "$DATABASE_CMD < /tmp/health_report.sql" | bash
    rm -f /tmp/health_report.sql
fi

# Performance report
if [[ "$REPORT_TYPE" == "performance" ]]; then
    echo -e "${GREEN}=== Database Performance Report ===${NC}"
    cat > /tmp/performance_report.sql << 'EOF'
-- Connection statistics
SELECT 'Current Connections by State' as section, '' as metric, '' as value;
SELECT '' as section, state as metric, count(*)::text as value
FROM pg_stat_activity 
GROUP BY state
ORDER BY count(*) DESC;

-- Most active tables
SELECT 'Most Active Tables (reads)' as section, '' as metric, '' as value;
SELECT '' as section, 
       schemaname || '.' || relname as metric,
       (seq_scan + idx_scan)::text as value
FROM pg_stat_user_tables
ORDER BY (seq_scan + idx_scan) DESC
LIMIT 5;

-- Largest tables
SELECT 'Largest Tables' as section, '' as metric, '' as value;
SELECT '' as section,
       schemaname || '.' || tablename as metric,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as value
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 5;

-- Cache hit ratio
SELECT 'Cache Performance' as section, '' as metric, '' as value;
SELECT '' as section,
       'Buffer Cache Hit Ratio' as metric,
       round(100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2)::text || '%' as value
FROM pg_stat_database;

-- Index usage
SELECT 'Index Usage' as section, '' as metric, '' as value;
SELECT '' as section,
       schemaname || '.' || relname as metric,
       round(100.0 * idx_scan / (seq_scan + idx_scan), 2)::text || '% index usage' as value
FROM pg_stat_user_tables
WHERE (seq_scan + idx_scan) > 0
ORDER BY (seq_scan + idx_scan) DESC
LIMIT 5;
EOF

    echo "$DATABASE_CMD < /tmp/performance_report.sql" | bash | column -t -s '|'
    rm -f /tmp/performance_report.sql
fi

# Size report
if [[ "$REPORT_TYPE" == "size" ]]; then
    echo -e "${GREEN}=== Database Size Report ===${NC}"
    cat > /tmp/size_report.sql << 'EOF'
-- Overall database size
SELECT 'Total Database Size' as category, 
       pg_size_pretty(pg_database_size(current_database())) as size;

-- Table sizes
SELECT 'Tables' as category, '' as size;
SELECT schemaname || '.' || tablename as category,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index sizes
SELECT 'Indexes' as category, '' as size;
SELECT schemaname || '.' || indexname as category,
       pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC
LIMIT 10;

-- Row counts
SELECT 'Row Counts' as category, '' as size;
SELECT schemaname || '.' || relname as category,
       n_tup_ins::text || ' rows' as size
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
EOF

    echo "$DATABASE_CMD < /tmp/size_report.sql" | bash | column -t -s '|'
    rm -f /tmp/size_report.sql
fi

# Activity report
if [[ "$REPORT_TYPE" == "activity" ]]; then
    echo -e "${GREEN}=== Database Activity Report ===${NC}"
    cat > /tmp/activity_report.sql << 'EOF'
-- Current activity
SELECT 'Current Active Queries' as section, '' as query, '' as duration;
SELECT '' as section,
       left(query, 60) as query,
       EXTRACT(EPOCH FROM (now() - query_start))::int || 's' as duration
FROM pg_stat_activity 
WHERE state = 'active' 
AND query != '<IDLE>'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;

-- Recent migrations
SELECT 'Recent Migrations' as section, '' as query, '' as duration;
SELECT '' as section,
       migration_name as query,
       applied_at::text as duration
FROM schema_migrations
ORDER BY applied_at DESC
LIMIT 5;

-- Table activity summary
SELECT 'Table Activity (24h estimate)' as section, '' as query, '' as duration;
SELECT '' as section,
       schemaname || '.' || relname as query,
       (n_tup_ins + n_tup_upd + n_tup_del)::text || ' modifications' as duration
FROM pg_stat_user_tables
WHERE (n_tup_ins + n_tup_upd + n_tup_del) > 0
ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC
LIMIT 10;

-- Database stats
SELECT 'Database Statistics' as section, '' as query, '' as duration;
SELECT '' as section,
       'Transactions Committed' as query,
       xact_commit::text as duration
FROM pg_stat_database 
WHERE datname = current_database();

SELECT '' as section,
       'Transactions Rolled Back' as query,
       xact_rollback::text as duration
FROM pg_stat_database 
WHERE datname = current_database();

SELECT '' as section,
       'Blocks Read from Disk' as query,
       blks_read::text as duration
FROM pg_stat_database 
WHERE datname = current_database();

SELECT '' as section,
       'Blocks Hit in Cache' as query,
       blks_hit::text as duration
FROM pg_stat_database 
WHERE datname = current_database();
EOF

    echo "$DATABASE_CMD < /tmp/activity_report.sql" | bash | column -t -s '|'
    rm -f /tmp/activity_report.sql
fi

echo ""
echo -e "${GREEN}Monitoring complete!${NC}"
echo -e "${BLUE}Available reports:${NC} health, performance, size, activity"
echo -e "${BLUE}Run with different --report types for more insights${NC}"