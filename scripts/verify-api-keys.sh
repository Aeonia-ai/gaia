#!/bin/bash
# Verify API key configuration across all Gaia services
set -e

echo "Verifying API key configuration across services..."
echo "================================================"

# Services and their API key env vars (macOS compatible)
SERVICES="gaia-gateway-dev:API_KEY gaia-auth-dev:API_KEY gaia-web-dev:WEB_API_KEY gaia-asset-dev:API_KEY gaia-chat-dev:API_KEY"

# Get the digest from the first service
FIRST_DIGEST=""
ALL_MATCH=true

for PAIR in $SERVICES; do
    SERVICE=$(echo $PAIR | cut -d: -f1)
    ENV_VAR=$(echo $PAIR | cut -d: -f2)
    
    echo -n "Checking $SERVICE ($ENV_VAR): "
    
    # Get the digest for this service (exact match)
    DIGEST=$(fly secrets list -a "$SERVICE" 2>/dev/null | grep "^${ENV_VAR} " | awk '{print $2}')
    
    if [ -z "$DIGEST" ]; then
        echo "❌ NOT FOUND!"
        ALL_MATCH=false
    elif [ -z "$FIRST_DIGEST" ]; then
        FIRST_DIGEST="$DIGEST"
        echo "✅ $DIGEST (reference)"
    elif [ "$DIGEST" != "$FIRST_DIGEST" ]; then
        echo "❌ $DIGEST (MISMATCH!)"
        ALL_MATCH=false
    else
        echo "✅ $DIGEST"
    fi
done

echo "================================================"

if $ALL_MATCH && [ -n "$FIRST_DIGEST" ]; then
    echo "✅ SUCCESS: All services have matching API keys!"
    echo ""
    echo "API Key Digest: $FIRST_DIGEST"
else
    echo "❌ FAILURE: API key configuration issues detected!"
    echo ""
    echo "To fix mismatched API keys:"
    echo "1. Get your API key from .env or a working service"
    echo "2. Run the following commands:"
    echo ""
    echo "API_KEY=\"your-actual-api-key-here\""
    for PAIR in $SERVICES; do
        SERVICE=$(echo $PAIR | cut -d: -f1)
        ENV_VAR=$(echo $PAIR | cut -d: -f2)
        echo "fly secrets set -a $SERVICE $ENV_VAR=\"\$API_KEY\""
    done
    exit 1
fi