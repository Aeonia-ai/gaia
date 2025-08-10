"""
Simplified Prompt Manager for Gaia Platform
Provides basic system prompt functionality.
"""

class PromptManager:
    """Simplified prompt manager for basic chat functionality."""
    
    @staticmethod
    async def get_system_prompt(user_id: str = None) -> str:
        """
        Get system prompt for a user based on their persona.
        """
        if not user_id:
            return "You are a helpful AI assistant."
        
        try:
            from app.services.chat.persona_service_postgres import PostgresPersonaService
            persona_service = PostgresPersonaService()
            
            # Try user's persona first, then default
            persona = await persona_service.get_user_persona(user_id)
            if not persona:
                persona = await persona_service.get_default_persona()
            
            if persona and persona.system_prompt:
                return persona.system_prompt
                
        except Exception:
            pass
        
        return "You are a helpful AI assistant."