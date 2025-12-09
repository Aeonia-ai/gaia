"""
Unit tests for UnifiedStateManager

Tests config loading, state management, and bootstrap functionality
for both shared and isolated state models.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.services.kb.unified_state_manager import (
    UnifiedStateManager,
    ConfigValidationError,
    StateNotFoundError,
    StateLockError
)


@pytest.fixture
def temp_kb():
    """Create temporary KB directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    kb_root = Path(temp_dir) / "kb"
    kb_root.mkdir()

    # Create directory structure
    (kb_root / "experiences").mkdir()
    (kb_root / "players").mkdir()

    yield kb_root

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def shared_experience(temp_kb):
    """Create a test experience with shared state model."""
    exp_path = temp_kb / "experiences" / "test-shared"
    exp_path.mkdir()

    # Create config
    config = {
        "id": "test-shared",
        "name": "Test Shared Experience",
        "version": "1.0.0",
        "state": {
            "model": "shared",
            "coordination": {
                "locking_enabled": True,
                "lock_timeout_ms": 1000
            }
        }
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    # Create state directory and world.json
    state_path = exp_path / "state"
    state_path.mkdir()

    world_state = {
        "entities": {
            "npc_1": {"name": "TestNPC", "location": "area_1"}
        },
        "world_flags": {"test_flag": True},
        "metadata": {"_version": 1}
    }

    with open(state_path / "world.json", 'w') as f:
        json.dump(world_state, f)

    return "test-shared"


@pytest.fixture
def isolated_experience(temp_kb):
    """Create a test experience with isolated state model."""
    exp_path = temp_kb / "experiences" / "test-isolated"
    exp_path.mkdir()

    # Create config
    config = {
        "id": "test-isolated",
        "name": "Test Isolated Experience",
        "version": "1.0.0",
        "state": {
            "model": "isolated"
        }
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    # Create state directory and world.json template
    state_path = exp_path / "state"
    state_path.mkdir()

    world_template = {
        "session": {"id": None, "started_at": None},
        "player": {"current_room": "start", "inventory": []},
        "world_state": {"flag_1": False},
        "metadata": {}
    }

    with open(state_path / "world.json", 'w') as f:
        json.dump(world_template, f)

    return "test-isolated"


# ===== CONFIG TESTS =====

@pytest.mark.asyncio
async def test_load_config_success(temp_kb, shared_experience):
    """Test successful config loading."""
    manager = UnifiedStateManager(temp_kb)

    config = manager.load_config(shared_experience)

    assert config["id"] == "test-shared"
    assert config["name"] == "Test Shared Experience"
    assert config["state"]["model"] == "shared"


@pytest.mark.asyncio
async def test_load_config_caching(temp_kb, shared_experience):
    """Test config is cached after first load."""
    manager = UnifiedStateManager(temp_kb)

    config1 = manager.load_config(shared_experience)
    config2 = manager.load_config(shared_experience)

    # Should return same object (cached)
    assert config1 is config2


@pytest.mark.asyncio
async def test_load_config_not_found(temp_kb):
    """Test error when config doesn't exist."""
    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(ConfigValidationError, match="Config not found"):
        manager.load_config("nonexistent-experience")


@pytest.mark.asyncio
async def test_config_validation_missing_required_field(temp_kb):
    """Test validation fails with missing required fields."""
    exp_path = temp_kb / "experiences" / "invalid-exp"
    exp_path.mkdir()

    # Missing 'state' field
    config = {
        "id": "invalid-exp",
        "name": "Invalid",
        "version": "1.0.0"
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(ConfigValidationError, match="missing required field: state"):
        manager.load_config("invalid-exp")


@pytest.mark.asyncio
async def test_config_validation_id_mismatch(temp_kb):
    """Test validation fails when ID doesn't match directory name."""
    exp_path = temp_kb / "experiences" / "correct-name"
    exp_path.mkdir()

    config = {
        "id": "wrong-name",  # Doesn't match directory
        "name": "Test",
        "version": "1.0.0",
        "state": {"model": "shared"}
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(ConfigValidationError, match="doesn't match directory name"):
        manager.load_config("correct-name")


@pytest.mark.asyncio
async def test_config_validation_invalid_state_model(temp_kb):
    """Test validation fails with invalid state model."""
    exp_path = temp_kb / "experiences" / "bad-model"
    exp_path.mkdir()

    config = {
        "id": "bad-model",
        "name": "Bad Model",
        "version": "1.0.0",
        "state": {"model": "invalid"}  # Invalid model type
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(ConfigValidationError, match="Invalid state model"):
        manager.load_config("bad-model")


@pytest.mark.asyncio
async def test_config_defaults_applied(temp_kb, shared_experience):
    """Test that config defaults are properly applied."""
    manager = UnifiedStateManager(temp_kb)

    config = manager.load_config(shared_experience)

    # Check defaults were applied
    assert "coordination" in config["state"]
    assert "persistence" in config["state"]
    assert "multiplayer" in config
    assert "bootstrap" in config
    assert "content" in config
    assert "capabilities" in config

    # Check specific defaults
    assert config["state"]["coordination"]["optimistic_versioning"] is True
    assert config["state"]["persistence"]["auto_save"] is True
    assert config["content"]["markdown_enabled"] is True


# ===== SHARED STATE TESTS =====

@pytest.mark.asyncio
async def test_get_shared_world_state(temp_kb, shared_experience):
    """Test getting shared world state."""
    manager = UnifiedStateManager(temp_kb)

    world_state = await manager.get_world_state(shared_experience)

    assert "entities" in world_state
    assert "npc_1" in world_state["entities"]
    assert world_state["entities"]["npc_1"]["name"] == "TestNPC"


@pytest.mark.asyncio
async def test_update_shared_world_state(temp_kb, shared_experience):
    """Test updating shared world state."""
    manager = UnifiedStateManager(temp_kb)

    updates = {
        "entities": {
            "npc_1": {"location": "area_2"}  # Change location
        },
        "world_flags": {"new_flag": True}
    }

    updated = await manager.update_world_state(shared_experience, updates)

    # Check update was applied
    assert updated["entities"]["npc_1"]["location"] == "area_2"
    assert updated["world_flags"]["new_flag"] is True

    # Check original data preserved
    assert updated["entities"]["npc_1"]["name"] == "TestNPC"
    assert updated["world_flags"]["test_flag"] is True

    # Check version incremented
    assert updated["metadata"]["_version"] == 2


@pytest.mark.asyncio
async def test_shared_state_not_found(temp_kb):
    """Test error when shared world state doesn't exist."""
    exp_path = temp_kb / "experiences" / "no-state"
    exp_path.mkdir()
    (exp_path / "state").mkdir()

    config = {
        "id": "no-state",
        "name": "No State",
        "version": "1.0.0",
        "state": {"model": "shared"}
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(StateNotFoundError, match="World state not found"):
        await manager.get_world_state("no-state")


# ===== ISOLATED STATE TESTS =====

@pytest.mark.asyncio
async def test_get_isolated_world_state(temp_kb, isolated_experience):
    """Test getting isolated world state (player's copy)."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "test-user@example.com"

    # Bootstrap player first
    await manager.bootstrap_player(isolated_experience, user_id)

    # Get world state (player's copy)
    world_state = await manager.get_world_state(isolated_experience, user_id)

    assert "session" in world_state
    assert "player" in world_state
    assert world_state["player"]["current_room"] == "start"


@pytest.mark.asyncio
async def test_update_isolated_world_state(temp_kb, isolated_experience):
    """Test updating isolated world state."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "test-user@example.com"

    # Bootstrap player
    await manager.bootstrap_player(isolated_experience, user_id)

    # Update world state
    updates = {
        "player": {"current_room": "room_2"},
        "world_state": {"flag_1": True}
    }

    updated = await manager.update_world_state(
        isolated_experience, updates, user_id=user_id
    )

    assert updated["player"]["current_room"] == "room_2"
    assert updated["world_state"]["flag_1"] is True


@pytest.mark.asyncio
async def test_isolated_state_requires_user_id(temp_kb, isolated_experience):
    """Test that isolated model requires user_id."""
    manager = UnifiedStateManager(temp_kb)

    with pytest.raises(ConfigValidationError, match="user_id required"):
        await manager.get_world_state(isolated_experience)


# ===== PLAYER VIEW TESTS =====

@pytest.mark.asyncio
async def test_get_player_view_not_found(temp_kb, shared_experience):
    """Test getting player view that doesn't exist."""
    manager = UnifiedStateManager(temp_kb)

    view = await manager.get_player_view(shared_experience, "new-user@example.com")

    assert view is None


@pytest.mark.asyncio
async def test_get_player_view_after_bootstrap(temp_kb, shared_experience):
    """Test getting player view after bootstrap."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "test-user@example.com"

    # Bootstrap
    await manager.bootstrap_player(shared_experience, user_id)

    # Get view
    view = await manager.get_player_view(shared_experience, user_id)

    assert view is not None
    assert "player" in view
    assert "progress" in view
    assert "session" in view


@pytest.mark.asyncio
async def test_update_player_view(temp_kb, shared_experience):
    """Test updating player view."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "test-user@example.com"

    # Bootstrap
    await manager.bootstrap_player(shared_experience, user_id)

    # Update view
    updates = {
        "player": {"inventory": ["item_1", "item_2"]},
        "progress": {"achievements": ["first_login"]}
    }

    updated = await manager.update_player_view(shared_experience, user_id, updates)

    assert updated["player"]["inventory"] == ["item_1", "item_2"]
    assert updated["progress"]["achievements"] == ["first_login"]


# ===== BOOTSTRAP TESTS =====

@pytest.mark.asyncio
async def test_bootstrap_shared_model(temp_kb, shared_experience):
    """Test bootstrapping player for shared model."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "new-player@example.com"

    view = await manager.bootstrap_player(shared_experience, user_id)

    # Check minimal view structure
    assert "player" in view
    assert "progress" in view
    assert "session" in view
    assert "metadata" in view

    # Check defaults
    assert view["player"]["inventory"] == []
    assert view["progress"]["visited_locations"] == []
    assert view["session"]["turns_taken"] == 0
    assert view["metadata"]["_version"] == 1


@pytest.mark.asyncio
async def test_bootstrap_isolated_model(temp_kb, isolated_experience):
    """Test bootstrapping player for isolated model."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "new-player@example.com"

    view = await manager.bootstrap_player(isolated_experience, user_id)

    # Check world template was copied
    assert "session" in view
    assert "player" in view
    assert "world_state" in view

    # Check session was initialized
    assert view["session"]["id"] is not None
    assert view["session"]["started_at"] is not None

    # Check metadata added
    assert "_version" in view["metadata"]
    assert "_copied_from_template" in view["metadata"]


@pytest.mark.asyncio
async def test_bootstrap_already_exists(temp_kb, shared_experience):
    """Test bootstrap returns existing view if already bootstrapped."""
    manager = UnifiedStateManager(temp_kb)
    user_id = "existing-player@example.com"

    # Bootstrap first time
    view1 = await manager.bootstrap_player(shared_experience, user_id)

    # Bootstrap again (should return existing)
    view2 = await manager.bootstrap_player(shared_experience, user_id)

    assert view1 == view2


@pytest.mark.asyncio
async def test_bootstrap_with_starting_inventory(temp_kb):
    """Test bootstrap applies starting inventory from config."""
    exp_path = temp_kb / "experiences" / "with-inventory"
    exp_path.mkdir()
    (exp_path / "state").mkdir()

    config = {
        "id": "with-inventory",
        "name": "With Inventory",
        "version": "1.0.0",
        "state": {"model": "shared"},
        "bootstrap": {
            "player_starting_inventory": ["compass", "map"]
        }
    }

    with open(exp_path / "config.json", 'w') as f:
        json.dump(config, f)

    # Create world.json
    with open(exp_path / "state" / "world.json", 'w') as f:
        json.dump({"entities": {}}, f)

    manager = UnifiedStateManager(temp_kb)
    view = await manager.bootstrap_player("with-inventory", "test-user@example.com")

    assert view["player"]["inventory"] == ["compass", "map"]


# ===== UTILITY TESTS =====

@pytest.mark.asyncio
async def test_list_experiences(temp_kb, shared_experience, isolated_experience):
    """Test listing all experiences."""
    manager = UnifiedStateManager(temp_kb)

    experiences = manager.list_experiences()

    assert "test-shared" in experiences
    assert "test-isolated" in experiences
    assert len(experiences) == 2


@pytest.mark.asyncio
async def test_get_experience_info(temp_kb, shared_experience):
    """Test getting experience info."""
    manager = UnifiedStateManager(temp_kb)

    info = manager.get_experience_info(shared_experience)

    assert info["id"] == "test-shared"
    assert info["name"] == "Test Shared Experience"
    assert info["state_model"] == "shared"
    assert "capabilities" in info


# ===== LOCKING TESTS =====

@pytest.mark.asyncio
async def test_locked_update_acquires_lock(temp_kb, shared_experience):
    """Test that locked update successfully acquires and releases lock."""
    manager = UnifiedStateManager(temp_kb)

    updates = {"world_flags": {"locked_update": True}}

    # Should complete without error
    updated = await manager.update_world_state(
        shared_experience, updates, use_locking=True
    )

    assert updated["world_flags"]["locked_update"] is True


@pytest.mark.asyncio
async def test_update_without_locking(temp_kb, shared_experience):
    """Test update without locking (direct write)."""
    manager = UnifiedStateManager(temp_kb)

    updates = {"world_flags": {"direct_update": True}}

    updated = await manager.update_world_state(
        shared_experience, updates, use_locking=False
    )

    assert updated["world_flags"]["direct_update"] is True


# ===== MERGE TESTS =====

@pytest.mark.asyncio
async def test_deep_merge_updates(temp_kb, shared_experience):
    """Test that updates are deep-merged into existing state."""
    manager = UnifiedStateManager(temp_kb)

    # Initial state has: entities.npc_1.name and entities.npc_1.location
    # Update only location, name should be preserved
    updates = {
        "entities": {
            "npc_1": {"location": "new_area"},
            "npc_2": {"name": "NewNPC"}  # Add new NPC
        }
    }

    updated = await manager.update_world_state(shared_experience, updates)

    # Check merge preserved existing fields
    assert updated["entities"]["npc_1"]["name"] == "TestNPC"
    assert updated["entities"]["npc_1"]["location"] == "new_area"

    # Check new entity added
    assert "npc_2" in updated["entities"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
