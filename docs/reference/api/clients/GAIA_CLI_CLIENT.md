# GAIA CLI Client

An interactive command-line interface for the GAIA platform, supporting v0.3 API endpoints with conversation management, persona switching, and rich text output.

## Features

- 🔐 **Secure Authentication**: API key storage in OS keyring
- 💬 **Interactive Chat**: Real-time streaming responses
- 📚 **Conversation Management**: Create, list, and switch conversations
- 🎭 **Persona Support**: Switch between different AI personas
- 📝 **Conversation Logging**: Export conversations to JSON
- 🌐 **Multi-Environment**: Connect to local, dev, staging, or production
- ⚡ **Batch Mode**: One-off queries for scripting

## Installation

### Prerequisites

- Python 3.8+ (3.12+ recommended)
- Homebrew Python recommended on macOS: `brew install python`

### Setup Steps

```bash
# 1. Navigate to GAIA repository
cd /path/to/gaia

# 2. Create virtual environment
python3 -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# 4. Install CLI dependencies
python3 -m pip install httpx python-dotenv keyring

# 5. Configure VS Code (recommended for auto-activation)
cp .vscode/settings.json.example .vscode/settings.json
# Then reload VS Code - venv will auto-activate in integrated terminal

# 6. Configure API key (choose one method):

# Method A: Add to .env file (recommended for local dev)
echo "GAIA_API_KEY=your-api-key-here" >> .env

# Method B: Set environment variable for this session
export GAIA_API_KEY="your-api-key-here"

# Method C: Let the client prompt you (stores in OS keyring)
# Just run the client and it will ask for your key
```

### Verification

```bash
# If using VS Code with auto-activation (recommended):
python3 scripts/gaia_client.py --env local --batch "Hello"

# If running outside VS Code:
.venv/bin/python3 scripts/gaia_client.py --env local --batch "Hello"

# Expected output: Response from Mu persona
```

### What Gets Installed

The CLI requires these Python packages:
- **httpx** (0.28.1+): Async HTTP client for API calls
- **python-dotenv** (1.1.1+): Load environment variables from .env files
- **keyring** (25.6.0+): Secure OS-level credential storage

### Directory Structure

The client creates these directories automatically:
- `./logs/`: For conversation logs
- `~/.gaia/`: For future config files (currently empty)

### Why Virtual Environment?

The CLI client is a **standalone Python script** (not Dockerized like the main GAIA services). Using a virtual environment:
- ✅ Isolates dependencies from your global Python installation
- ✅ Prevents conflicts with other Python projects
- ✅ Follows Homebrew + pip best practices on macOS
- ✅ Makes dependency management reproducible

**Note**: The main GAIA services (Gateway, Chat, Auth, etc.) run in Docker and don't need a venv

## Usage

**IMPORTANT**: The CLI client runs as a standalone Python script (not in Docker). You must use the virtual environment.

### Command Format Options

```bash
# Option 1: VS Code with auto-activation (RECOMMENDED)
# - Configure .vscode/settings.json (see Installation)
# - VS Code terminal auto-activates venv
python3 scripts/gaia_client.py [options]

# Option 2: Manual venv activation (for any terminal)
source .venv/bin/activate
python3 scripts/gaia_client.py [options]
deactivate  # When done

# Option 3: Direct venv path (for scripts/automation)
.venv/bin/python3 scripts/gaia_client.py [options]

# Option 4: Inline API key (one-off commands)
GAIA_API_KEY="your-key" .venv/bin/python3 scripts/gaia_client.py [options]
```

### Interactive Mode

**Note**: Examples below assume VS Code auto-activation or manual `source .venv/bin/activate`. If not activated, prefix with `.venv/bin/python3`.

```bash
# Connect to dev environment (default)
python3 scripts/gaia_client.py

# Connect to production
python3 scripts/gaia_client.py --env prod

# Connect to local (Docker services)
python3 scripts/gaia_client.py --env local

# Start with specific persona
python3 scripts/gaia_client.py --persona ava

# Enable conversation logging
python3 scripts/gaia_client.py --log

# Continue existing conversation
python3 scripts/gaia_client.py --conversation conv-123abc
```

### Batch Mode

```bash
# Single query to local environment
python3 scripts/gaia_client.py --env local --batch "What is quantum computing?"

# With specific environment
python3 scripts/gaia_client.py --env prod --batch "Explain relativity"

# With API key inline (useful for scripts)
GAIA_API_KEY="your-key" python3 scripts/gaia_client.py --env dev --batch "Hello"

# Pipe input
echo "What is the meaning of life?" | python3 scripts/gaia_client.py --batch -

# Batch mode with logging
python3 scripts/gaia_client.py --env local --log --batch "Explain AI"

# Script/automation example (explicit venv path)
.venv/bin/python3 scripts/gaia_client.py --env local --batch "Test query"
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/new [title]` | Start a new conversation |
| `/list` | List all conversations |
| `/switch <id>` | Switch to a conversation |
| `/personas` | List available personas |
| `/persona <id>` | Switch to a persona |
| `/status` | Show current status |
| `/export [file]` | Export conversation |
| `/clear` | Clear screen |
| `/quit` | Exit the client |

## Authentication

The client uses a **secure, layered approach** for API key management:

### Authentication Priority Order

1. **Environment Variables** (.env file or shell)
2. **OS Keyring** (secure storage)
3. **User Prompt** (first-time setup)

### How It Works

```bash
# Method 1: Environment variable (highest priority)
export GAIA_API_KEY="your-api-key-here"
python3 scripts/gaia_client.py

# Method 2: .env file in project root
echo "GAIA_API_KEY=your-api-key-here" > .env
python3 scripts/gaia_client.py

# Method 3: First-time prompt (stored in keyring)
python3 scripts/gaia_client.py
# Prompts: "Enter your GAIA API key: "
# Saves securely to OS keyring for future use
```

### Keyring Storage Details

API keys are stored securely in your operating system's credential manager:

- **macOS**: Keychain Access (searchable as "gaia-client-dev", "gaia-client-prod", etc.)
- **Windows**: Windows Credential Manager
- **Linux**: GNOME Keyring, KWallet, or Secret Service

**Benefits:**
- ✅ Encrypted by OS
- ✅ Survives terminal sessions
- ✅ Separate keys per environment
- ✅ No plaintext storage

### Managing Stored Keys

```bash
# View stored keys (macOS)
security find-generic-password -s "gaia-client-dev" -a "api_key"

# Remove stored key if needed (assumes venv activated)
python3 -c "import keyring; keyring.delete_password('gaia-client-dev', 'api_key')"

# Or with explicit venv path:
.venv/bin/python3 -c "import keyring; keyring.delete_password('gaia-client-dev', 'api_key')"

# The client will prompt for a new key on next run
```

## Configuration

### Environment Variables

```bash
# API Authentication
export GAIA_API_KEY="your-api-key-here"

# Custom endpoints (optional)
export GAIA_DEV_URL="https://custom-dev.example.com"
export GAIA_PROD_URL="https://custom-prod.example.com"
```

### Environments

- `local`: http://localhost:8666
- `dev`: https://gaia-gateway-dev.fly.dev (default)
- `staging`: https://gaia-gateway-staging.fly.dev
- `prod`: https://gaia-gateway-prod.fly.dev

## Examples

### Basic Conversation

```bash
$ python3 scripts/gaia_client.py

🤖 GAIA Chat Client v1.0
==================================================
🌐 Environment: https://gaia-gateway-dev.fly.dev
💬 Conversation: None
🎭 Persona: mu
✅ Gateway: Healthy
==================================================
Type /help for available commands
==================================================

👤 You: Hello! Can you explain quantum entanglement?

🤖 Assistant: Quantum entanglement is one of the most fascinating...
```

**Note**: This assumes venv is activated (VS Code auto-activation or manual `source .venv/bin/activate`)

### Persona Switching

```bash
👤 You: /personas

🎭 Available Personas:
✓ [mu] μ (Mu) - Embodiment of unity consciousness
  [ava] Ava - Quantum mechanics and multiverse researcher
  [nova] Nova - Astrophysicist and cosmic explorer

👤 You: /persona ava
✅ Switched to persona: ava

👤 You: Now explain it from a physics perspective
🤖 Assistant: From a quantum physics standpoint, entanglement...
```

### Conversation Management

```bash
👤 You: /new Quantum Physics Discussion
✅ Created new conversation: conv-xyz123

👤 You: /list
📚 Conversations:
- [conv-xyz1] 2025-08-21 - Quantum Physics Discussion
- [conv-abc4] 2025-08-20 - AI Ethics Debate
- [conv-def7] 2025-08-19 - Python Programming Help

👤 You: /switch conv-abc4
✅ Switched to conversation: conv-abc4
```

## Conversation Logging

The client can automatically log conversations to JSON files for analysis, research, or record-keeping.

### Enabling Logging

```bash
# Auto-generated log file (timestamped)
python3 scripts/gaia_client.py --log
# Creates: logs/gaia_mu_20250821_143022.json

# Named log file (append to existing)
python3 scripts/gaia_client.py --log-name quantum-research
# Creates/appends: logs/quantum-research.json

# Batch mode with logging
python3 scripts/gaia_client.py --log --batch "What is quantum computing?"
```

### Log File Location

- **Directory**: `./logs/` (created during setup)
- **Safety**: Won't overwrite if directory already exists
- **Format**: JSON with structured conversation data

### Log File Structure

```json
{
  "session_id": "20250821_143022",
  "conversation_id": "conv-xyz123", 
  "persona_name": "μ (Mu)",
  "started_at": "2025-08-21T14:30:22.123456",
  "log_file": "/path/to/logs/gaia_mu_20250821_143022.json",
  "exchanges": [
    {
      "timestamp": "2025-08-21T14:30:45.789012",
      "user_message": "What is quantum entanglement?",
      "ai_response": "Quantum entanglement is a fundamental phenomenon..."
    },
    {
      "timestamp": "2025-08-21T14:32:15.345678", 
      "user_message": "Can you give me an example?",
      "ai_response": "Certainly! Imagine two particles..."
    }
  ],
  "total_exchanges": 2
}
```

### Log Management

```bash
# View recent logs
ls -la logs/

# Search through logs
grep -r "quantum" logs/

# Export specific conversation
jq '.exchanges[] | select(.user_message | contains("quantum"))' logs/*.json

# Clean old logs (older than 30 days)
find logs/ -name "*.json" -mtime +30 -delete
```

## Troubleshooting

### Connection Issues

```bash
# Check gateway health
curl https://gaia-gateway-dev.fly.dev/health

# Verify API key with local environment (assumes venv activated)
python3 scripts/gaia_client.py --env local --batch "test"

# Verify API key with dev environment
python3 scripts/gaia_client.py --env dev --batch "test"

# If venv not activated, use explicit path:
.venv/bin/python3 scripts/gaia_client.py --env local --batch "test"
```

### Virtual Environment Issues

```bash
# Check if venv is activated (should show .venv path)
which python3

# If not showing .venv, activate it:
source .venv/bin/activate

# In VS Code, check that interpreter is set:
# Cmd+Shift+P → "Python: Select Interpreter" → Choose .venv/bin/python3

# Verify packages are installed in venv:
python3 -m pip list | grep -E "httpx|keyring|dotenv"
```

### Authentication Errors

1. Check API key is correct
2. Verify environment matches your key
3. Try clearing keyring: `keyring del gaia-client-dev api_key`

### Streaming Issues

If streaming doesn't work, the client will automatically fall back to non-streaming mode.

## Development

### Adding New Commands

1. Add command to `ChatCommands` class
2. Register in `command_map` dictionary
3. Update help text

### Testing

```bash
# Test basic functionality (assumes venv activated)
python3 scripts/gaia_client.py --env local --batch "test"

# Test with different environments
python3 scripts/gaia_client.py --env dev --batch "test"

# Test with mock server (if pytest tests exist)
python3 -m pytest tests/test_gaia_client.py

# Or with explicit venv path (for CI/scripts):
.venv/bin/python3 scripts/gaia_client.py --env local --batch "test"
.venv/bin/python3 -m pytest tests/test_gaia_client.py
```

## Related Documentation

- [CLIENT_API_REFERENCE.md](CLIENT_API_REFERENCE.md) - Full v0.3 API documentation
- [CLIENT_SIDE_SERVER_PLAN.md](CLIENT_SIDE_SERVER_PLAN.md) - Local proxy server plan
- [GAIA Platform README](../README.md) - Main project documentation