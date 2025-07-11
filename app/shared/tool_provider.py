"""
Simplified Tool Provider for Gaia Platform
Provides minimal tool functionality for chat endpoints to work.
"""
from typing import List, Dict, Any

class ToolProvider:
    """Simplified tool provider for basic chat functionality."""
    
    @staticmethod
    async def get_tools_for_activity(activity: str = "generic") -> List[Dict[str, Any]]:
        """
        Get tools for a specific activity.
        Returns empty list for now - tools can be added later.
        """
        return []
    
    @staticmethod
    async def initialize_tools():
        """Initialize the tool system."""
        pass