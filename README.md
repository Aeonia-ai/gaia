# Gaia Platform

**Microservices Backend for Aeonia - Phase 1 Foundation**

Gaia Platform is a microservices-based backend that replaces the LLM Platform monolith while maintaining full client compatibility. This implementation follows a **foundation-first** approach, extracting proven components and building incrementally.

## 🎯 Phase 1 Goals - COMPLETE ✅

- **✅ Maintain Client Compatibility**: Unity XR, Unity Mobile AR, Unreal Engine, and NextJS clients work unchanged
- **✅ Extract Core Services**: Auth, Asset, and Chat services from LLM Platform 
- **✅ Add Service Coordination**: NATS messaging for inter-service communication
- **✅ Preserve All Features**: Every LLM Platform feature preserved with equal or better performance
- **✅ User-Associated Authentication**: Database-driven API keys with SHA256 hashing
- **✅ Portable Database Architecture**: Consistent schema across all environments
- **✅ Production-Ready Dev Environment**: Deployed and tested on Fly.io

## 🏗️ Architecture

```
External Clients → FastAPI Gateway → 3 Core Services
Unity/Unreal/Web → (Port 8666)    → ├─ Auth Service (Supabase JWT + API keys)
                                    ├─ Asset Service (Universal Asset Server)
                                    └─ Chat Service (MCP-agent workflows)
```

### Services

- **Gateway Service**: Main entry point (port 8666), routes to appropriate services
- **Auth Service**: JWT validation, user-associated API key auth, user management via Supabase  
- **Asset Service**: Universal Asset Server functionality from LLM Platform
- **Chat Service**: LLM interactions with MCP-agent workflows
- **KB Service**: Knowledge Base with Git sync, multi-user support (teams/workspaces)
- **Web Service**: FastHTML frontend for chat interface (port 8080)
- **Shared Modules**: Common utilities, database, NATS, security, RBAC system

### Infrastructure

- **PostgreSQL**: Single database (preserves LLM Platform schema)
- **NATS**: Lightweight messaging for service coordination
- **Docker**: Multi-service orchestration
- **Supabase**: Authentication and database hosting

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for MCP server)
- PostgreSQL (or use Docker)

### Setup

1. **Clone and Setup**
   ```bash
   cd /Users/jasonasbahr/Development/Aeonia/Server/gaia
   ./scripts/setup.sh
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   
   # For KB Service with Git sync (optional):
   # KB_GIT_REPO_URL=https://github.com/your-org/your-kb.git
   # KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxx  # GitHub Personal Access Token
   ```

3. **Start Services**
   ```bash
   docker compose up
   ```

4. **Test with User-Associated Authentication**
   ```bash
   # API key automatically created: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE
   # User: dev@gaia.local
   curl http://localhost:8666/health
   ```

### Development Commands

```bash
# Start all services
docker-compose up

# Start specific service
docker-compose up gateway auth-service

# View logs
docker-compose logs -f gateway

# Rebuild services
docker-compose build

# Run tests
docker-compose run test

# Extract LLM Platform components
./scripts/extract-components.sh
```

## 📡 API Compatibility

Gaia maintains **identical** API endpoints to LLM Platform:

- `GET /health` - Service health check
- `POST /api/v1/chat/completions` - Chat completions
- `GET /api/v1/chat/personas` - Get personas
- `GET /api/v1/assets` - List assets
- `POST /api/v1/assets/generate` - Generate assets
- `POST /api/v1/auth/validate` - Validate authentication
- All other LLM Platform endpoints...

## 🔧 Service Details

### Gateway Service (`localhost:8666`)

- Accepts all client requests
- Routes to appropriate backend services  
- Maintains LLM Platform API compatibility
- Handles rate limiting and CORS

### Auth Service

- JWT token validation via Supabase
- API key authentication  
- User registration and login
- Inter-service auth coordination

### Asset Service

- Universal Asset Server functionality
- Asset generation and management
- External API integrations (Stability, DALL-E, etc.)
- Cost optimization and caching

### Chat Service  

- LLM interactions (OpenAI, Anthropic)
- MCP-agent workflows
- Persona management
- Filesystem operations via MCP

## 🗄️ Database

Uses the **same PostgreSQL schema** as LLM Platform for seamless migration:

- User authentication data
- Asset metadata and storage
- Chat history and personas
- System configuration

## 🔄 NATS Messaging

Services coordinate via NATS for:

- Service health monitoring
- Asset generation notifications  
- Authentication events
- Inter-service requests

**Subjects:**
- `gaia.service.health` - Service health events
- `gaia.asset.generation.*` - Asset generation events
- `gaia.auth.*` - Authentication events

## 🧪 Testing

### Health Checks

```bash
# Overall system health
curl http://localhost:8666/health

# Individual service health
curl http://auth-service:8000/health
curl http://asset-service:8000/health  
curl http://chat-service:8000/health
```

### Client Compatibility

Test that existing clients work unchanged:

```bash
# Test chat endpoint (same as LLM Platform)
curl -X POST http://localhost:8666/api/v1/chat/completions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

### Integration Tests

```bash
# Run full test suite
docker-compose run test

# Run specific test files
docker-compose run test pytest tests/test_auth.py
docker-compose run test pytest tests/test_integration.py
```

### AI Test Specifications

The repository includes comprehensive AI test specifications that achieve 100% specification coverage with 88% passing rate:

```bash
# Run all AI test specifications
docker-compose run test pytest tests/ai_specs/ -v

# Run tests for a specific service
docker-compose run test pytest tests/ai_specs/v1/llm/ -v
docker-compose run test pytest tests/ai_specs/v1/web/ -v
docker-compose run test pytest tests/ai_specs/v1/auth/ -v
docker-compose run test pytest tests/ai_specs/v1/kb/ -v

# Run only passing tests (skip TODO tests)
docker-compose run test pytest tests/ai_specs/ -v -m "not skip"

# Generate test coverage report
docker-compose run test pytest tests/ai_specs/ --cov=app --cov-report=html

# View skipped tests with reasons
docker-compose run test pytest tests/ai_specs/ -v -rs
```

Test specifications are organized by service:
- **LLM Service**: Chat operations, provider management, streaming
- **Web Service**: UI interactions, authentication flows, HTMX components  
- **Auth Service**: User management, JWT validation, API keys
- **KB Service**: Knowledge base operations, search, Git sync
- **Asset Service**: Generation, management, external integrations
- **Gateway Service**: Routing, rate limiting, authentication
- **Persona Service**: AI personality management (component, not microservice)
- **NATS Service**: Messaging, event handling, service coordination
- **Shared Utilities**: Redis caching, database operations, RBAC

See `tests/ai_specs/AI_TEST_COVERAGE.md` for detailed test coverage information.

## 📁 Project Structure

```
gaia/
├── app/
│   ├── gateway/           # Gateway service
│   │   └── main.py
│   ├── services/
│   │   ├── auth/          # Auth service
│   │   ├── asset/         # Asset service  
│   │   └── chat/          # Chat service
│   └── shared/            # Common utilities
│       ├── config.py      # Configuration
│       ├── database.py    # Database setup
│       ├── logging.py     # Logging utilities
│       ├── nats_client.py # NATS messaging
│       ├── security.py    # Authentication
│       └── supabase.py    # Supabase client
├── scripts/
│   ├── setup.sh           # Initial setup
│   └── extract-components.sh  # Extract from LLM Platform
├── docker-compose.yml     # Multi-service orchestration
├── requirements.txt       # Python dependencies
└── .env.example          # Environment template
```

## 🔐 Security

- **API Keys**: Same validation as LLM Platform
- **JWT Tokens**: Supabase authentication preserved
- **CORS**: Configurable origins
- **Rate Limiting**: Request throttling
- **Service-to-Service**: NATS coordination with auth validation

## 📊 Monitoring

### Service Health

- Health check endpoints on all services
- NATS health events
- Database connectivity monitoring
- Supabase connection status

### Logging

- Color-coded logs by service
- Structured logging for operations
- Inter-service request tracking
- Authentication event logging

### Performance

- Request/response timing
- Service coordination metrics
- Database connection pooling
- NATS message throughput

## 🔄 Migration from LLM Platform

### Data Migration

1. **Database**: Uses same schema - no migration needed
2. **Environment**: Copy and adapt .env variables
3. **Assets**: Same storage configuration
4. **Users**: Preserved authentication

### Client Updates

**None required** - all clients work unchanged with Gaia Platform.

### Deployment

Replace LLM Platform service with:

```bash
# Stop LLM Platform
docker-compose -f llm-platform/docker-compose.yml down

# Start Gaia Platform
docker-compose -f gaia/docker-compose.yml up
```

## 🛣️ Roadmap

### Phase 1: Foundation (Complete)
- ✅ Service extraction and microservices architecture
- ✅ Client compatibility preservation  
- ✅ Basic NATS coordination
- ✅ KB service with Git integration
- 🔄 RBAC system implementation (in progress)

### Phase 2: Access Control & Multi-User (Current)
- 🔄 Role-Based Access Control (RBAC) - database schema complete
- 📋 Multi-user KB with teams/workspaces
- 📋 Permission management UI
- 📋 Sharing and collaboration features

### Phase 3: Memory & Intelligence (Next)
- 📋 Basic chat memory (PostgreSQL-based)
- 📋 Memory framework research (Mem0, MiniRAG)
- 📋 Usage pattern analysis
- 📋 Evidence-based memory enhancement

### Phase 4+: Advanced Features (Future)
- 📋 Sophisticated player modeling
- 📋 Advanced cross-platform coordination
- 📋 Real-time collaboration features
- 📋 Enhanced AI agent workflows

## 🤝 Contributing

### Development Workflow

1. **Extract Components**: Use `./scripts/extract-components.sh`
2. **Adapt for Microservices**: Update imports, add NATS coordination
3. **Test Compatibility**: Ensure client behavior unchanged
4. **Performance Validation**: Meet LLM Platform baseline

### Code Standards

- **Compatibility First**: Preserve LLM Platform behavior
- **Service Independence**: Clean boundaries between services
- **Shared Utilities**: Common functionality in `app/shared/`
- **Error Handling**: Graceful degradation patterns

## 📖 Documentation

- **Implementation Guide**: `/Vaults/KB/processes/gaia-foundation-first.md`
- **System Architecture**: `/Vaults/KB/gaia/requirements/02-system-architecture.md`
- **LLM Platform Reference**: `/Vaults/KB/llm-platform/+llm-platform.md`

## 🆘 Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check Docker status
docker info

# Rebuild images
docker-compose build --no-cache
```

**Database connection failed**
```bash
# Check database status
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up db
```

**NATS connection issues**
```bash
# Check NATS logs
docker-compose logs nats

# Test NATS connectivity
docker-compose exec nats nats-server --help
```

### Performance Issues

**Slow responses**
- Check service health: `curl localhost:8666/health`
- Review logs: `docker-compose logs gateway`
- Monitor resource usage: `docker stats`

**Memory usage**
- Adjust database pool settings in `.env`
- Scale services: `docker-compose up --scale chat-service=2`

---

**Gaia Platform v1.0.0** - Foundation-first microservices backend maintaining full LLM Platform compatibility while enabling future enhancements.
