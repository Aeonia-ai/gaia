"""
Unified State Manager for GAIA Experiences

Manages game state for all experiences using a unified "players as views" model.
Reads experience config.json files to determine state model (shared vs isolated).

Architecture:
- World state lives in: /experiences/{exp}/state/world.json
- Player state lives in: /players/{user}/{exp}/view.json
- Config determines if world state is shared (multiplayer) or copied per-player (isolated)

Author: GAIA Platform Team
Created: 2025-10-27
"""

import json
import fcntl
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StateManagerError(Exception):
    """Base exception for state manager errors"""
    pass


class ConfigValidationError(StateManagerError):
    """Raised when experience config is invalid"""
    pass


class StateNotFoundError(StateManagerError):
    """Raised when required state file doesn't exist"""
    pass


class StateLockError(StateManagerError):
    """Raised when unable to acquire state lock"""
    pass


class UnifiedStateManager:
    """
    Manages game state for all experiences using unified model.

    Key Responsibilities:
    - Load and validate experience configs
    - Read/write world state (shared or isolated)
    - Read/write player views
    - Bootstrap new players based on config
    - Handle file locking for concurrent access (shared model)
    - Optimistic versioning for conflict detection
    """

    def __init__(self, kb_root: Path):
        """
        Initialize state manager.

        Args:
            kb_root: Root path to knowledge base (contains /experiences/, /players/)
        """
        self.kb_root = Path(kb_root)
        self.experiences_path = self.kb_root / "experiences"
        self.players_path = self.kb_root / "players"

        # Cache loaded configs in memory
        self._config_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(f"UnifiedStateManager initialized with KB root: {kb_root}")

    # ===== CONFIG MANAGEMENT =====

    def load_config(self, experience: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load and validate experience config.

        Args:
            experience: Experience ID (e.g., "wylding-woods")
            force_reload: If True, reload even if cached

        Returns:
            Experience config dict

        Raises:
            ConfigValidationError: If config is invalid
        """
        # Return cached if available
        if not force_reload and experience in self._config_cache:
            return self._config_cache[experience]

        config_path = self.experiences_path / experience / "config.json"

        if not config_path.exists():
            raise ConfigValidationError(
                f"Config not found for experience '{experience}': {config_path}"
            )

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(
                f"Invalid JSON in config for '{experience}': {e}"
            )

        # Validate required fields
        self._validate_config(config, experience)

        # Apply defaults for optional fields
        config = self._apply_config_defaults(config)

        # Cache and return
        self._config_cache[experience] = config
        logger.info(f"Loaded config for experience '{experience}': {config['state']['model']} model")

        return config

    def _validate_config(self, config: Dict[str, Any], experience: str) -> None:
        """
        Validate experience config has required fields and valid values.

        Args:
            config: Config dict to validate
            experience: Experience ID (for error messages)

        Raises:
            ConfigValidationError: If validation fails
        """
        # Required fields
        required = ["id", "name", "version", "state"]
        for field in required:
            if field not in config:
                raise ConfigValidationError(
                    f"Config for '{experience}' missing required field: {field}"
                )

        # ID must match directory name
        if config["id"] != experience:
            raise ConfigValidationError(
                f"Config ID '{config['id']}' doesn't match directory name '{experience}'"
            )

        # State model must be valid
        state_model = config.get("state", {}).get("model")
        if state_model not in ["shared", "isolated"]:
            raise ConfigValidationError(
                f"Invalid state model '{state_model}' in '{experience}' "
                f"(must be 'shared' or 'isolated')"
            )

        # Shared model requires locking
        if state_model == "shared":
            locking = config.get("state", {}).get("coordination", {}).get("locking_enabled")
            if locking is False:
                raise ConfigValidationError(
                    f"Experience '{experience}' has state.model='shared' but "
                    f"locking_enabled=false (locking required for shared model)"
                )

        # Version format check (basic)
        version = config.get("version", "")
        if not version or version.count(".") != 2:
            raise ConfigValidationError(
                f"Invalid version format '{version}' in '{experience}' "
                f"(must be 'major.minor.patch')"
            )

        logger.debug(f"Config validation passed for '{experience}'")

    def _apply_config_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values for optional config fields.

        Args:
            config: Config dict (modified in place)

        Returns:
            Config with defaults applied
        """
        # State coordination defaults
        if "coordination" not in config["state"]:
            config["state"]["coordination"] = {}

        coord = config["state"]["coordination"]
        coord.setdefault("locking_enabled", config["state"]["model"] == "shared")
        coord.setdefault("lock_timeout_ms", 5000)
        coord.setdefault("optimistic_versioning", True)

        # Persistence defaults
        if "persistence" not in config["state"]:
            config["state"]["persistence"] = {}

        persist = config["state"]["persistence"]
        persist.setdefault("auto_save", True)
        persist.setdefault("save_interval_s", 30)
        persist.setdefault("backup_enabled", False)

        # Multiplayer defaults
        if "multiplayer" not in config:
            config["multiplayer"] = {}

        mp = config["multiplayer"]
        mp.setdefault("enabled", False)
        mp.setdefault("max_concurrent_players", None)
        mp.setdefault("player_visibility", "location")
        mp.setdefault("shared_entities", True)
        mp.setdefault("entity_ownership", "first_interaction")

        # Bootstrap defaults
        if "bootstrap" not in config:
            config["bootstrap"] = {}

        boot = config["bootstrap"]
        boot.setdefault("player_starting_location", None)
        boot.setdefault("player_starting_inventory", [])
        boot.setdefault("initialize_world_on_first_player", False)
        boot.setdefault("copy_template_for_isolated", True)
        boot.setdefault("world_template_path", "state/world.json")

        # Content defaults
        if "content" not in config:
            config["content"] = {}

        content = config["content"]
        content.setdefault("templates_path", "templates/")
        content.setdefault("state_path", "state/")
        content.setdefault("game_logic_path", "game-logic/")
        content.setdefault("markdown_enabled", True)
        content.setdefault("hierarchical_loading", True)

        # Capabilities defaults
        if "capabilities" not in config:
            config["capabilities"] = {}

        caps = config["capabilities"]
        caps.setdefault("gps_based", False)
        caps.setdefault("ar_enabled", False)
        caps.setdefault("voice_enabled", False)
        caps.setdefault("inventory_system", True)
        caps.setdefault("quest_system", False)
        caps.setdefault("combat_system", False)

        return config

    # ===== WORLD STATE MANAGEMENT =====

    async def get_world_state(
        self,
        experience: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get world state for experience.

        For shared model: Loads /experiences/{exp}/state/world.json
        For isolated model: Loads /players/{user}/{exp}/view.json (world portion)

        Args:
            experience: Experience ID
            user_id: User ID (required for isolated model)

        Returns:
            World state dict

        Raises:
            StateNotFoundError: If state file doesn't exist
            ConfigValidationError: If user_id required but not provided
        """
        config = self.load_config(experience)
        state_model = config["state"]["model"]

        if state_model == "shared":
            # Load shared world state
            world_path = self._get_world_state_path(experience, config)

            if not world_path.exists():
                raise StateNotFoundError(
                    f"World state not found for '{experience}': {world_path}"
                )

            with open(world_path, 'r') as f:
                world_state = json.load(f)

            logger.debug(f"Loaded shared world state for '{experience}'")
            return world_state

        else:  # isolated
            # Load player's copy of world state
            if not user_id:
                raise ConfigValidationError(
                    f"user_id required to get world state for isolated experience '{experience}'"
                )

            view_path = self._get_player_view_path(experience, user_id)

            if not view_path.exists():
                raise StateNotFoundError(
                    f"Player view not found for user '{user_id}' in '{experience}': {view_path}"
                )

            with open(view_path, 'r') as f:
                view = json.load(f)

            # For isolated model, view contains the world state
            logger.debug(f"Loaded isolated world state for '{experience}', user '{user_id}'")
            return view

    async def update_world_state(
        self,
        experience: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None,
        use_locking: bool = True
    ) -> Dict[str, Any]:
        """
        Update world state.

        For shared model: Updates /experiences/{exp}/state/world.json with locking
        For isolated model: Updates /players/{user}/{exp}/view.json directly

        Args:
            experience: Experience ID
            updates: Dict of updates to apply (merged with existing state)
            user_id: User ID (required for isolated model)
            use_locking: Use file locking (for shared model)

        Returns:
            Updated world state

        Raises:
            StateLockError: If unable to acquire lock
            StateNotFoundError: If state file doesn't exist
        """
        config = self.load_config(experience)
        state_model = config["state"]["model"]

        if state_model == "shared":
            return await self._update_shared_world_state(
                experience, config, updates, use_locking
            )
        else:  # isolated
            return await self._update_isolated_world_state(
                experience, config, updates, user_id
            )

    async def _update_shared_world_state(
        self,
        experience: str,
        config: Dict[str, Any],
        updates: Dict[str, Any],
        use_locking: bool
    ) -> Dict[str, Any]:
        """Update shared world state with optional file locking."""
        world_path = self._get_world_state_path(experience, config)

        if not world_path.exists():
            raise StateNotFoundError(
                f"World state not found for '{experience}': {world_path}"
            )

        locking_enabled = use_locking and config["state"]["coordination"]["locking_enabled"]
        lock_timeout_ms = config["state"]["coordination"]["lock_timeout_ms"]

        if locking_enabled:
            # Use file locking for concurrent access
            return await self._locked_update(world_path, updates, lock_timeout_ms)
        else:
            # Direct update (no locking)
            return await self._direct_update(world_path, updates)

    async def _update_isolated_world_state(
        self,
        experience: str,
        config: Dict[str, Any],
        updates: Dict[str, Any],
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Update isolated world state (player's copy)."""
        if not user_id:
            raise ConfigValidationError(
                f"user_id required to update isolated world state for '{experience}'"
            )

        view_path = self._get_player_view_path(experience, user_id)

        if not view_path.exists():
            raise StateNotFoundError(
                f"Player view not found for user '{user_id}' in '{experience}': {view_path}"
            )

        # No locking needed for isolated model (each player has own file)
        return await self._direct_update(view_path, updates)

    async def _locked_update(
        self,
        file_path: Path,
        updates: Dict[str, Any],
        lock_timeout_ms: int
    ) -> Dict[str, Any]:
        """
        Update file with exclusive file lock.

        Uses fcntl.flock for POSIX systems.
        """
        lock_timeout_s = lock_timeout_ms / 1000.0
        start_time = time.time()

        with open(file_path, 'r+') as f:
            # Try to acquire exclusive lock
            while True:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break  # Lock acquired
                except IOError:
                    # Lock held by another process
                    if time.time() - start_time > lock_timeout_s:
                        raise StateLockError(
                            f"Failed to acquire lock on {file_path} within {lock_timeout_ms}ms"
                        )
                    time.sleep(0.1)  # Wait 100ms before retry

            try:
                # Read current state
                f.seek(0)
                current_state = json.load(f)

                # Apply updates (merge)
                updated_state = self._merge_updates(current_state, updates)

                # Increment version for optimistic locking
                if "metadata" not in updated_state:
                    updated_state["metadata"] = {}
                updated_state["metadata"]["_version"] = updated_state.get("metadata", {}).get("_version", 0) + 1
                updated_state["metadata"]["last_modified"] = datetime.utcnow().isoformat() + "Z"

                # Write back
                f.seek(0)
                f.truncate()
                json.dump(updated_state, f, indent=2)
                f.flush()

                logger.debug(f"Locked update completed for {file_path}")
                return updated_state

            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    async def _direct_update(
        self,
        file_path: Path,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update file directly without locking.

        Used for isolated model or when locking disabled.
        """
        # Read current state
        with open(file_path, 'r') as f:
            current_state = json.load(f)

        # Apply updates
        updated_state = self._merge_updates(current_state, updates)

        # Increment version
        if "metadata" not in updated_state:
            updated_state["metadata"] = {}
        updated_state["metadata"]["_version"] = updated_state.get("metadata", {}).get("_version", 0) + 1
        updated_state["metadata"]["last_modified"] = datetime.utcnow().isoformat() + "Z"

        # Write back
        with open(file_path, 'w') as f:
            json.dump(updated_state, f, indent=2)

        logger.debug(f"Direct update completed for {file_path}")
        return updated_state

    def _merge_updates(self, current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge updates into current state (deep merge).

        Supports merge operation markers:
        - {"$append": item} - Append item to array
        - {"$remove": item} - Remove item from array (by matching item["id"])

        Args:
            current: Current state dict
            updates: Updates to apply

        Returns:
            Merged state dict
        """
        result = current.copy()

        for key, value in updates.items():
            # Check if value is a merge operation marker
            if isinstance(value, dict):
                if "$append" in value:
                    # Append operation: Add item to array
                    item_to_append = value["$append"]
                    logger.warning(f"[MERGE] Processing $append for key='{key}', current type={type(result.get(key))}")
                    if key not in result:
                        result[key] = []
                        logger.warning(f"[MERGE] Created new array for '{key}'")
                    if not isinstance(result[key], list):
                        logger.warning(f"[MERGE] Converting non-list '{key}' to list (was {type(result[key])})")
                        result[key] = [result[key]]
                    result[key].append(item_to_append)
                    logger.warning(f"[MERGE] Appended item to {key}: {item_to_append.get('id', 'unknown')}, new length={len(result[key])}")
                    continue

                elif "$remove" in value:
                    # Remove operation: Remove item from array by ID
                    item_to_remove = value["$remove"]
                    if key not in result or not isinstance(result[key], list):
                        logger.warning(f"Cannot remove from non-existent or non-list field '{key}'")
                        continue

                    # Remove item matching ID
                    item_id = item_to_remove.get("id") if isinstance(item_to_remove, dict) else item_to_remove
                    original_length = len(result[key])
                    result[key] = [item for item in result[key] if item.get("id") != item_id]
                    removed_count = original_length - len(result[key])
                    logger.debug(f"Removed {removed_count} item(s) with id '{item_id}' from {key}")
                    continue

                # Not a merge operation, check if we should do recursive merge
                elif key in result and isinstance(result[key], dict):
                    # Recursive merge for nested dicts
                    result[key] = self._merge_updates(result[key], value)
                    continue

            # Direct replacement for non-dict values or when key doesn't exist
            result[key] = value

        return result

    # ===== PLAYER VIEW MANAGEMENT =====

    async def get_player_view(
        self,
        experience: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get player's view for experience.

        Always loads /players/{user}/{exp}/view.json.
        Returns minimal view if doesn't exist (doesn't auto-create).

        Args:
            experience: Experience ID
            user_id: User ID

        Returns:
            Player view dict, or None if not found
        """
        view_path = self._get_player_view_path(experience, user_id)

        if not view_path.exists():
            logger.debug(f"Player view not found for user '{user_id}' in '{experience}'")
            return None

        with open(view_path, 'r') as f:
            view = json.load(f)

        logger.debug(f"Loaded player view for user '{user_id}' in '{experience}'")
        return view

    async def update_player_view(
        self,
        experience: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update player's view.

        Args:
            experience: Experience ID
            user_id: User ID
            updates: Updates to apply

        Returns:
            Updated player view
        """
        view_path = self._get_player_view_path(experience, user_id)

        if not view_path.exists():
            raise StateNotFoundError(
                f"Player view not found for user '{user_id}' in '{experience}': {view_path}"
            )

        # No locking needed for player views (each player has own file)
        return await self._direct_update(view_path, updates)

    # ===== BOOTSTRAP =====

    async def bootstrap_player(
        self,
        experience: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Bootstrap a new player for experience.

        Creates player view based on experience config:
        - Shared model: Create minimal view with empty inventory
        - Isolated model: Copy world template to player's view

        Args:
            experience: Experience ID
            user_id: User ID

        Returns:
            Created player view dict

        Raises:
            StateManagerError: If player already bootstrapped
        """
        config = self.load_config(experience)
        view_path = self._get_player_view_path(experience, user_id)

        # Check if already exists
        if view_path.exists():
            logger.warning(f"Player '{user_id}' already bootstrapped for '{experience}'")
            with open(view_path, 'r') as f:
                return json.load(f)

        # Create player directory if needed
        view_path.parent.mkdir(parents=True, exist_ok=True)

        state_model = config["state"]["model"]

        if state_model == "shared":
            # Shared model: Create minimal player view
            view = self._create_minimal_player_view(config, user_id)
        else:
            # Isolated model: Copy world template
            view = await self._copy_world_template_for_player(config, experience, user_id)

        # Write player view
        with open(view_path, 'w') as f:
            json.dump(view, f, indent=2)

        logger.info(f"Bootstrapped player '{user_id}' for '{experience}' ({state_model} model)")
        return view

    def _create_minimal_player_view(
        self,
        config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create minimal player view for shared model.

        Player view only tracks: position, inventory refs, personal progress.
        World state is in shared world.json file.
        """
        starting_location = config["bootstrap"]["player_starting_location"]
        starting_inventory = config["bootstrap"]["player_starting_inventory"]

        view = {
            "player": {
                "current_location": starting_location,
                "current_sublocation": None,
                "inventory": starting_inventory.copy(),
                "stats": {}
            },
            "progress": {
                "visited_locations": [],
                "discovered_sublocations": [],
                "quest_states": {},
                "achievements": [],
                "observations": {}
            },
            "session": {
                "started_at": datetime.utcnow().isoformat() + "Z",
                "last_active": datetime.utcnow().isoformat() + "Z",
                "turns_taken": 0
            },
            "metadata": {
                "_version": 1,
                "_created_at": datetime.utcnow().isoformat() + "Z"
            }
        }

        return view

    async def _copy_world_template_for_player(
        self,
        config: Dict[str, Any],
        experience: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Copy world template for isolated model.

        Player gets their own copy of entire world state.
        """
        world_template_path = self.experiences_path / experience / config["bootstrap"]["world_template_path"]

        if not world_template_path.exists():
            raise StateNotFoundError(
                f"World template not found for '{experience}': {world_template_path}"
            )

        # Load template
        with open(world_template_path, 'r') as f:
            template = json.load(f)

        # Initialize session info
        if "session" in template:
            template["session"]["id"] = f"{user_id}-{int(time.time())}"
            template["session"]["started_at"] = datetime.utcnow().isoformat() + "Z"

        # Add metadata
        if "metadata" not in template:
            template["metadata"] = {}
        template["metadata"]["_version"] = 1
        template["metadata"]["_copied_from_template"] = datetime.utcnow().isoformat() + "Z"
        template["metadata"]["_user_id"] = user_id

        return template

    # ===== PATH HELPERS =====

    def _get_world_state_path(self, experience: str, config: Dict[str, Any]) -> Path:
        """Get path to world state file."""
        state_path = config["content"]["state_path"]
        return self.experiences_path / experience / state_path / "world.json"

    def _get_player_view_path(self, experience: str, user_id: str) -> Path:
        """Get path to player view file."""
        return self.players_path / user_id / experience / "view.json"

    def _get_player_profile_path(self, user_id: str) -> Path:
        """Get path to player profile file."""
        return self.players_path / user_id / "profile.json"

    # ===== PLAYER PROFILE MANAGEMENT =====

    async def get_player_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player's global profile.

        Profile stores cross-experience data:
        - current_experience: Currently selected experience
        - preferences: Player preferences
        - global_stats: Cross-experience statistics

        Args:
            user_id: User ID

        Returns:
            Player profile dict, or None if doesn't exist
        """
        profile_path = self._get_player_profile_path(user_id)

        if not profile_path.exists():
            return None

        with open(profile_path, 'r') as f:
            profile = json.load(f)

        logger.debug(f"Loaded player profile for user '{user_id}'")
        return profile

    async def update_player_profile(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update player's global profile.

        Creates profile if doesn't exist.

        Args:
            user_id: User ID
            updates: Updates to apply

        Returns:
            Updated profile
        """
        profile_path = self._get_player_profile_path(user_id)

        # Create player directory if needed
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing or create new
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile = json.load(f)
        else:
            profile = {
                "user_id": user_id,
                "current_experience": None,
                "preferences": {},
                "global_stats": {
                    "total_play_time_minutes": 0,
                    "experiences_played": []
                },
                "metadata": {
                    "_version": 0,
                    "_created_at": datetime.utcnow().isoformat() + "Z"
                }
            }

        # Apply updates (deep merge)
        profile = self._merge_updates(profile, updates)

        # Increment version
        if "metadata" not in profile:
            profile["metadata"] = {}
        profile["metadata"]["_version"] = profile.get("metadata", {}).get("_version", 0) + 1
        profile["metadata"]["_last_updated"] = datetime.utcnow().isoformat() + "Z"

        # Write back
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

        logger.debug(f"Updated player profile for user '{user_id}'")
        return profile

    async def set_current_experience(
        self,
        user_id: str,
        experience: str
    ) -> Dict[str, Any]:
        """
        Set player's current experience.

        This is the main method for persisting experience selection.

        Args:
            user_id: User ID
            experience: Experience ID to set as current

        Returns:
            Updated profile
        """
        # Validate experience exists
        try:
            self.load_config(experience)
        except Exception as e:
            raise ConfigValidationError(f"Invalid experience '{experience}': {e}")

        # Update profile
        updates = {"current_experience": experience}

        # Track in global stats
        profile = await self.get_player_profile(user_id)
        if profile:
            experiences_played = profile.get("global_stats", {}).get("experiences_played", [])
            if experience not in experiences_played:
                updates["global_stats"] = {
                    "experiences_played": experiences_played + [experience]
                }

        profile = await self.update_player_profile(user_id, updates)

        logger.info(f"User '{user_id}' selected experience '{experience}'")
        return profile

    async def get_current_experience(self, user_id: str) -> Optional[str]:
        """
        Get player's currently selected experience.

        Args:
            user_id: User ID

        Returns:
            Experience ID or None
        """
        profile = await self.get_player_profile(user_id)

        if not profile:
            return None

        return profile.get("current_experience")

    # ===== UTILITY =====

    def list_experiences(self) -> List[str]:
        """
        List all available experiences.

        Returns:
            List of experience IDs
        """
        if not self.experiences_path.exists():
            return []

        experiences = []
        for path in self.experiences_path.iterdir():
            if path.is_dir() and (path / "config.json").exists():
                experiences.append(path.name)

        return sorted(experiences)

    def get_experience_info(self, experience: str) -> Dict[str, Any]:
        """
        Get high-level info about experience.

        Returns:
            Dict with name, description, capabilities, state model, etc.
        """
        config = self.load_config(experience)

        return {
            "id": config["id"],
            "name": config["name"],
            "version": config["version"],
            "description": config.get("description", ""),
            "state_model": config["state"]["model"],
            "multiplayer_enabled": config["multiplayer"]["enabled"],
            "capabilities": config["capabilities"]
        }
