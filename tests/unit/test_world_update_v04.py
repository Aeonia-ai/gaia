"""
Unit tests for WorldUpdate v0.4 implementation.

Tests:
- WorldUpdateEvent model validation
- Version tracking in player views
- Change formatting to v0.4 array format
- Template/instance merging in updates
"""
import pytest
import time
from pathlib import Path
from app.shared.events import WorldUpdateEvent
from app.services.kb.unified_state_manager import UnifiedStateManager
import app.services.kb.template_loader as template_loader_module


@pytest.fixture(autouse=True)
def reset_template_loader_singleton():
    """Reset the TemplateLoader singleton before each test."""
    template_loader_module._template_loader = None
    yield
    template_loader_module._template_loader = None


class TestWorldUpdateEventV04:
    """Test WorldUpdateEvent v0.4 model."""

    def test_world_update_event_v04_structure(self):
        """Test v0.4 event structure with required fields."""
        event = WorldUpdateEvent(
            experience="wylding-woods",
            user_id="test_user_123",
            base_version=12345,
            snapshot_version=12346,
            changes=[
                {
                    "operation": "remove",
                    "area_id": "spawn_zone_1",
                    "instance_id": "dream_bottle_woander_1"
                },
                {
                    "operation": "add",
                    "area_id": None,
                    "path": "player.inventory",
                    "item": {
                        "instance_id": "dream_bottle_woander_1",
                        "template_id": "dream_bottle",
                        "semantic_name": "dream bottle",
                        "collectible": True
                    }
                }
            ],
            timestamp=int(time.time() * 1000)
        )

        # Verify structure
        assert event.type == "world_update"
        assert event.version == "0.4"
        assert event.experience == "wylding-woods"
        assert event.user_id == "test_user_123"
        assert event.base_version == 12345
        assert event.snapshot_version == 12346
        assert isinstance(event.changes, list)
        assert len(event.changes) == 2

        # Verify changes format
        remove_change = event.changes[0]
        assert remove_change["operation"] == "remove"
        assert remove_change["area_id"] == "spawn_zone_1"
        assert remove_change["instance_id"] == "dream_bottle_woander_1"

        add_change = event.changes[1]
        assert add_change["operation"] == "add"
        assert add_change["area_id"] is None
        assert add_change["path"] == "player.inventory"
        assert "item" in add_change
        assert add_change["item"]["instance_id"] == "dream_bottle_woander_1"
        assert add_change["item"]["template_id"] == "dream_bottle"

    def test_world_update_event_serialization(self):
        """Test that v0.4 event serializes correctly to JSON."""
        event = WorldUpdateEvent(
            experience="wylding-woods",
            user_id="test_user_123",
            base_version=12345,
            snapshot_version=12346,
            changes=[
                {
                    "operation": "remove",
                    "area_id": "spawn_zone_1",
                    "instance_id": "dream_bottle_1"
                }
            ],
            timestamp=1731240000000,
            metadata={"source": "kb_service"}
        )

        # Serialize to dict
        event_dict = event.model_dump()

        # Verify JSON structure
        assert event_dict["type"] == "world_update"
        assert event_dict["version"] == "0.4"
        assert event_dict["base_version"] == 12345
        assert event_dict["snapshot_version"] == 12346
        assert isinstance(event_dict["changes"], list)
        assert event_dict["metadata"]["source"] == "kb_service"


class TestVersionTracking:
    """Test version tracking in player views."""

    @pytest.fixture
    def temp_kb_root(self, tmp_path):
        """Create temporary KB structure."""
        kb_root = tmp_path / "kb"
        kb_root.mkdir()

        # Create experiences directory
        exp_path = kb_root / "experiences" / "test_exp"
        exp_path.mkdir(parents=True)

        # Create config.json
        config = {
            "id": "test_exp",
            "name": "Test Experience",
            "version": "1.0.0",
            "state": {
                "model": "shared",
                "coordination": {
                    "locking_enabled": True
                }
            },
            "bootstrap": {
                "player_starting_location": "start",
                "player_starting_inventory": []
            }
        }
        import json
        with open(exp_path / "config.json", "w") as f:
            json.dump(config, f)

        # Create state directory
        state_path = exp_path / "state"
        state_path.mkdir()

        # Create minimal world.json
        world_state = {
            "metadata": {"version": "1.0.0"},
            "locations": {}
        }
        with open(state_path / "world.json", "w") as f:
            json.dump(world_state, f)

        return kb_root

    @pytest.mark.asyncio
    async def test_player_view_initial_version(self, temp_kb_root):
        """Test that new player views get initial snapshot_version."""
        manager = UnifiedStateManager(temp_kb_root)

        # Bootstrap new player
        view = await manager.bootstrap_player("test_exp", "test_user")

        # Verify snapshot_version exists
        assert "snapshot_version" in view
        assert isinstance(view["snapshot_version"], int)
        assert view["snapshot_version"] > 0

    @pytest.mark.asyncio
    async def test_version_increment_on_update(self, temp_kb_root):
        """Test that snapshot_version increments on state changes."""
        manager = UnifiedStateManager(temp_kb_root)

        # Bootstrap player
        await manager.bootstrap_player("test_exp", "test_user")

        # Get initial version
        view1 = await manager.get_player_view("test_exp", "test_user")
        initial_version = view1["snapshot_version"]

        # Update player view
        await manager.update_player_view(
            "test_exp",
            "test_user",
            {"player.stats": {"health": 100}}
        )

        # Get updated version
        view2 = await manager.get_player_view("test_exp", "test_user")
        new_version = view2["snapshot_version"]

        # Verify version incremented
        assert new_version > initial_version


class TestChangeFormatting:
    """Test v0.3 to v0.4 change formatting."""

    @pytest.fixture
    def temp_kb_root_with_templates(self, tmp_path):
        """Create KB structure with template."""
        kb_root = tmp_path / "kb"
        kb_root.mkdir()

        # Create experience directory
        exp_path = kb_root / "experiences" / "test_exp"
        exp_path.mkdir(parents=True)

        # Create config.json
        import json
        config = {
            "id": "test_exp",
            "name": "Test Experience",
            "version": "1.0.0",
            "state": {
                "model": "shared",
                "coordination": {
                    "locking_enabled": True
                }
            }
        }
        with open(exp_path / "config.json", "w") as f:
            json.dump(config, f)

        # Create template directory
        template_path = exp_path / "templates" / "items"
        template_path.mkdir(parents=True)

        # Create dream_bottle template
        template_md = """# Dream Bottle

> **Item ID**: dream_bottle
> **Type**: collectible

## Description
A small glass bottle that glows with inner light.

## Properties
- **Collectible**: Yes
- **Visual**: Ethereal glow
"""
        with open(template_path / "dream_bottle.md", "w") as f:
            f.write(template_md)

        return kb_root

    @pytest.mark.asyncio
    async def test_format_inventory_add(self, temp_kb_root_with_templates):
        """Test formatting player.inventory add to v0.4 format."""
        manager = UnifiedStateManager(temp_kb_root_with_templates)

        # v0.3 format change
        v03_changes = {
            "player.inventory": {
                "$append": {
                    "id": "dream_bottle_1",
                    "type": "dream_bottle",
                    "collected_at": "2025-11-10T12:00:00Z"
                }
            }
        }

        # Format to v0.4
        v04_changes = await manager._format_world_update_changes(
            v03_changes,
            "test_exp",
            "test_user"
        )

        # Verify v0.4 structure
        assert isinstance(v04_changes, list)
        assert len(v04_changes) == 1

        change = v04_changes[0]
        assert change["operation"] == "add"
        assert change["area_id"] is None
        assert change["path"] == "player.inventory"
        assert "item" in change
        assert change["item"]["instance_id"] == "dream_bottle_1"
        assert change["item"]["template_id"] == "dream_bottle"

    @pytest.mark.asyncio
    async def test_format_world_remove(self, temp_kb_root_with_templates):
        """Test formatting world item remove to v0.4 format."""
        manager = UnifiedStateManager(temp_kb_root_with_templates)

        # v0.3 format change
        v03_changes = {
            "world.locations.woander_store.sublocations.spawn_zone_1.items": {
                "$remove": {
                    "id": "dream_bottle_1"
                }
            }
        }

        # Format to v0.4
        v04_changes = await manager._format_world_update_changes(
            v03_changes,
            "test_exp",
            "test_user"
        )

        # Verify v0.4 structure
        assert isinstance(v04_changes, list)
        assert len(v04_changes) == 1

        change = v04_changes[0]
        assert change["operation"] == "remove"
        assert change["area_id"] == "spawn_zone_1"
        assert change["instance_id"] == "dream_bottle_1"


class TestTemplateMerging:
    """Test template/instance merging in world updates."""

    @pytest.fixture
    def temp_kb_with_template(self, tmp_path):
        """Create KB with template."""
        kb_root = tmp_path / "kb"
        kb_root.mkdir()

        # Create experience directory
        exp_path = kb_root / "experiences" / "test_exp"
        exp_path.mkdir(parents=True)

        # Create config.json
        import json
        config = {
            "id": "test_exp",
            "name": "Test Experience",
            "version": "1.0.0",
            "state": {
                "model": "shared",
                "coordination": {
                    "locking_enabled": True
                }
            }
        }
        with open(exp_path / "config.json", "w") as f:
            json.dump(config, f)

        # Create template
        template_path = exp_path / "templates" / "items"
        template_path.mkdir(parents=True)

        template_md = """# Dream Bottle

> **Item ID**: dream_bottle

## Description
A magical bottle.

## Properties
- **Collectible**: Yes
"""
        with open(template_path / "dream_bottle.md", "w") as f:
            f.write(template_md)

        return kb_root

    @pytest.mark.asyncio
    async def test_merge_template_with_instance(self, temp_kb_with_template):
        """Test that template properties merge with instance data."""
        manager = UnifiedStateManager(temp_kb_with_template)

        # Merge template + instance
        merged = await manager._merge_item_with_template(
            experience="test_exp",
            instance_id="dream_bottle_1",
            template_id="dream_bottle",
            item_data={"collected_at": "2025-11-10T12:00:00Z"}
        )

        # Verify merged data
        assert merged["instance_id"] == "dream_bottle_1"
        assert merged["template_id"] == "dream_bottle"
        assert "description" in merged  # From template
        assert merged["description"] == "A magical bottle."
        assert merged["collectible"] is True  # From template
        assert merged["collected_at"] == "2025-11-10T12:00:00Z"  # From instance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
