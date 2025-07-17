"""Chat interface routes"""
import json
from datetime import datetime
from fasthtml.components import Div, H2, Button, P, A, H1, Style
from starlette.responses import HTMLResponse
from app.services.web.components.gaia_ui import (
    gaia_layout, gaia_conversation_item, gaia_message_bubble,
    gaia_chat_input, gaia_loading_spinner, gaia_error_message
)
from app.services.web.utils.gateway_client import GaiaAPIClient
from app.services.web.utils.database_conversation_store import database_conversation_store
from app.shared.logging import setup_service_logger

logger = setup_service_logger("chat_routes")


def setup_routes(app):
    """Setup chat routes"""
    
    @app.get("/chat")
    async def chat_index(request):
        """Main chat interface"""
        from fasthtml.core import Script
        
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        # Get user's conversations
        conversations = database_conversation_store.get_conversations(user_id)
        
        # Build enhanced sidebar content with stagger animation
        sidebar_content = Div(
            *[gaia_conversation_item(conv) for conv in conversations],
            cls="space-y-2 stagger-children",
            id="conversation-list",
            style="--stagger-delay: 0;"
        )
        
        # Initialize HTMX properly and handle form clearing
        from fasthtml.core import NotStr
        debug_script = Script(NotStr('''
            // Enable HTMX debug logging
            htmx.config.logger = function(elt, event, data) {
                console.debug("[HTMX]", event, elt, data);
            };
            
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
            
            // Add event listener for successful swaps to debug
            document.body.addEventListener('htmx:afterSwap', function(evt) {
                console.log('[HTMX] After Swap:', evt.detail);
                if (evt.detail.target.id === 'main-content') {
                    console.log('[HTMX] Main content swapped, forcing reflow');
                    // Add visible debug info
                    const debugDiv = document.createElement('div');
                    debugDiv.style.cssText = 'position:fixed;top:10px;right:10px;background:yellow;color:black;padding:10px;z-index:9999';
                    debugDiv.textContent = 'HTMX Swap Completed at ' + new Date().toTimeString();
                    document.body.appendChild(debugDiv);
                    setTimeout(() => debugDiv.remove(), 3000);
                    
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
                            
                            // Update conversation list
                            htmx.ajax('GET', '/api/conversations', {target: '#conversation-list', swap: 'innerHTML'});
                            
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
            cls="flex flex-col h-full"
        )
        
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
        
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"Loading conversation {conversation_id} for user {user_id}")
        
        try:
            # Get conversation from store
            all_convs = database_conversation_store.get_conversations(user_id)
            logger.info(f"User {user_id} has {len(all_convs)} conversations")
            
            conversation = database_conversation_store.get_conversation(user_id, conversation_id)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return gaia_error_message("Conversation not found")
            
            # Get messages
            messages_list = database_conversation_store.get_messages(conversation_id)
            
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
                cls="flex flex-col h-full",
                data_conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return gaia_error_message("Failed to load conversation")
    
    @app.post("/chat/new")
    async def new_chat(request):
        """Create new conversation"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"New chat requested for user {user_id}")
        
        # Create a new conversation
        conversation = database_conversation_store.create_conversation(user_id)
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
                // Update conversation list
                htmx.ajax('GET', '/api/conversations', {{target: '#conversation-list', swap: 'innerHTML'}});
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
            data_conversation_id=conversation['id']
        )
    
    @app.post("/api/chat/send")
    async def send_message(request):
        """Send chat message"""
        logger.info("Chat send endpoint called")
        
        try:
            jwt_token = request.session.get("jwt_token")
            user = request.session.get("user", {})
            user_id = user.get("id", "dev-user-id")
            
            form_data = await request.form()
            message = form_data.get("message")
            conversation_id = form_data.get("conversation_id")
            
            logger.info(f"Received message: {message}, conversation: {conversation_id}")
            
            if not message:
                return gaia_error_message("Please enter a message")
            
            # Create new conversation if none exists
            if not conversation_id:
                conversation = database_conversation_store.create_conversation(user_id)
                conversation_id = conversation['id']
                logger.info(f"Created new conversation: {conversation_id}")
            
            # Store the user message BEFORE sending response
            user_msg = database_conversation_store.add_message(conversation_id, "user", message)
            logger.info(f"Stored user message: {user_msg}")
            
            # Update conversation preview with first message
            database_conversation_store.update_conversation(user_id, conversation_id, 
                                                 title=message[:50] + "..." if len(message) > 50 else message,
                                                 preview=message)
            
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
            
            # Clean response HTML for proper HTMX handling
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
    
    // Update conversation list
    htmx.ajax('GET', '/api/conversations', {{target: '#conversation-list', swap: 'innerHTML'}});
    
    // Fetch AI response with timeout handling
    setTimeout(() => {{
        const loadingEl = document.getElementById('loading-{message_id}');
        
        // Set a timeout for the response
        const timeoutId = setTimeout(() => {{
            if (loadingEl && loadingEl.parentNode) {{
                loadingEl.outerHTML = `<div class="flex justify-start mb-4 assistant-message-placeholder">
                    <div class="bg-yellow-900/50 border border-yellow-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                        <div class="flex items-center">
                            <span class="mr-2">⚠️</span>
                            <span>Response is taking longer than expected...</span>
                        </div>
                        <div class="text-xs opacity-70 mt-2">The AI is still thinking. Please wait or try again.</div>
                    </div>
                </div>`;
            }}
        }}, 30000); // 30 second timeout warning
        
        htmx.ajax('GET', '/api/chat/response?message={encoded_message}&id={message_id}&conversation_id={conversation_id}', {{
            target: '#loading-{message_id}',
            swap: 'outerHTML'
        }}).then(() => {{
            clearTimeout(timeoutId);
        }});
    }}, 500);
}})();
</script>'''
            
            logger.info("Returning chat response HTML")
            return HTMLResponse(content=response_html)
            
        except Exception as e:
            logger.error(f"Error in send_message: {e}", exc_info=True)
            # Return an error message that will be shown in the UI
            return gaia_error_message(f"Failed to send message: {str(e)[:100]}")
    
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
            # Get conversation history
            if conversation_id:
                messages_history = database_conversation_store.get_messages(conversation_id)
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
            
            # Get response from gateway
            async with GaiaAPIClient() as client:
                response = await client.chat_completion(messages, jwt_token)
                logger.info(f"Gateway response: {response}")
            
            # v0.2 format returns response directly
            response_content = response.get("response", "Sorry, I couldn't process that.")
            
            # Store assistant message
            if conversation_id:
                database_conversation_store.add_message(conversation_id, "assistant", response_content)
                # Update conversation preview with assistant response
                database_conversation_store.update_conversation(user_id, conversation_id, 
                                                     preview=response_content)
            
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
            
            return HTMLResponse(content=assistant_html)
            
        except Exception as e:
            logger.error(f"Error getting response: {e}", exc_info=True)
            
            # Determine error type and message
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                user_message = "Response timed out. Please try again."
            elif "rate limit" in error_msg:
                user_message = "Rate limit reached. Please wait a moment."
            elif "api" in error_msg or "key" in error_msg:
                user_message = "API error. Please check your configuration."
            elif "network" in error_msg or "connection" in error_msg:
                user_message = "Connection error. Please check your internet."
            else:
                user_message = "Something went wrong. Please try again."
            
            # Return error message that replaces the loading indicator
            error_html = f'''<div class="flex justify-start mb-4 assistant-message-placeholder">
    <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="flex items-center">
            <span class="mr-2">❌</span>
            <span>{user_message}</span>
        </div>
        <div class="text-xs opacity-70 mt-2">Error: {str(e)[:100]}...</div>
    </div>
</div>'''
            
            return HTMLResponse(content=error_html)
    
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
        conversations = database_conversation_store.get_conversations(user_id)[:3]  # Get first 3
        
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
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        conversations = database_conversation_store.get_conversations(user_id)
        
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
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        logger.info(f"Deleting conversation {conversation_id} for user {user_id}")
        
        try:
            # Delete the conversation
            success = database_conversation_store.delete_conversation(user_id, conversation_id)
            
            if not success:
                logger.warning(f"Failed to delete conversation {conversation_id}")
                return gaia_error_message("Conversation not found or could not be deleted")
            
            # Get updated conversation list
            conversations = database_conversation_store.get_conversations(user_id)
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
        user = request.session.get("user", {})
        user_id = user.get("id", "dev-user-id")
        
        query = request.query_params.get("query", "").strip()
        logger.info(f"Searching conversations for user {user_id} with query: '{query}'")
        
        try:
            if not query:
                # If no query, return all conversations
                conversations = database_conversation_store.get_conversations(user_id)
            else:
                # Search conversations
                conversations = database_conversation_store.search_conversations(user_id, query)
            
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
                status_script = Script(NotStr(f'''
                    const status = document.getElementById('search-status');
                    if (status) {{
                        status.textContent = '{len(conversations)} results{f" for \\"{query}\\"" if query else ""}';
                    }}
                '''))
                return Div(result_html, status_script)
                
            conversation_items = [gaia_conversation_item(conv) for conv in conversations]
            
            # Create result with status update
            from fasthtml.core import Script, NotStr
            status_script = Script(NotStr(f'''
                const status = document.getElementById('search-status');
                if (status) {{
                    status.textContent = '{len(conversations)} result{\"s\" if len(conversations) != 1 else \"\"}{f" for \\"{query}\\"" if query else ""}';
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