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

from app.services.kb.template_loader import get_template_loader

logger = logging.getLogger(__name__)

# NATS integration for real-time world updates
try:
    from app.shared.nats_client import NATSClient, NATSSubjects
    from app.shared.events import WorldUpdateEvent
    NATS_AVAILABLE = True
except ImportError:
    logger.warning("NATS modules not available - real-time updates disabled")
    NATS_AVAILABLE = False


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

    def __init__(
        self,
        kb_root: Path,
        nats_client: Optional['NATSClient'] = None,
        connection_manager: Optional['ExperienceConnectionManager'] = None
    ):
        """
        Initialize state manager.

        Args:
            kb_root: Root path to knowledge base (contains /experiences/, /players/)
            nats_client: Optional NATS client for real-time world update events
            connection_manager: Optional connection manager for client version tracking
        """
        self.kb_root = Path(kb_root)
        self.experiences_path = self.kb_root / "experiences"
        self.players_path = self.kb_root / "players"

        # Cache loaded configs in memory
        self._config_cache: Dict[str, Dict[str, Any]] = {}

        # NATS client for real-time updates (optional)
        self.nats_client = nats_client if NATS_AVAILABLE else None

        # Connection manager for client version tracking (optional)
        self.connection_manager = connection_manager

        # Template loader for entity blueprints
        self.template_loader = get_template_loader(kb_root)

        logger.info(f"UnifiedStateManager initialized with KB root: {kb_root}")
        if self.nats_client:
            logger.info("Real-time NATS updates enabled")
        if self.connection_manager:
            logger.info("Client version tracking enabled")

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

    async def _publish_world_update(
        self,
        experience: str,
        user_id: str,
        changes: Dict[str, Any],
        base_version: int,
        snapshot_version: int
    ) -> None:
        """
        Publish world state update to NATS for real-time client synchronization (v0.4).

        This method implements graceful degradation - if NATS is unavailable or
        publishing fails, the error is logged but game logic continues unaffected.

        Args:
            experience: Experience ID (e.g., 'wylding-woods')
            user_id: User ID that this update applies to
            changes: State delta describing what changed (v0.3 format from caller)
            base_version: Version number this delta applies on top of
            snapshot_version: New version number after applying delta
        """
        logger.warning(f"[PUBLISH-DEBUG] _publish_world_update called: exp={experience}, user={user_id}, changes={list(changes.keys())}")

        if not NATS_AVAILABLE or not self.nats_client:
            # NATS not configured - this is expected in many deployments
            logger.warning(f"[PUBLISH-DEBUG] NATS not available: NATS_AVAILABLE={NATS_AVAILABLE}, nats_client={'present' if self.nats_client else 'None'}")
            return

        if not self.nats_client.is_connected:
            logger.warning(f"[PUBLISH-DEBUG] NATS client not connected - skipping world update publish")
            return

        logger.warning(f"[PUBLISH-DEBUG] Proceeding with publish - NATS connected")
        try:
            # Convert v0.3 dict format to v0.4 array format
            logger.warning(f"[PUBLISH-DEBUG] Calling _format_world_update_changes...")
            formatted_changes = await self._format_world_update_changes(changes, experience, user_id)
            logger.warning(f"[PUBLISH-DEBUG] Formatted changes count: {len(formatted_changes)}")

            # Create world update event (v0.4)
            logger.warning(f"[PUBLISH-DEBUG] Creating WorldUpdateEvent...")
            event = WorldUpdateEvent(
                experience=experience,
                user_id=user_id,
                base_version=base_version,
                snapshot_version=snapshot_version,
                changes=formatted_changes,
                timestamp=int(time.time() * 1000),  # Unix timestamp in milliseconds
                metadata={
                    "source": "kb_service",
                    "state_model": "shared"  # TODO: Get from config if needed
                }
            )

            # Publish to user-specific NATS subject
            subject = NATSSubjects.world_update_user(user_id)
            logger.warning(f"[PUBLISH-DEBUG] Publishing to subject: {subject}")
            await self.nats_client.publish(subject, event.model_dump())

            logger.warning(
                f"[PUBLISH-DEBUG] ✅ Published world_update v0.4 to NATS: "
                f"experience={experience}, user={user_id}, "
                f"base_version={base_version}, snapshot_version={snapshot_version}, "
                f"changes_count={len(formatted_changes)}, subject={subject}"
            )

        except Exception as e:
            # Graceful degradation: log error but don't raise
            # Game logic must continue even if real-time updates fail
            logger.warning(
                f"Failed to publish world_update to NATS "
                f"(experience={experience}, user={user_id}): {e}"
            )

    def _flatten_nested_changes(
        self,
        changes: Dict[str, Any],
        prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Convert nested dict changes to flattened path format.

        Recursively traverses nested dicts and builds dotted path strings as keys.
        Stops at operation markers ($append, $remove) and preserves them.

        Args:
            changes: Nested dict changes (e.g., {"locations": {"store": {"items": {"$remove": ...}}}})
            prefix: Current path prefix (used during recursion)

        Returns:
            Flattened dict (e.g., {"world.locations.store.items": {"$remove": ...}})

        Example:
            >>> _flatten_nested_changes({"locations": {"woander_store": {"areas": {"main_room": {"spots": {"spot_1": {"items": {"$remove": {"instance_id": "bottle_mystery"}}}}}}}})
            {'world.locations.woander_store.areas.main_room.spots.spot_1.items': {'$remove': {'instance_id': 'bottle_mystery'}}}
        """
        result = {}

        for key, value in changes.items():
            # Build current path
            current_path = f"{prefix}.{key}" if prefix else key

            # Check if this is an operation marker
            if isinstance(value, dict) and ("$append" in value or "$remove" in value):
                # Preserve operation, add to result
                # Add "world" prefix for world state changes
                if current_path.startswith("locations."):
                    current_path = f"world.{current_path}"
                result[current_path] = value

            # Check if this is a nested dict (not an operation)
            elif isinstance(value, dict):
                # Recursively flatten
                nested_result = self._flatten_nested_changes(value, current_path)
                result.update(nested_result)

            else:
                # Scalar value - keep as-is (shouldn't happen for state updates, but handle it)
                result[current_path] = value

        return result

    async def _format_world_update_changes(
        self,
        changes: Dict[str, Any],
        experience: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Convert v0.3 dict-based changes to v0.4 array format with instance_id/template_id.

        Handles both flattened path format (e.g., {"player.inventory": {...}}) and
        nested dict format (e.g., {"locations": {"woander_store": {...}}}).

        Args:
            changes: v0.3 format changes (dict with paths as keys OR nested dicts)
            experience: Experience ID
            user_id: User ID

        Returns:
            v0.4 format changes (array of change objects)
        """
        formatted_changes = []

        # Convert nested dicts to flattened paths first
        flattened_changes = self._flatten_nested_changes(changes)

        for path, change_data in flattened_changes.items():
            # Handle player.inventory changes
            if path == "player.inventory" and isinstance(change_data, dict) and "$append" in change_data:
                # Item added to inventory
                item_data = change_data["$append"]
                instance_id = item_data.get("id") or item_data.get("instance_id")

                # Load template data if we have template_id
                template_id = item_data.get("template_id")
                merged_item = await self._merge_item_with_template(
                    experience=experience,
                    instance_id=instance_id,
                    template_id=template_id,
                    item_data=item_data
                )

                add_change = {
                    "operation": "add",
                    "instance_id": instance_id,  # Top-level instance_id for Unity tracking
                    "area_id": None,
                    "path": "player.inventory",
                    "item": merged_item
                }
                logger.warning(
                    f"[FORMAT-DEBUG] Adding ADD operation: "
                    f"path=player.inventory, instance_id={instance_id}, has_item_data={merged_item is not None}"
                )
                formatted_changes.append(add_change)

            # Handle world.locations changes (item removed from world)
            elif path.startswith("world.locations.") and "items" in path:
                # Extract location, area, and spot from path
                # Example v0.5: world.locations.woander_store.areas.main_room.spots.spot_4.items
                parts = path.split(".")
                location_id = parts[2] if len(parts) > 2 else None
                area_id = parts[4] if len(parts) > 4 else None
                spot_id = parts[6] if len(parts) > 6 and parts[5] == "spots" else None

                if isinstance(change_data, dict) and "$remove" in change_data:
                    # Item removed from world
                    item_to_remove = change_data["$remove"]
                    instance_id = item_to_remove.get("id") or item_to_remove.get("instance_id")

                    remove_change = {
                        "operation": "remove",
                        "area_id": area_id,
                        "spot_id": spot_id,  # v0.5 spot hierarchy support
                        "instance_id": instance_id
                    }
                    logger.warning(
                        f"[FORMAT-DEBUG] Adding REMOVE operation: "
                        f"path={path}, instance_id={instance_id}, area_id={area_id}, spot_id={spot_id}"
                    )
                    formatted_changes.append(remove_change)

        # Log summary of formatted changes
        change_summary = [f"op={c.get('operation')}, area={c.get('area_id')}" for c in formatted_changes]
        logger.warning(
            f"[FORMAT-DEBUG] Formatted {len(formatted_changes)} change(s): {change_summary}"
        )
        return formatted_changes

    async def _merge_item_with_template(
        self,
        experience: str,
        instance_id: str,
        template_id: str,
        item_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge item instance data with template properties.

        Args:
            experience: Experience ID
            instance_id: Item instance ID
            template_id: Item template ID
            item_data: Item instance data

        Returns:
            Merged item with template properties
        """
        # Load template if template_id provided
        if template_id and self.template_loader:
            try:
                template = await self.template_loader.load_template(
                    experience=experience,
                    entity_type="items",
                    template_id=template_id
                )
                if template:
                    # Merge template + instance
                    return self.template_loader.merge_template_instance(
                        template=template,
                        instance={
                            "instance_id": instance_id,
                            "template_id": template_id,
                            **item_data
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to load template {template_id}: {e}")

        # Fallback: just use instance data with normalized fields
        return {
            "instance_id": instance_id,
            "template_id": template_id,
            "type": item_data.get("type", template_id),
            **{k: v for k, v in item_data.items() if k not in ("id", "type")}
        }

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
            # ASSUMES: Player has been initialized via ensure_player_initialized()
            if not user_id:
                raise ConfigValidationError(
                    f"user_id required to get world state for isolated experience '{experience}'"
                )

            view_path = self._get_player_view_path(experience, user_id)

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
        use_locking: bool = True,
        connection_id: Optional[str] = None
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
            connection_id: Optional connection ID for client version tracking

        Returns:
            Updated world state

        Raises:
            StateLockError: If unable to acquire lock
            StateNotFoundError: If state file doesn't exist
        """
        config = self.load_config(experience)
        state_model = config["state"]["model"]

        # Get base version before update (for NATS event)
        # CRITICAL: Use client's version if available, not server's version!
        # This ensures deltas can be applied by Unity's version-checking system.
        if connection_id and self.connection_manager:
            base_version = self.connection_manager.get_client_version(connection_id)
            logger.debug(
                f"[VERSION-TRACK] Using client base_version: "
                f"connection={connection_id}, base_version={base_version}"
            )
        else:
            # Fallback: Use server's version (for non-WebSocket updates)
            if state_model == "shared":
                world_path = self._get_world_state_path(experience, config)
                current_state = json.loads(world_path.read_text()) if world_path.exists() else {}
            else:  # isolated
                if user_id:
                    view_path = self._get_player_view_path(experience, user_id)
                    current_state = json.loads(view_path.read_text()) if view_path.exists() else {}
                else:
                    current_state = {}
            base_version = current_state.get("metadata", {}).get("_version", 0)
            logger.debug(
                f"[VERSION-TRACK] Using server base_version (fallback): base_version={base_version}"
            )

        # Perform state update
        if state_model == "shared":
            updated_state = await self._update_shared_world_state(
                experience, config, updates, use_locking
            )
        else:  # isolated
            updated_state = await self._update_isolated_world_state(
                experience, config, updates, user_id
            )

        # Get new version after update
        snapshot_version = updated_state.get("metadata", {}).get("_version", 0)

        # Publish real-time update to NATS (if user_id available)
        if user_id:
            await self._publish_world_update(
                experience=experience,
                user_id=user_id,
                changes=updates,
                base_version=base_version,
                snapshot_version=snapshot_version
            )

            # Update client's tracked version after successful delta publish
            if connection_id and self.connection_manager:
                self.connection_manager.update_client_version(connection_id, snapshot_version)
                logger.debug(
                    f"[VERSION-TRACK] Updated client to new snapshot_version: "
                    f"connection={connection_id}, version={snapshot_version}"
                )

        return updated_state

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
        """
        Update isolated world state (player's copy).

        ASSUMES: Player has been initialized via ensure_player_initialized().
        """
        if not user_id:
            raise ConfigValidationError(
                f"user_id required to update isolated world state for '{experience}'"
            )

        view_path = self._get_player_view_path(experience, user_id)

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

    def _merge_updates(self, current: Dict[str, Any], updates: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """
        Merge updates into current state (deep merge).

        Supports merge operation markers:
        - {"$append": item} - Append item to array
        - {"$remove": item} - Remove item from array (by matching item["id"])

        Args:
            current: Current state dict
            updates: Updates to apply
            depth: Recursion depth for logging

        Returns:
            Merged state dict
        """
        result = current.copy()
        indent = "  " * depth

        for key, value in updates.items():
            logger.warning(f"{indent}[MERGE-L{depth}] Processing key='{key}', value_type={type(value).__name__}")
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
                    logger.warning(f"[MERGE] Appended item to {key}: {item_to_append.get('semantic_name') or item_to_append.get('instance_id', 'unknown')}, new length={len(result[key])}")
                    continue

                elif "$remove" in value:
                    # Remove operation: Remove item from array by ID
                    item_to_remove = value["$remove"]
                    logger.warning(
                        f"{indent}[MERGE-L{depth}] Processing $remove for key='{key}', "
                        f"key_exists={key in result}, "
                        f"current_type={type(result.get(key)).__name__ if key in result else 'N/A'}, "
                        f"result_keys={list(result.keys())}"
                    )
                    if key not in result or not isinstance(result[key], list):
                        logger.warning(
                            f"{indent}[MERGE-L{depth}] ❌ Cannot remove from non-existent or non-list field '{key}' "
                            f"(exists={key in result}, is_list={isinstance(result.get(key), list)})"
                        )
                        continue

                    # Remove item matching ID (check both 'instance_id' and 'id' fields)
                    if isinstance(item_to_remove, dict):
                        # Extract the ID to match (prefer instance_id, fallback to id)
                        item_id = item_to_remove.get("instance_id") or item_to_remove.get("id")
                        if not item_id:
                            logger.warning(f"$remove object has no 'instance_id' or 'id' field: {item_to_remove}")
                            continue
                    else:
                        # Simple string/value
                        item_id = item_to_remove

                    # Remove items matching either instance_id or id
                    original_length = len(result[key])
                    result[key] = [
                        item for item in result[key]
                        if item.get("instance_id") != item_id and item.get("id") != item_id
                    ]
                    removed_count = original_length - len(result[key])
                    logger.debug(f"Removed {removed_count} item(s) with id '{item_id}' from {key}")
                    continue

                # Not a merge operation, check if we should do recursive merge
                elif key in result and isinstance(result[key], dict):
                    # Recursive merge for nested dicts
                    logger.warning(f"{indent}[MERGE-L{depth}] Recursing into '{key}'")
                    result[key] = self._merge_updates(result[key], value, depth + 1)
                    continue
                else:
                    logger.warning(f"{indent}[MERGE-L{depth}] Direct replacement for '{key}' (key_exists={key in result}, is_dict={isinstance(result.get(key), dict)})")

            # Direct replacement for non-dict values or when key doesn't exist
            result[key] = value

        return result

    # ===== PLAYER VIEW MANAGEMENT =====

    async def ensure_player_initialized(
        self,
        experience: str,
        user_id: str
    ) -> None:
        """
        Ensure player state file exists for experience.

        Call this ONCE per session/connection before any state operations.
        If player view doesn't exist, bootstraps them automatically.

        Design principle: Single entry point for initialization validation.
        All other methods assume files exist.

        Args:
            experience: Experience ID
            user_id: User ID
        """
        view_path = self._get_player_view_path(experience, user_id)

        if not view_path.exists():
            logger.info(f"First-time join: bootstrapping player '{user_id}' for '{experience}'")
            await self.bootstrap_player(experience, user_id)
        else:
            logger.debug(f"Player '{user_id}' already initialized for '{experience}'")

    async def get_player_view(
        self,
        experience: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get player's view for experience.

        ASSUMES: Player has been initialized via ensure_player_initialized().
        No auto-bootstrap - callers must ensure initialization first.

        Args:
            experience: Experience ID
            user_id: User ID

        Returns:
            Player view dict

        Raises:
            StateNotFoundError: If player view doesn't exist (caller didn't initialize)
        """
        view_path = self._get_player_view_path(experience, user_id)

        if not view_path.exists():
            raise StateNotFoundError(
                f"Player view not found for user '{user_id}' in '{experience}'. "
                f"Call ensure_player_initialized() first."
            )

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
        Update player's view with version tracking.

        ASSUMES: Player has been initialized via ensure_player_initialized().

        Args:
            experience: Experience ID
            user_id: User ID
            updates: Updates to apply

        Returns:
            Updated player view

        Raises:
            StateNotFoundError: If player view doesn't exist (caller didn't initialize)
        """
        view_path = self._get_player_view_path(experience, user_id)

        # Read current version before update
        with open(view_path, 'r') as f:
            current_view = json.load(f)

        # CRITICAL: Use world's incremental _version, not timestamps
        # This ensures consistency with update_world_state() versioning
        world_state = await self.get_world_state(experience)
        current_world_version = world_state.get("metadata", {}).get("_version", 0)

        base_version = current_view.get("snapshot_version", current_world_version)
        new_version = current_world_version  # Player view versions track world version

        # Add version increment to updates
        if "snapshot_version" not in updates:
            updates["snapshot_version"] = new_version

        # No locking needed for player views (each player has own file)
        logger.debug(f"[UPDATE-PLAYER-VIEW] Updating view: exp={experience}, user={user_id}, base={base_version}, new={new_version}")
        updated_view = await self._direct_update(view_path, updates)

        # NOTE: Player view updates don't publish deltas - only world state changes do
        # Player inventory/position changes come through update_world_state() deltas
        # Publishing here would create duplicate/conflicting version updates

        return updated_view

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

        # Set snapshot_version to current world version (for delta tracking)
        world_state = await self.get_world_state(experience)
        view["snapshot_version"] = world_state.get("metadata", {}).get("_version", 0)

        # Write player view
        with open(view_path, 'w') as f:
            json.dump(view, f, indent=2)

        logger.info(
            f"Bootstrapped player '{user_id}' for '{experience}' ({state_model} model), "
            f"snapshot_version={view['snapshot_version']}"
        )
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
        logger.warning(f"[BOOTSTRAP-DEBUG] user={user_id}, starting_location={starting_location}, starting_inventory={starting_inventory}")

        view = {
            "player": {
                "current_location": starting_location,
                "current_area": None,
                "inventory": starting_inventory.copy(),
                "stats": {}
            },
            "progress": {
                "visited_locations": [],
                "discovered_areas": [],
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
            },
            "snapshot_version": 0  # Will be set to world._version after initialization
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

    # ===== RESET OPERATIONS =====

    def _get_world_template_path(self, experience: str) -> Path:
        """Get path to world template file."""
        return self.experiences_path / experience / "state" / "world.template.json"

    def create_backup(self, experience: str) -> Path:
        """
        Create timestamped backup of world state.

        Args:
            experience: Experience ID

        Returns:
            Path to backup file

        Raises:
            StateNotFoundError: If world.json doesn't exist
        """
        config = self.load_config(experience)
        world_path = self._get_world_state_path(experience, config)

        if not world_path.exists():
            raise StateNotFoundError(
                f"Cannot backup - world state not found for '{experience}': {world_path}"
            )

        # Create backup with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = world_path.parent / f"world.backup.{timestamp}.json"

        shutil.copy(world_path, backup_path)
        logger.info(f"Created backup for '{experience}': {backup_path}")

        return backup_path

    async def restore_from_template(self, experience: str) -> Dict[str, Any]:
        """
        Restore world state from template.

        Args:
            experience: Experience ID

        Returns:
            Restored world state

        Raises:
            StateNotFoundError: If template doesn't exist
        """
        config = self.load_config(experience)
        template_path = self._get_world_template_path(experience)
        world_path = self._get_world_state_path(experience, config)

        if not template_path.exists():
            raise StateNotFoundError(
                f"Template not found for '{experience}': {template_path}"
            )

        # Load template
        with open(template_path, 'r') as f:
            template = json.load(f)

        # Update metadata for restored state
        if "metadata" not in template:
            template["metadata"] = {}
        template["metadata"]["_version"] = 1
        template["metadata"]["last_modified"] = datetime.utcnow().isoformat() + "Z"
        template["metadata"]["_restored_from_template"] = datetime.utcnow().isoformat() + "Z"

        # Write restored state
        with open(world_path, 'w') as f:
            json.dump(template, f, indent=2)

        logger.info(f"Restored world state for '{experience}' from template")
        return template

    async def delete_all_player_views(self, experience: str) -> int:
        """
        Delete all player views for an experience.

        Args:
            experience: Experience ID

        Returns:
            Number of player views deleted
        """
        deleted_count = 0

        if not self.players_path.exists():
            logger.warning(f"Players directory doesn't exist: {self.players_path}")
            return 0

        # Iterate through all player directories
        for player_dir in self.players_path.iterdir():
            if not player_dir.is_dir():
                continue

            view_path = player_dir / experience / "view.json"
            if view_path.exists():
                view_path.unlink()
                deleted_count += 1
                logger.debug(f"Deleted player view: {view_path}")

                # Clean up empty directories
                exp_dir = player_dir / experience
                if exp_dir.exists() and not any(exp_dir.iterdir()):
                    exp_dir.rmdir()
                    logger.debug(f"Removed empty experience directory: {exp_dir}")

        logger.info(f"Deleted {deleted_count} player view(s) for '{experience}'")
        return deleted_count

    async def reset_experience(
        self,
        experience: str,
        reset_type: str = "full",
        create_backup_file: bool = True
    ) -> Dict[str, Any]:
        """
        Reset experience state.

        Reset types:
        - "full": Restore world + delete all player views (safe, recommended)
        - "world_only": Restore world only (WARNING: may cause item duplication)
        - "players_only": Delete player views only (WARNING: may cause item loss)

        Args:
            experience: Experience ID
            reset_type: Type of reset ("full", "world_only", "players_only")
            create_backup_file: Create backup before reset

        Returns:
            Dict with reset results

        Raises:
            ConfigValidationError: If reset_type invalid
            StateNotFoundError: If required files missing
        """
        if reset_type not in ["full", "world_only", "players_only"]:
            raise ConfigValidationError(
                f"Invalid reset_type '{reset_type}' (must be 'full', 'world_only', or 'players_only')"
            )

        logger.info(f"Starting {reset_type} reset for '{experience}'")
        results = {
            "experience": experience,
            "reset_type": reset_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "backup_created": None,
            "world_restored": False,
            "player_views_deleted": 0
        }

        # Step 1: Backup (if requested)
        if create_backup_file and reset_type in ["full", "world_only"]:
            try:
                backup_path = self.create_backup(experience)
                results["backup_created"] = str(backup_path)
            except Exception as e:
                logger.error(f"Backup failed: {e}")
                raise

        # Step 2: Restore world (if applicable)
        if reset_type in ["full", "world_only"]:
            try:
                await self.restore_from_template(experience)
                results["world_restored"] = True
            except Exception as e:
                logger.error(f"World restore failed: {e}")
                raise

        # Step 3: Delete player views (if applicable)
        if reset_type in ["full", "players_only"]:
            try:
                deleted_count = await self.delete_all_player_views(experience)
                results["player_views_deleted"] = deleted_count
            except Exception as e:
                logger.error(f"Player view deletion failed: {e}")
                raise

        logger.info(f"Reset complete for '{experience}': {results}")
        return results

    # ===== AREA OF INTEREST (AOI) =====

    async def build_aoi(
        self,
        experience: str,
        user_id: str,
        nearby_waypoints: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Build Area of Interest (AOI) payload for client.

        Constructs complete world state snapshot for player's current location,
        including zone info, areas with items/NPCs, and player state.

        Args:
            experience: Experience ID (e.g., "wylding-woods")
            user_id: User ID
            nearby_waypoints: Waypoints from find_nearby_locations() (GPS-filtered)

        Returns:
            AOI dict with zone, areas, player state, and snapshot_version
            None if no waypoints nearby
        """
        if not nearby_waypoints:
            logger.debug(f"No waypoints nearby for user {user_id}")
            return None

        # Use first waypoint as primary zone
        # TODO: Handle multiple overlapping zones (disambiguation)
        primary_waypoint = nearby_waypoints[0]

        # Use location_id if available (explicit mapping), fall back to waypoint id
        zone_id = primary_waypoint.get("location_id") or primary_waypoint.get("id")

        logger.debug(
            f"Building AOI for zone '{zone_id}' from waypoint '{primary_waypoint.get('id')}' "
            f"(user: {user_id})"
        )

        # Load world state to get items/NPCs at this location
        try:
            world_state = await self.get_world_state(experience)
        except StateNotFoundError:
            logger.warning(f"World state not found for experience '{experience}'")
            world_state = {"locations": {}}

        # Load player view for inventory/state
        try:
            player_view = await self.get_player_view(experience, user_id)
        except StateNotFoundError:
            logger.warning(f"Player view not found for user '{user_id}'")
            player_view = {"player": {"current_location": None, "inventory": []}}

        # Extract location data from world state
        locations = world_state.get("locations", {})
        zone_data = locations.get(zone_id, {})

        # Build areas dict with their spots/items/NPCs
        # New structure: zone > areas > spots > items
        areas = {}
        for area_id, area_data in zone_data.get("areas", {}).items():
            spots = {}

            # Iterate over spots within this area
            for spot_id, spot_data in area_data.get("spots", {}).items():
                spots[spot_id] = {
                    "id": spot_id,
                    "name": spot_data.get("name", spot_id),
                    "description": spot_data.get("description", ""),
                    "items": [],  # Build normalized items below
                    "npcs": []
                }

                # Load templates and merge with instance data for items at this spot
                for item_instance in spot_data.get("items", []):
                    # Handle items stored as strings (e.g., "dream_bottle_1")
                    if isinstance(item_instance, str):
                        instance_id = item_instance
                        template_id = item_instance  # Use instance_id as template_id
                        item_instance = {"instance_id": instance_id, "template_id": template_id}
                    else:
                        instance_id = item_instance.get("instance_id") or item_instance.get("id")
                        template_id = item_instance.get("template_id") or item_instance.get("type")

                    if not template_id:
                        logger.warning(
                            f"Item instance {instance_id} missing template_id, skipping"
                        )
                        continue

                    # Load template definition from markdown
                    template = await self.template_loader.load_template(
                        experience=experience,
                        entity_type="items",
                        template_id=template_id
                    )

                    if not template:
                        logger.warning(
                            f"Template not found: {template_id} (instance: {instance_id}), "
                            f"using instance data only"
                        )
                        # Fallback: use instance data if template not found
                        template = {}

                    # Merge template + instance (instance overrides template)
                    # Pass full item_instance so world.json booleans override template strings
                    merged_item = self.template_loader.merge_template_instance(
                        template=template,
                        instance=item_instance  # Pass full instance data
                    )

                    spots[spot_id]["items"].append(merged_item)

                # Add NPC if present at this spot
                npc_id = spot_data.get("npc")
                if npc_id:
                    npc_data = world_state.get("npcs", {}).get(npc_id)
                    if npc_data:
                        spots[spot_id]["npcs"].append({
                            "instance_id": f"{npc_id}_1",  # Synthetic instance ID
                            "template_id": npc_id,
                            **npc_data
                        })

            # Build area with its spots
            areas[area_id] = {
                "id": area_id,
                "name": area_data.get("name", area_id),
                "description": area_data.get("description", ""),
                "spots": spots
            }

        # Build zone info from waypoint + world state
        zone = {
            "id": zone_id,
            "name": primary_waypoint.get("name", zone_id),
            "description": zone_data.get("description") or primary_waypoint.get("description", ""),
            "gps": primary_waypoint.get("location")  # Raw GPS dict {lat, lng}
        }

        # Extract player state
        player_state = player_view.get("player", {})
        player_info = {
            "current_location": player_state.get("current_location"),
            "current_area": player_state.get("current_area"),
            "inventory": player_state.get("inventory", [])
        }

        # Construct AOI payload
        # Use server's authoritative version from world.json metadata
        server_version = world_state.get("metadata", {}).get("_version", 0)

        aoi = {
            "zone": zone,
            "areas": areas,
            "player": player_info,
            "snapshot_version": server_version  # Server-authoritative version (not timestamp)
        }

        logger.info(
            f"Built AOI for zone '{zone_id}' with {len(areas)} areas "
            f"(user: {user_id})"
        )

        return aoi
