# Persona Update Testing Guide

## Problem Solved

Previously, when updating a persona (like Louisa), the changes wouldn't take effect in **active conversations** until you:
- Restarted the chat service, OR
- Cleared conversation history, OR
- Created a new conversation

This was because:
1. System prompts are loaded into memory when a conversation starts
2. PersonaService only clears Redis caches, not in-memory chat histories
3. The in-memory `chat_histories` dictionary persists the old prompt

## Solution

The `iterate_louisa.sh` script now automatically calls `/chat/reload-prompt` after updating a persona, which:
- Fetches fresh system prompts from the database
- Updates ALL active in-memory chat histories
- Makes changes take effect immediately in existing conversations

## Updated Scripts

### 1. `scripts/persona/iterate_louisa.sh update`

**Enhanced behavior:**
```bash
./scripts/persona/iterate_louisa.sh update louisa_v5.txt
```

Now automatically:
1. ✅ Updates persona in database
2. ✅ Clears Redis caches (automatic from PersonaService)
3. ✅ Calls `/chat/reload-prompt` to update active conversations
4. ✅ Notifies you if you have an active conversation

**Output example:**
```
✓ Persona updated successfully
Note: Cache automatically cleared by service

Reloading prompts in active conversations...
✓ Active conversation prompts reloaded

Note: You have an active conversation
Run ./scripts/persona/iterate_louisa.sh new to start fresh with the updated prompt
```

### 2. `scripts/persona/test_persona_update.sh` (NEW)

**Automated test that verifies prompt updates work:**
```bash
./scripts/persona/iterate_louisa.sh test
# OR directly:
./scripts/persona/test_persona_update.sh
```

**What it tests:**
1. Creates a fresh conversation
2. Chats with baseline prompt
3. Updates persona with a test marker ("TEST MODE ACTIVE")
4. Calls `/chat/reload-prompt`
5. Chats again in the SAME conversation
6. ✅ Verifies the new prompt is active (looks for "TEST MODE")
7. Restores original persona
8. Cleans up test conversation

**Output example:**
```
═══════════════════════════════════════════════════════════
  Persona Update Test - Verifying Prompt Reload
═══════════════════════════════════════════════════════════

Step 1: Backing up original Louisa persona...
✓ Original prompt backed up (2451 bytes)

Step 2: Starting fresh conversation...
✓ Conversation created: abc-123-def

Step 3: Chatting with baseline prompt...
Baseline: Oh! Princess Eliska, is that you? No? Well, I'm Louisa...

Step 4: Updating persona with test marker...
✓ Persona updated with marker: TESTING_MARKER_1234567890

Step 5: Reloading prompts in active conversations...
✓ Prompts reloaded successfully

Step 6: Testing with same conversation (should see TEST MODE)...
Response: TEST MODE ACTIVE. Oh hello! I'm Louisa...

Step 7: Verifying prompt update took effect...
✓ SUCCESS - New prompt is active in existing conversation!
  Found 'TEST MODE' in response

Step 8: Restoring original persona...
✓ Original persona restored
✓ Prompts reloaded with original version

Step 9: Cleaning up test conversation...
✓ Test conversation deleted

═══════════════════════════════════════════════════════════
✓ TEST PASSED - Persona updates take effect immediately!
═══════════════════════════════════════════════════════════
```

## Typical Workflows

### Iterating on Persona Prompts

```bash
# 1. View current persona
./scripts/persona/iterate_louisa.sh show

# 2. Start a conversation
./scripts/persona/iterate_louisa.sh new
./scripts/persona/iterate_louisa.sh chat "Hello Louisa!"

# 3. Edit prompt (save to file)
nano louisa_v6.txt

# 4. Update persona (automatically reloads active conversations)
./scripts/persona/iterate_louisa.sh update louisa_v6.txt

# 5. Continue same conversation with updated prompt
./scripts/persona/iterate_louisa.sh chat "How are you now?"

# 6. Start fresh conversation if needed
./scripts/persona/iterate_louisa.sh new
./scripts/persona/iterate_louisa.sh chat "Testing new version"
```

### Testing After Changes

```bash
# Run automated test
./scripts/persona/iterate_louisa.sh test

# Or test manually
./scripts/persona/iterate_louisa.sh new
./scripts/persona/iterate_louisa.sh chat "Tell me about yourself"
# ... update persona ...
./scripts/persona/iterate_louisa.sh update louisa_new.txt
./scripts/persona/iterate_louisa.sh chat "Tell me again"  # Should reflect changes
```

## Technical Details

### `/chat/reload-prompt` Endpoint

**Location:** `app/services/chat/chat.py` lines 170-198

**What it does:**
```python
@router.post("/reload-prompt")
async def reload_system_prompt(auth_principal: Dict[str, Any] = Depends(get_current_auth)):
    # For each active chat history:
    for user_key, history in chat_histories.items():
        if history and history[0].role == "system":
            # Get fresh persona-specific prompt
            user_system_prompt = await PromptManager.get_system_prompt(user_id=user_key)
            # Update in-place
            history[0].content = user_system_prompt
```

**Key points:**
- Updates system prompt for ALL active users
- Preserves conversation history (only updates prompt)
- Gets persona-specific prompts per user
- Returns `{"status": "success", "message": "System prompt reloaded successfully"}`

### Cache Invalidation Flow

When `PersonaService.update_persona()` is called:

1. **Database updated** → `UPDATE personas SET ... WHERE id = persona_id`
2. **Redis caches cleared** (automatic):
   - `redis_client.delete(persona_cache_key(persona_id))` - Individual persona cache
   - `redis_client.flush_pattern("personas:list:*")` - All persona list caches
3. **Script calls reload** → `POST /chat/reload-prompt`
4. **In-memory histories updated** → Fresh prompts from database

**Cache TTLs:**
- Individual personas: 1 hour (3600s)
- Persona lists: 5 minutes (300s)
- User preferences: 10 minutes (600s)

## Troubleshooting

### Test Fails with "Old prompt still active"

**Possible causes:**
1. Chat service not running: `docker compose ps chat`
2. Reload endpoint failed: Check chat logs `docker compose logs chat --tail 50`
3. Database connection issue
4. Redis not connected (prompts would work but not be cached)

**Solutions:**
```bash
# Restart chat service
docker compose restart chat

# Check if reload endpoint is accessible
curl -X POST -H "X-API-Key: $API_KEY" http://localhost:8666/api/v1/chat/reload-prompt

# Verify database updated
docker exec gaia-db-1 psql -U postgres -d llm_platform \
  -c "SELECT substring(system_prompt from 1 for 100) FROM personas WHERE name='Louisa';"
```

### Update Successful but Chat Still Uses Old Prompt

**Quick fix:**
```bash
# Force conversation restart
./scripts/persona/iterate_louisa.sh clear
./scripts/persona/iterate_louisa.sh new
```

**Long-term fix:**
Ensure `iterate_louisa.sh update` includes the reload call (should be automatic now).

## Best Practices

1. **Always test after major prompt changes:**
   ```bash
   ./scripts/persona/iterate_louisa.sh test
   ```

2. **Start fresh for clean testing:**
   ```bash
   ./scripts/persona/iterate_louisa.sh new
   ```
   Instead of continuing old conversations

3. **Check current persona before updating:**
   ```bash
   ./scripts/persona/iterate_louisa.sh show
   ```

4. **Use version numbers in filenames:**
   ```bash
   louisa_v1.txt  # Original
   louisa_v2.txt  # Shorter responses
   louisa_v3.txt  # No stage directions
   ```

5. **Keep backups of working versions:**
   ```bash
   cp louisa_current.txt louisa_backup_$(date +%Y%m%d).txt
   ```

## See Also

- [Persona System Guide](../docs/architecture/services/persona-system-guide.md) - Complete persona architecture
- [Chat Service Endpoints](../app/services/chat/chat.py) - Implementation details
- [Testing Guide](../docs/testing/TESTING_GUIDE.md) - General testing practices