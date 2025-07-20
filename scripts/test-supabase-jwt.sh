#!/bin/bash
# Test Supabase JWT authentication with the gateway

set -e

echo "🔐 Testing Supabase JWT Authentication"
echo "====================================="

# For testing, we'll use a mock JWT token
# In production, this would come from Supabase after login
JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3MjE0MDAwMDAsImV4cCI6MTcyMTQwMzYwMH0.test-signature"

echo -e "\n1. Testing health endpoint with JWT:"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8666/health | jq . || echo "Failed"

echo -e "\n2. Testing streaming status with JWT:"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8666/api/v0.2/chat/stream/status | jq . || echo "Failed"

echo -e "\n3. Testing without any authentication (should fail):"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8666/api/v0.2/chat/stream/status || echo "Expected failure"

echo -e "\n4. Testing with API key (backward compatibility):"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE" \
  http://localhost:8666/api/v0.2/chat/stream/status | jq . || echo "Failed"

echo -e "\n✅ Test complete!"