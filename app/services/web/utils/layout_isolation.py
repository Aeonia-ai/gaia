"""Layout isolation utilities to prevent layout bugs

This module provides standardized functions for maintaining proper layout isolation
across different page types (auth, chat, etc.) to prevent the recurring layout bugs.
"""

from typing import List, Optional, Union, Dict, Any
from fasthtml.components import Div, H1, P, A, Button
from starlette.responses import HTMLResponse

from app.services.web.components.gaia_ui import gaia_layout


def auth_page_replacement(
    title: str,
    content: Union[str, List[str]], 
    actions: Optional[List[tuple]] = None,
    show_sidebar: bool = False,
    extra_classes: str = ""
) -> Any:
    """
    Create auth content that replaces the form container via HTMX.
    
    This function creates content that replaces the #auth-form-container
    to prevent the form+verification message mixing bug.
    
    Args:
        title: Page title to display
        content: Main content (string or list of strings for paragraphs)
        actions: List of (text, url, data) tuples for action buttons/links
        show_sidebar: Should always be False for auth pages (ignored for HTMX responses)
        extra_classes: Additional CSS classes for the content container
        
    Returns:
        Div element that replaces the auth form container
        
    Example:
        return auth_page_replacement(
            title="📧 Check Your Email",
            content=["We've sent a verification link.", "Check your email."],
            actions=[("Resend", "/resend", {"email": "user@email.com"})]
        )
    """
    from fasthtml.components import Div, H1, P, Button, A
    
    # Convert content to list if string
    if isinstance(content, str):
        content = [content]
    
    # Build content divs
    content_divs = [
        P(paragraph, cls="text-slate-300 text-center mb-4") 
        for paragraph in content
    ]
    
    # Build action buttons/links
    action_elements = []
    if actions:
        for action in actions:
            text, url, data = action
            if data:
                # HTMX action with data
                action_elements.append(
                    Button(
                        text,
                        cls="text-purple-400 hover:text-purple-300 underline transition-colors",
                        hx_post=url,
                        hx_vals=str(data).replace("'", '"'),
                        hx_target="#auth-form-container",
                        hx_swap="outerHTML"
                    )
                )
            else:
                # Simple link
                action_elements.append(
                    A(
                        text,
                        href=url,
                        cls="text-purple-400 hover:text-purple-300 underline transition-colors"
                    )
                )
    
    # Return content that replaces the form container
    return Div(
        H1(title, cls="text-2xl font-bold text-white mb-6 text-center"),
        *content_divs,
        Div(
            *action_elements,
            cls="flex flex-col sm:flex-row gap-4 justify-center items-center"
        ) if action_elements else "",
        cls=f"text-center {extra_classes}",
        id="auth-form-container"  # Same ID so HTMX can replace it
    )


def chat_content_replacement(content: Any, preserve_layout: bool = True) -> Any:
    """
    Replace chat content while preserving the main layout structure.
    
    This ensures chat updates don't accidentally break the overall layout.
    
    Args:
        content: The new content to display in the chat area
        preserve_layout: Whether to maintain the existing layout structure
        
    Returns:
        Content formatted for safe HTMX replacement
    """
    
    if not preserve_layout:
        raise ValueError("Chat content replacement must preserve layout")
    
    # Wrap content in the proper chat container structure
    return Div(
        content,
        id="chat-content",  # Target for HTMX swaps
        cls="flex-1 overflow-hidden"
    )


def sidebar_content_replacement(content: Any) -> Any:
    """
    Replace sidebar content while maintaining sidebar structure.
    
    Args:
        content: The new sidebar content
        
    Returns:
        Content formatted for safe sidebar replacement
    """
    
    return Div(
        content,
        id="sidebar-content",  # Target for HTMX swaps
        cls="h-full overflow-y-auto"
    )


def safe_htmx_response(
    content: Any,
    target: str,
    swap: str = "innerHTML",
    preserve_layout_structure: bool = True
) -> Any:
    """
    Create a safe HTMX response that won't break layout.
    
    Args:
        content: Content to return
        target: HTMX target selector
        swap: HTMX swap strategy
        preserve_layout_structure: Whether to validate layout preservation
        
    Returns:
        Safe content for HTMX response
    """
    
    # Validate dangerous swap patterns
    layout_breaking_targets = [
        "#app",  # Never swap the entire app
        "body",  # Never swap the body
        ".flex.h-screen"  # Never swap the main layout container
    ]
    
    if target in layout_breaking_targets:
        raise ValueError(f"HTMX target '{target}' is layout-breaking and forbidden")
    
    # Validate auth page isolation
    if target == "#auth-container" and swap != "outerHTML":
        raise ValueError("Auth container replacement must use outerHTML swap")
    
    return content


def validate_layout_isolation(page_type: str, has_sidebar: bool, has_chat_elements: bool) -> None:
    """
    Validate that page follows layout isolation rules.
    
    Args:
        page_type: Type of page (auth, chat, profile, etc.)
        has_sidebar: Whether page includes sidebar
        has_chat_elements: Whether page includes chat elements
        
    Raises:
        ValueError: If layout isolation rules are violated
    """
    
    if page_type == "auth":
        if has_sidebar:
            raise ValueError("Auth pages must not have sidebar")
        if has_chat_elements:
            raise ValueError("Auth pages must not have chat elements")
    
    elif page_type == "chat":
        if not has_sidebar:
            raise ValueError("Chat pages must have sidebar (can be hidden on mobile)")
        if not has_chat_elements:
            raise ValueError("Chat pages must have chat elements")


# Layout validation decorators for route functions
def require_auth_isolation(func):
    """Decorator to enforce auth page isolation rules"""
    def wrapper(*args, **kwargs):
        # Set show_sidebar=False for auth routes
        if 'show_sidebar' in kwargs:
            kwargs['show_sidebar'] = False
        result = func(*args, **kwargs)
        return result
    return wrapper


def require_chat_layout(func):
    """Decorator to enforce chat page layout requirements"""  
    def wrapper(*args, **kwargs):
        # Ensure chat pages have proper layout
        if 'show_sidebar' not in kwargs:
            kwargs['show_sidebar'] = True
        result = func(*args, **kwargs)
        return result
    return wrapper