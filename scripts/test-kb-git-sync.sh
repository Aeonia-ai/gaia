#!/bin/bash

# Test KB Git Sync Functionality
# 
# This script tests the manual Git sync endpoints added to the KB service.
# It tests both direct KB service access and gateway routing.

set -e

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8666}"
KB_DIRECT_URL="${KB_DIRECT_URL:-http://kb-service:8000}"  # Internal docker network
API_KEY="${API_KEY:-FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE}"

echo "🧪 Testing KB Git Sync Functionality"
echo "======================================="
echo "Gateway URL: $GATEWAY_URL"
echo "KB Direct URL: $KB_DIRECT_URL (internal)"
echo ""

# Function to test endpoint with different URLs
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="$4"
    
    echo "🔧 $description"
    
    # Try direct KB service access first (from container)
    echo "  📡 Testing via container network..."
    if [ "$method" == "GET" ]; then
        response=$(docker compose exec -T kb-service curl -s -w "%{http_code}" \
          -H "X-API-Key: $API_KEY" \
          -H "Content-Type: application/json" \
          "localhost:8000$endpoint" 2>/dev/null || echo "connection_failed")
    else
        response=$(docker compose exec -T kb-service curl -s -w "%{http_code}" \
          -X "$method" \
          -H "X-API-Key: $API_KEY" \
          -H "Content-Type: application/json" \
          ${data:+-d "$data"} \
          "localhost:8000$endpoint" 2>/dev/null || echo "connection_failed")
    fi
    
    if [[ "$response" == *"200" ]]; then
        http_code="200"
        response_body="${response%???}"
        echo "  ✅ Direct access successful"
        echo "  📄 Response: $response_body" | head -c 200
        echo ""
    else
        echo "  ❌ Direct access failed: $response"
    fi
    
    echo ""
}

# Test basic KB functionality first
echo "🏥 1. Testing KB service health..."
test_endpoint "GET" "/health" "KB service health check"

echo "🔍 2. Testing KB search functionality..."
test_endpoint "POST" "/search" "KB search test" '{"message": "gaia architecture"}'

# Test Git sync endpoints (these will fail gracefully if not available)
echo "📊 3. Testing sync status endpoint..."
test_endpoint "GET" "/sync/status" "Git sync status check"

echo "⬇️ 4. Testing sync from Git..."
test_endpoint "POST" "/sync/from-git" "Sync from Git test"

echo "⬆️ 5. Testing sync to Git..."
test_endpoint "POST" "/sync/to-git" "Sync to Git test"

echo "🎯 KB Git Sync Test Complete"
echo "=============================="
echo ""

# Show current configuration
echo "📋 Current Configuration:"
if [ -f ".env" ]; then
    echo "   • Storage Mode: $(grep '^KB_STORAGE_MODE=' .env 2>/dev/null | cut -d'=' -f2 || echo 'not set')"
    echo "   • Git Repo URL: $(grep '^KB_GIT_REPO_URL=' .env 2>/dev/null | cut -d'=' -f2 || echo 'not configured')"
    echo "   • Git Branch: $(grep '^KB_GIT_BRANCH=' .env 2>/dev/null | cut -d'=' -f2 || echo 'main')"
    echo "   • Auto Sync: $(grep '^KB_GIT_AUTO_SYNC=' .env 2>/dev/null | cut -d'=' -f2 || echo 'true')"
    echo "   • Auth Token: $([ -n "$(grep '^KB_GIT_AUTH_TOKEN=' .env 2>/dev/null)" ] && echo 'configured' || echo 'not set')"
else
    echo "   • .env file not found"
fi
echo ""

if grep -q "git_sync_not_available" <<< "$OUTPUT" 2>/dev/null; then
    echo "🔧 Setup Required:"
    echo "   1. Run: ./scripts/setup-kb-git-repo.sh"
    echo "   2. Configure your Git repository URL"
    echo "   3. Set KB_STORAGE_MODE=hybrid for full functionality"
    echo ""
fi

echo "💡 Usage Tips:"
echo "   • Use 'force=true' parameter for sync-from-git to override checks"
echo "   • Sync status shows if Git ahead of database or vice versa"
echo "   • Auto-sync runs in background every hour by default"
echo ""
echo "🚀 Quick Commands:"
echo "   • Setup Git repo: ./scripts/setup-kb-git-repo.sh"
echo "   • Manual sync: curl -X POST -H 'X-API-Key: $API_KEY' http://kb-service:8000/sync/from-git"
echo "   • Check status: curl -H 'X-API-Key: $API_KEY' http://kb-service:8000/sync/status"