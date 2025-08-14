"""
Conversation Memory Regression Tests

These tests ensure that conversation history is properly loaded and used
instead of incorrectly routing to knowledge base searches.

Bug fixed: AI was calling search_knowledge_base instead of using conversation history
for questions about recently mentioned information.
"""
import pytest
import httpx
from tests.fixtures.test_auth import TestAuthManager

class TestConversationMemoryRegression:
    """Test conversation memory to prevent regression of the routing bug."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Standard headers with JWT authentication."""
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_lucky_number_memory_bug_regression(self, gateway_url, headers):
        """Test the specific bug case that was fixed: lucky number memory."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - establish lucky number
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My lucky number is 777. Remember this for testing."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Second message - ask about lucky number (this was the failing case)
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What is my lucky number?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content = data2['choices'][0]['message']['content']
            
            # REGRESSION: Should remember 777, not search knowledge base
            assert "777" in content, f"Should remember lucky number from conversation: {content}"
            # Should NOT contain KB-related responses
            assert "knowledge base" not in content.lower(), f"Should not search KB for conversation memory: {content}"
    
    @pytest.mark.asyncio
    async def test_favorite_color_memory(self, gateway_url, headers):
        """Test conversation memory with favorite color."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Establish favorite color
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite color is emerald green. Please remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Ask about favorite color
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What color do I like best?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content = data2['choices'][0]['message']['content']
            
            # Should remember the color from conversation
            assert "emerald" in content.lower() or "green" in content.lower(), f"Should remember favorite color: {content}"
    
    @pytest.mark.asyncio
    async def test_name_memory(self, gateway_url, headers):
        """Test conversation memory with personal name."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Introduce name
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hi, my name is Alex. Nice to meet you!"}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Ask about name
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What's my name again?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content = data2['choices'][0]['message']['content']
            
            # Should remember the name
            assert "Alex" in content, f"Should remember name from conversation: {content}"
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation_memory(self, gateway_url, headers):
        """Test memory across multiple conversation turns."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            conversation_id = None
            
            # Turn 1: Establish pet name
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "I have a dog named Buddy."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Turn 2: Add pet age
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Buddy is 3 years old.",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            
            # Turn 3: Ask about both pieces of information
            response3 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Tell me about my dog.",
                    "conversation_id": conversation_id
                }
            )
            assert response3.status_code == 200
            data3 = response3.json()
            content = data3['choices'][0]['message']['content']
            
            # Should remember both name and age
            assert "Buddy" in content, f"Should remember dog's name: {content}"
            assert "3" in content, f"Should remember dog's age: {content}"
    
    @pytest.mark.asyncio
    async def test_conversation_without_id_no_memory(self, gateway_url, headers):
        """Test that without conversation_id, no memory is maintained (isolation test)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message with secret word
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "The secret code is GAMMA-7. Remember this."}
            )
            assert response1.status_code == 200
            
            # Second message WITHOUT conversation_id (should not remember)
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is the secret code?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content = data2['choices'][0]['message']['content'].lower()
            
            # Should NOT remember the code without conversation_id
            assert "gamma" not in content and "gamma-7" not in content.lower(), f"Should not remember without conversation_id: {content}"