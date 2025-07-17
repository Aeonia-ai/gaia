"""
Gaia UI Component Library
Extracted from React client for visual parity
"""
from fasthtml.components import Div, Span, Button, Input, Form, A, Img, H1, H2, P, Script
from fasthtml.core import Script, Style

# Design system constants
class GaiaDesign:
    """Design tokens matching React client"""
    # Background gradients
    BG_MAIN = "bg-gradient-to-br from-indigo-950 via-purple-900 to-slate-900"
    BG_SIDEBAR = "bg-gradient-to-b from-slate-900 to-slate-800"
    
    # Button styles with enhanced animations
    BTN_PRIMARY = "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-medium py-2 px-4 rounded-lg shadow-lg transform transition-all duration-300 hover:scale-105 hover:shadow-xl active:scale-95"
    BTN_SECONDARY = "bg-slate-700 hover:bg-slate-600 text-white font-medium py-2 px-3 rounded-lg transition-all duration-300 hover:shadow-lg active:scale-95"
    BTN_GHOST = "text-slate-300 hover:text-white hover:bg-slate-700/50 py-2 px-4 rounded-lg transition-all duration-300 hover:shadow-md active:scale-95"
    
    # Logo
    LOGO_EMOJI = "🦋"
    LOGO_BG_SMALL = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400 w-8 h-8 rounded-lg flex items-center justify-center shadow-md"
    LOGO_BG_LARGE = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400 w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
    
    # Text colors
    TEXT_PRIMARY = "text-white"
    TEXT_SECONDARY = "text-slate-300"
    TEXT_MUTED = "text-slate-400"
    
    # Message bubbles with enhanced shadows and animations
    MSG_USER = "bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-2xl rounded-br-sm px-4 py-3 max-w-[80%] ml-auto shadow-lg hover:shadow-xl transition-all duration-300 animate-slideInRight"
    MSG_ASSISTANT = "bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg hover:shadow-xl transition-all duration-300 animate-slideInLeft"
    
    # Input styles with enhanced focus states
    INPUT_PRIMARY = "bg-slate-800 border border-slate-600 text-white placeholder-slate-400 rounded-lg px-4 py-3 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 focus:shadow-lg transition-all duration-300"
    
    # Card styles with enhanced blur and animations
    CARD = "bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 shadow-xl hover:shadow-2xl transition-all duration-300 animate-fadeIn"


def gaia_logo(size="small", with_text=False):
    """Gaia butterfly logo component"""
    bg_class = GaiaDesign.LOGO_BG_SMALL if size == "small" else GaiaDesign.LOGO_BG_LARGE
    emoji_size = "text-sm" if size == "small" else "text-xl"
    
    logo = Div(
        Span(GaiaDesign.LOGO_EMOJI, cls=emoji_size),
        cls=bg_class
    )
    
    if with_text:
        return Div(
            logo,
            H1("Gaia", cls="text-base font-medium text-white ml-2"),
            cls="flex items-center"
        )
    return logo


def gaia_button(text, variant="primary", type="button", **kwargs):
    """Styled button component"""
    styles = {
        "primary": GaiaDesign.BTN_PRIMARY,
        "secondary": GaiaDesign.BTN_SECONDARY,
        "ghost": GaiaDesign.BTN_GHOST
    }
    
    cls = kwargs.pop("cls", "") + " " + styles.get(variant, styles["primary"])
    return Button(text, type=type, cls=cls.strip(), **kwargs)


def gaia_input(name, placeholder="", type="text", **kwargs):
    """Styled input component"""
    cls = kwargs.pop("cls", "") + " " + GaiaDesign.INPUT_PRIMARY + " w-full"
    return Input(
        name=name,
        type=type,
        placeholder=placeholder,
        cls=cls.strip(),
        **kwargs
    )


def gaia_card(content, title=None):
    """Card component with optional title"""
    children = []
    if title:
        children.append(H2(title, cls="text-xl font-semibold text-white mb-4"))
    children.append(content)
    
    return Div(*children, cls=GaiaDesign.CARD)


def gaia_message_bubble(content, role="user", timestamp=None):
    """Chat message bubble component"""
    bubble_cls = GaiaDesign.MSG_USER if role == "user" else GaiaDesign.MSG_ASSISTANT
    
    children = [
        Div(content, cls="whitespace-pre-wrap break-words")
    ]
    
    if timestamp:
        children.append(
            Div(timestamp, cls="text-xs opacity-70 mt-1")
        )
    
    return Div(
        Div(*children, cls=bubble_cls),
        cls=f"flex {'justify-end' if role == 'user' else 'justify-start'} mb-4"
    )


def gaia_sidebar_header(user=None):
    """Compact sidebar header matching modern chat interfaces"""
    return Div(
        # Logo and title
        Div(
            gaia_logo(with_text=True),
            cls="mb-4"
        ),
        # New chat button
        gaia_button(
            "New Chat",
            variant="secondary", 
            cls="w-full mb-3 text-xs",
            hx_post="/chat/new",
            hx_target="#main-content",
            hx_swap="innerHTML swap:0.5s settle:0.5s"
        ),
        # Search input with clear button
        Div(
            Div(
                Input(
                    type="text",
                    placeholder="Search conversations...",
                    cls="w-full bg-slate-800 border border-slate-600 text-white placeholder-slate-400 rounded-lg px-3 py-2 pr-8 text-xs focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all duration-300",
                    **{"hx-get": "/api/search-conversations"},
                    **{"hx-target": "#conversation-list"},
                    **{"hx-swap": "innerHTML"},
                    **{"hx-trigger": "keyup changed delay:300ms"},
                    name="query",
                    id="search-input"
                ),
                # Clear search button
                Button(
                    "×",
                    cls="absolute right-2 top-1/2 transform -translate-y-1/2 w-5 h-5 bg-slate-600 hover:bg-slate-500 text-white text-xs rounded-full opacity-0 transition-opacity duration-200 flex items-center justify-center font-bold leading-none",
                    id="clear-search",
                    title="Clear search",
                    onclick="document.getElementById('search-input').value = ''; htmx.ajax('GET', '/api/search-conversations', {target: '#conversation-list', swap: 'innerHTML'}); this.style.opacity = '0';"
                ),
                cls="relative"
            ),
            # Search status indicator
            Div(
                id="search-status",
                cls="text-xs text-slate-400 mt-1 h-4"
            ),
            cls="mb-3"
        ),
        # User info at bottom of header section
        Div(
            Div(
                user.get('email', 'User') if user else 'User',
                cls="text-xs text-slate-400 truncate mb-2"
            ),
            Div(
                A(
                    "Profile",
                    href="/profile",
                    cls="text-xs text-purple-400 hover:text-purple-300 transition-colors mr-3"
                ),
                A(
                    "Logout",
                    href="/logout",
                    cls="text-xs text-purple-400 hover:text-purple-300 transition-colors",
                    onclick="window.location.href='/logout'; return false;"
                ),
                cls="flex gap-3"
            ),
            cls="pt-2 border-t border-slate-700/50"
        ) if user else None,
        cls="p-3 border-b border-slate-700/50"
    )


def gaia_conversation_item(conversation, active=False):
    """Sidebar conversation item with ultra-compact typography and delete functionality"""
    base_cls = "group relative p-2 rounded-md transition-all duration-300 transform hover:scale-105 animate-slideInUp"
    active_cls = "bg-gradient-to-r from-purple-600/30 to-pink-600/30 border-l-3 border-purple-500 shadow-lg"
    hover_cls = "hover:bg-slate-700/50 hover:shadow-md"
    
    cls = f"{base_cls} {active_cls if active else hover_cls}"
    
    return Div(
        # Main conversation link
        A(
            Div(
                Div(
                    conversation.get("title", "New Conversation"),
                    cls="text-xs text-white truncate font-medium leading-tight pr-6"
                ),
                Div(
                    conversation.get("preview", ""),
                    cls="text-xs text-slate-400 truncate mt-0.5 opacity-60 leading-tight"
                ),
                cls="space-y-0.5"
            ),
            href=f"/chat/{conversation['id']}",
            cls="block",
            hx_get=f"/chat/{conversation['id']}",
            hx_target="#main-content",
            hx_swap="innerHTML swap:0.5s settle:0.5s",
            hx_indicator="#loading-indicator"
        ),
        # Delete button (appears on hover)
        Button(
            "×",
            cls="absolute top-1 right-1 w-5 h-5 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center font-bold leading-none",
            title="Delete conversation",
            **{"hx-delete": f"/api/conversations/{conversation['id']}"},
            **{"hx-target": "#conversation-list"},
            **{"hx-swap": "innerHTML"},
            **{"hx-confirm": "Are you sure you want to delete this conversation? This action cannot be undone."},
            onclick="event.stopPropagation();"
        ),
        cls=cls
    )


def gaia_auth_form(is_login=True):
    """Authentication form component"""
    form_title = "Welcome Back" if is_login else "Create Account"
    submit_text = "Sign In" if is_login else "Sign Up"
    alt_text = "Don't have an account?" if is_login else "Already have an account?"
    alt_link_text = "Sign up" if is_login else "Sign in"
    alt_link_href = "/register" if is_login else "/login"
    
    return Div(
        gaia_card(
            Div(
                H1(form_title, cls="text-3xl font-bold text-white mb-2 text-center"),
                P("Experience the magic of Gaia", cls="text-slate-400 text-center mb-8"),
                
                Form(
                    Div(
                        gaia_input("email", "Email address", type="email", required=True,
                                 pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$",
                                 title="Please enter a valid email address"),
                        cls="mb-4"
                    ),
                    Div(
                        gaia_input("password", "Password", type="password", required=True,
                                 minlength="6",
                                 title="Password must be at least 6 characters"),
                        cls="mb-6"
                    ),
                    
                    gaia_button(submit_text, type="submit", cls="w-full"),
                    
                    cls="space-y-4",
                    hx_post="/auth/login" if is_login else "/auth/register",
                    hx_target="#auth-message",
                    hx_swap="innerHTML"
                ),
                
                Div(id="auth-message", cls="mt-4"),
                
                # Dev login hint for local development
                Div(
                    P(
                        "For local development, use: dev@gaia.local / test",
                        cls="text-xs text-slate-500 text-center italic"
                    ),
                    P(
                        "Note: Registration may require a valid email domain",
                        cls="text-xs text-slate-500 text-center italic mt-1"
                    ) if not is_login else "",
                    cls="mt-2"
                ) if is_login or not is_login else "",
                
                Div(
                    P(
                        alt_text,
                        A(alt_link_text, href=alt_link_href, cls="text-purple-400 hover:text-purple-300 ml-1"),
                        cls="text-sm text-slate-400 text-center"
                    ),
                    cls="mt-6"
                ),
                cls="w-full max-w-md"
            )
        ),
        cls="min-h-screen flex items-center justify-center p-4"
    )


def gaia_chat_input(conversation_id=None):
    """Compact chat input component matching modern interfaces"""
    return Form(
        Div(
            Input(
                name="message",
                type="text",
                placeholder="Message Gaia...",
                cls="flex-1 bg-slate-800 border border-slate-600 text-white placeholder-slate-500 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all duration-300",
                autofocus=True,
                required=True,
                id="chat-message-input",
                onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();this.form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}"
            ),
            # Hidden input for conversation ID (always include it)
            Input(
                type="hidden",
                name="conversation_id",
                value=conversation_id or "",
                id="conversation-id-input"
            ),
            Button(
                "Send",
                type="submit",
                cls="ml-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white text-xs font-medium py-2 px-3 rounded-lg transition-all duration-300 hover:shadow-md active:scale-95",
                id="chat-send-button"
            ),
            cls="flex items-center"
        ),
        cls="p-3 border-t border-slate-700/50 backdrop-blur-sm",
        id="chat-form",
        hx_post="/api/chat/send",
        hx_target="#messages",
        hx_swap="beforeend",
        hx_disabled_elt="#chat-send-button, #chat-message-input"
    )


def gaia_layout(sidebar_content=None, main_content=None, page_class="", show_sidebar=True, user=None):
    """Main layout component"""
    if show_sidebar:
        return Div(
            # Hidden loading indicator (outside main-content so it doesn't get replaced)
            # Loading indicator with HTMX classes
            Div(
                gaia_loading_spinner(size="large"),
                id="loading-indicator",
                cls="htmx-indicator fixed inset-0 bg-black/50 z-50 items-center justify-center",
                style="display: none;"
            ),
            # Sidebar
            Div(
                gaia_sidebar_header(user=user),
                Div(
                    sidebar_content or "",
                    cls="p-2 overflow-y-auto flex-1"
                ),
                cls=f"w-64 {GaiaDesign.BG_SIDEBAR} flex flex-col h-screen"
            ),
            
            # Main content area
            Div(
                main_content or "",
                id="main-content",
                cls="flex-1 flex flex-col h-screen overflow-hidden"
            ),
            
            cls=f"flex h-screen {GaiaDesign.BG_MAIN} {page_class}"
        )
    else:
        # No sidebar layout for auth pages
        return Div(
            main_content or "",
            cls=f"h-screen {GaiaDesign.BG_MAIN} {page_class}"
        )


def gaia_loading_spinner(size="large", message="Loading..."):
    """Enhanced loading spinner component"""
    if size == "small":
        spinner_cls = "w-6 h-6 border-2"
        container_cls = "flex justify-center items-center p-2"
    else:
        spinner_cls = "w-12 h-12 border-4"
        container_cls = "flex flex-col justify-center items-center p-8 space-y-4"
    
    content = [
        Div(cls=f"{spinner_cls} border-purple-400 border-t-transparent rounded-full animate-spin")
    ]
    
    if size == "large" and message:
        content.append(
            Div(message, cls="text-slate-400 text-sm animate-pulse")
        )
    
    return Div(*content, cls=container_cls, id="loading-indicator")


def gaia_error_message(message):
    """Error message component"""
    return Div(
        Div(
            f"⚠️ {message}",
            cls="flex items-center space-x-2"
        ),
        cls="bg-red-500/10 backdrop-blur-sm border border-red-500/30 text-red-200 px-4 py-3 rounded-lg shadow-lg"
    )


def gaia_success_message(message):
    """Success message component"""
    return Div(
        Div(
            f"✓ {message}",
            cls="flex items-center space-x-2"
        ),
        cls="bg-green-500/10 backdrop-blur-sm border border-green-500/30 text-green-200 px-4 py-3 rounded-lg shadow-lg"
    )


def gaia_info_message(message):
    """Info message component"""
    return Div(
        Div(
            f"ℹ️ {message}",
            cls="flex items-center space-x-2"
        ),
        cls="bg-purple-500/10 backdrop-blur-sm border border-purple-500/30 text-purple-200 px-4 py-3 rounded-lg shadow-lg"
    )


def gaia_email_verification_notice(email: str):
    """Email verification notice component"""
    return gaia_card(
        Div(
            Div(
                "📧 Check Your Email",
                cls="text-2xl font-semibold text-white mb-4 text-center"
            ),
            Div(
                f"We've sent a verification link to:",
                cls="text-slate-300 text-center mb-2"
            ),
            Div(
                email,
                cls="text-purple-400 font-semibold text-center mb-6"
            ),
            Div(
                "Please check your email and click the verification link to activate your account.",
                cls="text-slate-300 text-center mb-8"
            ),
            Div(
                "Didn't receive the email? ",
                A(
                    "Resend verification email",
                    href="#",
                    cls="text-purple-400 hover:text-purple-300 underline transition-colors",
                    hx_post="/auth/resend-verification",
                    hx_vals=f'{{"email": "{email}"}}',
                    hx_target="#message-area",
                    hx_swap="innerHTML"
                ),
                cls="text-sm text-slate-400 text-center"
            ),
            cls="max-w-md mx-auto"
        ),
        title=None
    )


def gaia_email_confirmed_success():
    """Email confirmation success component"""
    return gaia_card(
        Div(
            Div(
                "✅ Email Verified!",
                cls="text-2xl font-semibold text-green-400 mb-4 text-center"
            ),
            Div(
                "Your email has been successfully verified. You can now log in to your account.",
                cls="text-slate-300 text-center mb-6"
            ),
            A(
                "Continue to Login",
                href="/login",
                cls="inline-block bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all transform hover:scale-105 shadow-lg"
            ),
            cls="max-w-md mx-auto text-center"
        ),
        title=None
    )


def gaia_email_not_verified_notice():
    """Notice shown when user tries to login with unverified email"""
    return gaia_error_message(
        "Please verify your email address before logging in. Check your email for the verification link."
    )


def gaia_profile_page(user, stats=None):
    """User profile page component"""
    stats = stats or {"total_conversations": 0, "total_messages": 0}
    
    return gaia_layout(
        main_content=Div(
            # Header
            Div(
                H1("Profile Settings", cls="text-2xl font-bold text-white mb-2"),
                P("Manage your account and preferences", cls="text-slate-400 mb-6"),
                cls="p-6 border-b border-slate-700/50"
            ),
            
            # Main content
            Div(
                # Left column - Profile info
                Div(
                    gaia_card(
                        Div(
                            # Avatar section
                            Div(
                                Div(
                                    Span("👤", cls="text-4xl"),
                                    cls="w-20 h-20 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center mb-4"
                                ),
                                H2(user.get('name', 'User'), cls="text-xl font-semibold text-white mb-1"),
                                P(user.get('email', ''), cls="text-slate-400 mb-4"),
                                cls="text-center"
                            ),
                            
                            # Stats
                            Div(
                                H2("Usage Statistics", cls="text-lg font-semibold text-white mb-3"),
                                Div(
                                    Div(
                                        Div(str(stats['total_conversations']), cls="text-2xl font-bold text-purple-400"),
                                        Div("Conversations", cls="text-xs text-slate-400"),
                                        cls="text-center"
                                    ),
                                    Div(
                                        Div(str(stats['total_messages']), cls="text-2xl font-bold text-pink-400"),
                                        Div("Messages", cls="text-xs text-slate-400"),
                                        cls="text-center"
                                    ),
                                    cls="grid grid-cols-2 gap-4"
                                ),
                                cls="border-t border-slate-600 pt-4"
                            ),
                            cls="space-y-4"
                        ),
                        title="Account Information"
                    ),
                    cls="space-y-6"
                ),
                
                # Right column - Settings
                Div(
                    # Account settings
                    gaia_card(
                        Div(
                            Form(
                                Div(
                                    gaia_input("name", "Display Name", value=user.get('name', ''), required=True),
                                    cls="mb-4"
                                ),
                                Div(
                                    gaia_input("email", "Email Address", type="email", value=user.get('email', ''), required=True),
                                    cls="mb-4"
                                ),
                                gaia_button("Update Profile", type="submit", cls="w-full"),
                                cls="space-y-4",
                                **{"hx-post": "/api/profile/update"},
                                **{"hx-target": "#profile-message"},
                                **{"hx-swap": "innerHTML"}
                            ),
                            Div(id="profile-message", cls="mt-4"),
                            cls="space-y-4"
                        ),
                        title="Account Settings"
                    ),
                    
                    # Back to chat button
                    Div(
                        A(
                            "← Back to Chat",
                            href="/chat",
                            cls="inline-flex items-center text-purple-400 hover:text-purple-300 transition-colors"
                        ),
                        cls="mt-6 text-center"
                    ),
                    cls="space-y-6"
                ),
                cls="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6"
            ),
            cls="flex-1 overflow-y-auto"
        ),
        show_sidebar=False,
        user=user
    )


def gaia_toast(message, type="info", duration=3000):
    """
    Toast notification component
    type: 'success', 'error', 'warning', 'info'
    duration: milliseconds to show toast
    """
    # Color schemes for different types
    colors = {
        "success": "bg-green-600",
        "error": "bg-red-600", 
        "warning": "bg-yellow-600",
        "info": "bg-purple-600"
    }
    
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    bg_color = colors.get(type, colors["info"])
    icon = icons.get(type, icons["info"])
    
    import uuid
    toast_id = f"toast-{str(uuid.uuid4())[:8]}"
    
    return Div(
        Div(
            Span(icon, cls="mr-2 text-lg"),
            Span(message),
            cls=f"{bg_color} text-white px-4 py-3 rounded-lg shadow-xl flex items-center"
        ),
        id=toast_id,
        cls="fixed top-4 right-4 z-50 animate-slideInRight",
        # Auto-remove after duration
        _=f"setTimeout(() => {{ document.getElementById('{toast_id}').remove(); }}, {duration});"
    )
