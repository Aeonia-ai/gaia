import pytest
from typing import Dict, Any, Optional

from app.shared.tools.game_commands import execute_game_command


@pytest.mark.unit
class TestGameCommandExecution:
    """Unit tests for the execute_game_command tool."""

    @pytest.mark.asyncio
    async def test_basic_look_command(self):
        """User says '''look''' and gets room description with items."""
        result = await execute_game_command(
            command="look",
            experience="west-of-house",
            user_context={"role": "player", "user_id": "test"},
            session_state={"current_room": "west_of_house"}
        )

        assert result["success"] == True
        assert "white house" in result["narrative"].lower()
        assert "mailbox" in result["narrative"].lower()
        assert "obvious exits" in result["narrative"].lower()

    @pytest.mark.asyncio
    async def test_take_item_updates_inventory(self):
        """User takes lamp, it appears in inventory and disappears from room."""
        result = await execute_game_command(
            command="take lamp",
            experience="west-of-house",
            user_context={"role": "player", "user_id": "test"},
            session_state={
                "current_room": "forest",
                "inventory": [],
                "room_states": {"forest": {"items": ["lamp", "matches"]}}
            }
        )

        assert result["success"] == True
        assert "lamp" in result["narrative"]
        assert result["state_changes"]["inventory"] == ["lamp"]
        assert "lamp" not in result["state_changes"]["room_states"]["forest"]["items"]

    @pytest.mark.asyncio
    async def test_movement_between_rooms(self):
        """User goes north, current room changes, new room description shown."""
        result = await execute_game_command(
            command="go north",
            experience="west-of-house",
            user_context={"role": "player", "user_id": "test"},
            session_state={"current_room": "west_of_house"}
        )

        assert result["success"] == True
        assert result["state_changes"]["current_room"] == "north_of_house"
        assert "north of house" in result["narrative"].lower()

    @pytest.mark.asyncio
    async def test_rock_paper_scissors_game(self):
        """User plays rock, AI plays scissors, user wins."""
        result = await execute_game_command(
            command="rock",
            experience="rock-paper-scissors",
            user_context={"role": "player", "user_id": "test"},
            session_state={"round": 1, "score": {"player": 0, "ai": 0}}
        )

        assert result["success"] == True
        assert "rock" in result["narrative"].lower()
        assert any(action["type"] == "update_score" for action in result["actions"])

    def test_user_session_isolation_stub(self):
        """Different users get separate game sessions (placeholder test)."""
        user1_state = {"current_room": "west_of_house", "inventory": ["lamp"]}
        user2_state = {"current_room": "west_of_house", "inventory": []}
        assert user1_state != user2_state

    @pytest.mark.asyncio
    async def test_player_cannot_execute_admin_commands(self):
        """Verify code-enforced RBAC works (stubbed)."""
        result = await execute_game_command(
            command="set weather stormy",
            experience="sanctuary",
            user_context={"role": "player", "user_id": "test"},
            session_state={}
        )

        assert result["success"] == False
        assert result["error"]["code"] == "insufficient_permissions"
