# Testing Experience Changes

**Guide for testing markdown-based experience logic changes**

Based on successful validation of reset system and collection bug fix (2025-11-02).

---

## 🎯 Key Insight: Direct API Testing

Experience changes (markdown files in KB) are **immediately available** when:
- KB is mounted via `KB_PATH` in `.env`
- Services are running with hot-reload enabled
- No Docker rebuild needed!

**What gets hot-loaded:**
- ✅ Markdown specification changes (`collect.md`, `@reset-experience.md`)
- ✅ World state files (`world.json`, `world.template.json`)
- ✅ Python code changes (with `--reload` flag in Docker)

**What requires rebuild:**
- ❌ New dependencies in `requirements.txt`
- ❌ Dockerfile changes
- ❌ Environment variable changes requiring container restart

---

## 📋 Testing Pattern: Experience Validation Scripts

### Location
```
scripts/experience-validation/wylding-woods/
├── interactive_play.py              # Manual testing
├── validate_player_commands.py      # Command validation
├── validate_woander_store_journey.py # Full E2E journey
├── validate_reset_and_collection.py # Specific feature test (example)
└── quick_collection_test.py         # Quick validation (example)
```

### Script Structure

**1. Use `/experience/interact` endpoint**
```python
BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

payload = {
    "experience": "wylding-woods",
    "message": "take the dream bottle",
    "user_id": "test-user@aeonia.ai"
}

response = requests.post(
    f"{BASE_URL}/experience/interact",
    headers=HEADERS,
    json=payload,
    timeout=60
)
```

**2. Create unique test users**
```python
# Use timestamp to avoid state pollution
TEST_USER = f"test-{int(time.time())}@aeonia.ai"
```

**3. Check state_updates for correctness**
```python
state_updates = result.get("state_updates", {})
world_update = state_updates.get("world", {})
path = world_update.get("path", "")

# Validate the generated path
if "sublocations" in path:
    print("✅ Correct sublocation path!")
else:
    print("❌ Missing sublocations - bug!")
```

**4. Verify world.json directly**
```python
import subprocess

result = subprocess.run([
    "cat",
    "/path/to/kb/experiences/wylding-woods/state/world.json"
], capture_output=True, text=True)

world_data = json.loads(result.stdout)
# Verify expected state
```

---

## 🧪 Example: Testing Collection Bug Fix

### What We Were Testing
- LLM generates correct sublocation paths for item collection
- Items properly removed from world state
- No item duplication

### Test Script Pattern

```python
#!/usr/bin/env python3
"""Quick collection test for sublocation path fix."""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}
TEST_USER = f"test-{int(time.time())}@aeonia.ai"

def send_command(message):
    payload = {
        "experience": "wylding-woods",
        "message": message,
        "user_id": TEST_USER
    }

    response = requests.post(
        f"{BASE_URL}/experience/interact",
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    return response.json()

# Step 1: Navigate to sublocation
result = send_command("go to spawn_zone_3")

# Step 2: Look around
result = send_command("look around")

# Step 3: Collect item
result = send_command("take the dream bottle")

# Step 4: Validate state_updates
state_updates = result.get("state_updates", {})
path = state_updates.get("world", {}).get("path", "")

if "sublocations" in path:
    print(f"✅ SUCCESS! Correct path: {path}")
else:
    print(f"❌ FAILURE! Wrong path: {path}")
```

### Running the Test

```bash
# Ensure venv is activated
source .venv/bin/activate

# Run test
python3 scripts/experience-validation/wylding-woods/quick_collection_test.py
```

---

## 🔍 What to Check in Test Results

### 1. **Narrative Response**
- Does the LLM understand the command?
- Is the response contextually appropriate?
- Any error messages?

### 2. **State Updates**
- Are `state_updates.world.path` correct?
- Are `state_updates.player.path` correct?
- Do operations match expectations? (`add`, `remove`, `update`)

### 3. **World State Files**
```bash
# Check if item was removed
cat /path/to/kb/experiences/wylding-woods/state/world.json | jq '.locations.woander_store.sublocations.spawn_zone_3.items'

# Should be empty after collection: []
```

### 4. **Success Flag**
```python
if not result.get("success"):
    error = result.get("error", {})
    print(f"Failed: {error}")
```

---

## 📊 Test Output Format

### Good Test Output
```
======================================================================
🎮 Command: "take the dream bottle"
======================================================================

📖 Response:
You reach out and carefully lift the dream bottle...

📝 State Updates:
   World: remove at locations.woander_store.sublocations.spawn_zone_3.items
   Item: dream_bottle_3

✅ SUCCESS! Path includes 'sublocations'
   Full path: locations.woander_store.sublocations.spawn_zone_3.items

🎉 BUG IS FIXED!

✅ Command succeeded
```

### Bad Test Output (Bug Present)
```
📝 State Updates:
   World: remove at locations.woander_store.items
   Item: dream_bottle_3

❌ FAILURE! Missing 'sublocations' in path
   Path: locations.woander_store.items
   This would cause duplication!
```

---

## 🚨 Common Issues & Solutions

### Issue 1: Timeout Errors
```
❌ Exception: HTTPConnectionPool(host='localhost', port=8001): Read timed out.
```

**Causes:**
- Claude API overloaded (500 error)
- Complex LLM reasoning taking >30s
- Fallback provider issues

**Solutions:**
- Increase timeout: `timeout=60` or `timeout=90`
- Check logs: `docker logs gaia-kb-service-1 --tail 100`
- Retry after a moment (API overload is temporary)

### Issue 2: Player Not at Sublocation
```
❌ Failed: You don't see any dream bottle here.
```

**Cause:** Player is at top-level location, not the specific sublocation

**Solution:** Navigate first
```python
send_command("go to spawn_zone_3")  # Navigate
send_command("look around")         # Establish location
send_command("take the dream bottle") # Now collection works
```

### Issue 3: Wrong Endpoint
```
❌ 404: Not Found
```

**Cause:** Using old `/game/command` endpoint instead of new `/experience/interact`

**Solution:** Use `/experience/interact` with simpler payload format

---

## 📚 Testing Checklist

When testing experience changes:

- [ ] Ensure `.venv` is activated
- [ ] Check services are running: `docker ps`
- [ ] Verify KB_PATH points to correct vault
- [ ] Use unique test user (timestamp-based)
- [ ] Navigate to correct location/sublocation first
- [ ] Check `state_updates` for correct paths
- [ ] Verify world.json changes directly
- [ ] Test both success and failure cases
- [ ] Check logs if timeout occurs
- [ ] Clean up test data if needed

---

## 🎯 Testing Best Practices

### 1. **Atomic Tests**
Test one thing at a time. Don't combine reset + collection + navigation in one test unless specifically testing integration.

### 2. **Unique Test Users**
```python
TEST_USER = f"test-{int(time.time())}@aeonia.ai"
```
Prevents state pollution between test runs.

### 3. **Explicit Validation**
Don't just check `success: true` - validate the actual state changes:
```python
# ❌ Weak validation
assert result.get("success")

# ✅ Strong validation
assert "sublocations" in state_updates["world"]["path"]
assert world_json["spawn_zone_3"]["items"] == []
```

### 4. **Direct File Verification**
When possible, check the actual files:
```bash
cat world.json | jq '.locations.X.sublocations.Y.items'
```

### 5. **Document Edge Cases**
In test output, explain what should happen:
```python
print("Expected: Item removed from locations.woander_store.sublocations.spawn_zone_3.items")
print(f"Actual path: {path}")
```

---

## 🔗 Related Documentation

- [Testing Guide](../testing/TESTING_GUIDE.md) - Comprehensive testing documentation
- [Command Reference](../current/development/command-reference.md) - Correct command syntax
- [Interactive Play Script](../../scripts/experience-validation/wylding-woods/interactive_play.py) - Manual testing example

---

## 📝 Example: Our Successful Test

**What we tested:** Reset system + collection sublocation path fix

**Test location:** `scripts/experience-validation/wylding-woods/validate_reset_and_collection.py`

**Results:**
- ✅ Reset created backup, restored template, deleted player views
- ✅ Collection generated correct path: `locations.woander_store.sublocations.spawn_zone_3.items`
- ✅ Item removed from world.json (verified with jq)
- ✅ No duplication

**Key learnings:**
1. Direct API testing is fast and reliable
2. State validation requires checking both response and files
3. Timeouts from Claude API overload are temporary
4. Navigation to sublocation is required before collection

---

**Created:** 2025-11-02
**Validated with:** Reset system + collection bug fix
