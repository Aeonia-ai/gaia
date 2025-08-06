"""Unit tests for PersonaService"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

from app.services.chat.persona_service_postgres import PostgresPersonaService
from app.models.persona import PersonaCreate, PersonaUpdate


class TestPersonaService:
    """Test PersonaService PostgreSQL implementation"""
    
    @pytest.fixture
    def persona_service(self):
        """Create PersonaService instance"""
        return PostgresPersonaService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        with patch('app.services.chat.persona_service_postgres.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            yield mock_session
    
    @pytest.mark.asyncio
    async def test_list_personas_active_only(self, persona_service, mock_db_session):
        """Test listing only active personas"""
        # Setup mock data - the service uses execute/fetchall pattern
        mock_row1 = Mock(
            id=uuid4(), 
            name="Mu", 
            description="Test",
            system_prompt="Test prompt",
            personality_traits={},
            capabilities={},
            is_active=True,
            created_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1]
        mock_db_session.execute.return_value = mock_result
        
        # Test
        personas = await persona_service.list_personas(active_only=True)
        
        # Verify
        assert len(personas) == 1
        assert personas[0].name == "Mu"
    
    @pytest.mark.asyncio
    async def test_get_user_persona_returns_none_for_new_user(self, persona_service, mock_db_session):
        """Test that new users have no persona preference"""
        # Mock no user preference found
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        persona = await persona_service.get_user_persona("new-user-123")
        assert persona is None
    
    @pytest.mark.asyncio
    async def test_set_user_persona_creates_preference(self, persona_service, mock_db_session):
        """Test setting user's persona preference"""
        user_id = "test-user"
        persona_id = str(uuid4())
        
        # Mock persona exists check
        mock_persona_row = Mock(
            id=persona_id, 
            name="Test Persona",
            description="Test",
            system_prompt="Test",
            personality_traits={},
            capabilities={},
            is_active=True,
            created_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_persona_row
        mock_db_session.execute.return_value = mock_result
        
        # Test
        preference = await persona_service.set_user_persona(user_id, persona_id)
        
        # Verify
        assert preference.user_id == user_id
        assert preference.persona_id == persona_id
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_default_persona_returns_mu(self, persona_service, mock_db_session):
        """Test that default persona is Mu"""
        mock_mu_row = Mock(
            id=uuid4(),
            name="Mu",
            description="Default assistant",
            system_prompt="You are Mu",
            personality_traits={},
            capabilities={},
            is_active=True,
            created_by=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_mu_row]
        mock_db_session.execute.return_value = mock_result
        
        persona = await persona_service.get_default_persona()
        assert persona.name == "Mu"
    
    @pytest.mark.asyncio
    async def test_create_persona_validates_name_unique(self, persona_service, mock_db_session):
        """Test that persona names must be unique"""
        # Mock existing persona with same name
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(name="Mu")  # Persona exists
        mock_db_session.execute.return_value = mock_result
        
        persona_data = PersonaCreate(
            name="Mu",
            description="Duplicate",
            system_prompt="test"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await persona_service.create_persona(persona_data)