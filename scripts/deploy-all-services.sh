#!/bin/bash

# Deploy all services with enhanced health endpoints and service discovery

echo "🚀 Deploying Gaia Services with Service Discovery"
echo "================================================"
echo ""

# Extract and export Fly token
export FLY_API_TOKEN=$(grep FLY_API_TOKEN .env | cut -d'=' -f2- | sed 's/^"//;s/"$//')

if [ -z "$FLY_API_TOKEN" ]; then
    echo "❌ Error: FLY_API_TOKEN not found in .env"
    exit 1
fi

echo "✅ Fly token loaded"
echo ""

# Function to deploy a service
deploy_service() {
    local service=$1
    local app_name=$2
    
    echo "📦 Deploying $service service to $app_name..."
    echo "-------------------------------------------"
    
    /home/dev/.fly/bin/flyctl deploy --config fly.$service.dev.toml --remote-only -a $app_name
    
    if [ $? -eq 0 ]; then
        echo "✅ $service service deployed successfully!"
    else
        echo "❌ Failed to deploy $service service"
        return 1
    fi
    echo ""
}

# Deploy services in order
echo "1️⃣ Auth Service"
deploy_service "auth" "gaia-auth-dev"

echo "2️⃣ Asset Service"
deploy_service "asset" "gaia-asset-dev"

echo "3️⃣ KB Service"
deploy_service "kb" "gaia-kb-dev"

echo "4️⃣ Chat Service (with hot loading & intelligent routing)"
deploy_service "chat" "gaia-chat-dev"

echo "5️⃣ Gateway Service (with service discovery)"
deploy_service "gateway" "gaia-gateway-dev"

echo ""
echo "🎉 All deployments complete!"
echo ""
echo "Next steps:"
echo "1. Run ./scripts/test-service-discovery.sh to verify"
echo "2. Test new endpoints with ./scripts/test-new-chat-simple.sh"
echo "3. Check service health at https://gaia-gateway-dev.fly.dev/health"