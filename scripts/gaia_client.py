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
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
from dotenv import load_dotenv
import keyring

# Load environment variables from .env
load_dotenv()

# GAIA API Configuration
GAIA_ENVIRONMENTS = {
    "local": "http://localhost:8666",
    "dev": "https://gaia-gateway-dev.fly.dev",
    "staging": "https://gaia-gateway-staging.fly.dev",
    "prod": "https://gaia-gateway-prod.fly.dev"
}

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
    
    def __init__(self, environment: str = "dev", base_url: str = None):
        self.environment = environment
        self.service_name = f"gaia-client-{environment}"
        self.base_url = base_url
        self._token = None
        self._refresh_token = None
        self._api_key = None
        self._user_email = None
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment or keyring."""
        # First try environment variable
        api_key = os.getenv('GAIA_API_KEY') or os.getenv('API_KEY')
        if api_key:
            return api_key
        
        # Try keyring
        try:
            api_key = keyring.get_password(self.service_name, "api_key")
            if api_key:
                return api_key
        except Exception:
            pass
        
        # Prompt user
        api_key = input("Enter your GAIA API key: ").strip()
        if api_key:
            # Save to keyring for future use
            try:
                keyring.set_password(self.service_name, "api_key", api_key)
                print("✅ API key saved securely")
            except Exception:
                print("⚠️ Could not save API key to keyring")
        
        return api_key
    
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
                self._token = session.get("access_token")
                self._refresh_token = session.get("refresh_token")
                self._user_email = data.get("user", {}).get("email", email)
                
                print(f"✅ Logged in as: {self._user_email}")
                return True
                
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
    
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        elif self._api_key:
            return {"X-API-Key": self._api_key}
        else:
            self._api_key = self.get_api_key()
            if not self._api_key:
                raise ValueError("No authentication credentials available")
            return {"X-API-Key": self._api_key}


class GaiaClient:
    """GAIA API client with v0.3 endpoint support."""
    
    def __init__(self, base_url: str, auth_manager: GaiaAuthManager):
        self.base_url = base_url
        self.auth = auth_manager
        self.current_conversation_id = None
        self.current_persona = "mu"  # Default persona
    
    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            return response.json()
    
    async def send_message(self, message: str, stream: bool = False) -> Dict[str, Any]:
        """Send a chat message using v0.3 API."""
        headers = self.auth.get_headers()
        headers["Content-Type"] = "application/json"
        
        data = {
            "message": message,
            "conversation_id": self.current_conversation_id,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if stream:
                # Handle streaming response
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/v0.3/chat",
                    headers=headers,
                    json=data
                ) as response:
                    response.raise_for_status()
                    full_response = ""
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                event = json.loads(data_str)
                                if event.get("type") == "content":
                                    content = event.get("content", "")
                                    print(content, end="", flush=True)
                                    full_response += content
                            except json.JSONDecodeError:
                                pass
                    
                    print()  # New line after streaming
                    return {
                        "response": full_response,
                        "conversation_id": self.current_conversation_id,
                        "message": message
                    }
            else:
                # Regular non-streaming request
                response = await client.post(
                    f"{self.base_url}/api/v0.3/chat",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # Update conversation ID if returned
                if "conversation_id" in result:
                    self.current_conversation_id = result["conversation_id"]
                
                return result
    
    async def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations."""
        headers = self.auth.get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v0.3/conversations",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("conversations", [])
    
    async def create_conversation(self, title: str = "New Conversation") -> Dict[str, Any]:
        """Create a new conversation."""
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
            self.current_conversation_id = result.get("id")
            return result
    
    async def get_personas(self) -> List[Dict[str, Any]]:
        """Get available personas (v1 endpoint)."""
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
            return response.json()


class ChatCommands:
    """Interactive chat commands."""
    
    def __init__(self, client: GaiaClient, auth_manager: GaiaAuthManager):
        self.client = client
        self.auth = auth_manager
    
    async def help(self, args: str = "") -> str:
        """Show available commands."""
        commands = [
            "=== Chat Commands ===",
            "/help - Show this help message",
            "/new [title] - Start a new conversation",
            "/list - List all conversations",
            "/switch <id> - Switch to a conversation by ID",
            "/personas - List available personas",
            "/persona <id> - Switch to a persona",
            "/status - Show current status",
            "/export [file] - Export current conversation",
            "/clear - Clear screen",
            "",
            "=== Auth Commands ===",
            "/login <email> <password> - Login with email/password",
            "/register <email> <password> - Register new account",
            "/logout - Logout current session",
            "/whoami - Show current user",
            "",
            "/quit - Exit the chat"
        ]
        return "\n".join(commands)
    
    async def new_conversation(self, args: str = "") -> str:
        """Create a new conversation."""
        title = args.strip() or "New Conversation"
        try:
            result = await self.client.create_conversation(title)
            return f"✅ Created new conversation: {result['id']}"
        except Exception as e:
            return f"❌ Error creating conversation: {e}"
    
    async def list_conversations(self, args: str = "") -> str:
        """List all conversations."""
        try:
            conversations = await self.client.list_conversations()
            if not conversations:
                return "No conversations found."
            
            output = "📚 Conversations:\n"
            for conv in conversations[:10]:  # Show last 10
                created = conv.get('created_at', 'Unknown')[:10]
                title = conv.get('title', 'Untitled')[:50]
                output += f"- [{conv['id'][:8]}] {created} - {title}\n"
            
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
        self.client.current_conversation_id = conv_id
        return f"✅ Switched to conversation: {conv_id}"
    
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
        status_lines = [
            f"🌐 Environment: {self.client.base_url}",
            f"💬 Conversation: {self.client.current_conversation_id or 'None'}",
            f"🎭 Persona: {self.client.current_persona}",
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
        self.auth._token = None
        self.auth._refresh_token = None
        self.auth._user_email = None
        return "✅ Logged out"
    
    async def whoami(self, args: str = "") -> str:
        """Show current user."""
        if self.auth._user_email:
            return f"👤 Logged in as: {self.auth._user_email} (JWT)"
        elif self.auth._api_key:
            return f"🔑 Using API key authentication"
        else:
            return "❌ Not authenticated"


async def process_command(command: str, args: str, commands: ChatCommands) -> Optional[str]:
    """Process a chat command."""
    command_map = {
        'help': commands.help,
        'new': commands.new_conversation,
        'list': commands.list_conversations,
        'switch': commands.switch_conversation,
        'personas': commands.list_personas,
        'persona': commands.set_persona,
        'status': commands.status,
        'export': commands.export_conversation,
        'clear': commands.clear_screen,
        'login': commands.login,
        'register': commands.register,
        'logout': commands.logout,
        'whoami': commands.whoami,
    }
    
    cmd = command.lower()
    if cmd in command_map:
        return await command_map[cmd](args)
    return None


async def interactive_mode(client: GaiaClient, auth_manager: GaiaAuthManager, logger: ConversationLogger):
    """Run interactive chat mode."""
    commands = ChatCommands(client, auth_manager)
    
    print("\n🤖 GAIA Chat Client v1.0")
    print("=" * 50)
    print(await commands.status())
    print("=" * 50)
    print("Type /help for available commands")
    print("=" * 50)
    
    # Start logging session
    logger.start_session(
        client.current_conversation_id or "new",
        client.current_persona
    )
    
    while True:
        try:
            message = input("\n👤 You: ").strip()
            
            if not message:
                continue
            
            if message.lower() == '/quit':
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
        print(f"Error: {e}", file=sys.stderr)
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
    
    # Create config directory
    config_dir = Path.home() / ".gaia"
    config_dir.mkdir(exist_ok=True)
    print(f"✅ Created config directory: {config_dir}")
    
    print("\n✅ Setup complete!")
    print("\n📖 Usage examples:")
    print("  # Interactive mode (default to dev environment)")
    print(f"  python {__file__}")
    print("\n  # Connect to production")
    print(f"  python {__file__} --env prod")
    print("\n  # Batch mode")
    print(f'  python {__file__} --batch "What is the meaning of life?"')
    print("\n  # With logging")
    print(f"  python {__file__} --log")
    print("\n💡 First time users will be prompted for their API key.")
    print("   The key will be stored securely in your OS keyring.")


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
        default="dev",
        help="GAIA environment to connect to"
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
    
    args = parser.parse_args()
    
    # Run setup if requested
    if args.setup:
        setup()
        return
    
    # Setup client
    base_url = GAIA_ENVIRONMENTS[args.env]
    auth_manager = GaiaAuthManager(args.env, base_url)
    client = GaiaClient(base_url, auth_manager)
    
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
    
    # Set conversation if specified
    if args.conversation:
        client.current_conversation_id = args.conversation
    
    # Set persona if specified
    if args.persona:
        try:
            await client.set_persona(args.persona)
            print(f"✅ Set persona to: {args.persona}")
        except Exception as e:
            print(f"⚠️ Could not set persona: {e}")
    
    # Initialize logger
    logger = ConversationLogger(enabled=args.log, log_name=args.log_name)
    
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
        await interactive_mode(client, auth_manager, logger)


if __name__ == "__main__":
    asyncio.run(main())