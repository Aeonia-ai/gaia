#\!/bin/bash

# Test web service directly without going through gateway
echo "Testing direct web service authentication flow..."

# Try to access chat without auth (should redirect)
echo -e "\n1. Testing unauthenticated access to /chat..."
curl -L http://localhost:8080/chat -v 2>&1 | grep -E "(HTTP/|Location:|303)"

# Since auth service is down due to asyncpg, let's verify the SPA navigation works
echo -e "\n2. Testing SPA navigation headers..."
curl http://localhost:8080/login \
  -H "HX-Request: true" \
  -H "Accept: text/html" \
  -s | grep -E "(hx-|id=\"main-content\"|htmx)" | head -5

echo -e "\n3. Testing home page navigation..."
curl http://localhost:8080/ \
  -H "Accept: text/html" \
  -s | grep -E "(href=\"/chat\"|href=\"/login\"|data-page|main-content)" | head -5

echo -e "\n4. Checking if SPA scripts are loaded..."
curl http://localhost:8080/ -s | grep -E "(htmx|historyCacheSize|beforeSwap)" | head -5

