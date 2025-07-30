"""
Test conversation deletion endpoint for persona development.
"""

import pytest
import httpx
import uuid
from tests.fixtures.test_auth import TestAuthManager


class TestConversationDeletion:
    """Test conversation deletion functionality."""
    
    @pytest.fixture
    def gateway_url(self):
        import os
        # Use localhost when running outside Docker
        if os.getenv("RUNNING_IN_DOCKER") == "true":
            return "http://gateway:8000"
        else:
            return "http://localhost:8666"
    
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
    
    async def test_delete_conversation(self, gateway_url, headers):
        """Test deleting a conversation for persona testing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, create a conversation through the v0.3 API
            create_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "Test conversation for deletion"}
            )
            
            # Debug the response if it fails
            if create_response.status_code not in [200, 201]:
                print(f"Create failed with status {create_response.status_code}")
                print(f"Response: {create_response.text}")
            
            assert create_response.status_code == 201  # 201 Created
            conversation_data = create_response.json()
            
            # The v0.3 API returns conversation_id (not id)
            conversation_id = conversation_data["conversation_id"]
            assert conversation_id is not None
            print(f"Created conversation: {conversation_id}")
            
            # Now delete the conversation
            delete_response = await client.delete(
                f"{gateway_url}/api/v1/conversations/{conversation_id}",
                headers=headers
            )
            
            # Debug the error if it fails
            if delete_response.status_code not in [200, 204]:
                print(f"Delete failed with status {delete_response.status_code}")
                print(f"Response: {delete_response.text}")
            
            # Should return 204 No Content on successful deletion
            assert delete_response.status_code in [200, 204]
            
            # Verify it's deleted by trying to send a message with that conversation_id
            # Should now return 404 since conversation doesn't exist
            verify_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Testing after deletion",
                    "conversation_id": conversation_id
                }
            )
            
            # Should return 404 for deleted conversation
            print(f"Verify response status: {verify_response.status_code}")
            if verify_response.status_code != 404:
                print(f"Expected 404, got {verify_response.status_code}")
                print(f"Response: {verify_response.text}")
            
            assert verify_response.status_code == 404, f"Expected 404 for deleted conversation, got {verify_response.status_code}"