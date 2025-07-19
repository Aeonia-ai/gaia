#!/bin/bash
# Script to check if authentication endpoints are being modified
# and remind developers about public endpoint requirements

echo "🔍 Checking authentication endpoint modifications..."

# Check if any auth-related files are being committed
AUTH_FILES=$(git diff --cached --name-only | grep -E "(auth|gateway_client|routes/auth)\.py$")

if [ -n "$AUTH_FILES" ]; then
    echo "⚠️  Authentication-related files detected in commit:"
    echo "$AUTH_FILES"
    echo ""
    echo "Please ensure:"
    echo "✓ Public endpoints (/auth/login, /auth/register) remain public"
    echo "✓ No authentication headers are added to public endpoint calls"
    echo "✓ Contract tests pass: pytest tests/web/test_auth_flow.py"
    echo "✓ Changes are documented in docs/api-contracts.md"
    echo ""
    
    # Check for common mistakes
    if git diff --cached | grep -E "(headers.*api_key|headers.*authorization).*/auth/(login|register)" > /dev/null; then
        echo "❌ ERROR: Found authentication headers being added to public endpoints!"
        echo "Public endpoints must not require authentication."
        exit 1
    fi
    
    # Check for auth dependencies on public endpoints
    if git diff --cached | grep -E "@app\.(post|get).*auth/(login|register).*Depends.*auth" > /dev/null; then
        echo "❌ ERROR: Found auth dependency on public endpoint!"
        echo "Login and register endpoints must be publicly accessible."
        exit 1
    fi
    
    echo "✅ No obvious auth issues detected, but please run tests to confirm."
fi

exit 0