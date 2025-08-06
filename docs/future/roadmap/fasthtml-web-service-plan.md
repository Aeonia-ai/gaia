# FastHTML Web Service Implementation Plan

## Overview

The FastHTML Web Service provides a server-side rendered web interface for the Gaia Platform, offering a lightweight alternative to the React client while maintaining full visual and functional parity.

## Architecture

### Service Integration
```
┌─────────────────┐
│  Web Browser    │
│  (Port 8080)    │
└────────┬────────┘
         │ HTTP/WebSocket
┌────────▼────────┐
│ FastHTML Web    │
│   Service       │
│ ┌─────────────┐ │
│ │   Routes    │ │
│ │  ├─ Auth    │ │
│ │  ├─ Chat    │ │
│ │  └─ API     │ │
│ └─────────────┘ │
└────────┬────────┘
         │ Internal API calls
┌────────▼────────┐
│    Gateway      │
│  (Port 8666)    │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    ▼         ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│ Auth  │ │ Chat  │ │ Asset │
└───────┘ └───────┘ └───────┘
```

### Key Design Principles
- **Server-Side Rendering**: FastHTML with HTMX for dynamic updates
- **Gateway Integration**: All API calls route through existing gateway
- **Visual Parity**: Exact match to React client design using extracted components
- **Progressive Enhancement**: Works without JavaScript, enhanced with HTMX
- **Independent Scaling**: Separate service that can scale independently

## Directory Structure

```
app/services/web/
├── __init__.py
├── main.py                 # FastHTML application entry point
├── config.py               # Web service configuration
├── components/
│   ├── __init__.py
│   ├── gaia_ui.py         # Core UI component library (already created)
│   ├── auth.py            # Authentication components
│   ├── chat.py            # Chat interface components
│   └── layout.py          # Layout and navigation components
├── routes/
│   ├── __init__.py
│   ├── auth.py            # Login/logout/register routes
│   ├── chat.py            # Chat interface and conversation routes
│   ├── api.py             # API proxy routes to gateway
│   └── websocket.py       # WebSocket handlers for real-time
├── static/
│   ├── gaia-design.css    # Design system CSS (already created)
│   └── gaia.js            # Minimal JavaScript for WebSocket
├── templates/
│   └── base.html          # Base HTML template
└── utils/
    ├── __init__.py
    ├── gateway_client.py   # Gateway API client
    └── session.py         # Session management utilities
```

## Implementation Phases

### Phase 1: Core Infrastructure (1-2 days)
- [ ] Create directory structure and basic FastHTML app
- [ ] Implement session management for auth tokens
- [ ] Create gateway API client for service communication
- [ ] Set up base templates and routing structure
- [ ] Integrate existing design system (gaia_ui.py and CSS)

### Phase 2: Authentication Flow (1 day)
- [ ] Login/logout routes with Supabase integration
- [ ] Session-based JWT token storage
- [ ] Auth state management and route protection
- [ ] User profile display component

### Phase 3: Chat Interface (2-3 days)
- [ ] Chat UI with conversation list
- [ ] Message display with streaming support
- [ ] Input form with HTMX submission
- [ ] WebSocket integration for real-time updates
- [ ] Conversation history from database

### Phase 4: Production Ready (1 day)
- [ ] Docker configuration and health checks
- [ ] Error handling and user feedback
- [ ] Performance optimization
- [ ] Deployment configuration
- [ ] Comprehensive testing

## Technical Implementation Details

### FastHTML Application Structure

```python
from fasthtml.fastapp import FastHTML, WebSocket
from fasthtml.components import Div, Form, Input, Button
from starlette.middleware.sessions import SessionMiddleware
import httpx

# Create FastHTML app with session support
app = FastHTML(
    hdrs=[
        Script(src="https://unpkg.com/htmx.org@1.9.10"),
        Link(rel="stylesheet", href="/static/gaia-design.css")
    ]
)

# Add session middleware for auth
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

# Gateway API client
gateway_client = httpx.AsyncClient(base_url=settings.GATEWAY_URL)
```

### Authentication Integration

```python
# routes/auth.py
@app.post("/login")
async def login(email: str, password: str, session):
    # Call gateway auth endpoint
    response = await gateway_client.post("/api/v1/auth/login", 
        json={"email": email, "password": password})
    
    if response.status_code == 200:
        # Store JWT in session
        session["jwt_token"] = response.json()["access_token"]
        session["user"] = response.json()["user"]
        return Redirect("/chat")
    
    return LoginForm(error="Invalid credentials")
```

### Chat Interface Components

```python
# components/chat.py
def ChatMessage(message: dict, is_user: bool = False):
    return Div(
        cls=f"gaia-message-{'user' if is_user else 'assistant'}",
        children=[
            Div(message["content"], cls="message-content"),
            Div(format_time(message["created_at"]), cls="message-time")
        ]
    )

def ChatInput():
    return Form(
        Input(name="message", placeholder="Type your message...", 
              cls="gaia-input", autofocus=True),
        Button("Send", cls="gaia-btn-primary"),
        hx_post="/api/chat/send",
        hx_target="#messages",
        hx_swap="beforeend"
    )
```

### WebSocket Real-time Updates

```python
# routes/websocket.py
@app.ws("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    
    # Subscribe to NATS for this conversation
    async def message_handler(msg):
        data = json.loads(msg.data.decode())
        await websocket.send_text(
            ChatMessage(data, is_user=False).render()
        )
    
    sub = await nats_client.subscribe(
        f"gaia.chat.{conversation_id}.*", 
        cb=message_handler
    )
    
    try:
        while True:
            await websocket.receive_text()
    finally:
        await sub.unsubscribe()
```

### Docker Configuration

```dockerfile
# Dockerfile.web
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application
COPY app/services/web app/services/web
COPY app/shared app/shared

# Run FastHTML app
CMD ["uvicorn", "app.services.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Addition

```yaml
# docker compose.yml addition
web-service:
  build:
    context: .
    dockerfile: Dockerfile.web
  ports:
    - "8080:8000"
  environment:
    - GATEWAY_URL=http://gateway:8000
    - NATS_URL=nats://nats:4222
    - SESSION_SECRET=${SESSION_SECRET}
    - LOG_LEVEL=INFO
  depends_on:
    - gateway
    - nats
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## API Integration Pattern

### Gateway Communication
All API calls from the web service go through the gateway:

```python
# utils/gateway_client.py
class GaiaAPIClient:
    def __init__(self, base_url: str = settings.GATEWAY_URL):
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def chat_completion(self, message: str, jwt_token: str):
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = await self.client.post(
            "/api/v1/chat/completions",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": message}],
                "stream": True
            }
        )
        return response
```

## Design System Integration

### Existing Components (from gaia_ui.py)
- `gaia_logo()` - Butterfly logo with gradient
- `gaia_button()` - Primary/secondary buttons
- `gaia_message_bubble()` - Chat message styling
- `gaia_sidebar_header()` - Navigation header

### CSS Classes (from gaia-design.css)
- `.gaia-bg` - Main gradient background
- `.gaia-btn-primary` - Purple/pink gradient buttons
- `.gaia-message-user` - User message styling
- `.gaia-message-assistant` - AI message styling

## Benefits

1. **Zero API Disruption**: Existing clients unaffected
2. **Service Reuse**: Leverages all microservices
3. **SEO Friendly**: Server-side rendered
4. **Lightweight**: Minimal JavaScript
5. **Real-time**: WebSocket + NATS integration
6. **Scalable**: Independent service deployment

## Success Criteria

- [ ] Visual parity with React client
- [ ] All auth flows working via gateway
- [ ] Real-time chat with streaming
- [ ] Session management secure
- [ ] Performance <200ms page loads
- [ ] Mobile responsive design
- [ ] Accessibility compliant

## Security Considerations

- **Session Security**: Secure, httpOnly cookies for JWT storage
- **CSRF Protection**: Built into FastHTML forms
- **Content Security Policy**: Restrict resource loading
- **Input Validation**: Server-side validation for all inputs
- **Rate Limiting**: Implement at gateway level

## Deployment Strategy

1. **Local Development**: Part of docker compose stack
2. **Staging**: Deploy as separate Fly.io app
3. **Production**: Scale independently based on traffic
4. **Monitoring**: Health checks and metrics via gateway

## Future Enhancements

- **PWA Support**: Offline capability
- **i18n**: Multi-language support
- **Themes**: Dark/light mode toggle
- **Advanced Features**: Voice input, file uploads
- **Analytics**: User behavior tracking

This plan provides a clear path to implementing a modern, server-rendered web interface that complements the existing API-based clients while maintaining the same high-quality user experience.