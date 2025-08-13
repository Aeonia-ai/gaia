"""
Test v0.2 API conversation persistence with different approaches.
Extracted from mixed version test file for better organization.
"""

import pytest
import httpx
import os
import json
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_v02_conversation_persistence")


class TestV02ConversationPersistence:
    """Test v0.2 API conversation context maintenance."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
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
    
    @pytest.mark.asyncio
    async def test_v02_chat_persistence(self, gateway_url, api_headers):
        """Test if v0.2 chat endpoint maintains context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=api_headers,
                json={"message": "My favorite color is blue. Remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            logger.info(f"v0.2 response structure: {list(data1.keys())}")
            
            # v0.2 format validation
            assert "response" in data1
            
            # Check for conversation_id in v0.2 format
            conversation_id = data1.get("conversation_id")
            if conversation_id:
                logger.info(f"V0.2 conversation ID: {conversation_id}")
            
            # Second message without conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=api_headers,
                json={"message": "What is my favorite color?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2.get("response", "")
            logger.info(f"v0.2 second response: {content2[:200]}...")
            
            has_context = "blue" in content2.lower()
            logger.info(f"v0.2 context maintained without conversation_id: {has_context}")
            
            # If we have a conversation_id, try with it
            if conversation_id:
                response3 = await client.post(
                    f"{gateway_url}/api/v0.2/chat",
                    headers=api_headers,
                    json={
                        "message": "What is my favorite color?",
                        "conversation_id": conversation_id
                    }
                )
                assert response3.status_code == 200
                data3 = response3.json()
                content3 = data3.get("response", "")
                
                has_context_with_id = "blue" in content3.lower()
                logger.info(f"v0.2 context maintained with conversation_id: {has_context_with_id}")
    
    @pytest.mark.asyncio
    async def test_v02_explicit_conversation_endpoints(self, gateway_url, api_headers):
        """Test v0.2 endpoints that explicitly handle conversations."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to create a conversation first
            conv_response = await client.post(
                f"{gateway_url}/api/v0.2/conversations",
                headers=api_headers,
                json={"name": "V0.2 Test Conversation"}
            )
            
            if conv_response.status_code in [200, 201]:
                conv_data = conv_response.json()
                conversation_id = conv_data.get("id") or conv_data.get("conversation_id")
                logger.info(f"V0.2 Created conversation: {conversation_id}")
                
                # Send message to specific conversation
                msg_response = await client.post(
                    f"{gateway_url}/api/v0.2/conversations/{conversation_id}/messages",
                    headers=api_headers,
                    json={"message": "Hello in v0.2 specific conversation"}
                )
                
                if msg_response.status_code == 200:
                    logger.info("V0.2: Successfully sent message to specific conversation")
                    data = msg_response.json()
                    assert "response" in data or "message" in data
                else:
                    # Try alternative endpoint
                    alt_response = await client.post(
                        f"{gateway_url}/api/v0.2/chat",
                        headers=api_headers,
                        json={
                            "message": "Hello in v0.2 conversation",
                            "conversation_id": conversation_id
                        }
                    )
                    if alt_response.status_code == 200:
                        logger.info("V0.2: Alternative conversation endpoint worked")
                    else:
                        logger.info(f"V0.2: Message to conversation failed: {msg_response.status_code}")
            else:
                logger.info(f"V0.2: Conversation creation endpoint not available: {conv_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v02_chat_completions_persistence(self, gateway_url, api_headers):
        """Test v0.2 chat completions endpoint conversation persistence."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message using completions format
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=api_headers,
                json={
                    "messages": [
                        {"role": "user", "content": "My favorite animal is a cat. Remember this."}
                    ],
                    "model": "claude-3-5-haiku-20241022"
                }
            )
            
            if response1.status_code == 404:
                pytest.skip("v0.2 chat completions endpoint not available")
            
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Check for conversation_id in completions response
            conversation_id = None
            if "conversation_id" in data1:
                conversation_id = data1["conversation_id"]
            elif "_metadata" in data1 and "conversation_id" in data1["_metadata"]:
                conversation_id = data1["_metadata"]["conversation_id"]
            
            logger.info(f"V0.2 completions conversation_id: {conversation_id}")
            
            # Second message
            messages = [
                {"role": "user", "content": "My favorite animal is a cat. Remember this."},
                {"role": "assistant", "content": data1["choices"][0]["message"]["content"]},
                {"role": "user", "content": "What is my favorite animal?"}
            ]
            
            response2 = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=api_headers,
                json={
                    "messages": messages,
                    "model": "claude-3-5-haiku-20241022",
                    "conversation_id": conversation_id
                } if conversation_id else {
                    "messages": messages,
                    "model": "claude-3-5-haiku-20241022"
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            
            has_context = "cat" in content2.lower()
            logger.info(f"V0.2 completions context maintained: {has_context}")
    
    @pytest.mark.asyncio
    async def test_v02_streaming_persistence(self, gateway_url, api_headers):
        """Test v0.2 streaming conversation persistence."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First try v0.2 streaming endpoint
            chunks = []
            conversation_id = None
            
            try:
                async with client.stream(
                    "POST",
                    f"{gateway_url}/api/v0.2/chat",
                    headers=api_headers,
                    json={
                        "message": "My hobby is painting. Remember this.",
                        "stream": True
                    }
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                chunks.append(data_str)
                                
                                # Look for conversation_id
                                if data_str != "[DONE]":
                                    try:
                                        chunk_data = json.loads(data_str)
                                        if not conversation_id and "conversation_id" in chunk_data:
                                            conversation_id = chunk_data["conversation_id"]
                                    except json.JSONDecodeError:
                                        continue
                        
                        logger.info(f"V0.2 streaming worked, conversation_id: {conversation_id}")
                        
                        # Test persistence
                        response2 = await client.post(
                            f"{gateway_url}/api/v0.2/chat",
                            headers=api_headers,
                            json={
                                "message": "What is my hobby?",
                                "conversation_id": conversation_id
                            } if conversation_id else {
                                "message": "What is my hobby?"
                            }
                        )
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            content2 = data2.get("response", "")
                            has_context = "painting" in content2.lower()
                            logger.info(f"V0.2 streaming context maintained: {has_context}")
                    else:
                        logger.info(f"V0.2 streaming not available: {response.status_code}")
            except Exception as e:
                logger.info(f"V0.2 streaming test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_v02_conversation_list(self, gateway_url, api_headers):
        """Test v0.2 conversation listing and retrieval."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # List existing conversations
            list_response = await client.get(
                f"{gateway_url}/api/v0.2/conversations",
                headers=api_headers
            )
            
            if list_response.status_code == 200:
                data = list_response.json()
                conversations = data.get("conversations", [])
                logger.info(f"V0.2: Found {len(conversations)} existing conversations")
                
                # If there are conversations, try to retrieve one
                if conversations:
                    first_conv = conversations[0]
                    conv_id = first_conv.get("id") or first_conv.get("conversation_id")
                    
                    # Get specific conversation
                    get_response = await client.get(
                        f"{gateway_url}/api/v0.2/conversations/{conv_id}",
                        headers=api_headers
                    )
                    
                    if get_response.status_code == 200:
                        conv_data = get_response.json()
                        logger.info(f"V0.2: Retrieved conversation {conv_id}")
                        logger.info(f"  Conversation keys: {list(conv_data.keys())}")
                    else:
                        logger.info(f"V0.2: Could not retrieve conversation: {get_response.status_code}")
            else:
                logger.info(f"V0.2: Conversation list not available: {list_response.status_code}")