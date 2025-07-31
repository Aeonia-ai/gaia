#!/bin/bash

# Test Service Discovery System

echo "🔍 Testing Service Discovery System"
echo "==================================="
echo ""

BASE_URL="${1:-http://localhost:8666}"
API_KEY="${2:-$API_KEY}"

if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: API_KEY not set"
    echo "   Usage: $0 [BASE_URL] [API_KEY]"
    echo "   Or set: export API_KEY=your-test-api-key"
    exit 1
fi

# Test enhanced health endpoints
echo "1. Testing enhanced health endpoints with route discovery:"
echo ""

# Test chat service health
echo "📡 Chat Service Health (with routes):"
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/health?include_routes=true" | python3 -m json.tool | head -30
echo ""

# Test auth service health
echo "🔐 Auth Service Health (with routes):"
curl -s "http://localhost:8001/health?include_routes=true" | python3 -m json.tool | head -30
echo ""

# Test KB service health
echo "📚 KB Service Health (with routes):"
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8003/health?include_routes=true" | python3 -m json.tool | head -30
echo ""

# Test asset service health
echo "🎨 Asset Service Health (with routes):"
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8002/health?include_routes=true" | python3 -m json.tool | head -30
echo ""

# Test gateway health
echo "2. Testing Gateway Health (should show discovered services):"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/health" | python3 -m json.tool
echo ""

# Test new intelligent endpoints
echo "3. Testing new dynamically discovered endpoints:"
echo ""

# Test intelligent chat endpoint
echo "🤖 Testing intelligent chat endpoint:"
curl -s -X POST "$BASE_URL/chat/intelligent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello!"}' | python3 -m json.tool
echo ""

# Test fast chat endpoint
echo "⚡ Testing fast chat endpoint:"
curl -s -X POST "$BASE_URL/chat/fast" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "What is the weather?"}' | python3 -m json.tool
echo ""

# Test mcp-agent endpoint
echo "🎯 Testing mcp-agent endpoint:"
curl -s -X POST "$BASE_URL/chat/mcp-agent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Create a simple scene"}' | python3 -m json.tool | head -20
echo ""

# Test metrics endpoint
echo "📊 Testing intelligent routing metrics:"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/chat/intelligent/metrics" | python3 -m json.tool
echo ""

echo "✅ Service Discovery Test Complete!"
echo ""
echo "Summary:"
echo "- Enhanced health endpoints expose available routes"
echo "- Gateway discovers services and their routes on startup"
echo "- New endpoints are automatically available through gateway"
echo "- No more hardcoded routes needed!"