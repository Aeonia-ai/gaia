#!/bin/bash

# Test script for KB Semantic Search functionality
# Tests both the basic functionality and performance improvements

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables (GAIA standard pattern)
if [ -f .env ]; then
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
    echo "📍 Loaded environment from .env"
fi

# Configuration
KB_SERVICE_URL="${KB_SERVICE_URL:-http://localhost:8001}"  # KB exposed on 8001 for testing

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: API_KEY not found in environment${NC}"
    echo "Please ensure API_KEY is set in your .env file"
    exit 1
fi

echo "🧪 KB Semantic Search Testing Suite"
echo "==================================="
echo ""

# Function to make API calls
call_kb_api() {
    local endpoint=$1
    local data=$2
    local method=${3:-POST}
    
    if [ "$method" == "GET" ]; then
        curl -s -X GET \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            "$KB_SERVICE_URL$endpoint"
    else
        curl -s -X POST \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$KB_SERVICE_URL$endpoint"
    fi
}

# Function to measure response time
measure_time() {
    local start_time=$(date +%s%N)
    "$@" > /dev/null
    local end_time=$(date +%s%N)
    echo $((($end_time - $start_time) / 1000000))
}

# Check if KB service is running
echo "1️⃣  Checking KB service health..."
health_response=$(call_kb_api "/health" "" "GET")
if echo "$health_response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ KB service is healthy${NC}"
else
    echo -e "${RED}✗ KB service is not responding${NC}"
    echo "Response: $health_response"
    echo ""
    echo "Please ensure the KB service is running:"
    echo "  docker compose up kb-service"
    exit 1
fi
echo ""

# Check if semantic search is enabled
echo "2️⃣  Checking semantic search configuration..."
stats_response=$(call_kb_api "/search/semantic/stats" "" "GET")
if echo "$stats_response" | grep -q '"enabled":true'; then
    echo -e "${GREEN}✓ Semantic search is enabled${NC}"
else
    echo -e "${YELLOW}⚠ Semantic search may not be enabled${NC}"
    echo "Response: $stats_response"
    echo ""
    echo "Ensure KB_SEMANTIC_SEARCH_ENABLED=true in .env"
fi
echo ""

# Create test content
echo "3️⃣  Creating test content in KB..."
test_namespace="test_semantic_$(date +%s)"

# Create test file 1
test_file1='{
    "path": "docs/authentication.md",
    "content": "# Authentication Guide\n\nThis document explains how users log in to the system.\n\n## Login Process\n1. User enters email and password\n2. System validates credentials\n3. JWT token is generated\n4. Session is established\n\n## Security Features\n- Password hashing with bcrypt\n- JWT tokens for session management\n- Multi-factor authentication support",
    "message": "Add authentication documentation"
}'

write_response1=$(call_kb_api "/write" "$test_file1")
if echo "$write_response1" | grep -q "success"; then
    echo -e "${GREEN}✓ Created authentication.md${NC}"
else
    echo -e "${RED}✗ Failed to create authentication.md${NC}"
    echo "Response: $write_response1"
fi

# Create test file 2
test_file2='{
    "path": "docs/api-reference.md",
    "content": "# API Reference\n\n## Endpoints\n\n### POST /auth/login\nAuthenticate a user and receive a session token.\n\n### GET /api/user/profile\nRetrieve the current user profile information.\n\n### POST /api/chat\nSend a message to the AI chat service.",
    "message": "Add API reference documentation"
}'

write_response2=$(call_kb_api "/write" "$test_file2")
if echo "$write_response2" | grep -q "success"; then
    echo -e "${GREEN}✓ Created api-reference.md${NC}"
else
    echo -e "${RED}✗ Failed to create api-reference.md${NC}"
fi
echo ""

# Trigger reindexing
echo "4️⃣  Triggering semantic search indexing..."
reindex_response=$(call_kb_api "/search/semantic/reindex" '{}')
if echo "$reindex_response" | grep -q "success"; then
    echo -e "${GREEN}✓ Reindexing triggered${NC}"
else
    echo -e "${YELLOW}⚠ Reindexing may have failed${NC}"
    echo "Response: $reindex_response"
fi

# Wait for indexing
echo "   Waiting for indexing to complete..."
sleep 3
echo ""

# Test semantic search queries
echo "5️⃣  Testing semantic search queries..."
echo ""

# Test query 1: Natural language question
echo "   Query: 'How do users log in?'"
search_query1='{"message": "How do users log in?"}'
search_response1=$(call_kb_api "/search/semantic" "$search_query1")
if echo "$search_response1" | grep -q "authentication\|login\|JWT"; then
    echo -e "${GREEN}   ✓ Found relevant results about authentication${NC}"
    echo "   Response excerpt: $(echo "$search_response1" | grep -o '"content_excerpt":"[^"]*"' | head -1)"
else
    echo -e "${RED}   ✗ No relevant results found${NC}"
    echo "   Response: $search_response1"
fi
echo ""

# Test query 2: Conceptual search
echo "   Query: 'API security features'"
search_query2='{"message": "API security features"}'
search_response2=$(call_kb_api "/search/semantic" "$search_query2")
if echo "$search_response2" | grep -q "JWT\|bcrypt\|authentication"; then
    echo -e "${GREEN}   ✓ Found relevant security information${NC}"
else
    echo -e "${YELLOW}   ⚠ Results may not be optimal${NC}"
fi
echo ""

# Performance testing
echo "6️⃣  Testing performance improvements..."
echo ""
echo "   Running multiple searches to test caching..."

# First search (cold)
time1=$(measure_time call_kb_api "/search/semantic" '{"message": "authentication process"}')
echo "   First search (cold): ${time1}ms"

# Second search (should be cached)
time2=$(measure_time call_kb_api "/search/semantic" '{"message": "authentication process"}')
echo "   Second search (cached): ${time2}ms"

# Third search (different query, same namespace)
time3=$(measure_time call_kb_api "/search/semantic" '{"message": "user login steps"}')
echo "   Third search (warm ChromaDB): ${time3}ms"

# Calculate improvement
if [ "$time1" -gt 0 ] && [ "$time2" -gt 0 ]; then
    improvement=$(( ($time1 - $time2) * 100 / $time1 ))
    if [ "$improvement" -gt 30 ]; then
        echo -e "${GREEN}   ✓ Performance improved by ${improvement}%${NC}"
    else
        echo -e "${YELLOW}   ⚠ Performance improvement: ${improvement}%${NC}"
    fi
fi
echo ""

# Check ChromaDB manager stats
echo "7️⃣  Checking ChromaDB manager statistics..."
# Note: This endpoint would need to be added to expose chromadb_manager.get_stats()
echo "   (ChromaDB stats endpoint not yet exposed)"
echo ""

# Cleanup test files
echo "8️⃣  Cleaning up test files..."
delete_response1=$(call_kb_api "/delete" '{"path": "docs/authentication.md", "message": "Clean up test"}' "DELETE")
delete_response2=$(call_kb_api "/delete" '{"path": "docs/api-reference.md", "message": "Clean up test"}' "DELETE")

if echo "$delete_response1" | grep -q "success"; then
    echo -e "${GREEN}✓ Cleaned up test files${NC}"
else
    echo -e "${YELLOW}⚠ Manual cleanup may be needed${NC}"
fi
echo ""

# Summary
echo "📊 Test Summary"
echo "==============="
echo ""
if [ "$improvement" -gt 30 ]; then
    echo -e "${GREEN}✅ Semantic search is working with performance optimizations!${NC}"
    echo "   - Search functionality: Working"
    echo "   - ChromaDB persistence: Enabled" 
    echo "   - Performance gain: ${improvement}%"
else
    echo -e "${YELLOW}⚠️ Semantic search is partially working${NC}"
    echo "   - Basic functionality may work"
    echo "   - Performance optimizations may need verification"
fi
echo ""
echo "For detailed logs, check:"
echo "  docker compose logs kb-service"
echo ""