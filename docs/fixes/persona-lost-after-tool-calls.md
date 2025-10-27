# Fix: Persona Lost After Tool Calls

**Date**: 2025-10-21
**Affected File**: `app/services/chat/unified_chat.py`
**Status**: Fixed ✅

## Summary

KB tool calls were losing persona context in the second LLM call, causing responses to use base LLM instead of the active persona (e.g., Louisa).

## The Bug

When intelligent routing triggers KB search:

1. **First LLM call** (line 274): Uses persona system prompt + routing tools
   - LLM analyzes message: "I think I saw a blue elf near the window!"
   - Decides to call `search_knowledge_base` tool

2. **Second LLM call** (line 336): Generates response from KB results
   - **BUG**: Used hardcoded `"You are a helpful assistant"`
   - Lost persona context from first call
   - Resulted in generic responses instead of in-character responses

## Example Behavior

**Input**: "I think I saw a blue elf near the window!"

**Before Fix** (base LLM):
```
I do not have any factual information about a "blue elf" being seen near a window.
Elves are mythical creatures, and sightings of them are generally considered to be
imaginary or the result of misperceptions...
```

**After Fix** (Louisa persona):
```
Oh! Near the window? Quick, can you check if there are dream bottles there?
```

## Root Cause

Line 340 in `unified_chat.py`:
```python
final_response = await chat_service.chat_completion(
    messages=messages,
    temperature=0.7,
    max_tokens=4096,
    request_id=f"{request_id}-final",
    system_prompt="You are a helpful assistant. Please provide a comprehensive response based on the tool results provided."  # ❌ LOST PERSONA
)
```

## The Fix

**File**: `app/services/chat/unified_chat.py`
**Line**: 340

```python
final_response = await chat_service.chat_completion(
    messages=messages,
    temperature=0.7,
    max_tokens=4096,
    request_id=f"{request_id}-final",
    system_prompt=system_prompt  # ✅ PRESERVE PERSONA
)
```

**Explanation**: Use the same `system_prompt` from the first call (which includes persona) instead of a hardcoded generic prompt.

## Testing

### Test Setup

1. **Active Persona**: Only Louisa (`7b197909-8837-4ed5-a67a-a05c90e817f0`)
2. **Test Message**: "I think I saw a blue elf near the window!"
   - This triggers KB search (tool call)
   - KB returns 0 results
   - LLM must respond in-character with those results

### Verification

```bash
# Test that triggers KB search
python3.11 scripts/gaia_client.py --env local --batch "I think I saw a blue elf near the window!"

# Expected: Louisa's in-character response
# "Oh! Near the window? Quick, can you check if there are dream bottles there?"

# Not: Generic base LLM response about mythical creatures
```

### Test Suite

Full conversation test: `/tmp/test_all_messages.sh`
- 12 messages covering typical AR gameplay flow
- Message 11 specifically tests KB search with persona preservation

## Impact

**Severity**: High
**Scope**: All KB tool calls (search_knowledge_base, read_kb_file, etc.)

Any message that triggers KB search would respond with base LLM instead of maintaining persona consistency, breaking immersion for character-based interactions.

## Related Changes

**Test-Only State** (not production code):
- Disabled v0.3 directives (lines 1479-1480) for Louisa voice testing
- Set `GAIA-MMOIRL` and `Mu` personas to `is_active = false`
- Set test users' persona preferences to Louisa

**To Revert Test State**:
```sql
-- Re-enable other personas
UPDATE personas SET is_active = true WHERE name IN ('GAIA-MMOIRL', 'Mu');

-- Uncomment lines 1479-1480 in unified_chat.py if v0.3 directives needed
```

## Prevention

**Code Review Checklist**:
- [ ] When making multiple LLM calls, verify `system_prompt` is consistent
- [ ] Tool call workflows should preserve persona context across all LLM calls
- [ ] Test with active persona to catch context loss

**Future Improvement**:
Consider refactoring to make `system_prompt` a class attribute that's consistently used across all LLM calls, preventing this class of bug.
