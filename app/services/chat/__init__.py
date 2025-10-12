"""
Chat service module.

This module provides chat functionality including:
- Unified chat handling with intelligent routing
- Conversation storage and retrieval
- Real streaming support with StreamBuffer
- KB and MCP agent integration
"""

__all__ = [
    "UnifiedChatHandler",
    "ConversationStore",
    "StreamBuffer",
    "chat_stream",
    "streaming_implementation",
    "mcp_agent_streaming",
]
