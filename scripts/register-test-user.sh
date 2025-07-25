#!/bin/bash

# Register a test user on the deployed Fly.io environment

EMAIL="${1:-jason.asbahr+test1@gmail.com}"
PASSWORD="${2:-TestPassword123!}"
BASE_URL="${3:-https://gaia-web-dev.fly.dev}"

echo "Registering user: $EMAIL"
echo "At: $BASE_URL"

# Register the user
response=$(curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=$EMAIL&password=$PASSWORD" \
  -c cookies.txt \
  -s)

# Check if registration was successful
if echo "$response" | grep -q "verification\|confirm\|success"; then
    echo "✅ Registration initiated!"
    echo "Check your email for verification link"
    echo ""
    echo "Response:"
    echo "$response" | grep -E "(success|verification|confirm|email)" | head -5
else
    echo "❌ Registration may have failed"
    echo "Response:"
    echo "$response" | grep -E "(error|failed|already)" | head -5
fi

echo ""
echo "Once verified, you can login with:"
echo "Email: $EMAIL"
echo "Password: $PASSWORD"