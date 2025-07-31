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
    """Chat message bubble component with entrance animations"""
    bubble_cls = GaiaDesign.MSG_USER if role == "user" else GaiaDesign.MSG_ASSISTANT
    
    # Add animation classes based on role
    animation_cls = "animate-slideInRight" if role == "user" else "animate-slideInLeft"
    
    children = [
        Div(content, cls="whitespace-pre-wrap break-words")
    ]
    
    if timestamp:
        children.append(
            Div(timestamp, cls="text-xs opacity-70 mt-1")
        )
    
    return Div(
        Div(*children, cls=f"{bubble_cls} {animation_cls}"),
        cls=f"flex {'justify-end' if role == 'user' else 'justify-start'} mb-4"
    )


def gaia_sidebar_header(user=None, mobile=False):
    """Compact sidebar header matching modern chat interfaces"""
    return Div(
        # Close button for mobile (top-right of sidebar)
        Div(
            Button(
                "×",
                cls="absolute top-3 right-3 text-white hover:text-gray-300 text-xl font-bold w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 transition-colors",
                onclick="toggleSidebar()",
                title="Close sidebar"
            ),
            cls="md:hidden relative"
        ) if mobile else "",
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
        # Search input - simplified version
        Div(
            Input(
                type="text",
                placeholder="Search conversations...",
                cls="w-full bg-slate-800 border border-slate-600 text-white placeholder-slate-400 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all duration-300",
                name="query",
                id="search-input"
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
                
                # Wrap the form in a container for proper HTMX replacement
                Div(
                    Form(
                        Div(
                            gaia_input("email", "Email address", type="email", required=True,
                                     pattern="[a-z0-9._%+\\-]+@[a-z0-9.\\-]+\\.[a-z]{2,}$",
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
                        hx_target="#auth-form-container", 
                        hx_swap="outerHTML"
                    ),
                    id="auth-form-container"
                ),
                
                # Dev login hint for local development (only show in debug mode)
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
                ) if False else "",  # Always hidden in production - remove dev hints
                
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
    """Compact chat input component matching modern interfaces with mobile responsiveness"""
    return Form(
        Div(
            # Input wrapper with better mobile sizing
            Div(
                Input(
                    name="message",
                    type="text",
                    placeholder="Message Gaia...",
                    cls="w-full bg-slate-800 border border-slate-600 text-white placeholder-slate-500 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all duration-300 resize-none",
                    autofocus=True,
                    required=True,
                    id="chat-message-input",
                    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();this.form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}"
                ),
                cls="flex-1 min-w-0"  # min-w-0 allows input to shrink properly
            ),
            # Hidden input for conversation ID (always include it)
            Input(
                type="hidden",
                name="conversation_id",
                value=conversation_id or "",
                id="conversation-id-input"
            ),
            # Send button with mobile-friendly sizing
            Button(
                Span("Send", cls="hidden sm:inline"),  # Hide text on very small screens
                Span("→", cls="sm:hidden text-lg"),  # Show arrow on mobile
                type="submit",
                cls="ml-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-medium py-2.5 px-3 sm:px-4 rounded-lg transition-all duration-300 hover:shadow-md active:scale-95 flex items-center justify-center min-w-[44px]",
                id="chat-send-button",
                title="Send message"
            ),
            cls="flex items-end gap-2 md:gap-3"
        ),
        cls="p-3 md:p-4 border-t border-slate-700/50 backdrop-blur-sm safe-area-padding-bottom",
        id="chat-form",
        hx_post="/api/chat/send",
        hx_target="#messages",
        hx_swap="beforeend",
        hx_disabled_elt="#chat-send-button, #chat-message-input"
    )


def gaia_layout(sidebar_content=None, main_content=None, page_class="", show_sidebar=True, user=None):
    """Main layout component with mobile-responsive sidebar"""
    from fasthtml.core import Script, NotStr
    
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
            # Toast container for notifications
            Div(
                id="toast-container",
                cls="fixed top-4 right-4 z-50 space-y-2"
            ),
            # Global toast utility script
            Script(NotStr('''
                window.GaiaToast = {
                    show: function(message, variant = 'info', duration = 3000) {
                        const toastContainer = document.getElementById('toast-container');
                        if (!toastContainer) return;
                        
                        const toastId = 'toast-' + Date.now();
                        const variants = {
                            success: { icon: '✓', bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-200' },
                            error: { icon: '⚠️', bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-200' },
                            info: { icon: 'ℹ️', bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-200' },
                            warning: { icon: '⚡', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-200' }
                        };
                        
                        const v = variants[variant] || variants.info;
                        
                        const toast = document.createElement('div');
                        toast.id = toastId;
                        toast.className = 'transition-all duration-300 transform animate-slideInFromTop mb-2';
                        toast.innerHTML = `
                            <div class="flex items-center justify-between ${v.bg} backdrop-blur-sm border ${v.border} ${v.text} px-4 py-3 rounded-lg shadow-lg min-w-[300px]">
                                <div class="flex items-center space-x-2">
                                    ${v.icon} ${message}
                                </div>
                                <button class="ml-4 text-xl leading-none hover:opacity-70" onclick="document.getElementById('${toastId}').remove()">×</button>
                            </div>
                        `;
                        
                        toastContainer.appendChild(toast);
                        
                        setTimeout(() => {
                            const el = document.getElementById(toastId);
                            if (el) {
                                el.style.opacity = '0';
                                el.style.transform = 'translateX(100%)';
                                setTimeout(() => el.remove(), 300);
                            }
                        }, duration);
                    },
                    success: function(message, duration) {
                        this.show(message, 'success', duration);
                    },
                    error: function(message, duration) {
                        this.show(message, 'error', duration);
                    },
                    info: function(message, duration) {
                        this.show(message, 'info', duration);
                    },
                    warning: function(message, duration) {
                        this.show(message, 'warning', duration);
                    }
                };
            ''')),
            # Mobile overlay for sidebar (only visible when sidebar is open on mobile)
            Div(
                id="sidebar-overlay",
                cls="fixed inset-0 bg-black/50 z-30 md:hidden",
                style="display: none;",
                onclick="toggleSidebar()"
            ),
            # Mobile header with hamburger menu
            Div(
                Div(
                    # Hamburger button
                    Button(
                        Div(
                            Div(cls="w-6 h-0.5 bg-white transition-all duration-300"),
                            Div(cls="w-6 h-0.5 bg-white transition-all duration-300 mt-1.5"),
                            Div(cls="w-6 h-0.5 bg-white transition-all duration-300 mt-1.5"),
                            cls="hamburger-lines"
                        ),
                        id="sidebar-toggle",
                        cls="p-2 text-white hover:bg-white/10 rounded-lg transition-colors md:hidden",
                        onclick="toggleSidebar()",
                        title="Toggle sidebar"
                    ),
                    # Mobile logo
                    Div(
                        gaia_logo(with_text=True),
                        cls="md:hidden"
                    ),
                    # User avatar/menu for mobile
                    Div(
                        Button(
                            user.get('email', 'U')[0].upper() if user else 'U',
                            cls="w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center text-white text-sm font-medium hover:scale-105 transition-transform",
                            onclick="toggleUserMenu()",
                            title="User menu"
                        ),
                        # User dropdown menu
                        Div(
                            Div(
                                user.get('email', 'dev@gaia.local') if user else 'User',
                                cls="px-4 py-2 text-xs text-slate-400 border-b border-slate-700"
                            ),
                            A(
                                "Profile",
                                href="/profile",
                                cls="block px-4 py-2 text-sm text-white hover:bg-slate-700 transition-colors",
                                onclick="document.getElementById('user-menu').style.display='none'"
                            ),
                            A(
                                "Logout",
                                href="/logout",
                                cls="block px-4 py-2 text-sm text-white hover:bg-slate-700 transition-colors",
                                onclick="window.location.href='/logout'; return false;"
                            ),
                            id="user-menu",
                            cls="absolute right-0 top-10 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden",
                            style="display: none;"
                        ),
                        cls="md:hidden relative"
                    ),
                    cls="flex items-center justify-between px-4 py-3"
                ),
                cls=f"md:hidden mobile-header {GaiaDesign.BG_SIDEBAR} border-b border-slate-700/50"
            ),
            # Sidebar - responsive positioning
            Div(
                gaia_sidebar_header(user=user, mobile=True),
                Div(
                    sidebar_content or "",
                    cls="p-2 overflow-y-auto flex-1"
                ),
                id="sidebar",
                cls=f"fixed md:relative top-0 left-0 z-40 w-64 {GaiaDesign.BG_SIDEBAR} flex flex-col h-screen transform -translate-x-full md:translate-x-0 transition-transform duration-300 ease-in-out"
            ),
            
            # Main content area - responsive margins
            Div(
                main_content or "",
                id="main-content",
                cls="flex-1 flex flex-col overflow-hidden"
            ),
            
            gaia_mobile_sidebar_script(),
            
            cls=f"flex h-screen {GaiaDesign.BG_MAIN} {page_class}"
        )
    else:
        # No sidebar layout for auth pages
        return Div(
            # Toast container for auth pages too
            Div(
                id="toast-container",
                cls="fixed top-4 right-4 z-50 space-y-2"
            ),
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


def gaia_toast(message, variant="info", duration=3000):
    """Toast notification component with auto-dismiss"""
    from fasthtml.core import Script, NotStr
    import time
    
    toast_id = f"toast-{int(time.time() * 1000)}"
    
    # Choose icon and colors based on variant
    variants = {
        "success": {
            "icon": "✓",
            "bg": "bg-green-500/10",
            "border": "border-green-500/30",
            "text": "text-green-200"
        },
        "error": {
            "icon": "⚠️",
            "bg": "bg-red-500/10",
            "border": "border-red-500/30",
            "text": "text-red-200"
        },
        "info": {
            "icon": "ℹ️",
            "bg": "bg-purple-500/10",
            "border": "border-purple-500/30",
            "text": "text-purple-200"
        },
        "warning": {
            "icon": "⚡",
            "bg": "bg-yellow-500/10",
            "border": "border-yellow-500/30",
            "text": "text-yellow-200"
        }
    }
    
    v = variants.get(variant, variants["info"])
    
    return Div(
        Div(
            Div(
                f"{v['icon']} {message}",
                cls="flex items-center space-x-2"
            ),
            Button(
                "×",
                cls="ml-4 text-xl leading-none hover:opacity-70",
                onclick=f"document.getElementById('{toast_id}').remove()"
            ),
            cls=f"flex items-center justify-between {v['bg']} backdrop-blur-sm border {v['border']} {v['text']} px-4 py-3 rounded-lg shadow-lg min-w-[300px]"
        ),
        Script(NotStr(f'''
            setTimeout(() => {{
                const toast = document.getElementById('{toast_id}');
                if (toast) {{
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateX(100%)';
                    setTimeout(() => toast.remove(), 300);
                }}
            }}, {duration});
        ''')),
        id=toast_id,
        cls="transition-all duration-300 transform animate-slideInFromTop",
        style="animation: slideInFromTop 0.3s ease-out forwards;"
    )


def gaia_show_toast_script(message, variant="info", duration=3000):
    """Generate script to show a toast notification"""
    from fasthtml.core import Script, NotStr
    
    return Script(NotStr(f'''
        (function() {{
            const toastContainer = document.getElementById('toast-container');
            if (!toastContainer) return;
            
            const toastId = 'toast-' + Date.now();
            const variants = {{
                success: {{ icon: '✓', bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-200' }},
                error: {{ icon: '⚠️', bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-200' }},
                info: {{ icon: 'ℹ️', bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-200' }},
                warning: {{ icon: '⚡', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-200' }}
            }};
            
            const v = variants['{variant}'] || variants.info;
            
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = 'transition-all duration-300 transform animate-slideInFromTop mb-2';
            toast.innerHTML = `
                <div class="flex items-center justify-between ${{v.bg}} backdrop-blur-sm border ${{v.border}} ${{v.text}} px-4 py-3 rounded-lg shadow-lg min-w-[300px]">
                    <div class="flex items-center space-x-2">
                        ${{v.icon}} {message}
                    </div>
                    <button class="ml-4 text-xl leading-none hover:opacity-70" onclick="document.getElementById('${{toastId}}').remove()">×</button>
                </div>
            `;
            
            toastContainer.appendChild(toast);
            
            setTimeout(() => {{
                if (document.getElementById(toastId)) {{
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateX(100%)';
                    setTimeout(() => toast.remove(), 300);
                }}
            }}, {duration});
        }})();
    '''))


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


def gaia_toast(message, type="info", duration=3000, dismissible=True):
    """
    Enhanced toast notification component
    type: 'success', 'error', 'warning', 'info'
    duration: milliseconds to show toast (0 = manual dismiss)
    dismissible: whether to show close button
    """
    # Color schemes for different types
    colors = {
        "success": "bg-gradient-to-r from-green-600 to-green-700",
        "error": "bg-gradient-to-r from-red-600 to-red-700", 
        "warning": "bg-gradient-to-r from-yellow-600 to-yellow-700",
        "info": "bg-gradient-to-r from-purple-600 to-purple-700"
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
    
    # Auto-dismiss script
    auto_dismiss = ""
    if duration > 0:
        auto_dismiss = f"setTimeout(() => {{ const toast = document.getElementById('{toast_id}'); if(toast) toast.remove(); }}, {duration});"
    
    # Close button
    close_button = ""
    if dismissible:
        close_button = f'''
            <button onclick="document.getElementById('{toast_id}').remove()" 
                    class="ml-3 text-white hover:text-gray-200 font-bold text-lg leading-none"
                    title="Dismiss">×</button>
        '''
    
    from fasthtml.core import Script, NotStr
    
    return Div(
        Div(
            Span(icon, cls="mr-2 text-lg"),
            Span(message, cls="flex-1"),
            NotStr(close_button) if dismissible else "",
            cls=f"{bg_color} text-white px-4 py-3 rounded-lg shadow-xl flex items-center min-w-[300px] max-w-[500px]"
        ),
        Script(NotStr(auto_dismiss)) if duration > 0 else "",
        id=toast_id,
        cls="fixed top-4 right-4 z-50 animate-slideInRight transform transition-all duration-300 hover:scale-105"
    )


def gaia_error_toast(message, details=None, retry_action=None):
    """
    Specialized error toast with optional retry button
    """
    import uuid
    toast_id = f"error-toast-{str(uuid.uuid4())[:8]}"
    
    # Retry button if action provided
    retry_button = ""
    if retry_action:
        retry_button = f'''
            <button onclick="{retry_action}" 
                    class="ml-2 px-3 py-1 bg-white bg-opacity-20 hover:bg-opacity-30 rounded text-sm font-medium transition-all duration-200">
                Retry
            </button>
        '''
    
    # Details toggle if provided
    details_content = ""
    if details:
        details_content = f'''
            <div id="{toast_id}-details" class="mt-2 text-xs text-red-100 bg-black bg-opacity-20 p-2 rounded" style="display: none;">
                {details}
            </div>
            <button onclick="
                const details = document.getElementById('{toast_id}-details');
                const btn = this;
                if (details.style.display === 'none') {{
                    details.style.display = 'block';
                    btn.textContent = 'Hide Details';
                }} else {{
                    details.style.display = 'none';
                    btn.textContent = 'Show Details';
                }}
            " class="ml-2 text-xs text-red-200 hover:text-white underline">Show Details</button>
        '''
    
    from fasthtml.core import Script, NotStr
    
    return Div(
        Div(
            Div(
                Span("❌", cls="mr-2 text-lg"),
                Span(message, cls="flex-1"),
                NotStr(retry_button),
                Button(
                    "×",
                    onclick=f"document.getElementById('{toast_id}').remove()",
                    cls="ml-2 text-white hover:text-gray-200 font-bold text-lg leading-none",
                    title="Dismiss"
                ),
                cls="flex items-center"
            ),
            NotStr(details_content),
            cls="bg-gradient-to-r from-red-600 to-red-700 text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px]"
        ),
        id=toast_id,
        cls="fixed top-4 right-4 z-50 animate-slideInRight transform transition-all duration-300"
    )


def gaia_loading_toast(message="Loading...", timeout_ms=30000):
    """
    Loading toast that auto-converts to error if timeout exceeded
    """
    import uuid
    toast_id = f"loading-toast-{str(uuid.uuid4())[:8]}"
    
    from fasthtml.core import Script, NotStr
    
    timeout_script = NotStr(f'''
        setTimeout(() => {{
            const toast = document.getElementById('{toast_id}');
            if (toast) {{
                toast.innerHTML = `
                    <div class="bg-gradient-to-r from-yellow-600 to-yellow-700 text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px]">
                        <div class="flex items-center">
                            <span class="mr-2 text-lg">⚠️</span>
                            <span class="flex-1">Request is taking longer than expected...</span>
                            <button onclick="this.closest('[id]').remove()" 
                                    class="ml-2 text-white hover:text-gray-200 font-bold text-lg leading-none"
                                    title="Dismiss">×</button>
                        </div>
                    </div>
                `;
                toast.className = toast.className.replace('animate-pulse', '');
            }}
        }}, {timeout_ms});
    ''')
    
    return Div(
        Div(
            Span("⏳", cls="mr-2 text-lg animate-pulse"),
            Span(message, cls="flex-1"),
            cls="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px] flex items-center"
        ),
        Script(timeout_script),
        id=toast_id,
        cls="fixed top-4 right-4 z-50 animate-slideInRight"
    )


def gaia_toast_script():
    """
    JavaScript helper functions for toast management
    """
    from fasthtml.core import Script, NotStr
    
    return Script(NotStr('''
        // Global toast management system
        window.GaiaToast = {
            // Show a toast notification
            show: function(message, type = 'info', duration = 3000) {
                const toastId = 'toast-' + Math.random().toString(36).substr(2, 9);
                const colors = {
                    success: 'from-green-600 to-green-700',
                    error: 'from-red-600 to-red-700',
                    warning: 'from-yellow-600 to-yellow-700',
                    info: 'from-purple-600 to-purple-700'
                };
                const icons = {
                    success: '✅',
                    error: '❌',
                    warning: '⚠️',
                    info: 'ℹ️'
                };
                
                const color = colors[type] || colors.info;
                const icon = icons[type] || icons.info;
                
                const toast = document.createElement('div');
                toast.id = toastId;
                toast.className = 'bg-gradient-to-r ' + color + ' text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px] animate-slideInRight transform transition-all duration-300 hover:scale-105 mb-2';
                toast.innerHTML = `
                    <div class="flex items-center">
                        <span class="mr-2 text-lg">${icon}</span>
                        <span class="flex-1">${message}</span>
                        <button onclick="this.closest('[id]').remove()" 
                                class="ml-3 text-white hover:text-gray-200 font-bold text-lg leading-none"
                                title="Dismiss">×</button>
                    </div>
                `;
                
                const container = document.getElementById('toast-container');
                if (container) {
                    container.appendChild(toast);
                } else {
                    document.body.appendChild(toast);
                }
                
                // Auto-dismiss if duration > 0
                if (duration > 0) {
                    setTimeout(() => {
                        if (document.getElementById(toastId)) {
                            document.getElementById(toastId).remove();
                        }
                    }, duration);
                }
                
                return toastId;
            },
            
            // Show success toast
            success: function(message, duration = 3000) {
                return this.show(message, 'success', duration);
            },
            
            // Show error toast
            error: function(message, duration = 5000) {
                return this.show(message, 'error', duration);
            },
            
            // Show warning toast
            warning: function(message, duration = 4000) {
                return this.show(message, 'warning', duration);
            },
            
            // Show info toast
            info: function(message, duration = 3000) {
                return this.show(message, 'info', duration);
            },
            
            // Show loading toast
            loading: function(message = 'Loading...', timeoutMs = 30000) {
                const toastId = 'loading-toast-' + Math.random().toString(36).substr(2, 9);
                const toast = document.createElement('div');
                toast.id = toastId;
                toast.className = 'bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px] animate-slideInRight mb-2';
                toast.innerHTML = `
                    <div class="flex items-center">
                        <span class="mr-2 text-lg animate-pulse">⏳</span>
                        <span class="flex-1">${message}</span>
                    </div>
                `;
                
                const container = document.getElementById('toast-container');
                if (container) {
                    container.appendChild(toast);
                } else {
                    document.body.appendChild(toast);
                }
                
                // Convert to warning after timeout
                setTimeout(() => {
                    const loadingToast = document.getElementById(toastId);
                    if (loadingToast) {
                        loadingToast.className = 'bg-gradient-to-r from-yellow-600 to-yellow-700 text-white px-4 py-3 rounded-lg shadow-xl min-w-[300px] max-w-[500px] mb-2';
                        loadingToast.innerHTML = `
                            <div class="flex items-center">
                                <span class="mr-2 text-lg">⚠️</span>
                                <span class="flex-1">Request is taking longer than expected...</span>
                                <button onclick="this.closest('[id]').remove()" 
                                        class="ml-2 text-white hover:text-gray-200 font-bold text-lg leading-none"
                                        title="Dismiss">×</button>
                            </div>
                        `;
                    }
                }, timeoutMs);
                
                return toastId;
            },
            
            // Hide specific toast
            hide: function(toastId) {
                const toast = document.getElementById(toastId);
                if (toast) {
                    toast.remove();
                }
            },
            
            // Clear all toasts
            clear: function() {
                const container = document.getElementById('toast-container');
                if (container) {
                    container.innerHTML = '';
                }
            }
        };
        
        // Enhanced HTMX error handling
        document.body.addEventListener('htmx:responseError', function(evt) {
            console.error('[HTMX] Response Error:', evt.detail);
            const status = evt.detail.xhr.status;
            let message = 'Request failed';
            
            if (status === 0) {
                message = 'Connection lost. Please check your internet.';
            } else if (status === 400) {
                message = 'Invalid request. Please try again.';
            } else if (status === 401) {
                message = 'Please log in again.';
            } else if (status === 403) {
                message = 'Access denied.';
            } else if (status === 404) {
                message = 'Requested resource not found.';
            } else if (status === 429) {
                message = 'Too many requests. Please wait a moment.';
            } else if (status >= 500) {
                message = 'Server error. Please try again later.';
            }
            
            GaiaToast.error(message);
        });
        
        document.body.addEventListener('htmx:timeout', function(evt) {
            console.error('[HTMX] Timeout:', evt.detail);
            GaiaToast.error('Request timed out. Please try again.');
        });
        
        document.body.addEventListener('htmx:sendError', function(evt) {
            console.error('[HTMX] Send Error:', evt.detail);
            GaiaToast.error('Failed to send request. Please check your connection.');
        });
    '''))


def gaia_mobile_sidebar_script():
    """
    JavaScript for mobile sidebar toggle functionality
    """
    from fasthtml.core import Script, NotStr
    
    return Script(NotStr('''
        // Mobile sidebar toggle functionality
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            const hamburger = document.getElementById('sidebar-toggle');
            
            if (!sidebar) return;
            
            const isOpen = !sidebar.classList.contains('-translate-x-full');
            
            if (isOpen) {
                // Close sidebar
                sidebar.classList.add('-translate-x-full');
                if (overlay) overlay.style.display = 'none';
                if (hamburger) hamburger.classList.remove('active');
                document.body.style.overflow = '';
            } else {
                // Open sidebar
                sidebar.classList.remove('-translate-x-full');
                if (overlay) overlay.style.display = 'block';
                if (hamburger) hamburger.classList.add('active');
                // Prevent background scrolling on mobile
                document.body.style.overflow = 'hidden';
            }
        }
        
        // User menu toggle functionality
        function toggleUserMenu() {
            const userMenu = document.getElementById('user-menu');
            if (!userMenu) return;
            
            const isVisible = userMenu.style.display === 'block';
            userMenu.style.display = isVisible ? 'none' : 'block';
        }
        
        // Close user menu when clicking outside
        document.addEventListener('click', function(e) {
            const userMenu = document.getElementById('user-menu');
            const userButton = e.target.closest('[onclick*="toggleUserMenu"]');
            
            if (userMenu && !userButton && !userMenu.contains(e.target)) {
                userMenu.style.display = 'none';
            }
        });
        
        // Auto-close sidebar when clicking on main content links (mobile)
        document.addEventListener('click', function(e) {
            // Check if we're on mobile (sidebar is positioned fixed)
            const sidebar = document.getElementById('sidebar');
            if (!sidebar || window.innerWidth >= 768) return;
            
            // Check if clicked element is a link or button that would navigate/change content
            const target = e.target.closest('a, button[hx-get], button[hx-post]');
            if (target && !sidebar.contains(target) && !target.closest('#sidebar-toggle')) {
                // Close sidebar after a short delay to allow the action to process
                setTimeout(() => {
                    toggleSidebar();
                }, 100);
            }
        });
        
        // Handle window resize - close sidebar on desktop, reset overflow
        window.addEventListener('resize', function() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            
            if (window.innerWidth >= 768) {
                // Desktop view - reset sidebar state
                if (sidebar) sidebar.classList.remove('-translate-x-full');
                if (overlay) overlay.style.display = 'none';
                document.body.style.overflow = '';
            }
        });
        
        // Enhanced hamburger animation
        document.addEventListener('DOMContentLoaded', function() {
            const hamburger = document.getElementById('sidebar-toggle');
            if (hamburger) {
                // Add CSS for hamburger animation
                const style = document.createElement('style');
                style.textContent = `
                    .hamburger-lines div:nth-child(1) {
                        transform-origin: center;
                    }
                    .hamburger-lines div:nth-child(2) {
                        transform-origin: center;
                    }
                    .hamburger-lines div:nth-child(3) {
                        transform-origin: center;
                    }
                    
                    #sidebar-toggle.active .hamburger-lines div:nth-child(1) {
                        transform: rotate(45deg) translate(6px, 6px);
                    }
                    #sidebar-toggle.active .hamburger-lines div:nth-child(2) {
                        opacity: 0;
                    }
                    #sidebar-toggle.active .hamburger-lines div:nth-child(3) {
                        transform: rotate(-45deg) translate(6px, -6px);
                    }
                `;
                document.head.appendChild(style);
            }
        });
        
        // Swipe gesture support for mobile
        let startX = 0;
        let startY = 0;
        let isSwipe = false;
        
        document.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isSwipe = true;
        }, { passive: true });
        
        document.addEventListener('touchmove', function(e) {
            if (!isSwipe) return;
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const diffX = currentX - startX;
            const diffY = currentY - startY;
            
            // Check if it's more horizontal than vertical movement
            if (Math.abs(diffX) < Math.abs(diffY)) {
                isSwipe = false;
                return;
            }
        }, { passive: true });
        
        document.addEventListener('touchend', function(e) {
            if (!isSwipe || window.innerWidth >= 768) return;
            
            const endX = e.changedTouches[0].clientX;
            const diffX = endX - startX;
            const sidebar = document.getElementById('sidebar');
            
            if (!sidebar) return;
            
            const isOpen = !sidebar.classList.contains('-translate-x-full');
            
            // Right swipe to open (from left edge)
            if (!isOpen && startX < 20 && diffX > 50) {
                toggleSidebar();
            }
            // Left swipe to close (when sidebar is open)
            else if (isOpen && diffX < -50) {
                toggleSidebar();
            }
            
            isSwipe = false;
        }, { passive: true });
    '''))


def gaia_mobile_styles():
    """
    CSS styles for mobile responsiveness and safe areas
    """
    from fasthtml.core import Style, NotStr
    
    return Style(NotStr('''
        /* Mobile-specific styles */
        @media (max-width: 768px) {
            /* Ensure mobile viewport is properly handled */
            html, body {
                overflow-x: hidden;
                -webkit-overflow-scrolling: touch;
            }
            
            /* Fix mobile layout structure - simpler approach */
            .mobile-header {
                height: 4rem !important;
                flex-shrink: 0 !important;
                width: 100% !important;
            }
            
            /* Main content takes remaining space */
            #main-content {
                flex: 1 !important;
                min-height: 0 !important;
                overflow: hidden !important;
            }
            
            /* Don't override sidebar transform - let Tailwind classes handle it */
            /* The sidebar already has -translate-x-full on mobile and md:translate-x-0 on desktop */
            
            /* Safe area support for mobile devices */
            .safe-area-padding-bottom {
                padding-bottom: calc(0.75rem + env(safe-area-inset-bottom));
            }
            
            /* Prevent zoom on input focus (iOS) */
            input[type="text"], input[type="email"], input[type="password"], textarea {
                font-size: 16px;
            }
            
            /* Touch-friendly minimum sizes */
            button, .touch-target {
                min-height: 44px;
                min-width: 44px;
            }
            
            /* Conversation items more touch-friendly on mobile */
            .conversation-item {
                min-height: 48px;
                padding: 12px;
            }
            
            /* Message bubbles more readable on mobile */
            .message-bubble {
                max-width: 85%;
                font-size: 15px;
                line-height: 1.4;
            }
            
            /* Better spacing for mobile header */
            .mobile-header {
                padding-left: env(safe-area-inset-left);
                padding-right: env(safe-area-inset-right);
            }
        }
        
        /* Tablet-specific adjustments */
        @media (min-width: 768px) and (max-width: 1024px) {
            /* Sidebar width adjustment for tablets */
            .sidebar-tablet {
                width: 280px;
            }
        }
        
        /* Enhanced focus states for accessibility */
        .focus\\:ring-purple-500\\/30:focus {
            ring-color: rgb(168 85 247 / 0.3);
        }
        
        /* Smooth transitions for sidebar */
        .sidebar-transition {
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Loading states */
        .loading-skeleton {
            background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }
        
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        /* Custom scrollbar for webkit browsers */
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-track {
            background: #1e293b;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #475569;
            border-radius: 3px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #64748b;
        }
        
        /* Animation utilities */
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideInLeft {
            from {
                transform: translateX(-100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideInUp {
            from {
                transform: translateY(20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .animate-slideInRight {
            animation: slideInRight 0.3s ease-out;
        }
        
        .animate-slideInLeft {
            animation: slideInLeft 0.3s ease-out;
        }
        
        .animate-slideInUp {
            animation: slideInUp 0.3s ease-out;
        }
        
        .animate-fadeIn {
            animation: fadeIn 0.3s ease-out;
        }
    '''))
