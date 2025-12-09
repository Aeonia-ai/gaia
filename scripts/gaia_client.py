#!/usr/bin/env python3
"""
GAIA Interactive Chat Client

A command-line interface for interacting with the GAIA platform v0.3 API.
Supports conversation management, persona switching, and rich text output.
"""

import os
import sys
import json
import argparse
import asyncio
import getpass
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx
import keyring

# GAIA API Configuration
GAIA_ENVIRONMENTS = {
    "local": "http://localhost:8666",
    "dev": "https://gaia-gateway-dev.fly.dev",
    "staging": "https://gaia-gateway-staging.fly.dev",
    "prod": "https://gaia-gateway-prod.fly.dev"
}

CONFIG_DIR = Path.home() / ".gaia"
CONFIG_FILE = CONFIG_DIR / "gaia_client.settings.json"
CONFIG_VERSION = 1


class StreamEventType(str, Enum):
    CONTENT = "content"
    METADATA = "metadata"
    DONE = "done"
    ERROR = "error"
    RAW = "raw"


@dataclass
class StreamEvent:
    type: StreamEventType
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class TransportProtocol(str, Enum):
    SSE = "sse"
    WEBSOCKET = "websocket"


class AuthMode(str, Enum):
    """Authentication strategy preference for the CLI."""

    AUTO = "auto"       # Prefer JWT if available, fall back to API key
    JWT_ONLY = "jwt"    # Require JWT (email/password); never auto-use API keys
    API_KEY = "api_key" # Always use API key (keyring/env/prompt)


@dataclass
class GaiaClientConfig:
    """Persisted, non-sensitive client preferences."""

    version: int = CONFIG_VERSION
    environment: str = "local"
    default_persona: str = "mu"
    logging_enabled: bool = False
    log_name: Optional[str] = None
    last_conversation_id: Optional[str] = None
    default_transport: TransportProtocol = TransportProtocol.SSE
    conversation_aliases: Dict[str, str] = field(default_factory=dict)
    auth_mode: AuthMode = AuthMode.AUTO

    @classmethod
    def load(cls) -> "GaiaClientConfig":
        if not CONFIG_FILE.exists():
            CONFIG_DIR.mkdir(exist_ok=True)
            return cls()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            version = raw.get("version", CONFIG_VERSION)
            if version != CONFIG_VERSION:
                raw["version"] = CONFIG_VERSION
            raw.setdefault("default_transport", TransportProtocol.SSE.value)
            raw.setdefault("auth_mode", AuthMode.AUTO.value)
            auth_mode_value = raw.get("auth_mode", AuthMode.AUTO.value)
            if auth_mode_value not in AuthMode._value2member_map_:
                auth_mode_value = AuthMode.AUTO.value
            return cls(
                version=raw.get("version", CONFIG_VERSION),
                environment=raw.get("environment", "local"),
                default_persona=raw.get("default_persona", "mu"),
                logging_enabled=raw.get("logging_enabled", False),
                log_name=raw.get("log_name"),
                last_conversation_id=raw.get("last_conversation_id"),
                default_transport=TransportProtocol(
                    raw.get("default_transport", TransportProtocol.SSE.value)
                ),
                conversation_aliases=raw.get("conversation_aliases", {}),
                auth_mode=AuthMode(auth_mode_value),
            )
        except (json.JSONDecodeError, OSError, ValueError):
            return cls()

    def save(self):
        CONFIG_DIR.mkdir(exist_ok=True)
        data = asdict(self)
        data["default_transport"] = self.default_transport.value
        data["auth_mode"] = self.auth_mode.value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass

    def update_alias(self, alias: str, conversation_id: str):
        self.conversation_aliases[alias] = conversation_id
        self.save()


class ChatStreamTransport:
    """Handles streaming transport (SSE today, WebSocket-ready)."""

    def __init__(self, base_url: str, auth_manager: "GaiaAuthManager"):
        self.base_url = base_url
        self.auth = auth_manager

    async def stream_chat(
        self,
        payload: Dict[str, Any],
        protocol: TransportProtocol = TransportProtocol.SSE,
    ) -> AsyncGenerator[StreamEvent, None]:
        if protocol == TransportProtocol.SSE:
            async for event in self._stream_via_sse(payload):
                yield event
        else:
            raise NotImplementedError("WebSocket transport not implemented yet")

    async def _stream_via_sse(
        self, payload: Dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:
        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v0.3/chat",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield StreamEvent(type=StreamEventType.DONE)
                        break
                    try:
                        event_payload = json.loads(data_str)
                        if "choices" in event_payload:
                            delta = event_payload.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield StreamEvent(
                                    type=StreamEventType.CONTENT,
                                    content=content,
                                    data=event_payload,
                                )
                            continue
                        event_type = event_payload.get("type", StreamEventType.CONTENT.value)
                        if event_type in {"metadata", "model_selection"}:
                            event_enum = StreamEventType.METADATA
                        elif event_type in StreamEventType._value2member_map_:
                            event_enum = StreamEventType(event_type)
                        else:
                            event_enum = StreamEventType.RAW
                        yield StreamEvent(
                            type=event_enum,
                            content=event_payload.get("content"),
                            data=event_payload,
                        )
                    except json.JSONDecodeError:
                        yield StreamEvent(
                            type=StreamEventType.RAW,
                            content=data_str,
                            data={"raw": data_str},
                        )

class ConversationLogger:
    """Handles logging of conversations to JSON files."""
    
    def __init__(self, log_dir="logs", enabled=False, log_name=None):
        self.log_dir = Path(log_dir)
        self.enabled = enabled or log_name is not None
        self.log_name = log_name
        self.current_session = None
        self.session_log = []
        
        if self.enabled:
            self.log_dir.mkdir(exist_ok=True)
    
    def start_session(self, conversation_id: str, persona_name: str = "Default"):
        """Start a new conversation session."""
        if not self.enabled:
            return
        
        if self.log_name:
            # Use specified log name and append to existing file
            log_file = self.log_dir / f"{self.log_name}.json"
            self._load_existing_log(log_file)
        else:
            # Create new timestamped session file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_persona = persona_name.replace(' ', '_').replace(',', '')
            log_file = self.log_dir / f"gaia_{safe_persona}_{timestamp}.json"
            self.session_log = []
        
        self.current_session = {
            "session_id": self.log_name or datetime.now().strftime("%Y%m%d_%H%M%S"),
            "conversation_id": conversation_id,
            "persona_name": persona_name,
            "started_at": datetime.now().isoformat(),
            "log_file": str(log_file)
        }
        
        print(f"📝 Logging to: {self.current_session['log_file']}")
    
    def _load_existing_log(self, log_file):
        """Load existing log file and append to it."""
        self.session_log = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and "exchanges" in existing_data:
                        self.session_log = existing_data["exchanges"]
                    elif isinstance(existing_data, list):
                        self.session_log = existing_data
                print(f"📖 Loaded {len(self.session_log)} existing exchanges")
            except (json.JSONDecodeError, KeyError):
                print(f"⚠️ Could not load existing log, starting fresh")
                self.session_log = []
    
    def log_exchange(self, user_message: str, ai_response: str):
        """Log a single exchange in the conversation."""
        if not self.enabled or not self.current_session:
            return
            
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response
        }
        self.session_log.append(exchange)
        
        # Save updated log
        session_data = {
            **self.current_session,
            "exchanges": self.session_log,
            "total_exchanges": len(self.session_log)
        }
        
        with open(self.current_session['log_file'], 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def end_session(self):
        """End the current session."""
        if self.enabled and self.current_session:
            total = len(self.session_log)
            action = "appended to" if self.log_name else "saved to"
            print(f"💾 {total} total exchanges {action} {self.current_session['log_file']}")
            self.current_session = None
            self.session_log = []


class GaiaAuthManager:
    """Manages authentication for GAIA API."""
    
    def __init__(
        self,
        environment: str = "dev",
        base_url: str = None,
        auth_mode: AuthMode = AuthMode.AUTO,
    ):
        self.environment = environment
        self.service_name = f"gaia-client-{environment}"
        self.base_url = base_url
        self.auth_mode = auth_mode
        self._token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._api_key = None
        self._user_email = None
        self._api_key_source: Optional[str] = None
        
        # Try to load saved tokens on init
        self._load_saved_tokens()

    def set_auth_mode(self, mode: AuthMode):
        self.auth_mode = mode
    
    def get_api_key(self, prompt: bool = False, force_prompt: bool = False) -> Optional[str]:
        """Fetch API key, preferring stored credentials over manual prompts."""
        if self.auth_mode == AuthMode.JWT_ONLY and not force_prompt:
            return None

        if self._api_key and not force_prompt:
            return self._api_key

        # Keyring takes precedence so user logins persist
        try:
            if not force_prompt:
                stored_key = keyring.get_password(self.service_name, "api_key")
                if stored_key:
                    self._api_key = stored_key
                    self._api_key_source = "keyring"
                    return stored_key
        except Exception:
            pass

        if not prompt and not force_prompt:
            return None

        api_key = self._prompt_and_store_api_key()
        self._api_key = api_key
        self._api_key_source = "keyring" if api_key else None
        return api_key

    def _prompt_and_store_api_key(self) -> Optional[str]:
        print("\n🔑 Enter your GAIA API key (input hidden).")
        api_key = getpass.getpass("API key: ").strip()
        if not api_key:
            print("⚠️ No API key entered.")
            return None
        try:
            keyring.set_password(self.service_name, "api_key", api_key)
            print("✅ API key saved securely")
            self._api_key_source = "keyring"
        except Exception:
            print("⚠️ Could not save API key to keyring")
        return api_key

    def prompt_for_api_key(self) -> Optional[str]:
        """Interactive helper for commands to store an API key."""
        api_key = self._prompt_and_store_api_key()
        if api_key:
            self._api_key = api_key
            self._api_key_source = "keyring"
        return api_key
    
    def _load_saved_tokens(self):
        """Load saved JWT tokens from keyring."""
        try:
            import keyring
            # Load access token and metadata
            self._token = keyring.get_password(self.service_name, "access_token")
            self._refresh_token = keyring.get_password(self.service_name, "refresh_token")
            self._user_email = keyring.get_password(self.service_name, "user_email")
            
            expiry_str = keyring.get_password(self.service_name, "token_expires_at")
            if expiry_str:
                try:
                    self._token_expires_at = datetime.fromisoformat(expiry_str)
                except ValueError:
                    self._token_expires_at = None
            
            if self._token:
                if self._token_expires_at and datetime.now() > self._token_expires_at:
                    print("⚠️ Saved session expired — will attempt refresh automatically")
                else:
                    print(f"✅ Loaded saved session for: {self._user_email}")
        except Exception:
            # Silently fail if keyring is not available
            pass
    
    def _save_tokens(self, access_token: str, refresh_token: str, expires_in: int, email: str):
        """Save JWT tokens to keyring."""
        try:
            import keyring
            keyring.set_password(self.service_name, "access_token", access_token)
            keyring.set_password(self.service_name, "refresh_token", refresh_token)
            keyring.set_password(self.service_name, "user_email", email)
            
            # Calculate and save expiry time
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            keyring.set_password(self.service_name, "token_expires_at", expires_at.isoformat())
            
            self._token = access_token
            self._refresh_token = refresh_token
            self._user_email = email
            self._token_expires_at = expires_at
        except Exception as e:
            print(f"⚠️ Could not save tokens to keyring: {e}")
    
    def _clear_saved_tokens(self):
        """Clear saved JWT tokens from keyring."""
        try:
            import keyring
            keyring.delete_password(self.service_name, "access_token")
            keyring.delete_password(self.service_name, "refresh_token")
            keyring.delete_password(self.service_name, "user_email")
            keyring.delete_password(self.service_name, "token_expires_at")
        except Exception:
            pass
        
        self._token = None
        self._refresh_token = None
        self._user_email = None
        self._token_expires_at = None

    def clear_api_key(self):
        try:
            keyring.delete_password(self.service_name, "api_key")
        except Exception:
            pass
        self._api_key = None
        self._api_key_source = None

    def has_keyring_api_key(self) -> bool:
        try:
            return keyring.get_password(self.service_name, "api_key") is not None
        except Exception:
            return False

    @property
    def api_key_source(self) -> Optional[str]:
        return self._api_key_source

    def describe_user_state(self) -> str:
        if self._user_email:
            return f"👤 User: {self._user_email} (JWT)"

        source = self._api_key_source
        if source == "keyring":
            return "🔑 User: API key (keyring)"
        if self._api_key:
            return "🔑 User: API key (session)"

        if self.has_keyring_api_key():
            return "🔑 User: API key (keyring stored)"
        return "❌ User: Not authenticated"

    def has_credentials(self) -> bool:
        return bool(
            self._token
            or self._user_email
            or self._api_key
            or self.has_keyring_api_key()
        )

    async def login(self, email: str, password: str) -> bool:
        """Login with email and password to get JWT tokens."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v0.3/auth/login",
                    json={"email": email, "password": password}
                )
                response.raise_for_status()
                data = response.json()
                
                # Store tokens
                session = data.get("session", {})
                access_token = session.get("access_token")
                refresh_token = session.get("refresh_token")
                expires_in = session.get("expires_in", 3600)  # Default 1 hour
                user_email = data.get("user", {}).get("email", email)
                
                # Save tokens to keyring
                if access_token and refresh_token:
                    self._save_tokens(access_token, refresh_token, expires_in, user_email)
                    print(f"✅ Logged in as: {user_email}")
                    print(f"💾 Session saved (expires in {expires_in//60} minutes)")
                    return True
                else:
                    print("⚠️ Login succeeded but no tokens received")
                    return False
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Login failed: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def register(self, email: str, password: str) -> bool:
        """Register a new user account."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v0.3/auth/register",
                    json={"email": email, "password": password}
                )
                response.raise_for_status()
                data = response.json()
                
                # Store tokens if returned
                session = data.get("session", {})
                if session:
                    self._token = session.get("access_token")
                    self._refresh_token = session.get("refresh_token")
                    self._user_email = data.get("user", {}).get("email", email)
                    print(f"✅ Registered and logged in as: {self._user_email}")
                else:
                    print(f"✅ Registered: {email} - Please check your email to confirm")
                
                return True
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Registration failed: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    async def refresh_tokens(self) -> bool:
        """Refresh JWT tokens using refresh token."""
        if not self._refresh_token:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v0.3/auth/refresh",
                    json={"refresh_token": self._refresh_token}
                )
                response.raise_for_status()
                data = response.json()
                
                # Store new tokens
                session = data.get("session", {})
                access_token = session.get("access_token")
                refresh_token = session.get("refresh_token", self._refresh_token)
                expires_in = session.get("expires_in", 3600)
                
                if access_token:
                    self._save_tokens(access_token, refresh_token, expires_in, self._user_email)
                    print("🔄 Token refreshed successfully")
                    return True
                    
        except Exception as e:
            print(f"⚠️ Token refresh failed: {e}")
            self._clear_saved_tokens()
        
        return False
    
    async def ensure_valid_token(self) -> bool:
        """Ensure we have a valid JWT session, refreshing if necessary."""
        # API key-only mode never needs JWT validation
        if self.auth_mode == AuthMode.API_KEY:
            return True

        if self._token and self._token_expires_at:
            # Token still healthy
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return True
            # Otherwise attempt refresh
            return await self.refresh_tokens()

        if self._token and not self._token_expires_at:
            # No expiry info (shouldn't happen), trust current token
            return True

        if self._refresh_token:
            return await self.refresh_tokens()
        
        return False
    
    def get_headers(self, prompt_for_api_key: bool = False) -> Dict[str, str]:
        """Get authentication headers respecting the configured auth mode."""
        prefer_jwt = self.auth_mode in {AuthMode.AUTO, AuthMode.JWT_ONLY}

        if prefer_jwt and self._token:
            return {"Authorization": f"Bearer {self._token}"}

        if self.auth_mode == AuthMode.JWT_ONLY:
            raise ValueError(
                "JWT authentication required. Use /login <email> <password> to sign in."
            )

        if not self._api_key and prompt_for_api_key:
            self._api_key = self.get_api_key(prompt=True)

        if not self._api_key:
            raise ValueError(
                "No authentication credentials available. "
                "Use /login <email> <password> for JWT or /api-key store to save an API key."
            )

        return {"X-API-Key": self._api_key}


class GaiaClient:
    """GAIA API client with v0.3 endpoint support."""
    
    def __init__(
        self,
        base_url: str,
        auth_manager: GaiaAuthManager,
        config: GaiaClientConfig,
    ):
        self.base_url = base_url
        self.auth = auth_manager
        self.config = config
        self.current_conversation_id = config.last_conversation_id
        self.current_persona = config.default_persona
        self.transport = ChatStreamTransport(base_url, auth_manager)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            return response.json()
    
    async def send_message(self, message: str, stream: bool = False) -> Dict[str, Any]:
        """Send a chat message using v0.3 API."""
        payload = {
            "message": message,
            "conversation_id": self.current_conversation_id,
            "stream": stream,
        }

        if stream:
            attempt = 0
            while attempt < 2:
                try:
                    full_response = ""
                    async for event in self.stream_message(payload):
                        if event.type == StreamEventType.METADATA and event.data:
                            conversation_id = event.data.get("conversation_id")
                            if conversation_id:
                                self.set_conversation(conversation_id)
                        elif event.type == StreamEventType.CONTENT and event.content:
                            print(event.content, end="", flush=True)
                            full_response += event.content
                        elif event.type == StreamEventType.ERROR:
                            raise RuntimeError(event.data or event.content)
                    print()
                    return {
                        "response": full_response,
                        "conversation_id": self.current_conversation_id,
                        "message": message,
                    }
                except httpx.HTTPStatusError as error:
                    if self._reset_stale_conversation(error, payload):
                        attempt += 1
                        continue
                    raise

        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        headers["Content-Type"] = "application/json"

        attempt = 0
        while attempt < 2:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/v0.3/chat",
                        headers=headers,
                        json=payload,
                    )
                response.raise_for_status()
                result = response.json()
                if "conversation_id" in result:
                    self.set_conversation(result["conversation_id"])
                return result
            except httpx.HTTPStatusError as error:
                if self._reset_stale_conversation(error, payload):
                    attempt += 1
                    continue
                raise

    async def stream_message(
        self,
        payload: Dict[str, Any],
        protocol: Optional[TransportProtocol] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Yield streaming events for a message (transport-agnostic)."""
        payload = {**payload, "stream": True}
        protocol = protocol or self.config.default_transport
        async for event in self.transport.stream_chat(payload, protocol):
            yield event

    def set_conversation(self, conversation_id: Optional[str], persist: bool = True):
        self.current_conversation_id = conversation_id
        if persist:
            self.config.last_conversation_id = conversation_id
            self.config.save()

    def _reset_stale_conversation(
        self, error: httpx.HTTPStatusError, payload: Dict[str, Any]
    ) -> bool:
        """Clear invalid conversation IDs and signal caller to retry once."""
        if error.response.status_code != 404:
            return False
        stale_id = payload.get("conversation_id")
        if not stale_id:
            return False
        print(f"⚠️ Clearing missing conversation {stale_id}; starting fresh.")
        self.set_conversation(None)
        payload["conversation_id"] = None
        return True

    async def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations."""
        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v0.3/conversations",
                headers=headers
            )
            response.raise_for_status()
            conversations = response.json().get("conversations", [])

        normalized: List[Dict[str, Any]] = []
        for conv in conversations:
            conv_id = conv.get("conversation_id") or conv.get("id")
            if conv_id:
                # Maintain backward compatibility for callers expecting `id`
                conv = {**conv, "conversation_id": conv_id, "id": conv_id}
            normalized.append(conv)
        return normalized
    
    async def create_conversation(self, title: str = "New Conversation") -> Dict[str, Any]:
        """Create a new conversation."""
        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": title}
            )
            response.raise_for_status()
            result = response.json()

        conversation_id = result.get("conversation_id") or result.get("id")
        if conversation_id:
            # Normalize both keys for downstream callers
            result.setdefault("conversation_id", conversation_id)
            result.setdefault("id", conversation_id)
        self.set_conversation(conversation_id)
        return result
    
    async def get_personas(self) -> List[Dict[str, Any]]:
        """Get available personas (v1 endpoint)."""
        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/chat/personas",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("personas", [])
    
    async def set_persona(self, persona_id: str) -> Dict[str, Any]:
        """Set the active persona."""
        await self.auth.ensure_valid_token()
        headers = self.auth.get_headers()
        headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/v1/chat/personas",
                headers=headers,
                json={"persona_id": persona_id}
            )
            response.raise_for_status()
            self.current_persona = persona_id
            self.config.default_persona = persona_id
            self.config.save()
            return response.json()


class ChatCommands:
    """Interactive chat commands."""
    
    def __init__(
        self,
        client: GaiaClient,
        auth_manager: GaiaAuthManager,
        config: GaiaClientConfig,
    ):
        self.client = client
        self.auth = auth_manager
        self.config = config
    
    async def help(self, args: str = "") -> str:
        """Show available commands."""
        commands = [
            "=== Chat Commands ===",
            "/help - Show this help message",
            "/new [title] - Start a new conversation",
            "/list - List all conversations",
            "/switch <id> - Switch to a conversation by ID",
            "/alias <name> [conversation_id] - Map alias to a conversation",
            "/personas - List available personas",
            "/persona <id> - Switch to a persona",
            "/status - Show current status",
            "/export [file] - Export current conversation",
            "/clear - Clear screen",
            "",
            "=== Auth Commands ===",
            "/login <email> <password> - Login with email/password",
            "/register <email> <password> - Register new account",
            "/api-key <store|clear|status> - Manage stored API keys",
            "/logout - Logout current session and clear stored credentials",
            "/whoami - Show current user",
            "/config [show|set key=value|reset] - Manage CLI preferences",
            "",
            "/quit - Exit the chat",
            "/exit - Exit the chat"
        ]
        return "\n".join(commands)
    
    async def new_conversation(self, args: str = "") -> str:
        """Create a new conversation."""
        title = args.strip() or "New Conversation"
        try:
            result = await self.client.create_conversation(title)
            conv_id = result.get("conversation_id") or result.get("id") or "unknown"
            return f"✅ Created new conversation: {conv_id}"
        except Exception as e:
            return f"❌ Error creating conversation: {e}"
    
    async def list_conversations(self, args: str = "") -> str:
        """List all conversations."""
        try:
            conversations = await self.client.list_conversations()
            if not conversations:
                return "No conversations found."
            
            output = "📚 Conversations:\n"
            for index, conv in enumerate(conversations[:10], start=1):
                created = conv.get('created_at', 'Unknown')[:10]
                title = conv.get('title', 'Untitled')[:50]
                preview = (conv.get('preview') or '').strip()[:60]
                preview_text = f" | {preview}" if preview else ""
                conv_id = (conv.get('id') or conv.get('conversation_id') or 'unknown')[:8]
                output += f"{index}. [{conv_id}] {created} - {title}{preview_text}\n"
            
            if len(conversations) > 10:
                output += f"\n... and {len(conversations) - 10} more"
            
            return output
        except Exception as e:
            return f"❌ Error listing conversations: {e}"
    
    async def switch_conversation(self, args: str) -> str:
        """Switch to a different conversation."""
        if not args:
            return "Usage: /switch <conversation_id>"
        
        conv_id = args.strip()
        conv_id = self.config.conversation_aliases.get(conv_id, conv_id)
        self.client.set_conversation(conv_id)
        return f"✅ Switched to conversation: {conv_id}"

    async def alias(self, args: str = "") -> str:
        """Manage conversation aliases."""
        if args.strip().lower() == "list":
            if not self.config.conversation_aliases:
                return "No aliases configured."
            lines = ["🔖 Conversation Aliases:"]
            for name, conv in self.config.conversation_aliases.items():
                lines.append(f"- {name} → {conv}")
            return "\n".join(lines)
        parts = args.split()
        if not parts:
            return "Usage: /alias <name> [conversation_id]"
        name = parts[0]
        if len(parts) == 1:
            if not self.client.current_conversation_id:
                return "⚠️ No active conversation to alias."
            conv_id = self.client.current_conversation_id
        else:
            conv_id = parts[1]
        self.config.update_alias(name, conv_id)
        return f"✅ Alias '{name}' saved for conversation {conv_id}"
    
    async def list_personas(self, args: str = "") -> str:
        """List available personas."""
        try:
            personas = await self.client.get_personas()
            if not personas:
                return "No personas available."
            
            output = "🎭 Available Personas:\n"
            for p in personas:
                marker = "✓" if p['id'] == self.client.current_persona else " "
                output += f"{marker} [{p['id']}] {p['name']} - {p['description']}\n"
            
            return output
        except Exception as e:
            return f"❌ Error listing personas: {e}"
    
    async def set_persona(self, args: str) -> str:
        """Set the active persona."""
        if not args:
            return "Usage: /persona <persona_id>"
        
        persona_id = args.strip()
        try:
            await self.client.set_persona(persona_id)
            return f"✅ Switched to persona: {persona_id}"
        except Exception as e:
            return f"❌ Error setting persona: {e}"
    
    async def status(self, args: str = "") -> str:
        """Show current status."""
        user_info = self.auth.describe_user_state()

        status_lines = [
            f"🌐 Environment: {self.client.base_url}",
            user_info,
            f"🔐 Auth mode: {self.auth.auth_mode.value}",
            f"💬 Conversation: {self.client.current_conversation_id or 'None'}",
        ]
        
        # Check health
        try:
            health = await self.client.health_check()
            if health.get("status") == "healthy":
                status_lines.append("✅ Gateway: Healthy")
                
                # Show service status
                services = health.get("services", {})
                if services:
                    status_lines.append("\n📊 Services:")
                    for name, info in services.items():
                        status = "✅" if info.get("status") == "healthy" else "❌"
                        status_lines.append(f"  {status} {name}")
            else:
                status_lines.append("❌ Gateway: Unhealthy")
        except Exception:
            status_lines.append("❌ Gateway: Unreachable")
        
        return "\n".join(status_lines)
    
    async def export_conversation(self, args: str = "") -> str:
        """Export current conversation to file."""
        # This would need conversation history API endpoint
        return "⚠️ Export feature not yet implemented"
    
    async def clear_screen(self, args: str = "") -> str:
        """Clear the screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
        return ""
    
    async def login(self, args: str) -> str:
        """Login with email and password."""
        parts = args.strip().split()
        if len(parts) != 2:
            return "Usage: /login <email> <password>"
        
        email, password = parts
        success = await self.auth.login(email, password)
        if success:
            if (
                not self.client.current_conversation_id
                and self.config.last_conversation_id
            ):
                self.client.set_conversation(self.config.last_conversation_id)
            return f"✅ Logged in as {email}"
        return "❌ Login failed"
    
    async def register(self, args: str) -> str:
        """Register a new account."""
        parts = args.strip().split()
        if len(parts) != 2:
            return "Usage: /register <email> <password>"
        
        email, password = parts
        success = await self.auth.register(email, password)
        if success:
            return f"✅ Registration successful"
        return "❌ Registration failed"
    
    async def logout(self, args: str = "") -> str:
        """Logout current session."""
        self.auth._clear_saved_tokens()
        self.auth.clear_api_key()
        return "✅ Logged out (session and API key cleared)"
    
    async def api_key(self, args: str = "") -> str:
        """Manage stored API key."""
        action = (args or "").strip().lower()
        if action in {"", "help"}:
            return "Usage: /api-key <store|clear|status>"
        if action == "store":
            key = self.auth.prompt_for_api_key()
            if key and not self.client.current_conversation_id and self.config.last_conversation_id:
                self.client.set_conversation(self.config.last_conversation_id)
            return "✅ API key saved securely" if key else "⚠️ API key not saved"
        if action == "clear":
            self.auth.clear_api_key()
            return "🗑️ API key removed from keyring"
        if action == "status":
            return (
                "🔑 API key present in keyring"
                if self.auth.has_keyring_api_key()
                else "⚠️ No API key stored"
            )
        return "Usage: /api-key <store|clear|status>"
    
    async def whoami(self, args: str = "") -> str:
        """Show current user."""
        return self.auth.describe_user_state()

    async def config_command(self, args: str = "") -> str:
        """Inspect or update local config (non-secret)."""
        if not args or args.strip().lower() == "show":
            data = {
                "environment": self.config.environment,
                "default_persona": self.config.default_persona,
                "logging_enabled": self.config.logging_enabled,
                "log_name": self.config.log_name,
                "default_transport": self.config.default_transport.value,
                "last_conversation_id": self.config.last_conversation_id,
                "aliases": self.config.conversation_aliases,
                "auth_mode": self.config.auth_mode.value,
                "config_path": str(CONFIG_FILE),
            }
            return json.dumps(data, indent=2)
        lower = args.strip().lower()
        if lower == "reset":
            confirm = input(
                "This will remove local preferences (not credentials). Continue? [y/N]: "
            ).strip().lower()
            if confirm == "y" and CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
                self.config.__dict__.update(GaiaClientConfig().__dict__)
                return "✅ Config reset. Restart client to reload defaults."
            return "⚠️ Config reset cancelled"
        if lower.startswith("set"):
            parts = args.split(maxsplit=1)
            if len(parts) == 1:
                return "Usage: /config set key=value"
            assignments = parts[1].split()
            allowed = {
                "environment",
                "default_persona",
                "logging_enabled",
                "log_name",
                "default_transport",
                "auth_mode",
            }
            messages = []
            for assignment in assignments:
                if "=" not in assignment:
                    continue
                key, value = assignment.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key not in allowed:
                    messages.append(f"⚠️ Unknown key: {key}")
                    continue
                if key == "environment":
                    if value not in GAIA_ENVIRONMENTS:
                        messages.append(f"⚠️ Invalid environment: {value}")
                        continue
                    self.config.environment = value
                    messages.append(f"🌐 Environment set to {value} (takes effect next run)")
                elif key == "default_persona":
                    self.config.default_persona = value or self.config.default_persona
                    messages.append(f"🎭 Default persona set to {self.config.default_persona}")
                elif key == "logging_enabled":
                    truthy = value.lower() in {"1", "true", "yes", "on"}
                    self.config.logging_enabled = truthy
                    messages.append(f"📝 Logging default set to {truthy}")
                elif key == "log_name":
                    self.config.log_name = value or None
                    messages.append("📝 Log file name updated")
                elif key == "default_transport":
                    try:
                        self.config.default_transport = TransportProtocol(value.lower())
                        messages.append(f"📡 Default transport set to {value.lower()}")
                    except ValueError:
                        messages.append("⚠️ Transport must be 'sse' or 'websocket'")
                        continue
                elif key == "auth_mode":
                    mode_value = value.lower()
                    if mode_value not in AuthMode._value2member_map_:
                        messages.append("⚠️ Auth mode must be one of: auto, jwt, api_key")
                        continue
                    self.config.auth_mode = AuthMode(mode_value)
                    self.auth.set_auth_mode(self.config.auth_mode)
                    messages.append(f"🔐 Auth mode set to {self.config.auth_mode.value}")
            self.config.save()
            return "\n".join(messages) if messages else "No config keys updated"
        return "Usage: /config [show|set key=value|reset]"


async def process_command(command: str, args: str, commands: ChatCommands) -> Optional[str]:
    """Process a chat command."""
    command_map = {
        'help': commands.help,
        'new': commands.new_conversation,
        'list': commands.list_conversations,
        'switch': commands.switch_conversation,
        'alias': commands.alias,
        'personas': commands.list_personas,
        'persona': commands.set_persona,
        'status': commands.status,
        'export': commands.export_conversation,
        'clear': commands.clear_screen,
        'login': commands.login,
        'register': commands.register,
        'api-key': commands.api_key,
        'logout': commands.logout,
        'whoami': commands.whoami,
        'config': commands.config_command,
    }
    
    cmd = command.lower()
    if cmd in command_map:
        return await command_map[cmd](args)
    return None


async def interactive_mode(
    client: GaiaClient,
    auth_manager: GaiaAuthManager,
    logger: ConversationLogger,
    config: GaiaClientConfig,
):
    """Run interactive chat mode."""
    commands = ChatCommands(client, auth_manager, config)
    
    print("\n🤖 GAIA Chat Client v1.0")
    print("=" * 50)
    if auth_manager._user_email:
        print(f"👤 Logged in as: {auth_manager._user_email}")
    status_text = await commands.status()
    print(status_text)
    print("=" * 50)
    print("Type /help for available commands")
    print("=" * 50)
    
    # Start logging session
    if logger.enabled:
        logger.start_session(
            client.current_conversation_id or "new",
            client.current_persona,
        )
    
    while True:
        try:
            message = input("\n👤 You: ").strip()
            
            if not message:
                continue
            
            if message.lower() in ('/quit', '/exit'):
                break
            
            # Handle commands
            if message.startswith('/'):
                command_parts = message[1:].split(' ', 1)
                command = command_parts[0]
                args = command_parts[1] if len(command_parts) > 1 else ""
                
                result = await process_command(command, args, commands)
                if result:
                    print(result)
                continue
            
            # Send message to GAIA
            print("\n🤖 Assistant: ", end="", flush=True)
            
            try:
                response = await client.send_message(message, stream=True)
                ai_response = response.get("response", "")
                
                # Log the exchange
                logger.log_exchange(message, ai_response)
                
                print("\n" + "-" * 50)
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("-" * 50)
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break
    
    # End logging session
    if logger.enabled:
        logger.end_session()


async def batch_mode(client: GaiaClient, message: str, logger: ConversationLogger):
    """Send a single message and exit."""
    try:
        # Start logging session if enabled
        if logger.enabled:
            logger.start_session(
                client.current_conversation_id or "batch",
                client.current_persona
            )
        
        response = await client.send_message(message, stream=False)
        ai_response = response.get("response", "No response")
        print(ai_response)
        
        # Log the exchange if logging is enabled
        if logger.enabled:
            logger.log_exchange(message, ai_response)
            logger.end_session()
            
    except Exception as e:
        import traceback
        print(f"Error: {e}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def setup():
    """Run setup process for the GAIA client."""
    print("🚀 Setting up GAIA CLI Client...")
    
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ is required (found {sys.version_info.major}.{sys.version_info.minor})")
        sys.exit(1)
    
    # Check and install required packages
    required_packages = ["httpx", "python-dotenv", "keyring"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Installing required packages: {', '.join(missing_packages)}")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
    else:
        print("✅ All required packages are installed")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    print("✅ Created logs directory")
    
    CONFIG_DIR.mkdir(exist_ok=True)
    config = GaiaClientConfig.load()

    print("\n🛠 Configure defaults (press Enter to keep current value)")
    env_input = input(f"Preferred environment [{config.environment}]: ").strip() or config.environment
    while env_input not in GAIA_ENVIRONMENTS:
        env_input = input("Please choose from local/dev/staging/prod: ").strip().lower()
    persona_input = input(f"Default persona [{config.default_persona}]: ").strip() or config.default_persona
    logging_choice = input(
        f"Enable conversation logging by default? [{'Y' if config.logging_enabled else 'N'}]: "
    ).strip().lower()
    log_name = input(
        f"Default log name (blank for timestamped) [{config.log_name or 'auto'}]: "
    ).strip()
    transport_choice = input(
        f"Preferred streaming transport (sse/websocket) [{config.default_transport.value}]: "
    ).strip().lower() or config.default_transport.value
    if transport_choice not in TransportProtocol._value2member_map_:
        print("⚠️ Invalid transport, defaulting to SSE")
        transport_choice = TransportProtocol.SSE.value
    auth_mode_choice = input(
        f"Preferred auth mode (auto/jwt/api_key) [{config.auth_mode.value}]: "
    ).strip().lower() or config.auth_mode.value
    if auth_mode_choice not in AuthMode._value2member_map_:
        print("⚠️ Invalid auth mode, defaulting to auto")
        auth_mode_choice = AuthMode.AUTO.value

    config.environment = env_input
    config.default_persona = persona_input
    config.logging_enabled = logging_choice in {"y", "yes", "true", "1"}
    config.log_name = log_name or None
    config.default_transport = TransportProtocol(transport_choice)
    config.auth_mode = AuthMode(auth_mode_choice)
    config.save()
    print(f"✅ Preferences saved to {CONFIG_FILE}")

    store_key = input("Store an API key securely now? [y/N]: ").strip().lower()
    if store_key == "y":
        base_url = GAIA_ENVIRONMENTS[env_input]
        auth = GaiaAuthManager(env_input, base_url, config.auth_mode)
        auth.get_api_key(force_prompt=True)

    print("\n✅ Setup complete! You can run `python gaia_client.py` to start chatting.")


async def main():
    parser = argparse.ArgumentParser(
        description="GAIA Interactive Chat Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First time setup
  python gaia_client.py --setup
  
  # Interactive mode with dev environment
  python gaia_client.py --env dev
  
  # Batch mode
  python gaia_client.py --env prod --batch "What is quantum computing?"
  
  # Set persona on startup
  python gaia_client.py --env dev --persona ava
  
  # Enable logging
  python gaia_client.py --env dev --log
        """
    )
    
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run first-time setup"
    )
    parser.add_argument(
        "--env",
        choices=["local", "dev", "staging", "prod"],
        default=None,
        help="Override configured environment"
    )
    parser.add_argument(
        "--batch",
        metavar="MESSAGE",
        help="Run in batch mode with specified message"
    )
    parser.add_argument(
        "--persona",
        metavar="PERSONA_ID",
        help="Set persona by ID on startup"
    )
    parser.add_argument(
        "--conversation",
        metavar="CONV_ID",
        help="Use specific conversation ID"
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable conversation logging to logs/ directory"
    )
    parser.add_argument(
        "--log-name",
        metavar="LOG_NAME",
        help="Specific log file name to append to (enables logging)"
    )
    parser.add_argument(
        "--email",
        metavar="EMAIL",
        help="Login with email/password instead of API key"
    )
    parser.add_argument(
        "--password",
        metavar="PASSWORD",
        help="Password for email login"
    )
    parser.add_argument(
        "--auth-mode",
        choices=[mode.value for mode in AuthMode],
        help="Override authentication strategy (auto/jwt/api_key)"
    )
    parser.add_argument(
        "--store-api-key",
        action="store_true",
        help="Prompt once and store an API key in the OS keyring"
    )
    parser.add_argument(
        "--config-reset",
        action="store_true",
        help="Delete saved client preferences and exit"
    )
    
    args = parser.parse_args()
    
    # Run setup if requested
    if args.setup:
        setup()
        return
    
    if args.config_reset:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            print(f"🗑️ Deleted {CONFIG_FILE}")
        else:
            print("No config file to delete")
        return
    
    config = GaiaClientConfig.load()
    env_name = args.env or config.environment
    base_url = GAIA_ENVIRONMENTS[env_name]
    if config.environment != env_name:
        config.environment = env_name
        config.save()
    runtime_auth_mode = AuthMode(args.auth_mode) if args.auth_mode else config.auth_mode
    
    # Setup client
    auth_manager = GaiaAuthManager(env_name, base_url, runtime_auth_mode)
    if args.store_api_key:
        auth_manager.get_api_key(force_prompt=True)
    client = GaiaClient(base_url, auth_manager, config)
    
    # Handle email/password login if provided
    if args.email:
        if not args.password:
            import getpass
            password = getpass.getpass("Password: ")
        else:
            password = args.password
        
        success = await auth_manager.login(args.email, password)
        if not success:
            print("❌ Login failed. Exiting.")
            sys.exit(1)
    
    # Apply CLI persona override
    startup_persona = args.persona or config.default_persona
    if startup_persona and startup_persona != client.current_persona:
        try:
            await client.set_persona(startup_persona)
            print(f"✅ Set persona to: {startup_persona}")
        except Exception as e:
            print(f"⚠️ Could not set persona: {e}")
    
    # Apply conversation override or remembered session
    if args.conversation:
        client.set_conversation(args.conversation)
    elif config.last_conversation_id and auth_manager.has_credentials():
        client.set_conversation(config.last_conversation_id)
    else:
        client.set_conversation(None, persist=False)
    
    # Initialize logger preferences
    logging_enabled = args.log or config.logging_enabled or bool(args.log_name or config.log_name)
    log_name = args.log_name or config.log_name
    logger = ConversationLogger(enabled=logging_enabled, log_name=log_name)
    
    # Run appropriate mode
    if args.batch:
        # Handle piped input
        if args.batch == "-":
            # Read from stdin
            message = sys.stdin.read().strip()
            if not message:
                print("Error: No input provided via stdin", file=sys.stderr)
                sys.exit(1)
        else:
            message = args.batch
        
        await batch_mode(client, message, logger)
    else:
        await interactive_mode(client, auth_manager, logger, config)


if __name__ == "__main__":
    asyncio.run(main())
