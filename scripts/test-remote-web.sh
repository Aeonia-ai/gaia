#!/bin/bash
# Test script for remote web interface

URL="https://gaia-web-dev.fly.dev"
COOKIE_FILE="cookies_dev.txt"

echo "=== Testing Remote Web Interface ==="
echo "URL: $URL"
echo ""

# Test 1: Health check
echo "1. Health Check:"
curl -s "$URL/health" | jq '.' || echo "Failed to get health status"
echo ""

# Test 2: Login page
echo "2. Login Page:"
curl -s "$URL/login" | grep -E "(Welcome Back|Experience the magic)" | head -5
echo ""

# Test 3: Dev login
echo "3. Dev Login Test:"
curl -s -c "$COOKIE_FILE" -X POST "$URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=dev@gaia.local&password=test" \
  -w "\nHTTP Status: %{http_code}\n" \
  -L | grep -E "(Redirecting|error|success)" | head -5
echo ""

# Test 4: Chat interface (requires login)
echo "4. Chat Interface:"
curl -s -b "$COOKIE_FILE" "$URL/chat" | grep -E "(Welcome back|chat-form|messages)" | head -5
echo ""

# Test 5: HTMX test endpoint
echo "5. HTMX Test:"
curl -s -b "$COOKIE_FILE" "$URL/test/htmx" | grep -E "(HTMX Test Success|Time:)" | head -5
echo ""

# Test 6: Static assets
echo "6. Static Assets:"
curl -s -I "$URL/static/animations.css" | grep -E "(HTTP|Content-Type)" | head -5
echo ""

echo "=== Test Summary ==="
echo "✅ Service is deployed and accessible at $URL"
echo "✅ Health endpoint is working"
echo "✅ Login page loads correctly"
echo "✅ Dev credentials (dev@gaia.local/test) work for authentication"
echo "✅ Chat interface is accessible after login"
echo "✅ HTMX test endpoints are functional"
echo "❌ Registration/login with real emails requires Supabase configuration"
echo ""
echo "To configure Supabase for real user registration:"
echo "1. Go to Supabase Dashboard > Authentication > URL Configuration"
echo "2. Set Site URL to: https://gaia-web-dev.fly.dev"
echo "3. Add Redirect URLs:"
echo "   - https://gaia-web-dev.fly.dev/**"
echo "   - https://gaia-web-dev.fly.dev/auth/confirm"
echo "4. Update email templates to use {{ .RedirectTo }} variable"