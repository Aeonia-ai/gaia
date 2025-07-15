"""
Gaia Web Service - FastHTML Server-Side Rendered Interface
"""
from fasthtml.fastapp import FastHTML, serve
from starlette.responses import RedirectResponse
from fasthtml.core import Script, Link, Meta
from fasthtml.components import Div
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from app.services.web.config import settings
from app.services.web.routes import auth, chat, api, websocket
from app.services.web.components.gaia_ui import GaiaDesign, gaia_layout, gaia_auth_form
from app.shared.logging import setup_service_logger

# Setup logging
logger = setup_service_logger(settings.service_name)

# Create FastHTML app with Tailwind CSS and HTMX
app = FastHTML(
    hdrs=(
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        # FastHTML automatically includes HTMX, don't duplicate
        Script(src="https://cdn.tailwindcss.com"),
        # Temporarily disabled due to 500 error: Link(rel="stylesheet", href="/static/gaia-design.css"),
        Link(rel="icon", href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🦋%3C/text%3E%3C/svg%3E"),
    ),
    title="Gaia Platform",
    static_dir="app/services/web/static"
)

# Add middleware
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
auth.setup_routes(app)
chat.setup_routes(app)
api.setup_routes(app)
# WebSocket support is not available in FastHTML yet
# if settings.enable_websocket:
#     websocket.setup_routes(app)

# Root route - redirect to login or chat
@app.get("/")
async def index(request):
    """Home page - redirect based on auth status"""
    if request.session.get("user"):
        return RedirectResponse(url="/chat", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

# Login page
@app.get("/login")
async def login_page():
    """Login page"""
    return gaia_layout(
        main_content=gaia_auth_form(is_login=True),
        page_class="justify-center items-center",
        show_sidebar=False
    )

# Register page
@app.get("/register")
async def register_page():
    """Registration page"""
    return gaia_layout(
        main_content=gaia_auth_form(is_login=False),
        page_class="justify-center items-center",
        show_sidebar=False
    )

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "gateway_url": settings.gateway_url,
        "websocket_enabled": settings.enable_websocket
    }

# Error handlers
@app.exception_handler(404)
async def not_found(request, exc):
    """404 error handler"""
    from app.services.web.components.gaia_ui import gaia_card, H1, P, gaia_button
    return gaia_layout(
        main_content=gaia_card(
            Div(
                H1("404 - Page Not Found", cls="text-2xl font-bold text-white mb-4"),
                P("The page you're looking for doesn't exist.", cls="text-slate-400 mb-6"),
                gaia_button("Go Home", href="/", cls="inline-block")
            )
        ),
        page_class="justify-center items-center"
    )

@app.exception_handler(500)
async def server_error(request, exc):
    """500 error handler"""
    from app.services.web.components.gaia_ui import gaia_error_message
    logger.error(f"Server error: {exc}")
    return gaia_layout(
        main_content=gaia_error_message("An unexpected error occurred. Please try again later."),
        page_class="justify-center items-center"
    )

# Startup event
@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.service_name} service on port {settings.port}")
    logger.info(f"Gateway URL: {settings.gateway_url}")
    logger.info(f"WebSocket enabled: {settings.enable_websocket}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down {settings.service_name} service")

# Run the app
if __name__ == "__main__":
    logger.info(f"Starting Gaia Web Service on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.services.web.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
