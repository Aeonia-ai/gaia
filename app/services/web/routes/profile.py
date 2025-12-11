"""Profile and account management routes"""
from fasthtml.components import Div
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.services.web.components.gaia_ui import (
    gaia_profile_page, gaia_success_message, gaia_error_message, gaia_settings_page
)
from app.services.web.utils.database_conversation_store import database_conversation_store
from app.services.web.utils.chat_service_client import chat_service_client
from app.shared.logging import setup_service_logger

logger = setup_service_logger("profile_routes")


def setup_routes(app):
    """Setup profile routes"""
    
    @app.get("/profile")
    async def profile_page(request):
        """User profile page"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        
        logger.info(f"Profile page accessed - JWT: {bool(jwt_token)}, User: {bool(user)}")
        logger.info(f"Session contents: {dict(request.session)}")
        
        if not jwt_token or not user:
            logger.warning("Profile access denied - redirecting to login")
            return RedirectResponse(url="/login", status_code=302)
        
        user_id = user.get("id", "dev-user-id")
        
        # Get user statistics
        try:
            stats = database_conversation_store.get_conversation_stats(user_id)
            logger.info(f"Retrieved stats for user {user_id}: {stats}")
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            stats = {"total_conversations": 0, "total_messages": 0}
        
        return gaia_profile_page(user, stats)
    
    @app.post("/api/profile/update")
    async def update_profile(request):
        """Update user profile information"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        
        if not jwt_token or not user:
            return gaia_error_message("Not authenticated")
        
        try:
            form_data = await request.form()
            name = form_data.get("name", "").strip()
            email = form_data.get("email", "").strip()
            
            if not name or not email:
                return gaia_error_message("Name and email are required")
            
            # Update user session data
            user["name"] = name
            user["email"] = email
            request.session["user"] = user
            
            logger.info(f"Updated profile for user {user.get('id')}: name={name}, email={email}")
            return gaia_success_message("Profile updated successfully!")
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return gaia_error_message("Failed to update profile")
    
    @app.post("/api/profile/change-password")
    async def change_password(request):
        """Change user password"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        
        if not jwt_token or not user:
            return gaia_error_message("Not authenticated")
        
        try:
            form_data = await request.form()
            current_password = form_data.get("current_password", "")
            new_password = form_data.get("new_password", "")
            confirm_password = form_data.get("confirm_password", "")
            
            if not current_password or not new_password or not confirm_password:
                return gaia_error_message("All password fields are required")
            
            if new_password != confirm_password:
                return gaia_error_message("New passwords do not match")
            
            if len(new_password) < 6:
                return gaia_error_message("New password must be at least 6 characters")
            
            # For now, we'll simulate password change success
            # In a real implementation, this would validate the current password
            # and update it via Supabase Auth API
            logger.info(f"Password change requested for user {user.get('id')}")
            
            # TODO: Implement actual password change via Supabase Auth
            # For now, just return success for demo purposes
            return gaia_success_message("Password changed successfully!")
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return gaia_error_message("Failed to change password")
    
    @app.post("/api/profile/preferences")
    async def update_preferences(request):
        """Update user preferences"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        
        if not jwt_token or not user:
            return gaia_error_message("Not authenticated")
        
        try:
            form_data = await request.form()
            theme = form_data.get("theme", "dark")
            
            # Store preferences in session (in a real app, this would go to database)
            if "preferences" not in request.session:
                request.session["preferences"] = {}
            
            request.session["preferences"]["theme"] = theme
            
            logger.info(f"Updated preferences for user {user.get('id')}: theme={theme}")
            return gaia_success_message("Preferences saved successfully!")
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return gaia_error_message("Failed to save preferences")

    # =====================
    # Settings Page Routes
    # =====================

    @app.get("/settings")
    async def settings_page(request):
        """Settings page for single-chat mode"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})

        if not jwt_token or not user:
            logger.warning("Settings access denied - redirecting to login")
            return RedirectResponse(url="/login", status_code=302)

        return gaia_settings_page(user)

    @app.post("/api/settings/clear-history")
    async def clear_history(request):
        """Clear user's chat history"""
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})

        if not jwt_token or not user:
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        user_id = user.get("id", "dev-user-id")

        try:
            # Get the user's primary conversation
            conversation = await chat_service_client.get_or_create_primary_conversation(user_id, jwt_token)
            conversation_id = conversation.get("id")

            if conversation_id:
                # Clear messages from the conversation
                await chat_service_client.clear_messages(conversation_id, jwt_token)
                logger.info(f"Cleared chat history for user {user_id}, conversation {conversation_id}")

            return JSONResponse({"success": True})

        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)