"""Chat interface routes"""
import json
from datetime import datetime
from fasthtml.components import Div, H2, Button, P, A, H1, Style
from fasthtml.core import Script, NotStr
from starlette.responses import HTMLResponse, JSONResponse
from app.services.web.components.gaia_ui import (
    gaia_layout, gaia_conversation_item, gaia_message_bubble,
    gaia_chat_input, gaia_loading_spinner, gaia_error_message, gaia_toast_script, gaia_mobile_styles
)
from app.services.web.utils.gateway_client import GaiaAPIClient
from app.services.web.utils.chat_service_client import chat_service_client
from app.shared.logging import setup_service_logger

logger = setup_service_logger("chat_routes")


def setup_routes(app):
    """Setup chat routes"""
    
    @app.get("/api/session")
    async def get_session(request):
        """Get current session info"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user")
        
        if not user or not jwt_token:
            return {"authenticated": False}
        
        return {
            "authenticated": True,
            "jwt_token": jwt_token,
            "user": user
        }
    
    @app.get("/chat")
    async def chat_index(request):
        """Main chat interface"""
        from fasthtml.core import Script
        from starlette.responses import RedirectResponse
        
        # Check authentication
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user")
        
        if not user or not jwt_token:
            # Redirect to login if not authenticated
            return RedirectResponse(url="/login", status_code=303)
        
        user_id = user.get("id", "dev-user-id")
        
        # Get user's conversations from chat service
        try:
            conversations = await chat_service_client.get_conversations(user_id, jwt_token)
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            conversations = []
        
        # Build simple sidebar content
        sidebar_content = Div(
            *[gaia_conversation_item(conv) for conv in conversations[:5]],  # Limit to 5 for debugging
            cls="space-y-2",
            id="conversation-list"
        )
        
        # Initialize HTMX properly and handle form clearing
        from fasthtml.core import NotStr
        debug_script = Script(NotStr('''
            // Enable HTMX debug logging
            htmx.config.logger = function(elt, event, data) {
                console.debug("[HTMX]", event, elt, data);
            };

            // CONVERSATION LIST UPDATE MANAGER - Prevents duplicate requests
            window.ConversationListManager = (function() {
                let updateInProgress = false;
                let updateQueued = false;
                let debounceTimer = null;

                function updateConversationList(immediate = false) {
                    console.log('[ConversationList] Update requested, immediate:', immediate);

                    if (immediate) {
                        clearTimeout(debounceTimer);
                        performUpdate();
                        return;
                    }

                    // Debounce updates - only update after 200ms of no new requests
                    if (debounceTimer) {
                        clearTimeout(debounceTimer);
                    }

                    debounceTimer = setTimeout(() => {
                        performUpdate();
                    }, 200);
                }

                function performUpdate() {
                    if (updateInProgress) {
                        updateQueued = true;
                        console.log('[ConversationList] Update already in progress, queued');
                        return;
                    }

                    updateInProgress = true;
                    console.log('[ConversationList] Performing update...');

                    htmx.ajax('GET', '/api/conversations', {
                        target: '#conversation-list',
                        swap: 'innerHTML',
                        callback: function() {
                            updateInProgress = false;
                            console.log('[ConversationList] Update completed');

                            // If another update was queued while we were updating
                            if (updateQueued) {
                                updateQueued = false;
                                setTimeout(performUpdate, 100); // Small delay to prevent thrashing
                            }
                        }
                    });
                }

                return { update: updateConversationList };
            })();

            // Add comprehensive HTMX event listeners
            document.body.addEventListener('htmx:beforeRequest', function(evt) {
                console.log('[HTMX] Before Request:', evt.detail);
            });

            document.body.addEventListener('htmx:afterRequest', function(evt) {
                console.log('[HTMX] After Request:', evt.detail);
            });

            document.body.addEventListener('htmx:responseError', function(evt) {
                console.error('[HTMX] Response Error:', evt.detail);
            });

            document.body.addEventListener('htmx:xhr:loadstart', function(evt) {
                console.log('[HTMX] XHR Load Start:', evt.detail);
            });

            document.body.addEventListener('htmx:xhr:loadend', function(evt) {
                console.log('[HTMX] XHR Load End:', evt.detail);
            });

            // Check if HTMX is loaded
            console.log('[HTMX] Loaded:', typeof htmx);
            
            // Search functionality
            const searchInput = document.getElementById('search-input');
            const clearButton = document.getElementById('clear-search');
            
            if (searchInput && clearButton) {
                // Show/hide clear button based on input content
                searchInput.addEventListener('input', function() {
                    if (this.value.length > 0) {
                        clearButton.style.opacity = '1';
                    } else {
                        clearButton.style.opacity = '0';
                    }
                });
                
                // Clear search on Escape key
                searchInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        this.value = '';
                        clearButton.style.opacity = '0';
                        htmx.ajax('GET', '/api/search-conversations', {target: '#conversation-list', swap: 'innerHTML'});
                    }
                });
            }
            
            // Add event listener for successful swaps
            document.body.addEventListener('htmx:afterSwap', function(evt) {
                console.log('[HTMX] After Swap:', evt.detail);
                if (evt.detail.target.id === 'main-content') {
                    console.log('[HTMX] Main content swapped, forcing reflow');
                    // Force browser reflow/repaint
                    evt.detail.target.style.display = 'none';
                    evt.detail.target.offsetHeight; // Force reflow
                    evt.detail.target.style.display = '';
                }
            });
            
            document.addEventListener('DOMContentLoaded', function() {
                const form = document.getElementById('chat-form');
                if (form) {
                    // Ensure HTMX processes the form
                    htmx.process(form);
                    
                    // Process entire body after a short delay
                    setTimeout(() => {
                        htmx.process(document.body);
                    }, 100);
                    
                    // Add event listener for form clearing and conversation updates
                    document.body.addEventListener('htmx:afterRequest', function(evt) {
                        if (evt.detail.elt && evt.detail.elt.id === 'chat-form') {
                            evt.detail.elt.reset();
                            
                            // Hide welcome message when first message is sent
                            const welcome = document.getElementById('welcome-message');
                            if (welcome) {
                                welcome.style.display = 'none';
                            }
                            
                            // Update conversation list via manager
                            window.ConversationListManager.update();
                            
                            // Update conversation ID if it was created
                            (function() {
                                const mainContent = document.getElementById('main-content').firstElementChild;
                                if (mainContent && mainContent.dataset.conversationId) {
                                    const convInput = document.getElementById('conversation-id-input');
                                    if (convInput && !convInput.value) {
                                        convInput.value = mainContent.dataset.conversationId;
                                    }
                                }
                            })();
                        }
                    });
                    
                    // Process new elements after they're added to the DOM
                    document.body.addEventListener('htmx:afterSwap', function(evt) {
                        // Process any new HTMX elements
                        htmx.process(evt.detail.target);
                        
                        // Manually trigger any elements with hx-trigger="load"
                        const loadElements = evt.detail.target.querySelectorAll('[hx-trigger*="load"]');
                        loadElements.forEach(el => {
                            htmx.trigger(el, 'load');
                        });
                    });
                }
            });
        '''))
        
        # Main content - properly structured chat area
        main_content = Div(
            # Messages container (always visible, shows welcome when empty)
            Div(
                # Welcome message (shown when no messages)
                Div(
                    H2(f"Welcome back, {user.get('name', 'User')}!", 
                       cls="text-lg text-white mb-2"),
                    Div("Start a conversation by typing below", 
                        cls="text-xs text-slate-400"),
                    cls="flex flex-col items-center justify-center text-center h-full",
                    id="welcome-message"
                ),
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar"
            ),
            gaia_chat_input(),  # No conversation ID yet
            debug_script,
            gaia_toast_script(),  # Add toast management
            gaia_mobile_styles(),  # Add mobile-responsive styles
            cls="flex flex-col h-full",
            id="main-content"  # Add ID for HTMX targeting
        )
        
        # For HTMX requests, return just the main content
        if request.headers.get('hx-request'):
            return main_content
        
        # For full page loads, return the complete layout
        return gaia_layout(
            sidebar_content=sidebar_content,
            main_content=main_content,
            user=user
        )
    
    @app.get("/chat/{conversation_id}")
    async def chat_conversation(request, conversation_id: str):
        """Load specific conversation"""
        logger.info(f"=== CHAT CONVERSATION ROUTE CALLED ===")
        logger.info(f"Conversation ID: {conversation_id}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Is HTMX request: {request.headers.get('hx-request')}")
        
        # Check authentication
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user")
        
        if not user or not jwt_token:
            from starlette.responses import RedirectResponse
            # For HTMX requests, return a client-side redirect
            if request.headers.get('hx-request'):
                return HTMLResponse('<script>window.location.href="/login"</script>')
            return RedirectResponse(url="/login", status_code=303)
        
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"Loading conversation {conversation_id} for user {user_id}")
        
        try:
            # Get conversation from chat service
            conversation = await chat_service_client.get_conversation(user_id, conversation_id, jwt_token)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return gaia_error_message("Conversation not found")
            
            # Get messages from chat service
            messages_list = await chat_service_client.get_messages(conversation_id, jwt_token)
            
            # Build message content - show welcome if no messages, otherwise show messages
            if not messages_list:
                message_content = [
                    Div(
                        H2(f"Welcome back, {user.get('name', 'User')}!", 
                           cls="text-2xl text-white mb-4"),
                        Div("Start a conversation by typing below", 
                            cls="text-slate-400"),
                        cls="flex flex-col items-center justify-center text-center h-full",
                        id="welcome-message"
                    )
                ]
            else:
                message_content = [
                    gaia_message_bubble(
                        msg["content"],
                        role=msg["role"],
                        timestamp=msg.get("created_at", "")
                    )
                    for msg in messages_list
                ]
            
            # Messages container
            messages_container = Div(
                *message_content,
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar"
            )
            
            # Return inner content for innerHTML swap
            return Div(
                messages_container,
                gaia_chat_input(conversation_id=conversation_id),
                # Add script to update active conversation in sidebar
                Script(NotStr(f'''
                    // Update active conversation in sidebar
                    document.querySelectorAll('#conversation-list a').forEach(a => {{
                        a.parentElement.classList.remove('bg-gradient-to-r', 'from-purple-600/30', 'to-pink-600/30', 'border-l-3', 'border-purple-500', 'shadow-lg');
                        a.parentElement.classList.add('hover:bg-slate-700/50', 'hover:shadow-md');
                    }});
                    const activeLink = document.querySelector('#conversation-list a[href="/chat/{conversation_id}"]');
                    if (activeLink) {{
                        activeLink.parentElement.classList.remove('hover:bg-slate-700/50', 'hover:shadow-md');
                        activeLink.parentElement.classList.add('bg-gradient-to-r', 'from-purple-600/30', 'to-pink-600/30', 'border-l-3', 'border-purple-500', 'shadow-lg');
                    }}
                    // Update browser URL without reload
                    history.pushState(null, '', '/chat/{conversation_id}');
                    
                    // Auto-scroll to bottom when loading conversation with messages
                    setTimeout(() => {{
                        const messagesContainer = document.getElementById('messages');
                        if (messagesContainer) {{
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }}
                    }}, 100); // Small delay to ensure DOM is updated
                ''')),
                cls="flex flex-col h-full",
                data_conversation_id=conversation_id,
                id="main-content"
            )
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return gaia_error_message("Failed to load conversation")
    
    @app.post("/chat/new")
    async def new_chat(request):
        """Create new conversation"""
        # Check authentication
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user")
        
        if not user or not jwt_token:
            return gaia_error_message("Please log in to create a new conversation")
        
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"New chat requested for user {user_id}")
        
        # Create a new conversation using chat service
        conversation = await chat_service_client.create_conversation(user_id, jwt_token=jwt_token)
        logger.info(f"Created new conversation: {conversation['id']}")
        
        # Return fresh chat interface with conversation ID
        # Add script to update conversation list
        from fasthtml.core import Script, NotStr
        update_script = Script(NotStr(f'''
            (function() {{
                // Update conversation ID input
                const convInput = document.getElementById('conversation-id-input');
                if (convInput) {{
                    convInput.value = '{conversation['id']}';
                }}
                // Update conversation list via manager
                window.ConversationListManager.update(true);
                // Show success toast
                if (window.GaiaToast) {{
                    GaiaToast.success('New conversation created!');
                }}
            }})();
        '''))
        
        # Return inner content for innerHTML swap
        return Div(
            # Messages container (always visible, shows welcome when empty)
            Div(
                # Welcome message (shown when no messages)
                Div(
                    H2(f"Welcome back, {user.get('name', 'User')}!", 
                       cls="text-lg text-white mb-2"),
                    Div("Start a conversation by typing below", 
                        cls="text-xs text-slate-400"),
                    cls="flex flex-col items-center justify-center text-center h-full",
                    id="welcome-message"
                ),
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar"
            ),
            gaia_chat_input(conversation_id=conversation['id']),
            update_script,
            cls="flex flex-col h-full",
            data_conversation_id=conversation['id'],
            id="main-content"
        )
    
    @app.post("/api/chat/send")
    async def send_message(request):
        """Send chat message"""
        logger.info("Chat send endpoint called")
        
        try:
            # Check authentication
            jwt_token = request.session.get("jwt_token")
            user = request.session.get("user")
            
            if not user or not jwt_token:
                return gaia_error_message("Please log in to send messages")
            
            user_id = user.get("id", "dev-user-id")
            
            form_data = await request.form()
            message = form_data.get("message")
            conversation_id = form_data.get("conversation_id")

            logger.info(f"Received message: {message}, conversation: {conversation_id} (using v0.3 format)")
            
            if not message:
                return gaia_error_message("Please enter a message")
            
            # Create new conversation if none exists - with race condition protection
            if not conversation_id:
                # Check if we already have a pending conversation in session (race condition protection)
                pending_conversation_id = request.session.get("pending_conversation_id")
                if pending_conversation_id:
                    # Verify it exists and is accessible
                    try:
                        existing_conv = await chat_service_client.get_conversation(user_id, pending_conversation_id, jwt_token=jwt_token)
                        if existing_conv:
                            conversation_id = pending_conversation_id
                            logger.info(f"Using pending conversation: {conversation_id}")
                        else:
                            # Pending conversation doesn't exist, clear it and create new
                            request.session.pop("pending_conversation_id", None)
                    except Exception as e:
                        logger.warning(f"Error checking pending conversation: {e}")
                        request.session.pop("pending_conversation_id", None)

                # Create new conversation if we still don't have one
                if not conversation_id:
                    conversation = await chat_service_client.create_conversation(user_id, jwt_token=jwt_token)
                    conversation_id = conversation['id']
                    # Store in session to prevent race conditions on subsequent rapid requests
                    request.session["pending_conversation_id"] = conversation_id
                    logger.info(f"Created new conversation: {conversation_id}")
            
            # Store the user message BEFORE sending response
            user_msg = await chat_service_client.add_message(conversation_id, "user", message, jwt_token=jwt_token)
            logger.info(f"Stored user message: {user_msg}")
            
            # Update conversation preview with first message
            await chat_service_client.update_conversation(user_id, conversation_id, 
                                                 title=message[:50] + "..." if len(message) > 50 else message,
                                                 preview=message, jwt_token=jwt_token)
            
            # For now, use a simple ID
            import uuid
            message_id = str(uuid.uuid4())[:8]
            
            # Add user message to UI immediately
            user_message = gaia_message_bubble(
                message,
                role="user",
                timestamp=datetime.now().strftime("%I:%M %p")
            )
            
            # Enhanced loading indicator with typing animation
            loading_html = f'''<div id="loading-{message_id}" class="flex justify-start mb-4 assistant-message-placeholder animate-slideInLeft">
    <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg hover:shadow-xl transition-all duration-300">
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        <div class="text-xs opacity-70 mt-2">Gaia is thinking...</div>
    </div>
</div>'''
            
            # URL encode the message to avoid HTML entity issues
            from urllib.parse import quote
            encoded_message = quote(message, safe='')
            
            # Create HTML manually to avoid FastHTML's automatic escaping
            user_message_html = str(user_message)
            
            # Clean response HTML for proper HTMX handling with SSE streaming
            response_html = f'''{user_message_html}
<div id="loading-{message_id}" class="flex justify-start mb-4">
    <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        <div class="text-xs opacity-70 mt-2">Gaia is thinking...</div>
    </div>
</div>
<script>
(function() {{
    // Hide welcome message on first message
    const welcome = document.getElementById('welcome-message');
    if (welcome) {{
        welcome.style.display = 'none';
    }}
    
    // Update conversation ID if it was just created
    (function() {{
        const convInput = document.getElementById('conversation-id-input');
        if (convInput && !convInput.value) {{
            convInput.value = '{conversation_id}';
        }}
    }})()
    
    // Update conversation list via manager
    window.ConversationListManager.update(true);
    
    // Show success notification
    if (window.GaiaToast) {{
        GaiaToast.success('Message sent successfully!', 2000);
    }}
    
    // Auto-scroll to bottom after adding user message
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {{
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }}
    
    // Use Server-Sent Events for streaming response
    setTimeout(() => {{
        const loadingEl = document.getElementById('loading-{message_id}');
        let responseContent = '';
        let responseStarted = false;
        
        // Create EventSource for streaming with v0.3 format
        const eventSource = new EventSource('/api/chat/stream?message={encoded_message}&conversation_id={conversation_id}');
        
        // Set a timeout for the response
        const timeoutId = setTimeout(() => {{
            if (!responseStarted && loadingEl && loadingEl.parentNode) {{
                loadingEl.outerHTML = `<div class="flex justify-start mb-4 assistant-message-placeholder">
                    <div class="bg-yellow-900/50 border border-yellow-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                        <div class="flex items-center">
                            <span class="mr-2">⚠️</span>
                            <span>Response is taking longer than expected...</span>
                        </div>
                        <div class="text-xs opacity-70 mt-2">The AI is still thinking. Please wait or try again.</div>
                    </div>
                </div>`;
                eventSource.close();
            }}
        }}, 30000); // 30 second timeout warning
        
        eventSource.onmessage = function(event) {{
            if (event.data === '[DONE]') {{
                eventSource.close();
                clearTimeout(timeoutId);
                if (window.GaiaToast) {{
                    GaiaToast.success('Response received!', 2000);
                }}
                return;
            }}
            
            try {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'metadata' && data.phase) {{
                    // Handle progressive phases
                    if (data.phase === 'immediate') {{
                        // Replace loading with immediate acknowledgment
                        const immediateContent = data.data.content || '🤖 Coordinating technical, knowledge_management agents...';
                        loadingEl.outerHTML = `<div id="response-{message_id}" class="flex justify-start mb-4 animate-slideInLeft">
                            <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg hover:shadow-xl transition-all duration-300">
                                <div id="response-content-{message_id}" class="whitespace-pre-wrap break-words">${{immediateContent}}</div>
                                <div class="flex items-center justify-between mt-2 text-xs opacity-70">
                                    <span>Gaia KB Agent</span>
                                    <span class="text-blue-400">Initializing...</span>
                                </div>
                            </div>
                        </div>`;
                    }} else if (data.phase === 'analysis') {{
                        // Update with analysis status
                        const contentEl = document.getElementById('response-content-{message_id}');
                        if (contentEl) {{
                            const analysisContent = data.data.content || '📊 Analyzing knowledge base content and making intelligent decisions...';
                            contentEl.textContent = analysisContent;
                            // Update status
                            const statusEl = contentEl.parentElement.querySelector('.text-blue-400');
                            if (statusEl) statusEl.textContent = 'Analyzing...';
                        }}
                    }} else if (data.phase === 'complete') {{
                        // Update final status
                        const statusEl = document.getElementById('response-{message_id}').querySelector('.text-blue-400');
                        if (statusEl) {{
                            const totalTime = data.data.total_time || 'unknown';
                            statusEl.textContent = `Completed in ${{totalTime}}ms`;
                            statusEl.classList.remove('text-blue-400');
                            statusEl.classList.add('text-green-400');
                        }}
                    }}
                }}
                else if (data.type === 'content') {{
                    // Progressive content - append to existing content
                    if (!responseStarted) {{
                        responseStarted = true;
                        clearTimeout(timeoutId);
                        const timestamp = new Date().toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit' }});
                        // Initialize response if not already done by metadata
                        if (!document.getElementById('response-{message_id}')) {{
                            loadingEl.outerHTML = `<div id="response-{message_id}" class="flex justify-start mb-4 animate-slideInLeft">
                                <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg hover:shadow-xl transition-all duration-300">
                                    <div id="response-content-{message_id}" class="whitespace-pre-wrap break-words"></div>
                                    <div class="flex items-center justify-between mt-2 text-xs opacity-70">
                                        <span>Gaia</span>
                                        <span>${{timestamp}}</span>
                                    </div>
                                </div>
                            </div>`;
                        }}
                    }}
                    
                    // Append content to response
                    responseContent += data.content;
                    const contentEl = document.getElementById('response-content-{message_id}');
                    if (contentEl) {{
                        contentEl.textContent = responseContent;
                        
                        // Auto-scroll to bottom as response streams in
                        const messagesContainer = document.getElementById('messages');
                        if (messagesContainer) {{
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }}
                    }}
                }}
                else if (data.type === 'error') {{
                    eventSource.close();
                    clearTimeout(timeoutId);
                    loadingEl.outerHTML = `<div class="flex justify-start mb-4 animate-slideInLeft">
                        <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                            <div class="flex items-center">
                                <span class="mr-2">❌</span>
                                <span>Error: ${{data.error}}</span>
                            </div>
                        </div>
                    </div>`;
                }}
            }} catch (e) {{
                console.error('Failed to parse SSE data:', e);
            }}
        }};
        
        eventSource.onerror = function(error) {{
            console.error('SSE error:', error);
            eventSource.close();
            clearTimeout(timeoutId);
            
            if (!responseStarted) {{
                loadingEl.outerHTML = `<div class="flex justify-start mb-4 animate-slideInLeft">
                    <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                        <div class="flex items-center">
                            <span class="mr-2">❌</span>
                            <span>Connection error. Please try again.</span>
                        </div>
                    </div>
                </div>`;
            }}
        }};
    }}, 500);
}})();
</script>'''
            
            logger.info("Returning chat response HTML")
            return HTMLResponse(content=response_html)
            
        except Exception as e:
            logger.error(f"Error in send_message: {e}", exc_info=True)
            
            # Show toast error and return user-friendly error message
            error_msg = str(e).lower()
            if "connection" in error_msg or "network" in error_msg:
                user_message = "Connection error. Please check your internet and try again."
            elif "timeout" in error_msg:
                user_message = "Request timed out. Please try again."
            elif "validation" in error_msg or "invalid" in error_msg:
                user_message = "Invalid message format. Please check your input."
            else:
                user_message = "Failed to send message. Please try again."
            
            # Return enhanced error with toast notification
            from fasthtml.core import Script, NotStr
            error_script = Script(NotStr(f'''
                if (window.GaiaToast) {{
                    GaiaToast.error('{user_message}', 5000);
                }}
            '''))
            
            return Div(
                gaia_error_message(user_message),
                error_script
            )
    
    @app.get("/api/chat/stream")
    async def stream_response(request):
        """Stream chat response using Server-Sent Events"""
        from starlette.responses import StreamingResponse
        import asyncio
        
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        message = request.query_params.get("message")
        conversation_id = request.query_params.get("conversation_id")

        logger.info(f"Stream response - message: {message}, conv: {conversation_id} (using v0.3 format), has_jwt: {bool(jwt_token)}, user_id: {user_id}")
        
        async def event_generator():
            import json  # Import json for error handling
            logger.info(f"Starting SSE generator for conversation {conversation_id}")
            try:
                # Get conversation history from chat service
                if conversation_id:
                    messages_history = await chat_service_client.get_messages(conversation_id, jwt_token)
                    messages = [
                        {"role": m["role"], "content": m["content"]} 
                        for m in messages_history 
                        if m.get("content", "").strip()
                    ]
                else:
                    messages = [{"role": "user", "content": message}]
                
                # Start streaming from gateway with v0.3 format
                response_content = ""
                async with GaiaAPIClient() as client:
                    async for chunk in client.chat_completion_stream(messages, jwt_token, response_format="v0.3"):
                        try:
                            # Parse the chunk
                            import json
                            if chunk.strip() == "[DONE]":
                                # Save BEFORE sending [DONE] to ensure it completes
                                if conversation_id and response_content:
                                    logger.info(f"Saving AI response (before DONE): conversation_id={conversation_id}, content_length={len(response_content)}")
                                    try:
                                        await chat_service_client.add_message(conversation_id, "assistant", response_content, jwt_token=jwt_token)
                                        logger.info(f"Successfully saved AI response to conversation {conversation_id}")
                                        await chat_service_client.update_conversation(user_id, conversation_id, preview=response_content, jwt_token=jwt_token)
                                        logger.info(f"Successfully updated conversation preview")
                                    except Exception as e:
                                        logger.error(f"Failed to save AI response: {e}", exc_info=True)
                                yield f"data: [DONE]\n\n"
                                break
                            
                            chunk_data = json.loads(chunk)
                            
                            # Handle OpenAI-compatible format
                            if chunk_data.get("object") == "chat.completion.chunk":
                                # Extract content from OpenAI format
                                choices = chunk_data.get("choices", [])
                                if choices and choices[0].get("delta"):
                                    content = choices[0]["delta"].get("content", "")
                                    if content:
                                        response_content += content
                                        # Send the content chunk in our format
                                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"

                                # Handle progressive metadata events
                                if chunk_data.get("_metadata"):
                                    metadata = chunk_data["_metadata"]
                                    # Send progressive metadata events for client-side UI updates
                                    if metadata.get("phase"):
                                        yield f"data: {json.dumps({'type': 'metadata', 'phase': metadata['phase'], 'data': metadata})}\n\n"

                                # Check for finish reason
                                finish_reason = choices[0].get("finish_reason") if choices else None
                                if finish_reason == "stop":
                                    # Save BEFORE sending [DONE] to ensure it completes
                                    if conversation_id and response_content:
                                        logger.info(f"Saving AI response (finish stop): conversation_id={conversation_id}, content_length={len(response_content)}")
                                        try:
                                            await chat_service_client.add_message(conversation_id, "assistant", response_content, jwt_token=jwt_token)
                                            logger.info(f"Successfully saved AI response to conversation {conversation_id}")
                                            await chat_service_client.update_conversation(user_id, conversation_id, preview=response_content, jwt_token=jwt_token)
                                            logger.info(f"Successfully updated conversation preview")
                                        except Exception as e:
                                            logger.error(f"Failed to save AI response: {e}", exc_info=True)
                                    yield f"data: [DONE]\n\n"
                                    break
                            elif chunk_data.get("error"):
                                # Handle error responses
                                yield f"data: {json.dumps({'type': 'error', 'error': chunk_data['error'].get('message', 'Unknown error')})}\n\n"
                            else:
                                # Handle other formats (fallback for non-OpenAI format)
                                if chunk_data.get("type") == "content":
                                    content = chunk_data.get("content", "")
                                    response_content += content
                                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                                elif chunk_data.get("type") == "error":
                                    yield f"data: {json.dumps({'type': 'error', 'error': chunk_data.get('error')})}\n\n"
                                
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse chunk: {chunk}")
                            continue
                
                # Log end of streaming (save should have happened before [DONE])
                logger.info(f"End of streaming loop - conversation_id={conversation_id}, response_content_length={len(response_content) if response_content else 0}")
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            finally:
                logger.info(f"SSE generator completed - response_saved={conversation_id and response_content and 'will_save' or 'no_save'}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    @app.get("/api/chat/response")
    async def get_response(request):
        """Get chat response"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        message = request.query_params.get("message")
        message_id = request.query_params.get("id", "unknown")
        conversation_id = request.query_params.get("conversation_id")
        
        logger.info(f"Get response - message: {message}, id: {message_id}, conv: {conversation_id}")
        
        try:
            # Get conversation history from chat service
            if conversation_id:
                messages_history = await chat_service_client.get_messages(conversation_id, jwt_token)
                # Convert to API format (only content and role)
                # Filter out empty messages
                messages = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in messages_history 
                    if m.get("content", "").strip()
                ]
                logger.info(f"Sending {len(messages)} messages to gateway")
            else:
                messages = [{"role": "user", "content": message}]
            
            # Get response from gateway (fallback non-streaming mode)
            async with GaiaAPIClient() as client:
                response = await client.chat_completion(messages, jwt_token, response_format="v0.3")
                logger.info(f"Gateway response: {response}")
            
            # v0.2 format returns response directly
            response_content = response.get("response", "Sorry, I couldn't process that.")
            
            # Store assistant message using chat service
            if conversation_id:
                await chat_service_client.add_message(conversation_id, "assistant", response_content, jwt_token=jwt_token)
                # Update conversation preview with assistant response
                await chat_service_client.update_conversation(user_id, conversation_id, 
                                                     preview=response_content, jwt_token=jwt_token)
            
            # Return enhanced assistant message with entrance animation
            assistant_bubble = gaia_message_bubble(
                response_content,
                role="assistant",
                timestamp=datetime.now().strftime("%I:%M %p")
            )
            # Add entrance animation class
            assistant_html = str(assistant_bubble).replace(
                'class="flex justify-start mb-4"',
                'class="flex justify-start mb-4 animate-slideInLeft"'
            )
            
            # Add a small script to show success toast
            from fasthtml.core import Script, NotStr
            success_script = Script(NotStr('''
                if (window.GaiaToast) {
                    GaiaToast.success('Response received!', 2000);
                }
            '''))
            
            return HTMLResponse(content=assistant_html + str(success_script))
            
        except Exception as e:
            logger.error(f"Error getting response: {e}", exc_info=True)
            
            # Determine error type and message
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                user_message = "Response timed out. Please try again."
                error_type = "timeout"
            elif "rate limit" in error_msg:
                user_message = "Rate limit reached. Please wait a moment."
                error_type = "rate_limit"
            elif "api" in error_msg or "key" in error_msg:
                user_message = "API error. Please check your configuration."
                error_type = "api_error"
            elif "network" in error_msg or "connection" in error_msg:
                user_message = "Connection error. Please check your internet."
                error_type = "network_error"
            else:
                user_message = "Something went wrong. Please try again."
                error_type = "unknown_error"
            
            # URL encode the message for retry
            from urllib.parse import quote
            encoded_message = quote(message or "", safe='')
            
            # Enhanced error message with retry capability
            retry_action = f"htmx.ajax('GET', '/api/chat/response?message={encoded_message}&id={message_id}&conversation_id={conversation_id}', {{target: '#loading-{message_id}', swap: 'outerHTML'}})"
            
            # Show error toast
            from fasthtml.core import Script, NotStr
            error_toast_script = Script(NotStr(f'''
                if (window.GaiaToast) {{
                    GaiaToast.error('{user_message}', 5000);
                }}
            '''))
            
            error_html = f'''<div class="flex justify-start mb-4 assistant-message-placeholder">
    <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <span class="mr-2">❌</span>
                <span>{user_message}</span>
            </div>
            <button onclick="{retry_action}" 
                    class="ml-3 px-3 py-1 bg-white bg-opacity-20 hover:bg-opacity-30 rounded text-sm font-medium transition-all duration-200">
                Retry
            </button>
        </div>
        <div class="text-xs opacity-70 mt-2">Error: {str(e)[:100]}...</div>
    </div>
</div>
<script>
    // Show toast notification for the error
    if (window.GaiaToast) {{
        const errorMessages = {{
            'timeout': 'Response timed out. You can retry or try a shorter message.',
            'rate_limit': 'You\\'re sending messages too quickly. Please wait a moment.',
            'api_error': 'There\\'s an issue with the AI service. Please try again.',
            'network_error': 'Network connection issue. Please check your internet.',
            'unknown_error': 'An unexpected error occurred. Please try again.'
        }};
        GaiaToast.error(errorMessages['{error_type}'] || errorMessages['unknown_error'], 8000);
    }}
</script>'''
            
            return HTMLResponse(content=error_html + str(error_toast_script))
    
    @app.get("/test/htmx")
    async def test_htmx(request):
        """Simple HTMX test endpoint"""
        logger.info(f"Test HTMX endpoint called")
        logger.info(f"Is HTMX: {request.headers.get('hx-request')}")
        
        return Div(
            H2("HTMX Test Success!", cls="text-2xl text-white mb-4"),
            P(f"Time: {datetime.now().strftime('%H:%M:%S')}", cls="text-slate-400"),
            P(f"HTMX Request: {request.headers.get('hx-request') == '1'}", cls="text-slate-400"),
            id="main-content",
            cls="flex-1 flex flex-col h-screen overflow-hidden p-6"
        )
    
    @app.get("/test/conversation-switch")
    async def test_conversation_switch(request):
        """Test page for debugging conversation switching"""
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        conversations = await chat_service_client.get_conversations(user_id)
        conversations = conversations[:3]  # Get first 3
        
        from fasthtml.core import Script, NotStr
        
        # Build conversation buttons
        conv_buttons = []
        for conv in conversations:
            conv_buttons.append(
                Div(
                    conv.get("title", "New Conversation"),
                    cls="p-3 m-2 bg-gray-200 hover:bg-gray-300 cursor-pointer rounded",
                    hx_get=f"/chat/{conv['id']}",
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    hx_indicator="#loading-indicator"
                )
            )
        
        return Div(
            # Loading indicator OUTSIDE main-content
            Div("Loading conversation...", id="loading-indicator", 
                style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 10px; z-index: 1000;"),
            
            Style(NotStr(".htmx-request #loading-indicator { display: block !important; }")),
            
            H1("Conversation Switch Test", cls="text-2xl font-bold mb-4"),
            
            # Conversation list
            Div(
                H2("Conversations:", cls="text-xl mb-2"),
                *conv_buttons,
                cls="mb-4"
            ),
            
            # Main content area
            Div(
                P("Click a conversation to load it here"),
                id="main-content",
                cls="border-2 border-gray-400 p-5 min-h-[200px]"
            ),
            
            # Debug script
            Script(NotStr("""
                // Enable HTMX debugging
                htmx.config.logger = function(elt, event, data) {
                    console.debug("[HTMX]", event, elt, data);
                };
                
                document.body.addEventListener('htmx:beforeRequest', function(evt) {
                    console.log('[TEST] Before Request:', evt.detail);
                });
                
                document.body.addEventListener('htmx:afterRequest', function(evt) {
                    console.log('[TEST] After Request:', evt.detail);
                });
                
                document.body.addEventListener('htmx:responseError', function(evt) {
                    console.error('[TEST] Response Error:', evt.detail);
                });
            """)),
            cls="p-8"
        )
    
    @app.get("/api/conversations")
    async def get_conversations(request):
        """Get updated conversation list"""
        # Check authentication
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user")
        if not user or not jwt_token:
            return gaia_error_message("Please log in to view conversations")

        user_id = user.get("id", "dev-user-id")

        try:
            # Pass JWT token to chat service for authentication
            conversations = await chat_service_client.get_conversations(user_id, jwt_token=jwt_token)
        except Exception as e:
            # If JWT token is expired or invalid, redirect to login
            if "401" in str(e) or "expired" in str(e).lower() or "unauthorized" in str(e).lower():
                # Clear expired session
                request.session.clear()
                return gaia_error_message("Your session has expired. Please log in again.")
            else:
                logger.error(f"Error getting conversations: {e}")
                return gaia_error_message("Failed to load conversations")
        
        # Return updated conversation list with smooth animations
        conversation_items = [gaia_conversation_item(conv) for conv in conversations]
        
        return Div(
            *conversation_items,
            cls="space-y-2 stagger-children animate-fadeIn",
            id="conversation-list",
            style="--stagger-delay: 0;"
        )
    
    @app.delete("/api/conversations/{conversation_id}")
    async def delete_conversation(request, conversation_id: str):
        """Delete a conversation"""
        # Check authentication
        user = request.session.get("user")
        if not user:
            return gaia_error_message("Please log in to delete conversations")
        
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"Deleting conversation {conversation_id} for user {user_id}")
        
        try:
            # Delete the conversation using chat service
            success = await chat_service_client.delete_conversation(user_id, conversation_id)
            
            if not success:
                logger.warning(f"Failed to delete conversation {conversation_id}")
                return gaia_error_message("Conversation not found or could not be deleted")
            
            # Get updated conversation list from chat service
            conversations = await chat_service_client.get_conversations(user_id)
            conversation_items = [gaia_conversation_item(conv) for conv in conversations]
            
            # Return updated conversation list
            return Div(
                *conversation_items,
                cls="space-y-2 stagger-children animate-fadeIn",
                id="conversation-list",
                style="--stagger-delay: 0;"
            )
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return gaia_error_message(f"Failed to delete conversation: {str(e)[:100]}")
    
    @app.get("/api/search-conversations")
    async def search_conversations(request):
        """Search conversations by title or content"""
        # Check authentication
        user = request.session.get("user")
        if not user:
            return gaia_error_message("Please log in to search conversations")
        
        user_id = user.get("id", "dev-user-id")
        
        query = request.query_params.get("query", "").strip()
        logger.info(f"Searching conversations for user {user_id} with query: '{query}'")
        
        try:
            if not query:
                # If no query, return all conversations from chat service
                conversations = await chat_service_client.get_conversations(user_id)
            else:
                # Search conversations using chat service
                conversations = await chat_service_client.search_conversations(user_id, query)
            
            # Return updated conversation list with search results
            if not conversations:
                result_html = Div(
                    Div(
                        f"No conversations found for '{query}'" if query else "No conversations found",
                        cls="text-xs text-slate-400 text-center py-4 italic"
                    ),
                    cls="space-y-2"
                )
                # Update search status
                from fasthtml.core import Script, NotStr
                query_text = f' for "{query}"' if query else ""
                status_script = Script(NotStr(f'''
                    const status = document.getElementById('search-status');
                    if (status) {{
                        status.textContent = '{len(conversations)} results{query_text}';
                    }}
                '''))
                return Div(result_html, status_script)
                
            conversation_items = [gaia_conversation_item(conv) for conv in conversations]
            
            # Create result with status update
            from fasthtml.core import Script, NotStr
            plural = "s" if len(conversations) != 1 else ""
            query_text = f' for "{query}"' if query else ""
            status_script = Script(NotStr(f'''
                const status = document.getElementById('search-status');
                if (status) {{
                    status.textContent = '{len(conversations)} result{plural}{query_text}';
                }}
            '''))
            
            return Div(
                Div(
                    *conversation_items,
                    cls="space-y-2 stagger-children animate-fadeIn",
                    id="conversation-list",
                    style="--stagger-delay: 0;"
                ),
                status_script
            )
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}", exc_info=True)
            return gaia_error_message(f"Search failed: {str(e)[:100]}")