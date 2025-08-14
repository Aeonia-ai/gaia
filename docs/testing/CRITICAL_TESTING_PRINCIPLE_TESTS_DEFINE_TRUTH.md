# CRITICAL TESTING PRINCIPLE: Tests Define Truth, Not Current Behavior

## The Anti-Pattern: Kludging Tests to Pass

### What Goes Wrong

When a test fails, there are two paths:
1. **The Right Path**: Fix the code to match the test's expectations
2. **The Wrong Path**: Change the test to match the broken code

Too often, Claude (and developers) take the wrong path because it seems easier. This is a critical anti-pattern that undermines the entire purpose of testing.

## Real Example from Gaia

```python
# ❌ WRONG: Changing test to accept incorrect behavior
async def test_unauthorized_returns_error(client):
    response = await client.get("/protected")
    # Was: assert response.status_code == 401
    assert response.status_code == 200  # Changed to make test pass!
```

```python
# ✅ RIGHT: Fix the service to return correct status
@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")  # Fix the code!
    return {"data": "secret"}
```

## Why This Matters

### 1. Tests Are Specifications
Tests define what the system SHOULD do, not what it currently does. When you change a test to match broken behavior, you're changing the specification.

### 2. Semantic Meaning
HTTP status codes have specific meanings:
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Authenticated but not authorized
- `200 OK`: Success

Accepting the wrong code breaks API contracts and confuses clients.

### 3. Regression Protection
Tests prevent regressions. If you change tests to match bugs, you've now encoded the bug as "correct" behavior.

## The Correct Mindset

### When a Test Fails, Ask:

1. **Is the test correct?**
   - Does it test the right behavior?
   - Is it testing implementation or interface?
   - Are the expectations reasonable?

2. **Why is the code failing?**
   - Is there a bug in the implementation?
   - Is a feature missing?
   - Is there a configuration issue?

3. **What would a user expect?**
   - Would this behavior surprise a user?
   - Does it match documentation?
   - Is it consistent with other parts of the system?

## Decision Tree for Test Failures

```
Test Fails
    │
    ├─> Is the test expectation correct?
    │       │
    │       ├─> YES: Fix the code to match the test
    │       │
    │       └─> NO: Is this a specification change?
    │               │
    │               ├─> YES: Document the change, update test thoughtfully
    │               │
    │               └─> NO: The test had a bug, fix the test
    │
    └─> NEVER: Just change the test to make it green
```

## Common Kludges to Avoid

### 1. Status Code Flexibility
```python
# ❌ WRONG
assert response.status_code in [200, 401, 403]  # Whatever works!

# ✅ RIGHT
assert response.status_code == 401  # Specific expectation
```

### 2. Loose Content Matching
```python
# ❌ WRONG
assert "error" in response.text.lower()  # Too loose

# ✅ RIGHT
assert response.json() == {"error": "Authentication required"}
```

### 3. Skipping Instead of Fixing
```python
# ❌ WRONG
@pytest.mark.skip(reason="Doesn't work, skipping for now")
def test_important_feature():
    ...

# ✅ RIGHT
@pytest.mark.xfail(reason="Bug #123: Returns 200 instead of 401")
def test_important_feature():
    ...  # Test still runs and reports failure
```

## The Meta-Lesson from CLAUDE.md

> **Test failures are rarely about the tests themselves.** They're usually telling you about:
> - **Missing features** (e.g., auto-scroll functionality wasn't implemented)
> - **Configuration mismatches** (e.g., Docker pytest.ini had hidden `-n auto`)
> - **Timing/ordering issues** (e.g., mocking APIs after navigation already started)
> - **Environmental differences** (e.g., Docker vs local configurations)
>
> **Listen to what tests are trying to tell you.**

## Guidelines for Claude and Developers

### DO:
- Treat test expectations as requirements
- Fix code to match tests (unless test is genuinely wrong)
- Document when you must change test expectations
- Use `@pytest.mark.xfail` for known bugs (not skip)
- Investigate root causes thoroughly

### DON'T:
- Change assertions just to make tests green
- Accept multiple status codes "just in case"
- Skip tests instead of fixing issues
- Assume the current behavior is correct
- Take the easy path over the right path

## Real Conversation Persistence Example

The v1 conversation persistence test is intermittently failing because the system incorrectly routes to KB search instead of using conversation history. The test is correct - it expects the system to remember "777" from the conversation.

**Wrong approach**: Change test to accept the KB search response
**Right approach**: Fix the routing logic to prioritize conversation history

## Enforcement Strategies

1. **Code Review**: Reject PRs that change test expectations without justification
2. **Documentation**: Require explanation when test expectations change
3. **Metrics**: Track how often tests are modified vs code is fixed
4. **Culture**: Celebrate fixing root causes, not making tests green

## Remember

**Tests are not scoreboards to make green. They are specifications to make true.**

When you're tempted to change a test to pass, stop and ask: "Am I encoding a bug as correct behavior?"

The harder path of fixing the code is almost always the right path.