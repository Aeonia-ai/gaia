"""
Test v1 conversation deletion functionality.
Tests conversation management through v1 OpenAI-compatible API.
"""

import pytest
import httpx
import uuid
from tests.fixtures.test_auth import TestAuthManager


class TestV1ConversationDeletion:
    """Test v1 conversation deletion functionality."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_v1_delete_conversation(self, gateway_url, headers):
        """Test deleting a conversation through v1 API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create conversation implicitly through v1 chat
            chat_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Create conversation for v1 deletion test"}
            )
            
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            
            # v1 returns conversation_id in metadata
            assert "_metadata" in chat_data
            conversation_id = chat_data["_metadata"]["conversation_id"]
            assert conversation_id is not None
            
            # Delete through v1 endpoint
            delete_response = await client.delete(
                f"{gateway_url}/api/v1/conversations/{conversation_id}",
                headers=headers
            )
            
            assert delete_response.status_code in [200, 204]
            
            # Verify deletion - v1 with deleted conversation_id should fail
            verify_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Testing after deletion",
                    "conversation_id": conversation_id
                }
            )
            
            # v1 may return 404 or create new conversation
            if verify_response.status_code == 200:
                # If it succeeded, it should have created a new conversation
                new_data = verify_response.json()
                new_conversation_id = new_data["_metadata"]["conversation_id"]
                assert new_conversation_id != conversation_id, "Should create new conversation for deleted ID"
            else:
                assert verify_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_v1_conversation_lifecycle(self, gateway_url, headers):
        """Test complete conversation lifecycle in v1."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Create conversation implicitly
            first_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Start v1 conversation"}
            )
            assert first_response.status_code == 200
            conversation_id = first_response.json()["_metadata"]["conversation_id"]
            
            # 2. Continue conversation
            second_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Continue conversation",
                    "conversation_id": conversation_id
                }
            )
            assert second_response.status_code == 200
            
            # 3. List conversations (if v1 supports it)
            list_response = await client.get(
                f"{gateway_url}/api/v1/conversations",
                headers=headers
            )
            
            if list_response.status_code == 200:
                conversations = list_response.json()
                # v1 format may vary
                if isinstance(conversations, list):
                    assert any(c.get("id") == conversation_id or c.get("conversation_id") == conversation_id for c in conversations)
            
            # 4. Delete conversation
            delete_response = await client.delete(
                f"{gateway_url}/api/v1/conversations/{conversation_id}",
                headers=headers
            )
            assert delete_response.status_code in [200, 204]
            
            # 5. Verify deletion behavior
            final_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "After deletion",
                    "conversation_id": conversation_id
                }
            )
            
            # v1 should either return 404 or create new conversation
            if final_response.status_code == 200:
                final_id = final_response.json()["_metadata"]["conversation_id"]
                assert final_id != conversation_id
    
    @pytest.mark.asyncio
    async def test_v1_delete_nonexistent_conversation(self, gateway_url, headers):
        """Test deleting a non-existent conversation."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            fake_id = str(uuid.uuid4())
            
            delete_response = await client.delete(
                f"{gateway_url}/api/v1/conversations/{fake_id}",
                headers=headers
            )
            
            # Should return 404 for non-existent conversation
            assert delete_response.status_code == 404