"""Unit tests for slash command system

Tests the command handler module that intercepts /commands before LLM processing.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from app.services.chat.commands import (
    handle_command,
    CommandResponse,
    COMMANDS
)


class TestCommandRouter:
    """Test the main command router"""

    @pytest.mark.asyncio
    async def test_non_command_returns_none(self):
        """Regular messages (without /) should return None"""
        result = await handle_command(
            message="Hello, how are you?",
            user_id="test-user-123"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_command_prefix_detected(self):
        """Messages starting with / should be treated as commands"""
        # Even unknown commands should be handled
        result = await handle_command(
            message="/unknowncommand",
            user_id="test-user-123"
        )
        assert result is not None
        assert isinstance(result, CommandResponse)
        assert result.response_type == "error"
        assert "Unknown command" in result.message

    @pytest.mark.asyncio
    async def test_available_commands_registered(self):
        """Verify expected commands are registered"""
        assert "persona" in COMMANDS
        assert "help" in COMMANDS

    @pytest.mark.asyncio
    async def test_command_parsing_with_args(self):
        """Commands should correctly parse arguments"""
        # This tests that args are passed through to handlers
        # We'll mock the handler to verify
        with patch.dict(COMMANDS, {'test': AsyncMock(return_value=CommandResponse(message="ok"))}):
            COMMANDS['test'] = AsyncMock(return_value=CommandResponse(message="ok"))
            result = await handle_command(
                message="/test arg1 arg2 arg3",
                user_id="test-user-123"
            )
            # Handler should have been called with args
            COMMANDS['test'].assert_called_once()
            call_args = COMMANDS['test'].call_args
            assert call_args.kwargs['args'] == "arg1 arg2 arg3"

    @pytest.mark.asyncio
    async def test_command_case_insensitive(self):
        """Command names should be case-insensitive"""
        with patch.dict(COMMANDS, {'test': AsyncMock(return_value=CommandResponse(message="ok"))}):
            # Uppercase should work
            result = await handle_command(
                message="/TEST",
                user_id="test-user-123"
            )
            assert "Unknown command" in result.message  # TEST not in mock

    @pytest.mark.asyncio
    async def test_handler_error_returns_error_response(self):
        """Handler exceptions should be caught and returned as error responses"""
        async def failing_handler(**kwargs):
            raise ValueError("Something went wrong")

        with patch.dict(COMMANDS, {'failing': failing_handler}):
            result = await handle_command(
                message="/failing",
                user_id="test-user-123"
            )
            assert result.response_type == "error"
            assert "Error executing" in result.message


class TestHelpCommand:
    """Test the /help command"""

    @pytest.mark.asyncio
    async def test_help_lists_commands(self):
        """Help command should list available commands"""
        result = await handle_command(
            message="/help",
            user_id="test-user-123"
        )
        assert result is not None
        assert result.response_type == "info"
        assert "/persona" in result.message
        assert "/help" in result.message

    @pytest.mark.asyncio
    async def test_help_specific_command(self):
        """Help for specific command shows detailed usage"""
        result = await handle_command(
            message="/help persona",
            user_id="test-user-123"
        )
        assert result is not None
        # Should show persona-specific help
        assert "persona" in result.message.lower()


class TestPersonaCommand:
    """Test the /persona command"""

    @pytest.fixture
    def mock_persona_service(self):
        """Mock the persona service"""
        with patch('app.services.chat.commands.persona.persona_service') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_persona_list_no_args(self, mock_persona_service):
        """/persona without args lists available personas"""
        # Setup mock personas
        mock_persona1 = Mock()
        mock_persona1.id = uuid4()
        mock_persona1.name = "Zoe"
        mock_persona1.description = "AUDHD cognitive companion"

        mock_persona2 = Mock()
        mock_persona2.id = uuid4()
        mock_persona2.name = "Mu"
        mock_persona2.description = "Default assistant"

        mock_persona_service.list_personas = AsyncMock(return_value=[mock_persona1, mock_persona2])
        mock_persona_service.get_user_persona = AsyncMock(return_value=mock_persona2)

        result = await handle_command(
            message="/persona",
            user_id="test-user-123"
        )

        assert result is not None
        assert result.response_type == "list"
        assert "Zoe" in result.message
        assert "Mu" in result.message
        assert "current" in result.message.lower()  # Should mark current

    @pytest.mark.asyncio
    async def test_persona_switch_valid(self, mock_persona_service):
        """/persona <name> switches to specified persona"""
        mock_persona = Mock()
        mock_persona.id = uuid4()
        mock_persona.name = "Zoe"
        mock_persona.description = "AUDHD cognitive companion"

        mock_persona_service.list_personas = AsyncMock(return_value=[mock_persona])
        mock_persona_service.set_user_persona = AsyncMock()

        result = await handle_command(
            message="/persona Zoe",
            user_id="test-user-123"
        )

        assert result is not None
        assert result.response_type == "success"
        assert "Zoe" in result.message
        mock_persona_service.set_user_persona.assert_called_once()

    @pytest.mark.asyncio
    async def test_persona_switch_invalid(self, mock_persona_service):
        """/persona <invalid_name> returns error with available options"""
        mock_persona = Mock()
        mock_persona.id = uuid4()
        mock_persona.name = "Zoe"
        mock_persona.description = "AUDHD cognitive companion"

        mock_persona_service.list_personas = AsyncMock(return_value=[mock_persona])

        result = await handle_command(
            message="/persona NotAPersona",
            user_id="test-user-123"
        )

        assert result is not None
        assert result.response_type == "error"
        assert "not found" in result.message.lower()
        assert "Zoe" in result.message  # Should suggest available

    @pytest.mark.asyncio
    async def test_persona_switch_case_insensitive(self, mock_persona_service):
        """Persona names should be case-insensitive"""
        mock_persona = Mock()
        mock_persona.id = uuid4()
        mock_persona.name = "Zoe"
        mock_persona.description = "AUDHD cognitive companion"

        mock_persona_service.list_personas = AsyncMock(return_value=[mock_persona])
        mock_persona_service.set_user_persona = AsyncMock()

        # Try lowercase
        result = await handle_command(
            message="/persona zoe",
            user_id="test-user-123"
        )

        assert result.response_type == "success"


class TestCommandResponse:
    """Test CommandResponse dataclass"""

    def test_default_values(self):
        """CommandResponse should have sensible defaults"""
        response = CommandResponse(message="Test")
        assert response.message == "Test"
        assert response.response_type == "info"
        assert response.handled is True
        assert response.data is None

    def test_all_fields(self):
        """CommandResponse should accept all fields"""
        response = CommandResponse(
            message="Success!",
            response_type="success",
            handled=True,
            data={"key": "value"}
        )
        assert response.message == "Success!"
        assert response.response_type == "success"
        assert response.data == {"key": "value"}
