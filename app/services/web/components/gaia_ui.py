"""
Gaia UI Components - FastHTML version of React components
Maintains exact visual parity with the React client
"""

from fasthtml.common import *

# ========================================================================================
# DESIGN TOKENS (extracted from React app)
# ========================================================================================

class GaiaDesign:
    """Design system constants extracted from React components."""
    
    # Main background (used everywhere)
    BG_MAIN = "min-h-screen bg-gradient-to-br from-indigo-950 via-purple-900 to-slate-900"
    
    # Logo (butterfly emoji with gradient background)
    LOGO_EMOJI = "🦋"
    LOGO_BG = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400"
    LOGO_SMALL = "w-8 h-8"
    LOGO_LARGE = "w-16 h-16" 
    
    # Brand
    APP_NAME = "Gaia"
    
    # Cards and containers
    CARD_BG = "bg-slate-900/50 border border-purple-500/20 backdrop-blur-sm"
    SIDEBAR_BG = "bg-slate-900/50 border-r border-purple-500/20 backdrop-blur-sm"
    
    # Buttons
    BTN_PRIMARY = "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
    BTN_OUTLINE = "border border-purple-500/30 text-purple-300 hover:bg-purple-600/20"
    
    # Inputs
    INPUT_BG = "bg-slate-800/50 border border-purple-500/30 text-white placeholder:text-purple-300"
    
    # Messages
    MSG_USER = "bg-gradient-to-r from-purple-600 to-pink-600 text-white"
    MSG_ASSISTANT = "bg-slate-800/50 text-white border border-purple-500/20"
    
    # Text colors
    TEXT_PRIMARY = "text-white"
    TEXT_SECONDARY = "text-purple-300"
    TEXT_ACCENT = "text-purple-200"
    
    # States
    ACTIVE = "bg-purple-600/20 border-purple-400/50"
    INACTIVE = "bg-slate-800/30 border-purple-500/10 hover:bg-slate-800/50"

# ========================================================================================
# ATOMIC COMPONENTS
# ========================================================================================

def gaia_logo(size="small", text_size="text-2xl"):
    """Butterfly logo with gradient background - exact match to React version."""
    size_class = GaiaDesign.LOGO_SMALL if size == "small" else GaiaDesign.LOGO_LARGE
    
    return Div(
        GaiaDesign.LOGO_EMOJI,
        cls=f"{size_class} {GaiaDesign.LOGO_BG} rounded-full flex items-center justify-center {text_size}"
    )

def gaia_button(text, variant="primary", **kwargs):
    """Gaia-styled button - exact match to React Button component."""
    if variant == "primary":
        btn_class = f"p-3 {GaiaDesign.BTN_PRIMARY} {GaiaDesign.TEXT_PRIMARY} rounded-lg font-medium"
    else:  # outline
        btn_class = f"p-3 {GaiaDesign.BTN_OUTLINE} rounded-lg"
    
    return Button(text, cls=btn_class, **kwargs)

def gaia_input(placeholder="", **kwargs):
    """Gaia-styled input - exact match to React Input component."""
    return Input(
        placeholder=placeholder,
        cls=f"p-3 {GaiaDesign.INPUT_BG} rounded-lg",
        **kwargs
    )

def gaia_card(content, active=False):
    """Gaia-styled card - exact match to React Card component."""
    state_class = GaiaDesign.ACTIVE if active else GaiaDesign.INACTIVE
    return Div(
        content,
        cls=f"p-3 cursor-pointer transition-colors rounded-lg border {state_class}"
    )

# ========================================================================================
# LAYOUT COMPONENTS  
# ========================================================================================

def gaia_layout(content, title="Gaia"):
    """Main layout wrapper with Gaia background."""
    return Html(
        Head(
            Title(title),
            Link(rel="stylesheet", href="https://cdn.tailwindcss.com"),
            Script(src="https://unpkg.com/htmx.org@1.9.10")
        ),
        Body(content, cls=GaiaDesign.BG_MAIN)
    )

def gaia_sidebar_header(on_new_chat=None):
    """Sidebar header with logo and new chat button - exact match to React."""
    return Div(
        # Logo and title
        Div(
            gaia_logo(size="small"),
            H1(GaiaDesign.APP_NAME, cls=f"text-xl font-bold {GaiaDesign.TEXT_PRIMARY}"),
            cls="flex items-center gap-3 mb-4"
        ),
        # New chat button
        gaia_button(
            "➕ New Chat",
            hx_post="/conversations/new" if on_new_chat else None,
            hx_target="#chat-area" if on_new_chat else None,
            cls="w-full"
        ),
        cls="p-4 border-b border-purple-500/20"
    )

def gaia_conversation_item(conversation, current_id=None, on_click=None):
    """Conversation list item - exact match to React version."""
    is_active = conversation.get("id") == current_id
    
    return gaia_card(
        Div(
            P(conversation.get("title", "New Conversation"), 
              cls=f"{GaiaDesign.TEXT_PRIMARY} text-sm truncate"),
            P(conversation.get("created_at", "Today"), 
              cls=f"{GaiaDesign.TEXT_SECONDARY} text-xs"),
        ),
        active=is_active,
        hx_get=f"/conversations/{conversation.get('id')}" if on_click else None,
        hx_target="#chat-area" if on_click else None
    )

def gaia_user_profile(user, on_logout=None):
    """User profile section - exact match to React version."""
    avatar_letter = user.get("email", "U")[0].upper() if user else "U"
    
    return Div(
        # User info
        Div(
            Div(
                avatar_letter,
                cls=f"w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center {GaiaDesign.TEXT_PRIMARY} text-sm font-bold"
            ),
            Span(user.get("email", ""), cls=f"{GaiaDesign.TEXT_PRIMARY} text-sm truncate"),
            cls="flex items-center gap-3 mb-3"
        ),
        # Logout button
        gaia_button(
            "🚪 Sign Out",
            variant="outline",
            hx_post="/auth/logout" if on_logout else None,
            cls="w-full"
        ),
        cls="p-4 border-t border-purple-500/20"
    )

# ========================================================================================
# CHAT COMPONENTS
# ========================================================================================

def gaia_message_bubble(content, role="user"):
    """Message bubble - exact match to React version."""
    if role == "user":
        justify = "justify-end"
        bubble_class = f"max-w-[70%] rounded-lg p-4 {GaiaDesign.MSG_USER}"
    else:  # assistant
        justify = "justify-start" 
        bubble_class = f"max-w-[70%] rounded-lg p-4 {GaiaDesign.MSG_ASSISTANT}"
    
    return Div(
        Div(
            P(content, cls="whitespace-pre-wrap"),
            cls=bubble_class
        ),
        cls=f"flex {justify} mb-6"
    )

def gaia_typing_indicator():
    """Typing indicator animation - exact match to React version."""
    return Div(
        Div(
            Div(
                *[Div(cls=f"w-2 h-2 bg-purple-400 rounded-full animate-bounce", 
                      style=f"animation-delay: {i*0.1}s") for i in range(3)],
                cls="flex space-x-2"
            ),
            cls=f"max-w-[70%] rounded-lg p-4 {GaiaDesign.MSG_ASSISTANT}"
        ),
        cls="flex justify-start mb-6"
    )

def gaia_chat_input(conversation_id=None):
    """Chat input form - exact match to React version."""
    return Div(
        Form(
            Div(
                gaia_input(
                    placeholder="Type your message...",
                    name="message",
                    required=True,
                    cls="flex-1"
                ),
                gaia_button(
                    "➤",
                    type="submit",
                    cls="p-3"
                ),
                cls="flex gap-4"
            ),
            hx_post=f"/conversations/{conversation_id}/messages" if conversation_id else None,
            hx_target="#messages-container",
            hx_swap="beforeend",
            hx_on_submit="this.reset()",
            cls="max-w-4xl mx-auto"
        ),
        cls="p-6 border-t border-purple-500/20"
    )

def gaia_welcome_screen(on_new_chat=None):
    """Welcome screen - exact match to React version."""
    return Div(
        Div(
            gaia_logo(size="large", text_size="text-2xl"),
            H2("Welcome to Gaia", cls=f"text-2xl font-bold {GaiaDesign.TEXT_PRIMARY} mb-2"),
            P("Select a conversation or create a new one to get started", 
              cls=f"{GaiaDesign.TEXT_SECONDARY} mb-4"),
            gaia_button(
                "➕ Start New Chat",
                hx_post="/conversations/new" if on_new_chat else None,
                hx_target="#chat-area" if on_new_chat else None
            ),
            cls="text-center"
        ),
        cls="flex-1 flex items-center justify-center"
    )

# ========================================================================================
# AUTHENTICATION COMPONENTS
# ========================================================================================

def gaia_auth_form(is_login=True, error=None):
    """Authentication form - exact match to React version."""
    form_title = "Sign in to your account" if is_login else "Create your account"
    button_text = "Sign In" if is_login else "Sign Up"
    toggle_text = "Don't have an account? " if is_login else "Already have an account? "
    toggle_link = "Sign up" if is_login else "Sign in"
    toggle_href = "/signup" if is_login else "/login"
    
    return Div(
        # Logo
        Div(gaia_logo(size="large", text_size="text-2xl"), cls="mx-auto mb-4"),
        
        # Title
        H1("Welcome to Gaia", cls=f"text-2xl font-bold {GaiaDesign.TEXT_PRIMARY} text-center mb-2"),
        P(form_title, cls=f"{GaiaDesign.TEXT_ACCENT} text-center mb-6"),
        
        # Error message
        *([P(error, cls="text-red-400 text-center mb-4")] if error else []),
        
        # Form
        Form(
            # Full name (signup only)
            *([gaia_input(placeholder="Full Name", name="full_name", required=True, cls="w-full mb-4")] if not is_login else []),
            
            gaia_input(placeholder="Email", name="email", type="email", required=True, cls="w-full mb-4"),
            gaia_input(placeholder="Password", name="password", type="password", required=True, cls="w-full mb-4"),
            gaia_button(button_text, type="submit", cls="w-full"),
            
            action="/auth/login" if is_login else "/auth/signup",
            method="post"
        ),
        
        # Toggle link
        P(
            toggle_text,
            A(toggle_link, href=toggle_href, cls="text-purple-400 hover:text-purple-300 underline"),
            cls=f"text-center mt-4 {GaiaDesign.TEXT_SECONDARY}"
        ),
        
        cls=f"w-full max-w-md {GaiaDesign.CARD_BG} rounded-lg p-6"
    )