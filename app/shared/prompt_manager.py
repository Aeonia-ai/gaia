"""
Simplified Prompt Manager for Gaia Platform
Provides basic system prompt functionality.
"""

class PromptManager:
    """Simplified prompt manager for basic chat functionality."""
    
    @staticmethod
    async def get_system_prompt(user_id: str = None) -> str:
        """
        Get system prompt for a user.
        Returns a basic prompt for now.
        """
        return "You are a helpful AI assistant."