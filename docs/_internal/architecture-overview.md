# Gaia Platform Architecture Overview

**Last Updated**: January 2025  
**Version**: 2.0

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Service Architecture](#service-architecture)
4. [Data Architecture](#data-architecture)
5. [Security Architecture](#security-architecture)
6. [Communication Patterns](#communication-patterns)
7. [Deployment Architecture](#deployment-architecture)
8. [Technology Stack](#technology-stack)
9. [Architectural Decisions](#architectural-decisions)
10. [Future Architecture](#future-architecture)

## Executive Summary

Gaia Platform is a distributed microservices system that evolved from the monolithic "LLM Platform" to provide enterprise-grade AI capabilities with enhanced scalability, reliability, and maintainability. The platform maintains 100% backward compatibility while introducing modern cloud-native patterns.

### Key Characteristics
- **Microservices Architecture**: 6 independent services (4 discoverable via SERVICE_REGISTRY + Gateway + Web)
- **Cloud-Agnostic**: Deployable on Fly.io, AWS, GCP, or on-premise
- **High Performance**: 97% improvement in auth performance via Redis caching
- **Multi-Provider**: Supports OpenAI, Anthropic, and multiple asset generation providers
- **Enterprise Security**: mTLS, JWT, API keys, and RBAC support
- **Developer Friendly**: Extensive automation and documentation

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Applications                      │
│     (Unity XR, Unity Mobile AR, Unreal Engine, NextJS, etc.)   │
└─────────────────────────────────────┬───────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (Port 8666)                       │
│  • Authentication  • Rate Limiting  • Routing  • Load Balancing  │
└────────┬────────────┬────────────┬────────────┬────────────────┘
         │            │            │            │
         ▼            ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
    │  Auth   │  │  Asset  │  │  Chat   │  │   KB    │
    │ Service │  │ Service │  │ Service │  │ Service │
    └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │            │
         └────────────┴────────────┴────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    ┌─────────┐      ┌─────────┐        ┌─────────┐
    │  Redis  │      │PostgreSQL│       │  NATS   │
    │  Cache  │      │ Database │       │Message  │
    └─────────┘      └─────────┘        │  Bus    │
                                        └─────────┘
```

### Service Responsibilities

| Service | Port | Responsibility | Registry |
|---------|------|----------------|----------|
| Gateway | 8666 | API routing, authentication, rate limiting | No (external entry point) |
| Auth | 8001 | JWT/API key validation, user management | ✓ SERVICE_REGISTRY |
| Asset | 8002 | Multi-provider asset generation and storage | ✓ SERVICE_REGISTRY |
| Chat | 8003 | LLM orchestration and conversation management | ✓ SERVICE_REGISTRY |
| KB | 8004 | Knowledge base with Git sync and search | ✓ SERVICE_REGISTRY |
| Web | 8080 | FastHTML web interface | No (external web UI) |

**Note**: Only the 4 backend services (Auth, Asset, Chat, KB) are registered in `SERVICE_REGISTRY` for smart service discovery. Gateway and Web services are external-facing and use static port/URL configuration.

## Service Architecture

### Gateway Service

The gateway serves as the single entry point for all external requests:

```python
# Core responsibilities
- Request routing to backend services
- Authentication validation
- Rate limiting and throttling
- CORS handling
- Response aggregation
- Health monitoring
```

**Key Features**:
- Maintains LLM Platform API compatibility
- Smart service discovery
- Graceful degradation when services unavailable
- Request/response logging and metrics

### Auth Service

Handles all authentication and authorization:

```python
# Authentication methods
1. API Keys (legacy support)
   - User-associated keys
   - SHA-256 hashed storage
   - Redis caching

2. Supabase JWTs (recommended)
   - Email/password authentication
   - Social login support
   - Automatic token refresh

3. mTLS + Service JWTs (internal)
   - Certificate-based auth
   - Short-lived tokens
   - Service-to-service security
```

### Asset Service

Universal asset generation across multiple providers:

```python
# Supported providers
- OpenAI (DALL-E)
- Stability AI
- Midjourney
- Meshy (3D models)
- Mubert (music)
- Freesound (audio)

# Features
- Cost optimization
- Preview generation
- Caching strategies
- Multi-format support
```

### Chat Service

LLM orchestration with advanced features:

```python
# Core capabilities
- Multi-provider support (OpenAI, Anthropic)
- Streaming responses (SSE)
- MCP-agent integration
- Conversation persistence
- Persona management

# Advanced scenarios
- Gamemaster mode
- Worldbuilding collaborations
- Problem-solving teams
- Storytelling orchestration
```

### KB Service

Knowledge Base with flexible storage:

```python
# Storage modes
1. Git-based: Version controlled files
2. Database: PostgreSQL for search performance
3. Hybrid: Best of both worlds

# Features
- Automatic Git synchronization
- Full-text search (ripgrep)
- Context loading (KOS)
- RBAC for multi-user access
- Deferred initialization
```

### Web Service

Modern web interface using FastHTML:

```python
# Technology choices
- FastHTML: Python-based UI
- HTMX: Dynamic updates
- Tailwind CSS: Styling
- Alpine.js: Interactivity

# Features
- Real-time chat interface
- Responsive design
- Session management
- WebSocket support
```

## Data Architecture

### Storage Layers

```
┌─────────────────────────────────────────────────────┐
│                   Application Layer                  │
├─────────────────────────────────────────────────────┤
│                    Redis Cache                       │
│  • API key validation (10min TTL)                   │
│  • JWT validation (15min TTL)                       │
│  • Session data                                     │
│  • Response caching                                 │
├─────────────────────────────────────────────────────┤
│                PostgreSQL Database                   │
│  • User profiles      • Conversations               │
│  • API keys          • Asset metadata               │
│  • Messages          • Provider configs             │
│  • RBAC permissions  • Audit logs                   │
├─────────────────────────────────────────────────────┤
│                 Supabase (Auth Only)                │
│  • User authentication                              │
│  • JWT management                                   │
│  • Email verification                               │
├─────────────────────────────────────────────────────┤
│              File/Object Storage                     │
│  • Generated assets (S3/GCS)                        │
│  • KB Git repositories                              │
│  • Service certificates                             │
└─────────────────────────────────────────────────────┘
```

### Data Flow Patterns

**Authentication Flow**:
```
Client Request → Gateway → Redis Cache (hit/miss)
                              ↓ (miss)
                          PostgreSQL/Supabase
                              ↓
                          Update Cache → Response
```

**Chat Completion Flow**:
```
Client → Gateway → Chat Service → LLM Provider
                       ↓
                  Save to DB → Stream Response
```

**Asset Generation Flow**:
```
Client → Gateway → Asset Service → Provider API
                       ↓
                  Store Asset → Save Metadata → Response
```

## Security Architecture

### Multi-Layer Security Model

```
┌─────────────────────────────────────────────────────┐
│              External Security Layer                 │
│  • TLS 1.3       • Rate Limiting                   │
│  • CORS          • DDoS Protection                 │
├─────────────────────────────────────────────────────┤
│            Authentication Layer                      │
│  • API Keys      • JWT Tokens                      │
│  • mTLS Certs    • Service Tokens                  │
├─────────────────────────────────────────────────────┤
│            Authorization Layer                       │
│  • RBAC          • Resource Permissions            │
│  • Scopes        • Team/Workspace Access           │
├─────────────────────────────────────────────────────┤
│              Data Security Layer                     │
│  • Encryption at Rest  • Encrypted Connections     │
│  • Secret Management   • Audit Logging             │
└─────────────────────────────────────────────────────┘
```

### Authentication Methods

1. **API Keys** (Backward Compatibility)
   - SHA-256 hashed storage
   - User-associated with permissions
   - Redis cached for performance

2. **Supabase JWTs** (Recommended)
   - Industry-standard JWT tokens
   - Automatic refresh mechanism
   - Social login support

3. **mTLS + Service JWTs** (Internal)
   - Certificate Authority infrastructure
   - Mutual TLS for service communication
   - Short-lived tokens (5 minutes)

### RBAC Implementation

```sql
-- Role hierarchy
roles
├── admin (full platform access)
├── developer (API access + KB)
├── user (standard access)
└── guest (read-only)

-- Resource permissions
resource_permissions
├── kb:read
├── kb:write
├── chat:create
├── asset:generate
└── admin:all
```

## Communication Patterns

### Synchronous Communication

**HTTP/REST API**:
- Primary communication method
- JSON request/response format
- Standard HTTP status codes
- Request forwarding with auth context

**Service Discovery**:
```python
# Smart URL generation
def get_service_url(service_name: str) -> str:
    # Format: gaia-{service}-{environment}.{provider}.{tld}
    # Example: gaia-auth-dev.fly.dev
    return generate_url(service_name, environment, provider)
```

### Asynchronous Communication

**NATS Message Bus**:
```
Subjects:
├── gaia.service.health     # Health status updates
├── gaia.service.ready      # Startup coordination
├── gaia.auth.*            # Auth events (login, logout)
├── gaia.asset.generation.* # Asset lifecycle
├── gaia.chat.*            # Chat events
└── world.updates.user.*   # AR/VR real-time world state (Phase 1B)
    └── world.updates.user.{user_id} # User-specific game state updates
```

**Event-Driven Patterns**:
- Service health monitoring
- Asset generation lifecycle
- Authentication events
- Chat message processing
- **Real-time AR/VR world state synchronization** (Phase 1B)
  - Per-request NATS subscriptions during SSE streaming
  - User-specific world update channels
  - Automatic cleanup on stream close
  - Graceful degradation if NATS unavailable

**NATS Integration Phases**:
- **Phase 1B** (✅ Complete): Per-request subscriptions during SSE streams
- **Phase 2** (Planned): Persistent WebSocket connections with NATS
- **Phase 3** (Future): JetStream for event replay and offline sync

## Deployment Architecture

### Multi-Cloud Strategy

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Fly.io      │  │       AWS       │  │       GCP       │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Quick deploy  │  │ • Auto-scaling  │  │ • Cloud Run     │
│ • Edge network  │  │ • ECS/Fargate   │  │ • GKE           │
│ • Simple config │  │ • ALB/NLB       │  │ • Cloud SQL     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                    Smart Service Discovery
                              │
                    ┌─────────────────┐
                    │ Unified Platform │
                    └─────────────────┘
```

### Environment Strategy

| Environment | Purpose | Database | Features |
|-------------|---------|----------|----------|
| Local | Development | Local PostgreSQL | Hot reload, debugging |
| Dev | Integration testing | Fly PostgreSQL | Feature branches |
| Staging | Pre-production | Fly PostgreSQL | Production-like |
| Production | Live system | Managed PostgreSQL | HA, backups |

### Scaling Patterns

**Horizontal Scaling**:
- Gateway: 2-10 instances based on traffic
- Chat: Scale based on concurrent sessions
- Asset: Scale based on generation queue
- KB: Read replicas for search

**Vertical Scaling**:
- Database: Increase resources as needed
- Redis: Memory based on cache size
- Services: CPU/memory per workload

## Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|------------|---------|
| Language | Python 3.11+ | Type hints, async/await |
| Web Framework | FastAPI | REST APIs, OpenAPI docs |
| UI Framework | FastHTML | Python-based UI |
| Database | PostgreSQL 15 | Primary data store |
| Cache | Redis 7 | Performance optimization |
| Message Bus | NATS | Service coordination |
| Container | Docker | Consistent deployments |

### Key Libraries

**Backend**:
- `pydantic`: Data validation
- `sqlalchemy`: ORM
- `asyncpg`: Async PostgreSQL
- `httpx`: Async HTTP client
- `python-jose`: JWT handling

**AI/ML**:
- `openai`: OpenAI integration
- `anthropic`: Claude integration
- Provider SDKs for assets

**Infrastructure**:
- `uvicorn`: ASGI server
- `pytest`: Testing framework
- `alembic`: Database migrations

## Architectural Decisions

### 1. Microservices vs Monolith

**Decision**: Migrate from monolith to microservices

**Rationale**:
- Independent scaling per service
- Technology flexibility
- Fault isolation
- Team autonomy
- Easier debugging

**Trade-offs**:
- Increased complexity
- Network latency
- Distributed transactions
- Operational overhead

### 2. Backward Compatibility

**Decision**: Maintain 100% API compatibility

**Rationale**:
- Zero client code changes
- Smooth migration path
- No breaking changes
- Client trust

**Implementation**:
- Same endpoints in gateway
- Response format preservation
- Legacy auth support

### 3. Authentication Strategy

**Decision**: Dual auth system (API keys + JWTs)

**Rationale**:
- Legacy support required
- Modern JWT benefits
- Gradual migration path
- Multiple use cases

**Future**: Phase out API keys

### 4. Caching Strategy

**Decision**: Redis for all caching needs

**Rationale**:
- 97% performance improvement
- Reduced database load
- Standard solution
- Easy to scale

**Cache Layers**:
- Auth validation (10min)
- Response caching (varies)
- Session data (30min)

### 5. Service Communication

**Decision**: HTTP/REST with NATS events

**Rationale**:
- Simple and standard
- Good tooling
- Easy debugging
- Async where needed

**Alternative Considered**: gRPC
- More complex
- Less standard tooling
- Overkill for current needs

## Future Architecture

### Phase 1: Service Mesh (Q2 2025)
- Istio/Linkerd evaluation
- Automatic mTLS
- Circuit breakers
- Distributed tracing

### Phase 2: Event Sourcing (Q3 2025)
- Event store implementation
- CQRS for read models
- Audit trail improvements
- Time-travel debugging

### Phase 3: Edge Computing (Q4 2025)
- CDN integration
- Edge functions
- Regional deployments
- Latency optimization

### Phase 4: AI-Native Features (2026)
- Vector databases
- Semantic search
- AI observability
- Model versioning

## Conclusion

The Gaia Platform architecture represents a modern, scalable approach to building AI-powered applications. By maintaining backward compatibility while introducing cloud-native patterns, the platform provides a solid foundation for future growth while serving current needs effectively.

Key strengths:
- **Flexibility**: Multi-cloud, multi-provider support
- **Performance**: Caching and optimization throughout
- **Security**: Multiple authentication layers
- **Developer Experience**: Extensive tooling and documentation
- **Future-Proof**: Clear evolution path

The architecture balances pragmatic decisions with forward-thinking design, creating a platform that can evolve with changing requirements while maintaining stability for existing users.