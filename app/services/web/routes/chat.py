"""Chat interface routes"""
import json
from datetime import datetime
from fasthtml.components import Div, H2
from starlette.responses import HTMLResponse
from app.services.web.components.gaia_ui import (
    gaia_layout, gaia_conversation_item, gaia_message_bubble,
    gaia_chat_input, gaia_loading_spinner, gaia_error_message
)
from app.services.web.utils.gateway_client import GaiaAPIClient
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
        
        # For now, use empty conversations list
        conversations = []
        
        # Build sidebar content
        sidebar_content = Div(
            *[gaia_conversation_item(conv) for conv in conversations],
            cls="space-y-2"
        )
        
        # Initialize HTMX properly and handle form clearing
        from fasthtml.core import NotStr
        debug_script = Script(NotStr('''
            document.addEventListener('DOMContentLoaded', function() {
                const form = document.getElementById('chat-form');
                if (form) {
                    // Ensure HTMX processes the form
                    htmx.process(form);
                    
                    // Process entire body after a short delay
                    setTimeout(() => {
                        htmx.process(document.body);
                    }, 100);
                    
                    // Add event listener for form clearing
                    document.body.addEventListener('htmx:afterRequest', function(evt) {
                        if (evt.detail.elt && evt.detail.elt.id === 'chat-form') {
                            evt.detail.elt.reset();
                            // Hide welcome message and show messages
                            document.getElementById('messages').classList.remove('hidden');
                            const welcome = document.getElementById('messages').parentElement.querySelector('.flex-1.flex.flex-col.items-center');
                            if (welcome) welcome.classList.add('hidden');
                        }
                    });
                }
            });
        '''))
        
        # Main content - empty chat area
        main_content = Div(
            # Welcome message
            Div(
                H2(f"Welcome back, {user.get('name', 'User')}!", 
                   cls="text-2xl text-white mb-4"),
                Div("Start a conversation by typing below", 
                    cls="text-slate-400"),
                cls="flex-1 flex flex-col items-center justify-center text-center"
            ),
            # Messages container
            Div(
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4 hidden"
            ),
            gaia_chat_input(),
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
        jwt_token = request.session.get("jwt_token")
        
        try:
            # Get conversation with messages
            async with GaiaAPIClient() as client:
                conversation = await client.get_conversation(conversation_id, jwt_token)
            
            # Build message list
            messages = Div(
                *[
                    gaia_message_bubble(
                        msg["content"],
                        role=msg["role"],
                        timestamp=msg.get("created_at", "")
                    )
                    for msg in conversation.get("messages", [])
                ],
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4"
            )
            
            # Return chat area
            return Div(
                messages,
                gaia_chat_input(),
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
        
        # For now, just return a fresh chat interface
        return Div(
            # Welcome message
            Div(
                H2(f"Welcome back, {user.get('name', 'User')}!", 
                   cls="text-2xl text-white mb-4"),
                Div("Start a conversation by typing below", 
                    cls="text-slate-400"),
                cls="flex-1 flex flex-col items-center justify-center text-center"
            ),
            # Messages container
            Div(
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4 hidden"
            ),
            gaia_chat_input(),
            cls="flex flex-col h-full"
        )
    
    @app.post("/api/chat/send")
    async def send_message(request):
        """Send chat message"""
        logger.info("Chat send endpoint called")
        
        jwt_token = request.session.get("jwt_token")
        form_data = await request.form()
        message = form_data.get("message")
        
        logger.info(f"Received message: {message}")
        
        # For now, use a simple ID
        import uuid
        message_id = str(uuid.uuid4())[:8]
        
        # Add user message to UI immediately
        user_message = gaia_message_bubble(
            message,
            role="user",
            timestamp=datetime.now().strftime("%I:%M %p")
        )
        
        # Add loading indicator with proper HTML structure
        loading_html = f'''<div id="loading-{message_id}" class="flex justify-start mb-4 assistant-message-placeholder">
    <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="flex justify-center items-center">
            <div class="w-8 h-8 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
    </div>
</div>'''
        
        # URL encode the message to avoid HTML entity issues
        from urllib.parse import quote
        encoded_message = quote(message, safe='')
        
        # Create HTML manually to avoid FastHTML's automatic escaping
        user_message_html = str(user_message)
        
        # Build raw HTML response to avoid entity encoding
        response_html = f'''<div hx-trigger="load" hx-get="/api/chat/stream?message={encoded_message}&id={message_id}" hx-target="#loading-{message_id}" hx-swap="outerHTML">
{user_message_html}
{loading_html}
</div>'''
        
        logger.info("Returning chat response HTML")
        return HTMLResponse(content=response_html)
    
    @app.get("/api/chat/stream")
    async def stream_response(request):
        """Stream chat response"""
        jwt_token = request.session.get("jwt_token")
        message = request.query_params.get("message")
        message_id = request.query_params.get("id", "unknown")
        
        logger.info(f"Stream response requested - message: {message}, id: {message_id}")
        
        try:
            # Prepare messages for API call
            messages = [{"role": "user", "content": message}]
            
            # Get non-streaming response for now
            async with GaiaAPIClient() as client:
                response = await client.chat_completion(messages, jwt_token)
                logger.info(f"Gateway response: {response}")
            
            # v0.2 format returns response directly
            response_content = response.get("response", "Sorry, I couldn't process that.")
            
            # Return complete assistant message
            assistant_html = str(gaia_message_bubble(
                response_content,
                role="assistant",
                timestamp=datetime.now().strftime("%I:%M %p")
            ))
            
            return HTMLResponse(content=assistant_html)
            
        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            error_html = str(gaia_error_message("Failed to get response"))
            return HTMLResponse(content=error_html)