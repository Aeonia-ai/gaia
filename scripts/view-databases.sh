#!/bin/bash

# Script to view databases across all environments
# Usage: ./scripts/view-databases.sh [environment] [query]

set -e

ENVIRONMENT=${1:-local}
QUERY=${2:-"SELECT COUNT(*) as user_count FROM users;"}

case $ENVIRONMENT in
    "local")
        echo "🏠 Viewing Local Database..."
        docker compose exec db psql -U postgres -d llm_platform -c "$QUERY"
        ;;
    "dev")
        echo "🚀 Viewing Dev Database..."
        fly postgres connect -a gaia-db-dev --command "$QUERY"
        ;;
    "staging")
        echo "🎭 Viewing Staging Database..."
        fly postgres connect -a gaia-db-staging --command "$QUERY"
        ;;
    "production"|"prod")
        echo "🌟 Viewing Production Database..."
        fly postgres connect -a gaia-db-production --command "$QUERY"
        ;;
    "supabase")
        echo "🔐 Viewing Supabase Auth Data..."
        echo "Go to: https://supabase.com/dashboard/project/lbaohvnusingoztdzlmj/editor"
        echo "Navigate to: Table Editor → auth schema → users table"
        ;;
    "all")
        echo "📊 Database Overview"
        echo "===================="
        echo ""
        echo "Local:"
        docker compose exec db psql -U postgres -d llm_platform -c "SELECT COUNT(*) as users FROM users;" 2>/dev/null || echo "Local DB not running"
        echo ""
        echo "Dev:"
        fly postgres connect -a gaia-db-dev --command "SELECT COUNT(*) as users FROM users;" 2>/dev/null || echo "Dev DB not accessible"
        echo ""
        echo "Staging:"
        fly postgres connect -a gaia-db-staging --command "SELECT COUNT(*) as users FROM users;" 2>/dev/null || echo "Staging DB not accessible"
        echo ""
        echo "Production:"
        fly postgres connect -a gaia-db-production --command "SELECT COUNT(*) as users FROM users;" 2>/dev/null || echo "Production DB not accessible"
        ;;
    *)
        echo "Usage: $0 [local|dev|staging|production|supabase|all] [query]"
        echo ""
        echo "Examples:"
        echo "  $0 local                    # View local database"
        echo "  $0 dev 'SELECT * FROM users;'  # Run custom query on dev"
        echo "  $0 all                      # Overview of all databases"
        echo "  $0 supabase                 # Instructions for Supabase"
        exit 1
        ;;
esac