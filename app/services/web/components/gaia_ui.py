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
    BTN_PRIMARY = "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-3 px-6 rounded-lg shadow-lg transform transition-all duration-300 hover:scale-105 hover:shadow-xl active:scale-95"
    BTN_SECONDARY = "bg-slate-700 hover:bg-slate-600 text-white font-medium py-2 px-4 rounded-lg transition-all duration-300 hover:shadow-lg active:scale-95"
    BTN_GHOST = "text-slate-300 hover:text-white hover:bg-slate-700/50 py-2 px-4 rounded-lg transition-all duration-300 hover:shadow-md active:scale-95"
    
    # Logo
    LOGO_EMOJI = "🦋"
    LOGO_BG_SMALL = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg"
    LOGO_BG_LARGE = "bg-gradient-to-br from-purple-400 via-pink-400 to-blue-400 w-16 h-16 rounded-2xl flex items-center justify-center shadow-xl"
    
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
    emoji_size = "text-xl" if size == "small" else "text-3xl"
    
    logo = Div(
        Span(GaiaDesign.LOGO_EMOJI, cls=emoji_size),
        cls=bg_class
    )
    
    if with_text:
        return Div(
            logo,
            H1("Gaia", cls="text-2xl font-bold text-white ml-3"),
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
    """Sidebar header with logo, new chat button, and logout"""
    return Div(
        Div(
            gaia_logo(with_text=True),
            cls="mb-8"
        ),
        gaia_button(
            "New Chat",
            variant="secondary",
            cls="w-full mb-6",
            hx_post="/chat/new",
            hx_target="#main-content",
            hx_swap="innerHTML swap:0.5s settle:0.5s"
        ),
        # User info and logout
        Div(
            Div(
                user.get('email', 'User') if user else 'User',
                cls="text-sm text-slate-400 truncate mb-2"
            ),
            A(
                "Logout",
                href="/logout",
                cls="text-sm text-purple-400 hover:text-purple-300 transition-colors",
                # Force regular navigation by using onclick
                onclick="window.location.href='/logout'; return false;"
            ),
            cls="pt-4 border-t border-slate-700"
        ) if user else None,
        cls="p-6 border-b border-slate-700"
    )


def gaia_conversation_item(conversation, active=False):
    """Sidebar conversation item with enhanced animations"""
    base_cls = "block p-3 rounded-lg transition-all duration-300 truncate transform hover:scale-105 animate-slideInUp"
    active_cls = "bg-gradient-to-r from-purple-600/30 to-pink-600/30 border-l-4 border-purple-500 shadow-lg"
    hover_cls = "hover:bg-slate-700/50 hover:shadow-md"
    
    cls = f"{base_cls} {active_cls if active else hover_cls}"
    
    return A(
        Div(
            Div(
                conversation.get("title", "New Conversation"),
                cls="text-sm text-white truncate font-medium"
            ),
            Div(
                conversation.get("preview", ""),
                cls="text-xs text-slate-400 truncate mt-1 opacity-80"
            ),
            cls="space-y-1"
        ),
        href=f"/chat/{conversation['id']}",
        cls=cls,
        hx_get=f"/chat/{conversation['id']}",
        hx_target="#main-content",
        hx_swap="innerHTML swap:0.5s settle:0.5s",
        hx_indicator="#loading-indicator"
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
    """Enhanced chat input component with better UX"""
    return Form(
        Div(
            gaia_input(
                "message",
                "Type your message...",
                cls="flex-1 transition-all duration-300 focus:ring-purple-500/30",
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
            gaia_button(
                "Send",
                type="submit",
                cls="ml-3 px-6 transition-all duration-300 hover:shadow-lg",
                id="chat-send-button"
            ),
            cls="flex items-center space-x-2"
        ),
        cls="p-4 border-t border-slate-700/50 backdrop-blur-sm",
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
                    cls="p-4 overflow-y-auto flex-1"
                ),
                cls=f"w-80 {GaiaDesign.BG_SIDEBAR} flex flex-col h-screen"
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
