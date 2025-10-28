# GAIA CLI Skill - General Chat Client

**Purpose**: This skill teaches you how to use the GAIA CLI client for interactive chat sessions, persona management, and conversation logging.

**Activation**: Use this skill when:
- Working with chat sessions and conversations
- Managing personas and switching contexts
- Logging and exporting conversations
- Testing chat API functionality

**For game-specific commands**: See [game-cli.md](game-cli.md) skill for admin @commands and player gameplay.

**Prerequisites**: Assumes virtual environment is set up (`.venv/` with httpx, keyring, python-dotenv installed) and API key is configured. See `docs/api/clients/GAIA_CLI_CLIENT.md` for initial setup.

---

## Basic Usage

### Interactive Mode

```bash
# Connect to environment (assumes venv activated or VS Code auto-activation)
python3 scripts/gaia_client.py                    # Dev (default)
python3 scripts/gaia_client.py --env local        # Local Docker
python3 scripts/gaia_client.py --env prod         # Production

# Start with specific persona
python3 scripts/gaia_client.py --persona ava

# Enable conversation logging
python3 scripts/gaia_client.py --log
python3 scripts/gaia_client.py --log-name research-session

# Continue existing conversation
python3 scripts/gaia_client.py --conversation conv-123abc
```

### Batch Mode (One-Off Queries)

```bash
# Single query
python3 scripts/gaia_client.py --env local --batch "What is quantum computing?"

# With logging
python3 scripts/gaia_client.py --env local --log --batch "Test query"

# Pipe input
echo "Explain AI" | python3 scripts/gaia_client.py --batch -

# For scripts/automation (explicit venv path)
.venv/bin/python3 scripts/gaia_client.py --env local --batch "Test"
```

---

## Interactive Commands

While in interactive mode, use `/` prefix commands:

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all commands | `/help` |
| `/new [title]` | Start new conversation | `/new Quantum Research` |
| `/list` | List conversations | `/list` |
| `/switch <id>` | Switch conversation | `/switch conv-abc123` |
| `/personas` | List available personas | `/personas` |
| `/persona <id>` | Switch persona | `/persona ava` |
| `/status` | Show current status | `/status` |
| `/export [file]` | Export conversation | `/export quantum-chat.json` |
| `/clear` | Clear screen | `/clear` |
| `/quit` | Exit client | `/quit` |

---

## Common Workflows

### Workflow 1: Research Session with Logging

```bash
# Start session with logging
python3 scripts/gaia_client.py --log-name quantum-research

You: /persona ava
You: Explain quantum entanglement
# ... conversation continues ...
You: /export
# Saves to logs/quantum-research.json
```

### Workflow 2: Multi-Persona Exploration

```bash
python3 scripts/gaia_client.py

You: /personas
# View available personas

You: /persona mu
You: What is consciousness from a unity perspective?

You: /persona ava
You: Same question from a physics perspective

You: /persona nova
You: And from an astrophysics view
```

### Workflow 3: Testing API Endpoints

```bash
# Quick test of local environment
python3 scripts/gaia_client.py --env local --batch "test"

# Test dev environment
python3 scripts/gaia_client.py --env dev --batch "test"

# Test with specific persona
python3 scripts/gaia_client.py --env local --persona nova --batch "test"
```

### Workflow 4: Conversation Management

```bash
python3 scripts/gaia_client.py

You: /new Physics Discussion
# Start new conversation

You: Explain relativity
# ... conversation ...

You: /list
# See all conversations

You: /switch conv-xyz789
# Switch to previous conversation

You: /export physics-discussion.json
# Export to file
```

---

## Environments

| Environment | URL | Use Case |
|-------------|-----|----------|
| `local` | http://localhost:8666 | Local Docker services |
| `dev` | https://gaia-gateway-dev.fly.dev | Development (default) |
| `staging` | https://gaia-gateway-staging.fly.dev | Staging tests |
| `prod` | https://gaia-gateway-prod.fly.dev | Production |

---

## Conversation Logging

### Enable Logging

```bash
# Auto-generated filename with timestamp
python3 scripts/gaia_client.py --log
# → logs/gaia_mu_20250821_143022.json

# Named file (append mode)
python3 scripts/gaia_client.py --log-name quantum-research
# → logs/quantum-research.json
```

### Log File Format

```json
{
  "session_id": "20250821_143022",
  "conversation_id": "conv-xyz123",
  "persona_name": "μ (Mu)",
  "started_at": "2025-08-21T14:30:22.123456",
  "exchanges": [
    {
      "timestamp": "2025-08-21T14:30:45.789012",
      "user_message": "What is quantum entanglement?",
      "ai_response": "Quantum entanglement is..."
    }
  ],
  "total_exchanges": 2
}
```

### Analyze Logs

```bash
# View recent logs
ls -la logs/

# Search logs
grep -r "quantum" logs/

# Extract specific exchanges
jq '.exchanges[] | select(.user_message | contains("quantum"))' logs/*.json

# Clean old logs (30+ days)
find logs/ -name "*.json" -mtime +30 -delete
```

---

## Troubleshooting

### Issue: "Connection refused" or Gateway unhealthy

**Check gateway health:**
```bash
curl https://gaia-gateway-dev.fly.dev/health

# For local:
curl http://localhost:8666/health
```

**Verify services running (local):**
```bash
docker compose ps
```

### Issue: "Authentication failed"

**Check API key configuration:**
```bash
# Verify .env file
cat .env | grep GAIA_API_KEY

# Check environment variable
echo $GAIA_API_KEY

# Clear keyring and re-authenticate
python3 -c "import keyring; keyring.delete_password('gaia-client-dev', 'api_key')"
python3 scripts/gaia_client.py --env dev --batch "test"
```

**Verify environment matches key:**
- Dev API key won't work on prod
- Check which environment you're targeting: `--env dev` vs `--env prod`

### Issue: "ModuleNotFoundError: No module named 'httpx'"

**Virtual environment not activated:**
```bash
# Check if venv active (should show .venv path)
which python3

# Activate if needed
source .venv/bin/activate

# Or use explicit path
.venv/bin/python3 scripts/gaia_client.py --env local --batch "test"
```

### Issue: Streaming not working (long wait, then full response)

**Expected behavior**: Response streams token-by-token

**Actual behavior**: Long wait, then complete response appears

**Solution**: Client automatically falls back to non-streaming mode. This is normal and requires no action.

### Issue: "Conversation not found"

**Check conversation exists:**
```bash
python3 scripts/gaia_client.py

You: /list
# Verify conversation ID

You: /switch <correct-id>
```

---

## Authentication Modes

The client checks authentication in this order:

1. **Environment variable**: `GAIA_API_KEY` in shell or `.env` file
2. **OS Keyring**: Stored from previous sessions
3. **User prompt**: First-time setup

**Managing stored keys:**
```bash
# View keyring entry (macOS)
security find-generic-password -s "gaia-client-dev" -a "api_key"

# Remove stored key
python3 -c "import keyring; keyring.delete_password('gaia-client-dev', 'api_key')"

# Client will prompt for new key on next run
```

---

## Quick Reference

**Start interactive session:**
```bash
python3 scripts/gaia_client.py [--env local|dev|prod] [--persona <id>] [--log]
```

**Batch mode:**
```bash
python3 scripts/gaia_client.py --batch "query" [--env <env>] [--log]
```

**In-session commands:**
- `/new [title]` - New conversation
- `/personas` - List personas
- `/persona <id>` - Switch persona
- `/list` - List conversations
- `/switch <id>` - Switch conversation
- `/export [file]` - Export conversation
- `/status` - Show status
- `/quit` - Exit

**Troubleshooting:**
- Check health: `curl <gateway-url>/health`
- Check venv: `which python3`
- Clear auth: `python3 -c "import keyring; keyring.delete_password('gaia-client-dev', 'api_key')"`
- Verify services: `docker compose ps` (local only)

---

## Related

- **Game commands**: [game-cli.md](game-cli.md) - Admin @commands, player gameplay
- **Setup docs**: `docs/api/clients/GAIA_CLI_CLIENT.md` - Initial installation
- **API reference**: `docs/api/clients/CLIENT_API_REFERENCE.md` - v0.3 endpoints
