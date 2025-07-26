"""Gateway API client for web service"""
import httpx
from typing import Optional, Dict, Any
from app.services.web.config import settings
from app.shared.logging import setup_service_logger

logger = setup_service_logger("gateway_client")


class GaiaAPIClient:
    """Client for communicating with the Gaia Gateway"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.gateway_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,  # Increased timeout for LLM responses
            follow_redirects=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user via gateway"""
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                # No authentication required for login
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Login failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise
    
    async def register(self, email: str, password: str, username: Optional[str] = None) -> Dict[str, Any]:
        """Register new user via gateway"""
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                # No authentication required for registration
                json={
                    "email": email,
                    "password": password
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Registration failed: {e.response.status_code} - {e.response.text}")
            # Re-raise with response text included for better error handling
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                error_detail = error_json.get("detail", error_detail)
            except:
                pass
            raise Exception(error_detail) from e
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise
    
    async def chat_completion_stream(
        self, 
        messages: list,
        jwt_token: str,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        """Stream chat completion response from gateway"""
        # Use JWT token if available, otherwise fall back to API key
        headers = {}
        if jwt_token and jwt_token != "dev-token-12345":  # Real JWT token
            headers["Authorization"] = f"Bearer {jwt_token}"
            logger.debug("Using Supabase JWT for gateway request")
        else:
            headers["X-API-Key"] = settings.api_key
            logger.debug("Using API key for gateway request")
        
        try:
            # Use v1 chat endpoint with stream=true (routes to unified)
            # Ensure we have a valid message
            message_content = ""
            if messages:
                message_content = messages[-1].get("content", "").strip()
            
            if not message_content:
                raise ValueError("Message content cannot be empty")
            
            async with self.client.stream(
                "POST",
                "/api/v1/chat",
                headers=headers,
                json={
                    "message": message_content,
                    "model": model,
                    "stream": True  # Enable streaming mode
                }
            ) as response:
                response.raise_for_status()
                logger.info(f"Started streaming from gateway, status: {response.status_code}")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        logger.debug(f"Gateway stream chunk: {data[:100]}")
                        yield data
        except httpx.HTTPStatusError as e:
            logger.error(f"Chat completion failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise
    
    async def chat_completion(
        self, 
        messages: list,
        jwt_token: str,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        """Send non-streaming chat completion request to gateway"""
        
        try:
            # Since we're maintaining message history on the server,
            # always use the v0.2 API format with single message
            headers = {}
            if jwt_token and jwt_token != "dev-token-12345":
                # Use real JWT for authenticated users
                headers["Authorization"] = f"Bearer {jwt_token}"
            else:
                # Fall back to API key for dev/testing
                headers["X-API-Key"] = settings.api_key
            
            # Use v1 chat endpoint (routes to unified)
            # Ensure we have a valid message
            message_content = ""
            if messages:
                message_content = messages[-1].get("content", "").strip()
            
            if not message_content:
                raise ValueError("Message content cannot be empty")
            
            endpoint = "/api/v1/chat"
            payload = {
                "message": message_content,
                "model": model,
                "stream": False  # Explicitly set non-streaming
            }
            
            response = await self.client.post(
                endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Chat completion failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise
    
    async def get_conversations(self, jwt_token: str) -> list:
        """Get user's conversations"""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        try:
            response = await self.client.get(
                "/api/v1/conversations",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("conversations", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Get conversations failed: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Get conversations error: {e}")
            return []
    
    async def get_conversation(self, conversation_id: str, jwt_token: str) -> Dict[str, Any]:
        """Get specific conversation with messages"""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        try:
            response = await self.client.get(
                f"/api/v1/conversations/{conversation_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Get conversation failed: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Get conversation error: {e}")
            raise
    
    async def create_conversation(self, jwt_token: str, title: str = "New Conversation") -> Dict[str, Any]:
        """Create new conversation"""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        try:
            response = await self.client.post(
                "/api/v1/conversations",
                headers=headers,
                json={"title": title}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Create conversation failed: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Create conversation error: {e}")
            raise
    
    async def get_models(self, jwt_token: str) -> list:
        """Get available models"""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        try:
            response = await self.client.get(
                "/api/v1/models",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("models", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Get models failed: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Get models error: {e}")
            return []
    
    async def resend_verification(self, email: str) -> Dict[str, Any]:
        """Resend email verification"""
        try:
            response = await self.client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Resend verification failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            raise
    
    async def confirm_email(self, token: str, email: str) -> Dict[str, Any]:
        """Confirm email with verification token"""
        try:
            response = await self.client.post(
                "/api/v1/auth/confirm",
                json={"token": token, "email": email}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Email confirmation failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Email confirmation error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health"""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


# Global client instance
gateway_client = GaiaAPIClient()