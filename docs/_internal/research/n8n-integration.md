# n8n Integration Guide

This document outlines how to integrate n8n workflow automation into the Gaia microservices cluster.

## Overview

n8n will be deployed as an additional containerized service in our existing Docker Compose setup, providing workflow automation capabilities that can orchestrate operations across our microservices (Gateway, Auth, Asset, Chat).

## Architecture Integration

### Service Addition
- **n8n Service**: Workflow automation platform with web UI
- **NATS Bridge Service**: Lightweight service to connect n8n with our existing NATS messaging system
- **Port**: 5678 (web interface)
- **Database**: Shared PostgreSQL instance for workflow persistence

### Communication Patterns
1. **HTTP/REST**: Direct API calls between n8n and services
2. **NATS Bridge**: Custom service translating NATS messages to n8n webhooks
3. **Webhooks**: Services trigger n8n workflows via HTTP webhooks

## Docker Compose Configuration

Add these services to `docker compose.yml`:

```yaml
services:
  # Existing services...
  
  n8n:
    image: n8nio/n8n:latest
    container_name: gaia-n8n
    ports:
      - '5678:5678'
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=db
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - WEBHOOK_URL=http://localhost:5678/
    depends_on:
      - db
      - nats
    networks:
      - gaia-network

  nats-n8n-bridge:
    build:
      context: .
      dockerfile: Dockerfile.nats-bridge
    container_name: gaia-nats-n8n-bridge
    environment:
      - NATS_URL=nats://nats:4222
      - N8N_WEBHOOK_BASE_URL=http://n8n:5678/webhook
      - API_KEY=${API_KEY}
    depends_on:
      - nats
      - n8n
    networks:
      - gaia-network

volumes:
  n8n_data:
```

## Environment Variables

Add to `.env`:

```bash
# n8n Configuration
N8N_USER=admin
N8N_PASSWORD=your_secure_password
N8N_ENCRYPTION_KEY=your_32_character_encryption_key

# NATS Bridge Configuration
N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
```

## NATS Bridge Service

Create a lightweight service to translate NATS messages to n8n webhooks:

### Purpose
- Subscribe to existing NATS subjects (`gaia.service.*`, `gaia.auth.*`, `gaia.asset.*`, `gaia.chat.*`)
- Transform NATS messages into HTTP webhook calls to n8n
- Handle authentication and message routing

### Implementation Location
- `app/services/nats-bridge/` - New service directory
- `Dockerfile.nats-bridge` - Container configuration
- Subscribe to relevant NATS subjects and forward to n8n webhooks

## Authentication Integration

### Service-to-Service Communication
- n8n workflows use API keys when calling Gaia services
- Configure n8n credentials vault with:
  - Primary API key for service authentication
  - Service URLs (internal Docker network addresses)

### n8n Security
- Basic authentication enabled for web interface
- Webhook endpoints secured with tokens
- Encryption key for sensitive workflow data

## Common Workflow Patterns

### 1. Asset Processing Pipeline
```
Asset Upload → NATS: gaia.asset.generation.started 
→ NATS Bridge → n8n Webhook 
→ n8n Workflow (progress tracking, notifications)
→ Chat Service API (notify users)
```

### 2. Authentication Events
```
User Login → Auth Service → NATS: gaia.auth.login
→ NATS Bridge → n8n Webhook
→ n8n Workflow (logging, analytics, welcome messages)
```

### 3. Service Health Monitoring
```
Service Health Check → NATS: gaia.service.health
→ NATS Bridge → n8n Webhook
→ n8n Workflow (alerting, dashboard updates)
```

## Workflow Development

### Accessing n8n Interface
- URL: `http://localhost:5678`
- Login with configured basic auth credentials

### Creating Workflows
1. Use Webhook Trigger nodes for NATS-originated events
2. Use HTTP Request nodes to call Gaia service APIs
3. Store API keys and URLs in n8n credentials
4. Test workflows using the n8n interface

### Example Workflow: Asset Generation Notification
1. **Webhook Trigger**: Listen for asset generation events
2. **HTTP Request**: Call Chat Service to send notification
3. **Conditional Logic**: Handle success/failure scenarios
4. **HTTP Request**: Update Asset Service with completion status

## Service URLs for n8n Workflows

Configure these internal service URLs in n8n:
- Gateway: `http://gateway:8000`
- Auth Service: `http://auth-service:8000`
- Asset Service: `http://asset-service:8000`
- Chat Service: `http://chat-service:8000`

## Monitoring and Maintenance

### Health Checks
- n8n health endpoint: `http://localhost:5678/health`
- Monitor workflow execution logs via n8n interface
- NATS Bridge service logs for message routing

### Backup and Recovery
- n8n data persisted in Docker volume `n8n_data`
- Workflow definitions stored in PostgreSQL
- Export workflows as JSON for version control

### Scaling Considerations
- Single n8n instance sufficient for initial deployment
- Can scale horizontally with multiple n8n containers if needed
- NATS Bridge service is stateless and can be scaled

## Development Workflow

1. **Setup**: Add n8n services to docker compose.yml
2. **Bridge Development**: Implement NATS-to-webhook bridge service
3. **Configuration**: Set environment variables and credentials
4. **Testing**: Create test workflows for existing service events
5. **Documentation**: Document workflow patterns for team use

## Security Best Practices

- Use strong passwords for n8n basic auth
- Rotate API keys regularly
- Limit n8n webhook exposure (internal network only)
- Monitor workflow execution logs for suspicious activity
- Use n8n credentials vault for sensitive data storage