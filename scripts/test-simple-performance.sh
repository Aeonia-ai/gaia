#!/bin/bash

# Simple performance test without bc dependency

echo "🚀 Simple Performance Test"
echo "========================"
echo ""

BASE_URL="${1:-https://gaia-gateway-dev.fly.dev}"
API_KEY="${2:-test-key}"

# Test 1: MCP-Agent endpoint (first request)
echo "1. Testing MCP-Agent (first request - should initialize)"
START=$(date +%s)
curl -X POST "$BASE_URL/chat/mcp-agent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Create a tavern scene", "stream": false}' \
  -s -o /tmp/response1.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
echo "Response preview:"
cat /tmp/response1.json | python3 -m json.tool 2>/dev/null | grep -A2 "content" | head -10
echo ""

# Wait a bit
sleep 2

# Test 2: MCP-Agent endpoint (second request - should be hot)
echo "2. Testing MCP-Agent (second request - should be faster)"
START=$(date +%s)
curl -X POST "$BASE_URL/chat/mcp-agent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Tell a story from multiple perspectives", "stream": false}' \
  -s -o /tmp/response2.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
echo "Response preview:"
cat /tmp/response2.json | python3 -m json.tool 2>/dev/null | grep -A2 "content" | head -10
echo ""

# Test 3: Intelligent routing (simple message)
echo "3. Testing Intelligent routing (simple message)"
START=$(date +%s)
curl -X POST "$BASE_URL/chat/intelligent" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello!", "stream": false}' \
  -s -o /tmp/response3.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
echo "Response:"
cat /tmp/response3.json | python3 -m json.tool 2>/dev/null | head -20
echo ""

# Test 4: Direct fast endpoint
echo "4. Testing Fast endpoint (no routing)"
START=$(date +%s)
curl -X POST "$BASE_URL/chat/fast" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "What is the weather?", "stream": false}' \
  -s -o /tmp/response4.json
END=$(date +%s)
DIFF=$((END - START))
echo "Response time: ${DIFF}s"
echo "Response:"
cat /tmp/response4.json | python3 -m json.tool 2>/dev/null | head -20
echo ""

echo "Test complete!"
echo "=============="
echo "Expected results:"
echo "- First MCP-agent: 3-6s (initialization)"
echo "- Second MCP-agent: 1-3s (hot loaded)"
echo "- Intelligent routing: ~1s (simple message)"
echo "- Fast endpoint: ~1s (direct)"