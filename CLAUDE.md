# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker Compose Operations
```bash
# Start all services
docker-compose up

# Start specific services
docker-compose up gateway auth-service
docker-compose up db nats  # Infrastructure only

# Rebuild services
docker-compose build
docker-compose build --no-cache  # Force rebuild

# View logs
docker-compose logs -f gateway
docker-compose logs -f auth-service
```

### Testing
```bash
# Run full test suite
docker-compose run test

# Run specific test files
docker-compose run test pytest tests/test_auth.py
docker-compose run test pytest tests/test_integration.py

# Run with specific markers
docker-compose run test pytest -m integration
docker-compose run test pytest -m compatibility
```

### Development Workflow
```bash
# Initial setup
./scripts/setup.sh

# Health check
curl http://localhost:8666/health

# Manual service health checks
curl http://auth-service:8000/health
curl http://asset-service:8000/health
curl http://chat-service:8000/health
```

## Architecture Overview

### Microservices Structure
- **Gateway Service** (port 8666): Main entry point maintaining LLM Platform API compatibility
- **Auth Service**: JWT validation via Supabase, API key authentication
- **Asset Service**: Universal Asset Server functionality (planned)
- **Chat Service**: LLM interactions with MCP-agent workflows (planned)

### Key Design Patterns
- **Backward Compatibility**: All API endpoints match LLM Platform exactly
- **Dual Authentication**: JWT tokens (users) + API keys (services)
- **NATS Messaging**: Service coordination via subjects like `gaia.service.health`, `gaia.auth.*`
- **Shared Utilities**: Common functionality in `app/shared/`

### Service Communication
- **HTTP**: Direct service-to-service calls via configured URLs
- **NATS**: Event-driven coordination for health, auth events, processing updates
- **Database**: Shared PostgreSQL with LLM Platform-compatible schema

## Configuration

### Environment Setup
1. Copy `.env.example` to `.env`
2. Configure required fields:
   - `API_KEY`: Primary authentication key
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`: Supabase auth
   - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: LLM providers
   - Asset generation APIs: `STABILITY_API_KEY`, `MESHY_API_KEY`, etc.

### Service URLs (Inter-service Communication)
- Gateway: `http://gateway:8000` (external: `localhost:8666`)
- Auth: `http://auth-service:8000`
- Asset: `http://asset-service:8000`
- Chat: `http://chat-service:8000`
- Redis: `redis://redis:6379` (caching layer)

## Shared Modules

### Core Utilities (`app/shared/`)
- **`config.py`**: Centralized Pydantic settings with environment variable management
- **`security.py`**: Authentication patterns, JWT validation, `AuthenticationResult` class
- **`database.py`**: SQLAlchemy setup with connection pooling
- **`logging.py`**: Color-coded structured logging with custom levels (NETWORK, SERVICE, NATS)
- **`nats_client.py`**: Async messaging client with reconnection handling
- **`redis_client.py`**: Redis caching client with connection pooling and fallback handling
- **`supabase.py`**: Supabase client integration

### Authentication Patterns
- Use `get_current_auth_legacy()` for LLM Platform compatibility
- Inter-service calls use `validate_auth_for_service()`
- Auth service provides `/internal/validate` for service coordination

## Development Guidelines

### Adding New Services
1. Create service directory in `app/services/`
2. Implement FastAPI app with `/health` endpoint
3. Add Dockerfile and docker-compose service
4. Configure service URL in `.env.example` and `config.py`
5. Add NATS message patterns if needed

### Testing Requirements
- Unit tests: `pytest -m unit`
- Integration tests: `pytest -m integration` 
- Compatibility tests: `pytest -m compatibility` (verify LLM Platform API compatibility)
- Performance tests: Redis caching validation and timing comparisons
- Use test markers defined in `pytest.ini`

### Performance Optimization (In Progress)

**Current Task**: Implementing quick-win optimizations from `/docs/optimization-guide.md`

**Completed**:
- ✅ Redis caching system (97% performance improvement locally)
- ✅ Local database indexing (composite index for `personas(is_active, created_at DESC)`)

**In Progress** (Priority order):
1. **Response compression middleware** - Add GZipMiddleware to all services (30-50% response size reduction)
2. **Database connection pooling** - Increase pool sizes for better concurrency
3. **Cache TTL optimization** - Extend TTLs for stable data (reduce DB load by 50-70%)

**Next Steps**:
- Apply database indexes to production database when connectivity available
- Container multi-stage builds for smaller images
- API pagination for large responses

**Expected Impact**: 40-60% overall performance improvement with ~1.5 hours total effort

**Notes**: 
- All optimizations maintain backward compatibility
- Changes are incremental and low-risk
- Performance gains validated locally, ready for production

### Client Compatibility
- Maintain identical API endpoints to LLM Platform
- All existing clients (Unity XR, Unity Mobile AR, Unreal Engine, NextJS) must work unchanged
- Gateway service handles routing and maintains response formats

## NATS Messaging Subjects

### Service Coordination
- `gaia.service.health`: Service health status updates
- `gaia.service.ready`: Service startup coordination

### Domain Events
- `gaia.auth.*`: Authentication events (login, logout, validation)
- `gaia.asset.generation.*`: Asset processing lifecycle events
- `gaia.chat.*`: Chat processing events

### Event Models
- `ServiceHealthEvent`: Service status with metadata
- `AssetGenerationEvent`: Asset processing lifecycle
- `ChatMessageEvent`: Chat processing coordination

## Troubleshooting

### Common Issues
```bash
# Services won't start
docker info  # Check Docker status
docker-compose build --no-cache

# Database connection issues
docker-compose logs db
docker-compose down -v && docker-compose up db

# NATS connection problems
docker-compose logs nats
docker-compose exec nats nats-server --help
```

### Performance Monitoring
```bash
# Resource usage
docker stats

# Service health
curl localhost:8666/health

# NATS monitoring
curl localhost:8222/varz  # NATS HTTP monitoring
```