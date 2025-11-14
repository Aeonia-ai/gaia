# app/services/kb/command_processor.py

import logging
from typing import Any, Callable, Coroutine, Dict
import time
import json

from app.shared.models.command_result import CommandResult

logger = logging.getLogger(__name__)

class ExperienceCommandProcessor:
    """
    The central orchestrator for all player commands.
    Receives commands and routes them to the appropriate handler.
    """
    def __init__(self):
        self._handlers: Dict[str, Callable[..., Coroutine[Any, Any, CommandResult]]] = {}

    def register(self, action: str, handler: Callable[..., Coroutine[Any, Any, CommandResult]]):
        """Register a handler for a specific action."""
        logger.info(f"Registering handler for action: {action}")
        self._handlers[action] = handler

    async def process_command(self, user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
        """Process an incoming command by routing it to the correct handler."""
        action = command_data.get("action")
        request_id = command_data.get("request_id", "unknown")

        if not action:
            return CommandResult(success=False, message_to_player="Command is missing the 'action' field.")

        # Admin Command Path: Route all @ commands through the admin router
        if action.startswith("@"):
            logger.info(f"Processing admin command '{action}' for user {user_id}")
            try:
                from .handlers.admin_command_router import route_admin_command
                return await route_admin_command(user_id, experience_id, command_data)
            except Exception as e:
                logger.error(f"Error in admin command router for '{action}': {e}", exc_info=True)
                return CommandResult(success=False, message_to_player=f"An error occurred while processing admin command: {action}")

        # Fast Path: Check for a registered, hardcoded Python handler first.
        handler = self._handlers.get(action)
        if handler:
            logger.info(f"Processing action '{action}' via fast path for user {user_id}")
            try:
                return await handler(user_id, experience_id, command_data)
            except Exception as e:
                logger.error(f"Error in fast path handler for action '{action}': {e}", exc_info=True)
                return CommandResult(success=False, message_to_player=f"An error occurred while processing the command: {action}")

        # Flexible Logic Path (LLM-Interpreted): If no hardcoded handler is found, pass to the kb_agent.
        from .kb_agent import kb_agent
        logger.info(f"No fast path handler for '{action}', routing to LLM-based system.")
        
        t_start = time.perf_counter()
        logger.info(json.dumps({
            "event": "timing_analysis",
            "request_id": request_id,
            "stage": "processing_llm_start",
            "action": action
        }))

        result = await kb_agent.process_llm_command(user_id, experience_id, command_data)
        
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(json.dumps({
            "event": "timing_analysis",
            "request_id": request_id,
            "stage": "processing_llm_end",
            "action": action,
            "elapsed_ms": elapsed_ms
        }))

        return result

# Create a singleton instance
command_processor = ExperienceCommandProcessor()
