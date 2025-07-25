#!/bin/bash

# Test new chat features without bc dependency

echo "🆕 Testing New Chat Features"
echo "============================"
echo ""

BASE_URL="${1:-https://gaia-gateway-dev.fly.dev}"
API_KEY="${2:-hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY}"

# Test existing endpoints first
echo "1. Testing existing chat endpoints:"
echo ""

# Test standard chat
echo "📱 Standard Chat:"
START=$(date +%s)
curl -X POST "$BASE_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello!", "stream": false}' \
  -s -o /tmp/chat1.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
cat /tmp/chat1.json | python3 -m json.tool 2>/dev/null | grep -E "(response|content)" | head -5
echo ""

# Test MCP agent (should be hot loaded now)
echo "🤖 MCP Agent (hot loaded):"
START=$(date +%s)
curl -X POST "$BASE_URL/api/v1/chat/mcp-agent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Create a simple scene", "stream": false}' \
  -s -o /tmp/chat2.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
cat /tmp/chat2.json | python3 -m json.tool 2>/dev/null | grep -E "(response|content)" | head -10
echo ""

# Test new endpoints (may not be deployed yet)
echo "2. Testing new chat endpoints (service discovery):"
echo ""

# Test intelligent routing
echo "🧠 Intelligent Chat:"
curl -X POST "$BASE_URL/chat/intelligent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "What is the weather?", "stream": false}' \
  -s | python3 -m json.tool 2>/dev/null | head -10
echo ""

# Test fast chat
echo "⚡ Fast Chat:"
curl -X POST "$BASE_URL/chat/fast" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello there!", "stream": false}' \
  -s | python3 -m json.tool 2>/dev/null | head -10
echo ""

# Test direct MCP agent
echo "🎯 Direct MCP Agent:"
curl -X POST "$BASE_URL/chat/mcp-agent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Tell a short story", "stream": false}' \
  -s | python3 -m json.tool 2>/dev/null | head -10
echo ""

# Check service health
echo "3. Checking service health:"
echo ""
curl -s "$BASE_URL/health" | python3 -m json.tool 2>/dev/null | grep -A5 "services"
echo ""

echo "✅ Test complete!"
echo ""
echo "Summary:"
echo "- Standard chat and MCP agent endpoints should work"
echo "- New endpoints require deployment of updated gateway"
echo "- MCP agent should respond faster due to hot loading"