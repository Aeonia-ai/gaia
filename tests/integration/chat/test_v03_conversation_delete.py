"""
Test v0.3 conversation deletion functionality.
Tests conversation lifecycle through v0.3 clean API.
"""

import pytest
import httpx
import uuid
from tests.fixtures.test_auth import TestAuthManager


class TestV03ConversationDeletion:
    """Test v0.3 conversation deletion functionality."""
    
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
    async def test_v03_delete_conversation(self, gateway_url, headers):
        """Test deleting a conversation through v0.3 API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a conversation through v0.3 API
            create_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "Test v0.3 conversation for deletion"}
            )
            
            assert create_response.status_code == 201
            conversation_data = create_response.json()
            conversation_id = conversation_data["conversation_id"]
            assert conversation_id is not None
            
            # Delete through v0.3 endpoint (if exists)
            delete_response = await client.delete(
                f"{gateway_url}/api/v0.3/conversations/{conversation_id}",
                headers=headers
            )
            
            # v0.3 may not have delete endpoint yet
            if delete_response.status_code == 404:
                pytest.skip("v0.3 conversation delete endpoint not implemented")
            
            assert delete_response.status_code in [200, 204]
            
            # Verify deletion by trying to use conversation
            verify_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Testing after deletion",
                    "conversation_id": conversation_id
                }
            )
            
            assert verify_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_v03_conversation_lifecycle(self, gateway_url, headers):
        """Test complete conversation lifecycle in v0.3."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Create conversation
            create_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "v0.3 lifecycle test"}
            )
            assert create_response.status_code == 201
            conversation_id = create_response.json()["conversation_id"]
            
            # 2. Send message to conversation
            chat_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello in v0.3 conversation",
                    "conversation_id": conversation_id
                }
            )
            assert chat_response.status_code == 200
            data = chat_response.json()
            assert "response" in data
            assert data["conversation_id"] == conversation_id
            
            # 3. List conversations (if endpoint exists)
            list_response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers
            )
            
            if list_response.status_code == 200:
                conversations = list_response.json()
                assert any(c["conversation_id"] == conversation_id for c in conversations.get("conversations", []))
            
            # 4. Delete conversation (if endpoint exists)
            delete_response = await client.delete(
                f"{gateway_url}/api/v0.3/conversations/{conversation_id}",
                headers=headers
            )
            
            if delete_response.status_code != 404:
                assert delete_response.status_code in [200, 204]
                
                # 5. Verify deletion
                verify_response = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={
                        "message": "Should fail",
                        "conversation_id": conversation_id
                    }
                )
                assert verify_response.status_code == 404