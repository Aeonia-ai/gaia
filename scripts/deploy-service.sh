#!/bin/bash
# Deploy a service with proper configuration and secret management
# Usage: ./scripts/deploy-service.sh gateway dev

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVICE=$1
ENVIRONMENT=$2

if [ -z "$SERVICE" ] || [ -z "$ENVIRONMENT" ]; then
    echo -e "${RED}Usage: $0 <service> <environment>${NC}"
    echo "Example: $0 gateway dev"
    echo "Services: gateway, auth, asset, chat"
    echo "Environments: dev, staging, prod"
    exit 1
fi

APP_NAME="gaia-${SERVICE}-${ENVIRONMENT}"
CONFIG_FILE="fly.${SERVICE}.${ENVIRONMENT}.toml"

echo -e "${BLUE}=== Deploying ${APP_NAME} ===${NC}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file $CONFIG_FILE not found${NC}"
    exit 1
fi

# Step 1: Deploy the service
echo -e "${BLUE}Step 1: Deploying application...${NC}"
fly deploy -a "$APP_NAME" -c "$CONFIG_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Deployment successful${NC}"

# Step 2: Sync secrets
echo -e "${BLUE}Step 2: Syncing secrets...${NC}"
./scripts/sync-secrets.sh --env "$ENVIRONMENT" --services "$SERVICE"

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Warning: Secret sync had issues${NC}"
fi

# Step 3: Wait for service to be healthy
echo -e "${BLUE}Step 3: Waiting for service to be healthy...${NC}"
sleep 10  # Give the service time to start

MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "https://${APP_NAME}.fly.dev/health" 2>/dev/null || echo "000")
    
    if [ "$response" == "200" ]; then
        echo -e "${GREEN}✓ Service is healthy${NC}"
        break
    else
        echo -e "${YELLOW}Waiting for service to be ready... (attempt $((ATTEMPT+1))/$MAX_ATTEMPTS)${NC}"
        sleep 5
        ((ATTEMPT++))
    fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}Service failed to become healthy in time${NC}"
    echo "Check logs: fly logs -a $APP_NAME"
    exit 1
fi

# Step 4: Run verification
echo -e "${BLUE}Step 4: Running deployment verification...${NC}"
./scripts/verify-deployment.sh --env "$ENVIRONMENT"

# Step 5: Run integration tests
echo -e "${BLUE}Step 5: Running integration tests...${NC}"
case $SERVICE in
    gateway)
        ./scripts/test.sh --url "https://${APP_NAME}.fly.dev" health
        ./scripts/test.sh --url "https://${APP_NAME}.fly.dev" providers
        ;;
    auth)
        ./scripts/test.sh --url "https://gaia-gateway-${ENVIRONMENT}.fly.dev" auth-all
        ;;
    asset)
        ./scripts/test.sh --url "https://gaia-gateway-${ENVIRONMENT}.fly.dev" assets-test
        ;;
    chat)
        ./scripts/test.sh --url "https://gaia-gateway-${ENVIRONMENT}.fly.dev" chat "Hello"
        ;;
esac

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Service URL: https://${APP_NAME}.fly.dev"
echo -e "View logs: fly logs -a $APP_NAME"
echo -e "SSH into service: fly ssh console -a $APP_NAME"