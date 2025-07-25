#!/bin/bash

# Deployment script for Gaia services
# Run this on your local machine with Fly CLI configured

echo "🚀 Deploying Gaia Services with Service Discovery"
echo "================================================"
echo ""

# Check if fly CLI is available
if ! command -v fly &> /dev/null; then
    echo "❌ Error: Fly CLI not found. Please install it first."
    echo "Visit: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Function to deploy a service
deploy_service() {
    local service=$1
    local app_name=$2
    
    echo ""
    echo "📦 Deploying $service service to $app_name..."
    echo "-------------------------------------------"
    
    fly deploy --config fly.$service.dev.toml --remote-only -a $app_name
    
    if [ $? -eq 0 ]; then
        echo "✅ $service service deployed successfully!"
        return 0
    else
        echo "❌ Failed to deploy $service service"
        return 1
    fi
}

# Ask for confirmation
echo "This will deploy the following services:"
echo "1. Auth Service (gaia-auth-dev)"
echo "2. Asset Service (gaia-asset-dev)"
echo "3. KB Service (gaia-kb-dev)"
echo "4. Chat Service (gaia-chat-dev)"
echo "5. Gateway Service (gaia-gateway-dev)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Deploy services in order
echo "Starting deployments..."

deploy_service "auth" "gaia-auth-dev"
deploy_service "asset" "gaia-asset-dev"
deploy_service "kb" "gaia-kb-dev"
deploy_service "chat" "gaia-chat-dev"
deploy_service "gateway" "gaia-gateway-dev"

echo ""
echo "🎉 Deployment process complete!"
echo ""
echo "To verify the deployments:"
echo "1. Check health: curl https://gaia-gateway-dev.fly.dev/health | jq"
echo "2. Test service discovery: ./scripts/test-service-discovery.sh https://gaia-gateway-dev.fly.dev"
echo "3. Test new chat features: ./scripts/test-new-chat-simple.sh https://gaia-gateway-dev.fly.dev"
echo ""
echo "Key improvements deployed:"
echo "- MCP-agent hot loading (5-10s → 1-3s)"
echo "- Intelligent chat routing (single LLM call)"
echo "- Service discovery (automatic endpoint detection)"
echo "- Enhanced health endpoints (route exposure)"