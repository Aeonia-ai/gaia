"""
Gaia Web Service - FastHTML Server-Side Rendered Interface
"""
from fasthtml.fastapp import FastHTML, serve
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fasthtml.core import Script, Link, Meta, Style
from fasthtml.components import Div, H1, P, Button
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

from app.services.web.config import settings
from app.services.web.routes import auth, chat, api, websocket, profile
from app.services.web.components.gaia_ui import GaiaDesign, gaia_layout, gaia_auth_form, gaia_mobile_styles
from app.shared.logging import setup_service_logger

# Setup logging
logger = setup_service_logger(settings.service_name)

# Create FastHTML app with Tailwind CSS and HTMX
app = FastHTML(
    hdrs=(
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        # FastHTML automatically includes HTMX, don't duplicate
        # HTMX SSE extension for streaming chat
        Script(src="https://unpkg.com/htmx.org@1.9.10/dist/ext/sse.js"),
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="stylesheet", href="/static/animations.css"),
        Link(rel="icon", href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🦋%3C/text%3E%3C/svg%3E"),
        # HTMX indicator styles - completely hidden
        Style("""
            .htmx-indicator { display: none !important; }
            .htmx-request .htmx-indicator { display: none !important; }
            .htmx-request.htmx-indicator { display: none !important; }
        """),
        # Global HTMX configuration for SPA-like behavior
        Script("""
            document.addEventListener('DOMContentLoaded', function() {
                // Configure HTMX for better SPA experience
                htmx.config.historyCacheSize = 10;
                htmx.config.refreshOnHistoryMiss = false;
                
                // Debug SSE extension
                console.log('HTMX version:', htmx.version);
                console.log('SSE extension loaded:', htmx.ext && htmx.ext.sse ? 'yes' : 'no');
                
                // Enable HTMX logging for debugging
                if (window.location.search.includes('debug')) {
                    htmx.config.logger = function(elt, event, data) {
                        console.log('[HTMX]', event, data);
                    };
                }
                
                // Add page transition effects
                document.body.addEventListener('htmx:beforeSwap', function(evt) {
                    // Fade out effect
                    if (evt.detail.target.id === 'main-content') {
                        evt.detail.target.style.opacity = '0';
                        evt.detail.target.style.transform = 'translateY(10px)';
                    }
                });
                
                document.body.addEventListener('htmx:afterSwap', function(evt) {
                    // Fade in effect
                    if (evt.detail.target.id === 'main-content') {
                        setTimeout(() => {
                            evt.detail.target.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            evt.detail.target.style.opacity = '1';
                            evt.detail.target.style.transform = 'translateY(0)';
                        }, 10);
                    }
                });
            });
        """),
    ),
    title="Gaia Platform"
    # Removed static_dir parameter - FastHTML() doesn't support it
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/services/web/static"), name="static")

# Add middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.session_secret,
    session_cookie="session",  # Use simple session cookie name
    max_age=settings.session_max_age,
    https_only=False,  # Allow HTTP for local development
    same_site="lax"    # Allow cross-site requests
)
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
profile.setup_routes(app)
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
async def login_page(request):
    """Login page"""
    # Check if coming from email verification
    verified = request.query_params.get("verified") == "true"
    
    content = []
    
    # Show success message if email was just verified
    if verified:
        from app.services.web.components.gaia_ui import gaia_success_message
        content.append(
            Div(
                gaia_success_message("✅ Email verified successfully! You can now log in."),
                cls="mb-4 max-w-md mx-auto"
            )
        )
    
    content.extend([
        gaia_auth_form(is_login=True),
        gaia_mobile_styles()
    ])
    
    return gaia_layout(
        main_content=Div(
            *content,
            cls="w-full"
        ),
        page_class="justify-center items-center",
        show_sidebar=False
    )

# Register page
@app.get("/register")
async def register_page():
    """Registration page"""
    return gaia_layout(
        main_content=Div(
            gaia_auth_form(is_login=False),
            gaia_mobile_styles(),
            cls="w-full"
        ),
        page_class="justify-center items-center",
        show_sidebar=False
    )

# Email verification page
@app.get("/email-verification")
async def email_verification_page(request):
    """Email verification page"""
    email = request.query_params.get("email", "your email")
    
    from app.services.web.components.gaia_ui import gaia_email_verification_notice
    
    return gaia_layout(
        main_content=Div(
            gaia_email_verification_notice(email),
            Div(id="message-area", cls="mt-4"),
            cls="min-h-screen flex items-center justify-center p-4"
        ),
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

# Debug page to test HTMX
@app.get("/debug/htmx")
async def debug_htmx():
    """Debug page to verify HTMX is working"""
    from fasthtml.core import Script, NotStr
    return Div(
        H1("HTMX Debug Test", cls="text-2xl font-bold mb-4"),
        
        # Simple button test
        Button("Click me!", 
               hx_get="/debug/response",
               hx_target="#result",
               cls="bg-blue-500 text-white px-4 py-2 rounded"),
        
        # Result area
        Div(id="result", cls="mt-4 p-4 border border-gray-300"),
        
        # Debug info
        Script(NotStr("""
            console.log('HTMX version:', htmx.version);
            console.log('HTMX loaded:', typeof htmx !== 'undefined');
            
            // Try manual HTMX request
            setTimeout(() => {
                console.log('Testing manual HTMX request...');
                htmx.ajax('GET', '/debug/response', {target: '#result'});
            }, 2000);
        """))
    )

@app.get("/debug/response")
async def debug_response():
    """Simple response for HTMX test"""
    return Div(
        P(f"HTMX is working! Time: {datetime.now().strftime('%H:%M:%S')}"),
        P("If you see this, HTMX requests are functioning correctly."),
        cls="text-green-600"
    )

@app.get("/debug/swap-test")
async def debug_swap_test():
    """Test page for innerHTML swapping"""
    from fasthtml.core import Script, NotStr
    return Div(
        H1("innerHTML Swap Test", cls="text-2xl font-bold mb-4"),
        
        Div(
            Button("Load Content 1", 
                   hx_get="/debug/content1",
                   hx_target="#test-content",
                   hx_swap="innerHTML",
                   cls="bg-blue-500 text-white px-4 py-2 rounded mr-2"),
            Button("Load Content 2",
                   hx_get="/debug/content2", 
                   hx_target="#test-content",
                   hx_swap="innerHTML",
                   cls="bg-green-500 text-white px-4 py-2 rounded mr-2"),
            Button("Clear",
                   hx_get="/debug/clear",
                   hx_target="#test-content", 
                   hx_swap="innerHTML",
                   cls="bg-red-500 text-white px-4 py-2 rounded"),
            cls="mb-4"
        ),
        
        Div(
            Div("Initial content", cls="p-4 bg-gray-100 rounded"),
            id="test-content",
            cls="border-2 border-blue-500 p-4 min-h-[200px]"
        ),
        
        Script(NotStr("""
            document.body.addEventListener('htmx:afterSwap', function(evt) {
                console.log('[SWAP TEST] After swap:', evt.detail);
            });
        """))
    )

@app.get("/debug/content1") 
async def debug_content1():
    """Test content 1"""
    return Div(
        Div("Content 1 - First message", cls="p-2 bg-yellow-100 rounded mb-2"),
        Div("Content 1 - Second message", cls="p-2 bg-yellow-100 rounded"),
        Div(f"Loaded at: {datetime.now().strftime('%H:%M:%S')}", cls="text-sm text-gray-500 mt-2")
    )

@app.get("/debug/content2")
async def debug_content2():
    """Test content 2"""
    return Div(
        Div("Content 2 - Different message", cls="p-2 bg-green-100 rounded mb-2"),  
        Div("Content 2 - Another message", cls="p-2 bg-green-100 rounded"),
        Div(f"Loaded at: {datetime.now().strftime('%H:%M:%S')}", cls="text-sm text-gray-500 mt-2")
    )

@app.get("/debug/clear")
async def debug_clear():
    """Clear content"""
    return Div(
        Div("Cleared - Ready for new content", cls="p-4 bg-gray-100 rounded")
    )

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
    logger.info(f"API Key: {settings.api_key[:10]}...")  # Debug: show first 10 chars
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
