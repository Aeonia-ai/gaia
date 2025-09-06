# GAIA Platform Architecture Documentation

## Overview

The GAIA Platform is a distributed microservices system providing enterprise-grade AI capabilities with a focus on scalability, reliability, and developer experience. This documentation covers the current implementation and architectural patterns.

## Core Architecture Principles

1. **Microservices First**: Independent services with clear responsibilities
2. **Cloud Agnostic**: Deployable on any cloud provider or on-premise
3. **Performance Optimized**: Redis caching, deferred initialization, hot-reloading
4. **Security by Design**: mTLS, JWT, API keys, RBAC
5. **Developer Friendly**: Extensive automation and clear patterns

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                          │
│            (Web UI, Mobile Apps, Game Engines)                  │
└─────────────────────────────────────┬───────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API Gateway (Port 8666)                         │
│     Authentication • Routing • Rate Limiting • Caching           │
└────────┬────────────┬────────────┬────────────┬────────────────┘
         │            │            │            │
         ▼            ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
    │  Auth   │  │  Chat   │  │  Asset  │  │   KB    │
    │ Service │  │ Service │  │ Service │  │ Service │
    └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │            │
         └────────────┴────────────┴────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    ┌─────────┐      ┌─────────┐        ┌─────────┐
    │  Redis  │      │PostgreSQL│       │Supabase │
    │  Cache  │      │    DB    │       │  Auth   │
    └─────────┘      └─────────┘        └─────────┘
```

## Service Ports & URLs

### Local Development Ports
| Service | External Port | Docker Internal | Purpose |
|---------|---------------|-----------------|----------|
| Gateway | 8666 | gateway:8000 | Main API entry point |
| Auth | N/A | auth-service:8000 | Authentication service |
| Chat | N/A | chat-service:8000 | LLM orchestration |
| Asset | N/A | asset-service:8000 | Asset generation |
| KB | N/A | kb-service:8000 | Knowledge base |
| Web UI | 8080 | web-service:8000 | FastHTML interface |
| Database | 5432 | db:5432 | PostgreSQL |
| Redis | 6379 | redis:6379 | Cache & sessions |

**Note**: Only Gateway (8666) and Web UI (8080) are externally accessible. All inter-service communication uses Docker internal networking on port 8000.

## Service Documentation

### Core Services

- **[Gateway Service](microservice-quick-reference.md#gateway)** - API routing and authentication
- **[Auth Service](microservice-quick-reference.md#auth-service)** - Authentication and authorization
- **[Chat Service](microservice-quick-reference.md#chat-service)** - LLM orchestration
- **[Asset Service](microservice-quick-reference.md#asset-service)** - Multi-provider asset generation
- **[KB Service](microservice-quick-reference.md#kb-service)** - Knowledge base with Git sync
- **[Web Service](../web-ui/fasthtml-web-service.md)** - FastHTML web interface

### Architectural Patterns

- **[Service Discovery](service-discovery-pattern.md)** - Smart URL generation
- **[Deferred Initialization](deferred-initialization-pattern.md)** - Fast startup pattern
- **[Service Creation](service-creation-automation.md)** - Automated service scaffolding
- **[Database Architecture](database-architecture.md)** - PostgreSQL + Redis hybrid
- **[Microservices Communication](microservices-communication-solution.md)** - Inter-service patterns

### Scaling & Performance

- **[Scaling Architecture](scaling-architecture.md)** - Horizontal scaling strategies
- **[Microservices Scaling](microservices-scaling.md)** - Service-specific scaling
- **[PostgreSQL Simplicity](postgresql-simplicity-lessons.md)** - Avoiding overengineering

### Implementation Guides

- **[Adding New Microservice](adding-new-microservice.md)** - Step-by-step guide
- **[Chat Request Flow](chat-request-response-flow.md)** - Request lifecycle
- **[Tool Routing](tool-routing-improvement-spec.md)** - Intelligent routing

## Key Architectural Decisions

### 1. Microservices with Clear Boundaries
Each service has a specific responsibility and can be developed, deployed, and scaled independently.

### 2. Smart Service Discovery
Services automatically discover each other based on environment:
```python
# Local: localhost:port
# Fly.io: service-name-env.fly.dev
# AWS: service-name-env.region.elb.amazonaws.com
```

### 3. Hybrid Database Strategy
- **PostgreSQL**: Relational data, transactions, complex queries
- **Redis**: Caching, session storage, real-time features
- **Supabase**: Primary authentication backend

### 4. Deferred Initialization
Services start quickly and initialize expensive resources (like Git repos) in the background.

### 5. Hot Reloading in Development
All services support `--reload` for instant code updates without container restarts.

## Technology Stack

### Core Technologies
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **UI Framework**: FastHTML + HTMX
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Auth**: Supabase (primary) or PostgreSQL (fallback)

### Infrastructure
- **Container**: Docker
- **Orchestration**: Docker Compose (local), Fly.io (cloud)
- **Monitoring**: OpenTelemetry ready
- **CI/CD**: GitHub Actions

### AI/ML Stack
- **LLM Providers**: OpenAI, Anthropic (Claude)
- **Asset Generation**: Midjourney, DALL-E, Mubert
- **Embeddings**: OpenAI text-embedding-3-small
- **Agent Framework**: MCP (Model Context Protocol)

## Communication Patterns

### Synchronous Communication
- REST APIs between services
- mTLS for service-to-service security
- JWT tokens for user authentication

### Asynchronous Communication
- Redis pub/sub for real-time updates
- Background tasks with FastAPI
- Event-driven patterns for scalability

### Caching Strategy
- Redis for hot data (97% performance improvement)
- Service-level caching for expensive operations
- Cache invalidation via pub/sub

## Security Architecture

### Authentication Layers
1. **API Keys**: Legacy support, database validated
2. **JWT Tokens**: Supabase or self-signed
3. **mTLS**: Service-to-service authentication
4. **RBAC**: Role-based access control

### Security Patterns
- All services validate authentication independently
- No service trusts another service blindly
- Secrets managed via environment variables
- TLS everywhere in production

## Deployment Architecture

### Local Development
```bash
docker compose up  # All services with hot-reload
```

### Production Deployment
- **Fly.io**: Primary cloud provider
- **AWS/GCP**: Supported via service discovery
- **On-premise**: Docker Compose or Kubernetes

### Service URLs
Services are accessible at:
- **Local**: `http://localhost:PORT`
- **Docker**: `http://service-name:PORT`
- **Fly.io**: `https://gaia-service-env.fly.dev`

## Performance Characteristics

### Response Times
- **Chat (simple)**: <1s with caching
- **Chat (complex)**: 2-3s with agent orchestration
- **Asset generation**: 10-30s depending on provider
- **KB search**: <200ms with indexing

### Scalability
- **Horizontal**: All services stateless, scale horizontally
- **Vertical**: Database can scale to 32+ cores
- **Caching**: Redis handles 100k+ ops/second

## Future Architecture

### Planned Enhancements
- GraphQL API gateway option
- WebSocket support for real-time
- Kubernetes deployment manifests
- Multi-region deployment

### Research Areas
- **[KOS Interface](../../research/kos-interface-exploration.md)** - Unified intelligence paradigm
- **[Multiagent Orchestration](../../future/research/multiagent-orchestration.md)** - Advanced agent patterns
- **[MCP Integration](../../future/research/mcp-integration-strategy.md)** - Enhanced tool capabilities

## Quick Links

### For Developers
- [Adding New Microservice](adding-new-microservice.md)
- [Service Creation Automation](service-creation-automation.md)
- [Development Setup](../development/dev-environment-setup.md)

### For DevOps
- [Deployment Best Practices](../deployment/deployment-best-practices.md)
- [Scaling Guide](scaling-architecture.md)
- [Monitoring Setup](../deployment/production-deployment.md)

### For Architects
- [Database Architecture](database-architecture.md)
- [Service Discovery](service-discovery-pattern.md)
- [Security Architecture](../authentication/authentication-guide.md)

---

For the complete historical architecture documentation, see [Archive: Architecture Overview](../../archive/architecture-overview.md)