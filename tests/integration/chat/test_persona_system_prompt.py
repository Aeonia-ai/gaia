"""
Quick test to verify persona system prompt issue
"""
import pytest
import httpx
import os
from tests.fixtures.shared_test_user import shared_test_user  # Fixed: was importing from non-existent jwt_auth module
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_persona_system")

@pytest.mark.asyncio
async def test_persona_system_prompt_method(shared_test_user):
    """Test if personas work with current implementation"""
    gateway_url = os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create auth headers using shared test user
        user = shared_test_user
        from tests.fixtures.jwt_auth import JWTAuthHelper
        jwt_auth = JWTAuthHelper()
        headers = jwt_auth.create_auth_headers(user_id=user["user_id"])
        
        # Test 1: Simple name question
        response = await client.post(
            f"{gateway_url}/api/v1/chat",
            headers=headers,
            json={
                "message": "What is your name?",
                "response_format": "v0.3"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Extract response content
        if "response" in data:
            content = data["response"]
        elif "choices" in data:
            content = data["choices"][0]["message"]["content"]
        else:
            content = str(data)
            
        logger.info(f"Response to 'What is your name?': {content}")
        
        # Check if Mu is mentioned
        contains_mu = "mu" in content.lower()
        contains_robot = any(word in content.lower() for word in ["robot", "beep", "boop"])
        
        print(f"\n{'='*60}")
        print("PERSONA TEST RESULTS")
        print(f"{'='*60}")
        print(f"Response: {content}")
        print(f"Contains 'Mu': {contains_mu}")
        print(f"Contains robot characteristics: {contains_robot}")
        print(f"{'='*60}\n")
        
        # This test currently EXPECTS failure to demonstrate the issue
        if not contains_mu and not contains_robot:
            print("❌ CONFIRMED: Personas are NOT being applied properly")
            print("   System messages in array are being ignored by Claude")
        else:
            print("✅ Personas ARE working (unexpected!)")
            
        # Don't assert - we're just testing to see the behavior
        return contains_mu or contains_robot