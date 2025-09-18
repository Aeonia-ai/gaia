"""
Game State Handler for Option 3: JSON blocks in message content.

This module manages game state by embedding it as JSON blocks within
assistant message content, leveraging existing PostgreSQL conversation
storage without schema changes.
"""
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class GameStateHandler:
    """
    Manages game state embedded in message content as JSON blocks.

    Format:
    ```json:game_state
    {"room": "forest", "inventory": ["lamp"], "score": 5}
    ```
    """

    JSON_BLOCK_PATTERN = re.compile(
        r'```json:game_state\s*\n(.*?)\n```',
        re.DOTALL | re.MULTILINE
    )

    def extract_game_state(self, messages: list) -> Optional[Dict[str, Any]]:
        """
        Extract the most recent game state from conversation messages.

        Args:
            messages: List of conversation messages (newest first recommended)

        Returns:
            Most recent game state dict or None if no state found
        """
        # Search messages in reverse order (newest first)
        for message in reversed(messages):
            if message.get("role") == "assistant":
                content = message.get("content", "")
                state = self.extract_state_from_content(content)
                if state:
                    logger.info(f"Found game state in message: {state.get('room', 'unknown')}")
                    return state

        logger.info("No existing game state found in conversation")
        return None

    def extract_state_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract game state JSON block from message content.

        Args:
            content: Message content that may contain game state

        Returns:
            Parsed game state dict or None
        """
        match = self.JSON_BLOCK_PATTERN.search(content)
        if match:
            try:
                state_json = match.group(1).strip()
                return json.loads(state_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse game state JSON: {e}")
                return None
        return None

    def embed_game_state(self, content: str, state: Dict[str, Any]) -> str:
        """
        Embed game state into message content as a JSON block.

        Args:
            content: The main message content
            state: Game state dictionary to embed

        Returns:
            Content with embedded game state
        """
        # Remove any existing game state blocks
        content = self.JSON_BLOCK_PATTERN.sub('', content).strip()

        # Add timestamp to state for tracking
        state["last_updated"] = datetime.utcnow().isoformat()

        # Format state as JSON block
        state_json = json.dumps(state, indent=2)
        state_block = f"\n\n```json:game_state\n{state_json}\n```"

        return content + state_block

    def parse_game_command(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse user input to identify game commands and parameters.

        Args:
            user_input: Raw user input

        Returns:
            Tuple of (command_type, parameters)
        """
        input_lower = user_input.lower().strip()

        # Game initialization commands
        if any(phrase in input_lower for phrase in ["play zork", "start game", "new game"]):
            return ("start_game", {"game": "zork"})

        # Movement commands
        movement_words = ["go", "move", "walk", "run", "head", "travel"]
        directions = ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"]

        for direction in directions:
            if direction in input_lower.split():
                return ("move", {"direction": direction})

        # Inventory and interaction
        if any(word in input_lower for word in ["look", "examine", "inspect"]):
            target = user_input.lower()
            for word in ["look at", "look", "examine", "inspect"]:
                target = target.replace(word, "").strip()
            return ("look", {"target": target})

        if any(word in input_lower for word in ["take", "get", "pick up", "grab"]):
            item = user_input
            for word in ["take", "get", "pick up", "grab"]:
                item = item.replace(word, "").strip()
            return ("take", {"item": item})

        # Check for exact inventory commands (not just 'i' which could be in other words)
        if input_lower in ["inventory", "inv", "i"]:
            return ("inventory", {})

        # Check for "open" commands
        if "open" in input_lower:
            target = user_input.replace("open", "").strip()
            return ("open", {"target": target})

        if any(word in input_lower for word in ["use", "apply"]):
            return ("use", {"item": user_input.replace("use", "").replace("apply", "").strip()})

        # Save/Load commands
        if "save" in input_lower:
            return ("save_game", {})

        if "load" in input_lower:
            return ("load_game", {})

        if "quit" in input_lower or "exit game" in input_lower:
            return ("quit_game", {})

        # Default: treat as a general game command
        return ("game_command", {"input": user_input})

    def format_kb_game_query(self, command: str, params: Dict[str, Any],
                            current_state: Optional[Dict[str, Any]] = None) -> str:
        """
        Format a game command into a KB Agent query.

        Args:
            command: Command type
            params: Command parameters
            current_state: Current game state

        Returns:
            Formatted query for KB Agent
        """
        if command == "start_game":
            return f"Initialize a new Zork game session and return the starting room description"

        elif command == "move":
            direction = params.get("direction", "")
            current_room = current_state.get("room", "unknown") if current_state else "unknown"
            return f"In Zork, from room '{current_room}', move {direction} and describe the new location"

        elif command == "look":
            target = params.get("target", "")
            current_room = current_state.get("room", "unknown") if current_state else "unknown"
            if target:
                return f"In Zork room '{current_room}', examine {target}"
            else:
                return f"In Zork, describe the current room '{current_room}' in detail"

        elif command == "take":
            item = params.get("item", "")
            current_room = current_state.get("room", "unknown") if current_state else "unknown"
            return f"In Zork room '{current_room}', take the item: {item}"

        elif command == "inventory":
            inventory = current_state.get("inventory", []) if current_state else []
            return f"List current Zork inventory items: {inventory}"

        elif command == "use":
            item = params.get("item", "")
            current_room = current_state.get("room", "unknown") if current_state else "unknown"
            return f"In Zork room '{current_room}', use item: {item}"

        else:
            # General game command
            user_input = params.get("input", "")
            current_room = current_state.get("room", "unknown") if current_state else "unknown"
            state_context = f"Current room: {current_room}"
            if current_state and current_state.get("inventory"):
                state_context += f", Inventory: {current_state['inventory']}"

            return f"In Zork game ({state_context}), execute command: {user_input}"

    def parse_kb_response_for_state(self, kb_response: str,
                                   current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse KB Agent response to extract state changes.

        Args:
            kb_response: Response from KB Agent
            current_state: Current game state to update

        Returns:
            Updated game state
        """
        if current_state is None:
            current_state = {
                "game": "zork",
                "room": "west_of_house",
                "inventory": [],
                "score": 0,
                "moves": 0
            }

        # Create a copy to avoid mutating original
        new_state = current_state.copy()
        new_state["moves"] = new_state.get("moves", 0) + 1

        # Parse room changes (look for common patterns)
        room_patterns = [
            r"You (?:are|stand|find yourself) (?:now )?(?:in|at) (?:the )?([^\.]+)",
            r"This is (?:the )?([^\.]+)",
            r"([^\.]+) - You are here",
        ]

        for pattern in room_patterns:
            match = re.search(pattern, kb_response, re.IGNORECASE)
            if match:
                room_name = match.group(1).strip().lower().replace(" ", "_")
                # Clean up common prefixes
                room_name = room_name.replace("the_", "").replace("a_", "")
                new_state["room"] = room_name
                logger.info(f"Detected room change to: {room_name}")
                break

        # Parse inventory changes
        if "you take" in kb_response.lower() or "you pick up" in kb_response.lower():
            # Extract item name
            item_match = re.search(r"(?:take|pick up) (?:the )?([^\.]+)", kb_response, re.IGNORECASE)
            if item_match:
                item = item_match.group(1).strip().lower()
                if item not in new_state.get("inventory", []):
                    new_state.setdefault("inventory", []).append(item)
                    logger.info(f"Added to inventory: {item}")

        # Parse score changes
        score_match = re.search(r"score:?\s*(\d+)", kb_response, re.IGNORECASE)
        if score_match:
            new_state["score"] = int(score_match.group(1))
            logger.info(f"Score updated to: {new_state['score']}")

        return new_state

    def create_game_response(self, kb_response: str, game_state: Dict[str, Any]) -> str:
        """
        Create a formatted game response with embedded state.

        Args:
            kb_response: Raw response from KB Agent
            game_state: Current game state to embed

        Returns:
            Formatted response with embedded state
        """
        # Format the game response nicely
        formatted_response = f"🎮 **Zork Adventure**\n\n{kb_response}"

        # Add game status
        if game_state:
            status_parts = []
            if "room" in game_state:
                status_parts.append(f"📍 Location: {game_state['room'].replace('_', ' ').title()}")
            if "score" in game_state:
                status_parts.append(f"🏆 Score: {game_state['score']}")
            if "moves" in game_state:
                status_parts.append(f"👣 Moves: {game_state['moves']}")

            if status_parts:
                formatted_response += "\n\n---\n" + " | ".join(status_parts)

        # Embed the game state
        return self.embed_game_state(formatted_response, game_state)


# Singleton instance
game_state_handler = GameStateHandler()