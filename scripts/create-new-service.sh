#!/bin/bash

# Create New Microservice Script
# Usage: ./scripts/create-new-service.sh <service-name> [port]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if service name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <service-name> [port]"
    echo "Example: $0 analytics 8005"
    exit 1
fi

SERVICE_NAME="$1"
SERVICE_NAME_UPPER=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]')
SERVICE_PORT="${2:-8000}"  # Default to 8000 if not provided

# Derive internal port (increment by 1000 from external port for local development)
if [ "$SERVICE_PORT" -eq 8000 ]; then
    INTERNAL_PORT=9000
else
    INTERNAL_PORT=$((SERVICE_PORT + 1000))
fi

echo -e "${BLUE}Creating new microservice: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}External port: ${SERVICE_PORT}${NC}"
echo -e "${BLUE}Internal port: ${INTERNAL_PORT}${NC}"

# 1. Create service directory structure
echo -e "\n${GREEN}1. Creating service directory structure...${NC}"
mkdir -p "app/services/${SERVICE_NAME}"
touch "app/services/${SERVICE_NAME}/__init__.py"

# 2. Create main.py for the service
echo -e "\n${GREEN}2. Creating service main.py...${NC}"
cat > "app/services/${SERVICE_NAME}/main.py" << EOF
"""
Gaia ${SERVICE_NAME^} Service
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.shared.config import settings
from app.shared.logging import configure_logging_for_service, logger
from app.shared.database import engine, Base
from app.shared.nats_client import NATSClient
from app.shared.security import get_current_auth_legacy

# Setup logging
configure_logging_for_service("${SERVICE_NAME}")

# NATS client for service coordination
nats_client = NATSClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting ${SERVICE_NAME^} Service...")
    
    # Initialize database
    Base.metadata.create_all(bind=engine)
    
    # Connect to NATS
    await nats_client.connect()
    
    # Publish service ready event
    await nats_client.publish(
        "gaia.service.ready",
        {
            "service": "${SERVICE_NAME}",
            "status": "ready",
            "timestamp": "2025-01-01T00:00:00Z"
        }
    )
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down ${SERVICE_NAME^} Service...")
    await nats_client.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Gaia ${SERVICE_NAME^} Service",
    description="${SERVICE_NAME^} functionality for Gaia Platform",
    version="0.1",
    lifespan=lifespan
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "${SERVICE_NAME}",
        "status": "healthy",
        "version": "0.1",
        "database": {"status": "connected"},
        "nats": {"status": "connected" if nats_client.is_connected else "disconnected"}
    }

# TODO: Add your service-specific endpoints here
@app.get("/info")
async def get_info(auth: dict = Depends(get_current_auth_legacy)):
    """Example authenticated endpoint"""
    return {
        "service": "${SERVICE_NAME}",
        "message": "Add your ${SERVICE_NAME} functionality here",
        "user": auth.get("user_id")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# 3. Create Dockerfile
echo -e "\n${GREEN}3. Creating Dockerfile...${NC}"
cat > "Dockerfile.${SERVICE_NAME}" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Set Python path
ENV PYTHONPATH=/app

# Run the service
CMD ["uvicorn", "app.services.SERVICE_NAME.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Replace SERVICE_NAME placeholder in Dockerfile
sed -i '' "s/SERVICE_NAME/${SERVICE_NAME}/g" "Dockerfile.${SERVICE_NAME}"

# 4. Add to docker-compose.yml
echo -e "\n${GREEN}4. Adding to docker-compose.yml...${NC}"
# Check if service already exists in docker-compose
if grep -q "${SERVICE_NAME}-service:" docker-compose.yml; then
    echo -e "${YELLOW}Service already exists in docker-compose.yml, skipping...${NC}"
else
    # Add service definition before the 'volumes:' line
    cat >> docker-compose.yml.tmp << EOF

  ${SERVICE_NAME}-service:
    build:
      context: .
      dockerfile: Dockerfile.${SERVICE_NAME}
    container_name: gaia-${SERVICE_NAME}-service-1
    environment:
      - SERVICE_NAME=${SERVICE_NAME}
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/llm_platform
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
      - LOG_LEVEL=DEBUG
    env_file:
      - .env
    ports:
      - "${INTERNAL_PORT}:8000"
    depends_on:
      - db
      - redis
      - nats
    networks:
      - gaia-network
    restart: unless-stopped
EOF
    
    # Insert before volumes section
    awk '/^volumes:/ {print ""; system("cat docker-compose.yml.tmp"); print ""} {print}' docker-compose.yml > docker-compose.yml.new
    mv docker-compose.yml.new docker-compose.yml
    rm docker-compose.yml.tmp
fi

# 5. Create Fly.io deployment config
echo -e "\n${GREEN}5. Creating Fly.io deployment configs...${NC}"
for ENV in dev staging production; do
    cat > "fly.${SERVICE_NAME}.${ENV}.toml" << EOF
app = "gaia-${SERVICE_NAME}-${ENV}"
primary_region = "lax"

[build]
  dockerfile = "Dockerfile.${SERVICE_NAME}"

[env]
  SERVICE_NAME = "${SERVICE_NAME}"
  ENVIRONMENT = "${ENV}"
  PYTHONPATH = "/app"
  LOG_LEVEL = "INFO"
  
  # Service URLs (using public URLs for reliability)
  AUTH_SERVICE_URL = "https://gaia-auth-${ENV}.fly.dev"
  ASSET_SERVICE_URL = "https://gaia-asset-${ENV}.fly.dev"
  CHAT_SERVICE_URL = "https://gaia-chat-${ENV}.fly.dev"
  KB_SERVICE_URL = "https://gaia-kb-${ENV}.fly.dev"
  GATEWAY_URL = "https://gaia-gateway-${ENV}.fly.dev"
  
  # NATS Configuration
  NATS_HOST = "gaia-nats-${ENV}.fly.dev"
  NATS_PORT = "4222"

[[services]]
  protocol = "tcp"
  internal_port = 8000
  
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
  
  [[services.ports]]
    port = 80
    handlers = ["http"]
  
  [[services.http_checks]]
    interval = "10s"
    grace_period = "5s"
    method = "get"
    path = "/health"
    timeout = "2s"
EOF
done

# 6. Update .env.example
echo -e "\n${GREEN}6. Updating .env.example...${NC}"
if grep -q "${SERVICE_NAME_UPPER}_SERVICE_URL" .env.example; then
    echo -e "${YELLOW}Service URL already in .env.example, skipping...${NC}"
else
    echo "" >> .env.example
    echo "# ${SERVICE_NAME^} Service" >> .env.example
    echo "${SERVICE_NAME_UPPER}_SERVICE_URL=http://localhost:${SERVICE_PORT}" >> .env.example
fi

# 7. Update shared config.py
echo -e "\n${GREEN}7. Updating shared config.py...${NC}"
# Add the service URL to config.py if not already present
if grep -q "${SERVICE_NAME_UPPER}_SERVICE_URL" app/shared/config.py; then
    echo -e "${YELLOW}Service URL already in config.py, skipping...${NC}"
else
    # Find the line with KB_SERVICE_URL and add after it
    sed -i '' "/KB_SERVICE_URL: str/a\\
    ${SERVICE_NAME_UPPER}_SERVICE_URL: str = os.getenv(\"${SERVICE_NAME_UPPER}_SERVICE_URL\", \"http://localhost:${SERVICE_PORT}\")
" app/shared/config.py
fi

# 8. Create a service registry update script
echo -e "\n${GREEN}8. Creating gateway route generator...${NC}"
cat > "scripts/update-gateway-routes.py" << 'EOF'
#!/usr/bin/env python3
"""
Update gateway routes based on service registry
"""
import os
import re

# Service registry - add new services here
SERVICES = {
    "auth": {"port": 8001, "has_api_v1": True, "has_api_v0_2": False},
    "asset": {"port": 8002, "has_api_v1": True, "has_api_v0_2": False},
    "chat": {"port": 8003, "has_api_v1": True, "has_api_v0_2": True},
    "kb": {"port": 8004, "has_api_v1": False, "has_api_v0_2": True},
    # Add new services here
}

def generate_service_urls():
    """Generate SERVICE_URLS dictionary"""
    lines = ["SERVICE_URLS = {"]
    for service, config in SERVICES.items():
        lines.append(f'    "{service}": settings.{service.upper()}_SERVICE_URL,')
    lines.append("}")
    return "\n".join(lines)

def generate_v0_2_routes(service):
    """Generate v0.2 API route forwards"""
    service_upper = service.upper()
    return f'''
# v0.2 {service_upper} endpoints
@app.get("/api/v0.2/{service}/health", tags=["v0.2 {service_upper}"])
async def v0_2_{service}_health(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get {service} service health"""
    return await forward_request_to_service(
        service_name="{service}",
        path="/health",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )
'''

def generate_v1_routes(service):
    """Generate v1 API route forwards"""
    service_upper = service.upper()
    return f'''
# v1 {service_upper} endpoints
@app.get("/api/v1/{service}/health", tags=["v1 {service_upper}"])
async def v1_{service}_health(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Get {service} service health"""
    return await forward_request_to_service(
        service_name="{service}",
        path="/health",
        method="GET",
        headers=dict(request.headers),
        params=dict(request.query_params)
    )
'''

if __name__ == "__main__":
    print("Service Registry:")
    print(generate_service_urls())
    print("\nAdd these routes to gateway/main.py as needed:")
    
    for service, config in SERVICES.items():
        if config.get("has_api_v0_2"):
            print(generate_v0_2_routes(service))
        if config.get("has_api_v1"):
            print(generate_v1_routes(service))
EOF

chmod +x scripts/update-gateway-routes.py

# 9. Final instructions
echo -e "\n${GREEN}✅ Service '${SERVICE_NAME}' created successfully!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Update gateway/main.py:"
echo "   - Add '${SERVICE_NAME}' to SERVICE_URLS dictionary"
echo "   - Add route forwarding endpoints as needed"
echo "   - Run: ./scripts/update-gateway-routes.py for examples"
echo ""
echo "2. Test locally:"
echo "   docker compose build ${SERVICE_NAME}-service"
echo "   docker compose up ${SERVICE_NAME}-service"
echo ""
echo "3. Deploy to Fly.io:"
echo "   fly apps create gaia-${SERVICE_NAME}-dev"
echo "   fly deploy --config fly.${SERVICE_NAME}.dev.toml"
echo ""
echo "4. Set secrets on Fly.io:"
echo "   fly secrets set DATABASE_URL=\"...\" -a gaia-${SERVICE_NAME}-dev"
echo "   fly secrets set API_KEY=\"...\" -a gaia-${SERVICE_NAME}-dev"
echo ""
echo "5. Update gateway service with new ${SERVICE_NAME_UPPER}_SERVICE_URL:"
echo "   fly secrets set ${SERVICE_NAME_UPPER}_SERVICE_URL=\"https://gaia-${SERVICE_NAME}-dev.fly.dev\" -a gaia-gateway-dev"