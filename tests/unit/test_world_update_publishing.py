"""
Unit tests for NATS world update publishing in UnifiedStateManager.

Tests verify that state changes trigger NATS events correctly and implement
graceful degradation when NATS is unavailable.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from app.services.kb.unified_state_manager import UnifiedStateManager
from app.shared.events import WorldUpdateEvent


class TestWorldUpdatePublishing:
    """Test NATS publishing from UnifiedStateManager"""

    @pytest.fixture
    def mock_nats_client(self):
        """Create mock NATS client"""
        client = Mock()
        client.is_connected = True
        client.publish = AsyncMock()
        return client

    @pytest.fixture
    def state_manager_with_nats(self, tmp_path, mock_nats_client):
        """Create state manager with NATS client"""
        manager = UnifiedStateManager(tmp_path, nats_client=mock_nats_client)
        return manager

    @pytest.fixture
    def state_manager_without_nats(self, tmp_path):
        """Create state manager without NATS client"""
        manager = UnifiedStateManager(tmp_path, nats_client=None)
        return manager

    @pytest.mark.asyncio
    async def test_publish_world_update_success(self, state_manager_with_nats, mock_nats_client):
        """Test successful NATS event publishing"""
        experience = "wylding-woods"
        user_id = "user123"
        changes = {
            "player.inventory": {
                "operation": "add",
                "item": {"id": "bottle_1", "type": "collectible"}
            }
        }

        # Call publishing method
        await state_manager_with_nats._publish_world_update(experience, user_id, changes)

        # Verify publish was called
        assert mock_nats_client.publish.called
        call_args = mock_nats_client.publish.call_args

        # Verify subject format
        subject = call_args[0][0]
        assert subject == f"world.updates.user.{user_id}"

        # Verify event payload
        event_data = call_args[0][1]
        assert event_data["type"] == "world_update"
        assert event_data["version"] == "0.3"
        assert event_data["experience"] == experience
        assert event_data["user_id"] == user_id
        assert event_data["changes"] == changes
        assert "timestamp" in event_data
        assert event_data["metadata"]["source"] == "kb_service"

    @pytest.mark.asyncio
    async def test_publish_world_update_validates_schema(self, state_manager_with_nats, mock_nats_client):
        """Test that published events match WorldUpdateEvent schema"""
        experience = "wylding-woods"
        user_id = "user123"
        changes = {"location": {"operation": "update", "value": "forest"}}

        await state_manager_with_nats._publish_world_update(experience, user_id, changes)

        # Get published event data
        event_data = mock_nats_client.publish.call_args[0][1]

        # Validate against Pydantic schema
        event = WorldUpdateEvent(**event_data)
        assert event.type == "world_update"
        assert event.version == "0.3"
        assert event.experience == experience
        assert event.user_id == user_id
        assert event.changes == changes

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_nats_client(self, state_manager_without_nats):
        """Test that publishing works when NATS client is None"""
        experience = "wylding-woods"
        user_id = "user123"
        changes = {"test": "data"}

        # Should not raise exception
        await state_manager_without_nats._publish_world_update(experience, user_id, changes)

    @pytest.mark.asyncio
    async def test_graceful_degradation_nats_disconnected(self, state_manager_with_nats, mock_nats_client):
        """Test that publishing works when NATS is disconnected"""
        mock_nats_client.is_connected = False

        experience = "wylding-woods"
        user_id = "user123"
        changes = {"test": "data"}

        # Should not raise exception
        await state_manager_with_nats._publish_world_update(experience, user_id, changes)

        # Verify publish was NOT called
        assert not mock_nats_client.publish.called

    @pytest.mark.asyncio
    async def test_graceful_degradation_publish_exception(self, state_manager_with_nats, mock_nats_client):
        """Test that exceptions during publish are caught and logged"""
        mock_nats_client.publish.side_effect = Exception("NATS publish failed")

        experience = "wylding-woods"
        user_id = "user123"
        changes = {"test": "data"}

        # Should not raise exception (graceful degradation)
        await state_manager_with_nats._publish_world_update(experience, user_id, changes)

    @pytest.mark.asyncio
    async def test_timestamp_is_milliseconds(self, state_manager_with_nats, mock_nats_client):
        """Test that timestamp is in milliseconds (Unity compatibility)"""
        import time

        before_ms = int(time.time() * 1000)

        await state_manager_with_nats._publish_world_update(
            "wylding-woods", "user123", {"test": "data"}
        )

        after_ms = int(time.time() * 1000)

        # Get timestamp from published event
        event_data = mock_nats_client.publish.call_args[0][1]
        timestamp = event_data["timestamp"]

        # Verify it's in milliseconds range (13 digits)
        assert len(str(timestamp)) >= 13
        assert before_ms <= timestamp <= after_ms

    @pytest.mark.asyncio
    @patch('app.services.kb.unified_state_manager.NATS_AVAILABLE', False)
    async def test_nats_not_available(self, tmp_path, mock_nats_client):
        """Test graceful degradation when NATS module not available"""
        # Even if we pass a NATS client, it should be ignored if NATS_AVAILABLE=False
        manager = UnifiedStateManager(tmp_path, nats_client=mock_nats_client)

        # nats_client should be None despite being passed in
        assert manager.nats_client is None

        # Publishing should not raise exception
        await manager._publish_world_update("wylding-woods", "user123", {"test": "data"})

        # Verify publish was never called
        assert not mock_nats_client.publish.called


class TestStateUpdateIntegration:
    """Integration tests: verify update methods call publishing"""

    @pytest.fixture
    def mock_nats_client(self):
        """Create mock NATS client"""
        client = Mock()
        client.is_connected = True
        client.publish = AsyncMock()
        return client

    @pytest.fixture
    async def configured_state_manager(self, tmp_path, mock_nats_client):
        """Create state manager with test experience config"""
        manager = UnifiedStateManager(tmp_path, nats_client=mock_nats_client)

        # Create test experience with isolated model
        exp_path = tmp_path / "experiences" / "test-exp"
        (exp_path / "state").mkdir(parents=True)

        # Write config
        import json
        config = {
            "experience": "test-exp",
            "state": {
                "model": "isolated",
                "coordination": {"locking_enabled": False, "lock_timeout_ms": 5000}
            },
            "bootstrap": {
                "player_starting_location": "start",
                "player_starting_inventory": []
            }
        }
        with open(exp_path / "config.json", 'w') as f:
            json.dump(config, f)

        # Create player view
        player_path = tmp_path / "players" / "user123" / "test-exp"
        player_path.mkdir(parents=True)

        player_view = {
            "location": "start",
            "inventory": [],
            "metadata": {"_version": 1}
        }
        with open(player_path / "view.json", 'w') as f:
            json.dump(player_view, f)

        return manager

    @pytest.mark.asyncio
    async def test_update_player_view_publishes_to_nats(self, configured_state_manager, mock_nats_client):
        """Test that update_player_view() triggers NATS publish"""
        experience = "test-exp"
        user_id = "user123"
        updates = {"inventory": [{"id": "bottle_1", "type": "collectible"}]}

        # Update player view
        await configured_state_manager.update_player_view(experience, user_id, updates)

        # Verify NATS publish was called
        assert mock_nats_client.publish.called

        # Verify subject and event data
        call_args = mock_nats_client.publish.call_args
        subject = call_args[0][0]
        event_data = call_args[0][1]

        assert subject == f"world.updates.user.{user_id}"
        assert event_data["experience"] == experience
        assert event_data["user_id"] == user_id
        assert event_data["changes"] == updates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
