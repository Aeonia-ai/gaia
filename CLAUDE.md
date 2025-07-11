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
- **Web Service** (port 8080): FastHTML frontend for chat interface (planned)

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
- Web: `http://web-service:8000` (external: `localhost:8080`)

## Shared Modules

### Core Utilities (`app/shared/`)
- **`config.py`**: Centralized Pydantic settings with environment variable management
- **`security.py`**: Authentication patterns, JWT validation, `AuthenticationResult` class
- **`database.py`**: SQLAlchemy setup with connection pooling
- **`logging.py`**: Color-coded structured logging with custom levels (NETWORK, SERVICE, NATS)
- **`nats_client.py`**: Async messaging client with reconnection handling
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
- Use test markers defined in `pytest.ini`

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

## FastHTML Web Service Integration

### Overview
The Web Service provides a FastHTML-based chat interface that integrates with all Gaia microservices while maintaining the visual design and functionality of the React client.

### Architecture
```
FastHTML Frontend (8080) → Gateway (8666) → Services
├─ User login → Auth Service → Supabase validation
├─ Chat messages → Chat Service → LLM Platform logic
├─ Real-time updates → NATS → WebSocket to frontend
└─ Asset requests → Asset Service → External APIs
```

### Key Features
- **Server-Side Rendering**: FastHTML components with Tailwind CSS
- **HTMX Integration**: Dynamic updates without complex JavaScript
- **Service Integration**: Uses existing Gaia microservices via Gateway
- **Real-time Chat**: WebSocket + NATS for live updates
- **Unified Auth**: Same Supabase JWT system as API clients

### Development Commands
```bash
# Start with web service
docker-compose up web-service

# Access points
# FastHTML frontend: http://localhost:8080
# API gateway: http://localhost:8666

# Web service logs
docker-compose logs -f web-service

# Test web service health
curl http://localhost:8080/health
```

### Directory Structure
```
app/services/web/
├── main.py              # FastHTML application
├── components/
│   ├── gaia_ui.py       # Complete UI component library (extracted from React)
│   ├── auth.py          # Authentication components
│   ├── chat.py          # Chat interface components
│   └── layout.py        # Layout and UI components
├── routes/
│   ├── auth.py          # Authentication routes
│   ├── chat.py          # Chat functionality routes
│   └── api.py           # Gateway API integration
└── static/
    └── gaia-design.css  # Design system CSS (extracted from React)
```

### API Integration Pattern
```python
# Web service communicates with other services via Gateway
class GaiaAPIClient:
    def __init__(self):
        self.gateway_url = settings.GATEWAY_URL  # http://gateway:8000
    
    async def authenticate_user(self, email: str, password: str):
        # Routes through Gateway → Auth Service → Supabase
        return await self.client.post(f"{self.gateway_url}/api/v1/auth/validate")
    
    async def send_message(self, conversation_id: str, message: str, auth_token: str):
        # Routes through Gateway → Chat Service → LLM Platform
        return await self.client.post(f"{self.gateway_url}/api/v1/chat/completions")
```

### Real-time Integration
- **WebSocket Endpoint**: `/ws/{conversation_id}` for live chat updates
- **NATS Subscription**: Listens to `gaia.chat.*` events for real-time coordination
- **Event-Driven**: New messages broadcast via NATS to all connected clients

### Session Management
- **FastHTML Sessions**: Built-in session middleware for user authentication
- **JWT Integration**: Stores Supabase JWT tokens in secure sessions
- **Auth Decorator**: `@require_auth` for protected routes

## Implementation Status & Future Tasks

### ✅ Completed Systems

#### Provider Management System (20/22 endpoints) - FULLY COMPLETE
- **Core functionality**: Multi-LLM provider support (Claude, OpenAI)
- **Health monitoring**: Real-time provider health and response times
- **Model management**: List, filter, and get detailed model information
- **Usage statistics**: Track requests, tokens, costs, error rates
- **Authentication**: Full API key validation through gateway
- **Removed by design**: Model recommendation and comparison endpoints

#### Streaming Chat System (10 endpoints) - FULLY COMPLETE
- **Server-Sent Events**: OpenAI/Anthropic compatible streaming
- **Multi-provider support**: Intelligent model selection
- **Performance optimized**: Sub-700ms response times for VR/AR
- **Caching system**: 0ms access time after first request

#### Core Infrastructure - FULLY COMPLETE
- **Gateway service**: Request routing and authentication
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **NATS messaging**: Service coordination
- **Authentication**: JWT + API key support

### 🔧 Next Priority Systems

#### 1. Asset Pricing System (18 endpoints) - HIGH PRIORITY
- Revenue and cost management functionality
- Asset generation pricing models
- Usage tracking and billing

#### 2. Persona Management CRUD (7 endpoints) - MEDIUM PRIORITY  
- User experience personalization
- Custom persona creation and management
- Persona memory and context

#### 3. Performance Monitoring (6 endpoints) - MEDIUM PRIORITY
- System health metrics
- Response time monitoring
- Error rate tracking

#### 4. Auth Service Enhancement (2 endpoints) - LOW PRIORITY
- User registration endpoints
- Login/logout functionality

### 🚨 Technical Debt to Address Later

#### Provider System Enhancements
- **Full LLM Registry**: Replace simple endpoints with complete provider registry system
- **Dynamic provider registration**: Add/remove providers at runtime
- **Advanced model selection**: Context-aware intelligent model selection
- **Cost optimization**: Real-time cost tracking and budget limits

#### Infrastructure Improvements
- **Service discovery**: Automatic service registration via NATS
- **Circuit breakers**: Fault tolerance for external API calls
- **Rate limiting**: Per-user and per-provider rate limits
- **Monitoring**: Comprehensive metrics and alerting

#### Security & Compliance
- **API key rotation**: Automatic key rotation and management
- **Audit logging**: Comprehensive request/response logging
- **Data retention**: Configurable data retention policies
- **Compliance**: GDPR/CCPA compliance features

### 🎯 Current Focus
Moving to **Asset Pricing System** implementation to enable revenue management and cost tracking across the platform.

### Deployment Integration
- **Docker Service**: Runs as `web-service` in docker-compose.yml
- **Port Mapping**: External port 8080, internal port 8000
- **Service Dependencies**: Depends on gateway, auth-service, chat-service
- **Shared Volumes**: Access to same data volumes as other services

### Design System Integration

The web service includes a complete design system extracted from the React client:

**Visual Elements**:
- **Color Scheme**: Purple/pink gradients (`from-purple-600 to-pink-600`), slate backgrounds
- **Butterfly Logo**: 🦋 emoji with gradient background (`from-purple-400 via-pink-400 to-blue-400`)
- **Typography**: White text on dark backgrounds, purple accent colors
- **Layout**: 320px sidebar, centered chat area, responsive design

**Component Library** (`app/services/web/components/gaia_ui.py`):
```python
# Pre-built components matching React versions exactly
gaia_logo(size="small")           # Butterfly logo with gradient
gaia_button("Text", variant="primary")  # Purple/pink gradient buttons
gaia_auth_form(is_login=True)     # Complete auth form
gaia_message_bubble(content, role="user")  # Chat message styling
gaia_sidebar_header()             # Sidebar with logo and new chat button
```

**Design Tokens**:
```python
class GaiaDesign:
    BG_MAIN = "bg-gradient-to-br from-indigo-950 via-purple-900 to-slate-900"
    BTN_PRIMARY = "bg-gradient-to-r from-purple-600 to-pink-600"
    LOGO_EMOJI = "🦋"
    LOGO_BG = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400"
```

**CSS Classes** (`app/services/web/static/gaia-design.css`):
- `.gaia-bg`: Main gradient background
- `.gaia-logo-small`, `.gaia-logo-large`: Logo styling
- `.gaia-btn-primary`: Button gradients
- `.gaia-message-user`, `.gaia-message-assistant`: Message bubble styling

### Benefits
1. **Zero API Disruption**: Existing API clients continue working unchanged
2. **Service Reuse**: Leverages all existing Gaia microservices
3. **Consistent Auth**: Same Supabase authentication across web and API
4. **Real-time**: NATS enables live chat updates
5. **Independent Scaling**: Web service scales separately from API services
6. **Modern SSR**: Server-side rendered with progressive enhancement
7. **Visual Parity**: Pixel-perfect match to React client design
8. **Design System**: Extracted and reusable UI components