#!/bin/bash
# Script to set Fly.io secrets from environment files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 <environment>"
    echo "Environments: dev, staging, production"
    echo
    echo "This script sets Fly.io secrets from .env.<environment> files"
    echo "Example: $0 staging"
    exit 1
}

# Check arguments
if [ $# -ne 1 ]; then
    usage
fi

ENV=$1
ENV_FILE=".env.$ENV"

# Validate environment
if [[ "$ENV" != "dev" && "$ENV" != "staging" && "$ENV" != "production" ]]; then
    echo -e "${RED}Error: Invalid environment '$ENV'${NC}"
    usage
fi

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file '$ENV_FILE' not found${NC}"
    exit 1
fi

# Set app name based on environment
APP_NAME="gaia-gateway-$ENV"

echo -e "${YELLOW}Setting secrets for $APP_NAME from $ENV_FILE...${NC}"

# Source the environment file and set DATABASE_URL
if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
    DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2-)
    echo -e "${GREEN}Setting DATABASE_URL...${NC}"
    fly secrets set DATABASE_URL="$DATABASE_URL" -a "$APP_NAME"
else
    echo -e "${RED}DATABASE_URL not found in $ENV_FILE${NC}"
fi

echo -e "${GREEN}Done! Secrets have been set for $APP_NAME${NC}"
echo
echo "To verify secrets are set:"
echo "  fly secrets list -a $APP_NAME"