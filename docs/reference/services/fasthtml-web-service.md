# FastHTML Web Service Integration

## Overview
The Web Service provides a FastHTML-based chat interface that integrates with all Gaia microservices while maintaining the visual design and functionality of the React client.

## Architecture
```
FastHTML Frontend (8080) → Gateway (8666) → Services
├─ User login → Auth Service → Supabase validation
├─ Chat messages → Chat Service → LLM Platform logic
├─ Real-time updates → NATS → WebSocket to frontend
└─ Asset requests → Asset Service → External APIs
```

## Key Features
- **Server-Side Rendering**: FastHTML components with Tailwind CSS
- **HTMX Integration**: Dynamic updates without complex JavaScript
- **Service Integration**: Uses existing Gaia microservices via Gateway
- **Real-time Chat**: WebSocket + NATS for live updates
- **Unified Auth**: Same Supabase JWT system as API clients

## Development Commands
```bash
# Start with web service
docker compose up web-service

# Access points
# FastHTML frontend: http://localhost:8080
# API gateway: http://localhost:8666

# Web service logs
docker compose logs -f web-service

# Test web service health
curl http://localhost:8080/health
```

## Directory Structure
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

## API Integration Pattern
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

## Conversation Management
The web service implements a conversation management system for organizing chat sessions:

```python
# In-memory conversation store (development)
from app.services.web.utils.conversation_store import conversation_store

# Create new conversation
conversation = conversation_store.create_conversation(user_id, title="Chat about Python")

# Store messages
conversation_store.add_message(conversation_id, "user", "Hello!")
conversation_store.add_message(conversation_id, "assistant", "Hi there!")

# Retrieve conversations and messages
conversations = conversation_store.get_conversations(user_id)
messages = conversation_store.get_messages(conversation_id)
```

**Features:**
- **Multi-user Support**: Conversations isolated by user ID
- **Message History**: Complete conversation persistence
- **Metadata Tracking**: Titles, previews, timestamps
- **Search Ready**: Structured for future search implementation

## Real-time Integration
- **HTMX Updates**: Dynamic conversation list updates
- **JavaScript Integration**: Custom scripts for AI response loading
- **Session Persistence**: Conversations survive browser refresh
- **Future WebSocket**: Ready for real-time multi-tab sync

## Session Management
- **FastHTML Sessions**: Built-in session middleware for user authentication
- **JWT Integration**: Stores Supabase JWT tokens in secure sessions
- **Auth Decorator**: `@require_auth` for protected routes

## Testing
The web service includes comprehensive unit tests and automated integration tests:

```bash
# Unit tests
./scripts/test-web-quick.sh  # Quick test summary
docker compose exec -e PYTHONPATH=/app web-service pytest /app/tests/web/ -v

# Integration and functional tests
./scripts/test-full-chat.sh     # Complete chat flow test
./scripts/test-ai-response.py   # AI response display verification
./scripts/test-registration.py  # User registration testing
./scripts/test-chat-automated.py # Automated multi-conversation test

# Test structure
tests/web/
├── test_auth_routes.py      # Authentication route tests
├── test_gateway_client.py   # Gateway API client tests (✅ 8/8 passing)
├── test_error_handling.py   # Error message and UI component tests
└── test_auth_integration.py # Full authentication flow tests

scripts/
├── test-web-quick.sh        # Quick unit test runner
├── test-full-chat.sh        # End-to-end chat functionality
├── test-ai-response.py      # AI response verification
├── test-registration.py     # Registration flow testing
├── test-chat-automated.py   # Multi-conversation simulation
└── debug-*.py              # Debugging utilities
```

**Test Coverage:**
- **Gateway Client**: All API interactions tested with mocks
- **Authentication**: Login, registration, logout, session management
- **Chat Functionality**: Message sending, AI responses, conversation management
- **Error Handling**: Nested error parsing, user-friendly messages
- **UI Components**: Message rendering, HTML escaping
- **Integration**: Full user journey from login to multi-conversation chat

## Deployment Integration
- **Docker Service**: Runs as `web-service` in docker compose.yml
- **Port Mapping**: External port 8080, internal port 8000
- **Service Dependencies**: Depends on gateway, auth-service, chat-service
- **Shared Volumes**: Access to same data volumes as other services

## Design System Integration

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

## Benefits
1. **Zero API Disruption**: Existing API clients continue working unchanged
2. **Service Reuse**: Leverages all existing Gaia microservices
3. **Consistent Auth**: Same Supabase authentication across web and API
4. **Real-time**: NATS enables live chat updates
5. **Independent Scaling**: Web service scales separately from API services
6. **Modern SSR**: Server-side rendered with progressive enhancement
7. **Visual Parity**: Pixel-perfect match to React client design
8. **Design System**: Extracted and reusable UI components