# Game POC Practical Testing Guide

## Quick Start: Test the Revolutionary Game System

This guide provides **working command-line examples** to immediately test the breakthrough "Executable Documentation" game system where markdown files become running game code.

## Prerequisites

- ✅ GAIA services running (`docker compose up`)
- ✅ KB content pulled with west-of-house game files
- ✅ API key configured (`gaia-local-key` for local testing)

## 🎮 Complete Test Workflow

### Step 1: Start New Game (Let Server Create Conversation)

```bash
python3 scripts/gaia_client.py --env local --batch "Start the west-of-house game. I'm standing west of a white house with a mailbox. Show me the starting location description and embed the game state as a JSON block formatted like: \`\`\`json:game_state {...} \`\`\`"
```

**Expected Output:**
```
You are standing west of a white house with a boarded front door. There is a small mailbox here.

```json:game_state
{
  "location": "west_of_house",
  "items": ["mailbox"],
  "directions": ["north", "south", "east"]
}
```
```

**Key Success Indicators:**
- ✅ Narrative description of the location
- ✅ JSON block with `json:game_state` tag
- ✅ State shows current location and available items

### Step 2: Extract Conversation ID

```bash
docker compose logs chat-service | grep "Created conversation" | tail -1
```

**Expected Output:**
```
chat-service-1 | Created conversation 4d246541-da33-4fe1-bd0b-bcb84053f3f0 for user a7f4370e-0af5-40eb-bb18-fcc10538b041
```

**Extract the UUID** (36 characters with hyphens) for the next step.

### Step 3: Test State Persistence with Game Action

```bash
# Replace YOUR-CONVERSATION-ID with the UUID from step 2
python3 scripts/gaia_client.py --env local --conversation YOUR-CONVERSATION-ID --batch "I want to open the mailbox. What do I find inside? Update the game state to reflect my new inventory and actions."
```

**Expected Output:**
```
You approach the small mailbox and open it up. Inside, you find a leaflet.

```json:game_state
{
  "location": "west_of_house",
  "items": ["mailbox", "leaflet"],
  "directions": ["north", "south", "east"],
  "inventory": ["leaflet"]
}
```
```

**Key Success Indicators:**
- ✅ Game remembers previous state
- ✅ Action executed based on Zork game rules
- ✅ Inventory updated with new item (leaflet)
- ✅ State persistence across conversation turns

### Step 4: Continue Adventure

```bash
python3 scripts/gaia_client.py --env local --conversation YOUR-CONVERSATION-ID --batch "I examine the leaflet. What does it say? Then I want to go north."
```

**Expected Behavior:**
- ✅ Leaflet contents revealed (based on Zork lore)
- ✅ Movement executed to new location
- ✅ Updated JSON state with new location

## 🚀 One-Command Test Script

Create this automated test:

```bash
cat > test_game_revolution.sh << 'EOF'
#!/bin/bash
echo "🎮 Testing Revolutionary Executable Documentation Game System..."

# Start game and capture output
echo "Starting west-of-house game..."
GAME_OUTPUT=$(python3 scripts/gaia_client.py --env local --batch "Start west-of-house game. Show location and embed game state JSON.")
echo "$GAME_OUTPUT"

# Extract conversation ID from logs
CONV_ID=$(docker compose logs chat-service | grep "Created conversation" | tail -1 | grep -o '[a-f0-9-]\{36\}')
echo -e "\n📱 Conversation ID: $CONV_ID"

# Test state persistence
echo -e "\n🔓 Opening mailbox..."
MAILBOX_OUTPUT=$(python3 scripts/gaia_client.py --env local --conversation $CONV_ID --batch "Open mailbox. Show what I find and update game state.")
echo "$MAILBOX_OUTPUT"

# Validate JSON blocks present
if echo "$GAME_OUTPUT" | grep -q "json:game_state"; then
    echo -e "\n✅ Initial state JSON block: FOUND"
else
    echo -e "\n❌ Initial state JSON block: MISSING"
fi

if echo "$MAILBOX_OUTPUT" | grep -q "json:game_state"; then
    echo -e "✅ Updated state JSON block: FOUND"
else
    echo -e "❌ Updated state JSON block: MISSING"
fi

echo -e "\n🎉 Revolutionary POC Test Complete!"
echo "📝 Markdown files have executed as game code through AI interpretation!"
EOF

chmod +x test_game_revolution.sh
./test_game_revolution.sh
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. 404 Not Found Error
**Problem:** `Client error '404 Not Found' for url 'http://localhost:8666/api/v0.3/chat'`

**Causes & Solutions:**
- **Services not running**: Run `docker compose up` and verify with `curl http://localhost:8666/health`
- **Wrong conversation ID format**: Use UUID format only (36 chars with hyphens), not custom strings like "game-session-1"

#### 2. Invalid Conversation ID Format
**Problem:** `Invalid conversation ID format: game-session-1`

**Solution:** Let the server create the conversation ID on first request, then extract it from logs:
```bash
# ❌ Don't use custom IDs
python3 scripts/gaia_client.py --conversation "my-game" ...

# ✅ Use server-generated UUIDs
python3 scripts/gaia_client.py --conversation 4d246541-da33-4fe1-bd0b-bcb84053f3f0 ...
```

#### 3. Missing JSON State Blocks
**Problem:** Response lacks `json:game_state` blocks

**Solutions:**
- **Request explicitly**: Include "embed the game state as a JSON block" in your prompt
- **Check game content**: Verify KB has west-of-house game files with `docker exec gaia-kb-service-1 ls /kb/experiences/`
- **Use specific format**: Request `\`\`\`json:game_state {...} \`\`\`` format explicitly

#### 4. Authentication Issues
**Problem:** `Could not validate credentials`

**Solution:** CLI client should automatically handle local auth. If issues persist:
```bash
# Check API key configuration
grep API_KEY .env

# Verify service health
curl -H "X-API-Key: gaia-local-key" http://localhost:8666/health
```

## 🌟 What Makes This Revolutionary

### Traditional Game Development
```
Write Requirements → Code Game Logic → Compile → Test → Deploy
(Months of development, thousands of lines of code)
```

### Executable Documentation Pattern
```
Write Game Rules in Markdown → AI Interprets → Game Runs
(Days of development, natural language rules)
```

### Key Innovations Demonstrated

1. **Documentation IS Code**: Markdown files in `/kb/experiences/west-of-house/` literally execute as game logic
2. **State in Messages**: Game state persists in conversation history via JSON blocks (no database schema changes)
3. **AI Interpretation**: KB Agent reads markdown rules and executes them naturally
4. **Zero Compilation**: No build process, deployment, or traditional game engine required

## 🎯 Success Metrics

After running these tests, you should see:

- ✅ **JSON State Persistence**: Each response contains updated game state
- ✅ **Natural Language Processing**: Commands like "open mailbox" work intuitively
- ✅ **Markdown Rule Execution**: Actions follow documented game rules from KB files
- ✅ **Conversation Continuity**: Game state carries forward across multiple requests
- ✅ **No Traditional Code**: Entire game runs from markdown documentation

This validates a **fundamental shift in software development** where documentation becomes executable code through AI interpretation!

## 📚 Related Documentation

- [Executable Documentation Pattern](executable-documentation-pattern.md) - The revolutionary concept explained
- [Game System Implementation Guide](game-system-implementation-guide.md) - Technical architecture
- [KB Endpoints Integration Guide](kb-endpoints-integration-guide.md) - How KB Agent accesses game content

## 🔄 Next Steps

Once you've validated the POC:

1. **Create Your Own Game**: Add markdown files to `/kb/experiences/your-game/`
2. **Extend Mechanics**: Define new game rules in plain English documentation
3. **Scale the Pattern**: Apply executable documentation to other software domains

The revolution in software development starts with markdown files that think they're code! 🚀