#!/bin/bash

# Test semantic search using Docker compose
# This avoids local dependency installation issues

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🐳 Testing Semantic Search with Docker"
echo "======================================="
echo ""

# Step 1: Build the KB service with new dependencies
echo "1️⃣  Building KB service with semantic search dependencies..."
docker compose build kb-service 2>&1 | tail -5

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ KB service built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build KB service${NC}"
    echo "  Check: docker compose build kb-service"
    exit 1
fi
echo ""

# Step 2: Start the KB service
echo "2️⃣  Starting KB service..."
docker compose up -d kb-service redis

# Wait for service to be ready
echo "   Waiting for service to start..."
sleep 5

# Check if running
if docker compose ps | grep -q "kb-service.*running"; then
    echo -e "${GREEN}✓ KB service is running${NC}"
else
    echo -e "${RED}✗ KB service failed to start${NC}"
    echo "  Check logs: docker compose logs kb-service"
    exit 1
fi
echo ""

# Step 3: Check service health
echo "3️⃣  Checking service health..."
health_response=$(curl -s http://localhost:8000/health)

if echo "$health_response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ KB service is healthy${NC}"
else
    echo -e "${YELLOW}⚠ KB service health check failed${NC}"
    echo "  Response: $health_response"
fi
echo ""

# Step 4: Check if semantic search is enabled
echo "4️⃣  Checking semantic search configuration..."

# Load environment variables (GAIA standard pattern)
if [ -f .env ]; then
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

if [ -z "$API_KEY" ]; then
    echo -e "${RED}✗ API_KEY not found in .env${NC}"
    echo "  Please set API_KEY in your .env file"
    exit 1
fi

# Test semantic search stats endpoint
stats_response=$(curl -s -X GET \
    -H "X-API-Key: $API_KEY" \
    http://localhost:8000/search/semantic/stats)

if echo "$stats_response" | grep -q '"enabled":true'; then
    echo -e "${GREEN}✓ Semantic search is enabled${NC}"
    echo "  Response: $stats_response"
elif echo "$stats_response" | grep -q '"enabled":false'; then
    echo -e "${YELLOW}⚠ Semantic search is disabled${NC}"
    echo "  Ensure KB_SEMANTIC_SEARCH_ENABLED=true in .env"
    echo "  Response: $stats_response"
else
    echo -e "${RED}✗ Could not check semantic search status${NC}"
    echo "  Response: $stats_response"
fi
echo ""

# Step 5: Test a semantic search query
echo "5️⃣  Testing semantic search..."

# Create a simple test query
test_query='{"message": "how to authenticate users"}'

search_response=$(curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$test_query" \
    http://localhost:8000/search/semantic)

if echo "$search_response" | grep -q "success\|results\|indexing"; then
    echo -e "${GREEN}✓ Semantic search endpoint is working${NC}"
    
    if echo "$search_response" | grep -q "indexing"; then
        echo "  Status: Indexing in progress (this is normal for first run)"
    else
        echo "  Response preview: $(echo "$search_response" | head -c 200)..."
    fi
else
    echo -e "${RED}✗ Semantic search failed${NC}"
    echo "  Response: $search_response"
fi
echo ""

# Step 6: Check ChromaDB is working
echo "6️⃣  Checking ChromaDB integration..."
# Look for ChromaDB-related logs
docker compose logs kb-service 2>&1 | grep -i "chroma" | tail -3

if docker compose logs kb-service 2>&1 | grep -q "ChromaDB manager initialized"; then
    echo -e "${GREEN}✓ ChromaDB manager is initialized${NC}"
else
    echo -e "${YELLOW}⚠ ChromaDB manager status unclear${NC}"
    echo "  Check full logs: docker compose logs kb-service"
fi
echo ""

# Summary
echo "📊 Summary"
echo "=========="
echo ""
echo "KB Service: Running on http://localhost:8000"
echo "Semantic Search Endpoint: POST /search/semantic"
echo "Stats Endpoint: GET /search/semantic/stats"
echo "Reindex Endpoint: POST /search/semantic/reindex"
echo ""
echo "Next steps:"
echo "1. Create some KB content via /write endpoint"
echo "2. Trigger reindexing via /search/semantic/reindex"
echo "3. Search with natural language queries via /search/semantic"
echo ""
echo "View logs:"
echo "  docker compose logs -f kb-service"
echo ""
echo "Stop services:"
echo "  docker compose down"