"""
Test general conversation persistence functionality.
Extracted version-specific tests to separate files.
Focuses on direct service endpoints and general conversation behavior.
"""

import pytest
import httpx
import os
import json
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestUserFactory

logger = setup_service_logger("test_conversation_persistence")


class TestConversationPersistence:
    """Test different approaches to maintaining conversation context."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def chat_url(self):
        """Direct chat service URL."""
        return os.getenv("CHAT_URL", "http://chat-service:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        return os.getenv("AUTH_URL", "http://auth-service:8000")
    
    @pytest.fixture
    def api_key(self):
        """Get API key for testing."""
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
    @pytest.fixture
    def api_headers(self, api_key):
        """Headers with API key auth."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def user_factory(self):
        """Factory for creating test users."""
        factory = TestUserFactory()
        yield factory
        factory.cleanup_all()
    
    async def login_user(self, auth_url: str, email: str, password: str) -> Dict[str, Any]:
        """Login and get JWT."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_url}/auth/login",
                json={"email": email, "password": password}
            )
            assert response.status_code == 200
            data = response.json()
            # Normalize response
            if "session" in data and "access_token" in data["session"]:
                data["access_token"] = data["session"]["access_token"]
            return data
    
    
    
    @pytest.mark.asyncio
    async def test_direct_chat_endpoints(self, chat_url, api_headers):
        """Test direct chat service endpoints for conversation support."""
        endpoints_to_test = [
            ("/chat", "Basic chat endpoint"),
            ("/chat/direct", "Direct chat endpoint"),
            ("/chat/direct-db", "Database-backed chat"),
            ("/chat/unified", "Unified chat endpoint")
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, description in endpoints_to_test:
                try:
                    # Send a test message
                    response = await client.post(
                        f"{chat_url}{endpoint}",
                        headers=api_headers,
                        json={"message": "Hello, testing conversation support"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"{description} ({endpoint}): SUCCESS")
                        logger.info(f"  Response keys: {list(data.keys())}")
                        
                        # Check for conversation_id
                        if "conversation_id" in data:
                            logger.info(f"  Has conversation_id at top level")
                        elif "_metadata" in data and "conversation_id" in data["_metadata"]:
                            logger.info(f"  Has conversation_id in metadata")
                        else:
                            logger.info(f"  No conversation_id found")
                    else:
                        logger.info(f"{description} ({endpoint}): {response.status_code}")
                except Exception as e:
                    logger.info(f"{description} ({endpoint}): ERROR - {e}")
    
    
