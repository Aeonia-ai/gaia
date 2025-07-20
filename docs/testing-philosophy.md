# Testing Philosophy

## 🎯 Core Principle: Scripts Over Curl

**Always use test scripts instead of manual curl commands.** This isn't just about convenience - it's about building institutional knowledge and preventing regression.

## Why Test Scripts?

### 1. **Reproducibility**
```bash
# ❌ Bad: Manual curl that gets lost in terminal history
curl -H "X-API-Key: $API_KEY" http://localhost:8666/api/v1/providers

# ✅ Good: Test script that anyone can run
./scripts/test.sh --local providers
```

### 2. **Environment Handling**
Test scripts automatically:
- Load environment variables from `.env`
- Handle different environments (local, staging, prod)
- Use the correct API keys and URLs
- Provide consistent authentication

### 3. **Knowledge Capture**
Each test script captures:
- The correct endpoint URL
- Required headers and authentication
- Expected request format
- How to interpret responses
- Common error conditions

### 4. **Evolution and Improvement**
When you discover a new test case:
1. **Don't just run curl** - Add it to a test script
2. **Found a bug?** - Add a test that would have caught it
3. **Fixed an issue?** - Update the test to verify the fix

## Test Script Hierarchy

```
scripts/
├── test.sh                    # Main test runner (legacy compatible)
├── test-comprehensive.sh      # Full test suite with all features
├── test-kb-operations.sh      # KB-specific tests
├── manage-users.sh           # User and permission management
├── layout-check.sh           # UI layout validation
└── [feature]-test.sh         # Feature-specific test scripts
```

## Best Practices

### 1. **Extend, Don't Replace**
When adding new functionality:
```bash
# Add to existing test script
echo "Testing new feature..." >> test-kb-operations.sh

# Or create a focused test script
./scripts/test-new-feature.sh
```

### 2. **Use Helper Functions**
```bash
# Define reusable test functions
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    # ... test logic ...
}

# Use them consistently
test_endpoint "POST" "/api/v1/chat" "$payload" "Chat completion test"
```

### 3. **Capture Context**
Always include:
- What you're testing
- Why it matters
- Expected vs actual results
- Environment information

### 4. **Make Tests Discoverable**
```bash
# Bad: Hidden knowledge
curl -X POST $SECRET_ENDPOINT -d @complex_payload.json

# Good: Documented in script
# Test the new webhook endpoint (added for issue #123)
test_endpoint "POST" "/api/v1/webhooks" '{"event": "test"}' "Webhook delivery"
```

## Common Patterns

### Testing Authentication
```bash
# Use test script functions
./scripts/test.sh --local auth

# Not manual curl
curl -H "X-API-Key: ..." 
```

### Testing New Endpoints
```bash
# 1. Add to comprehensive test
vim scripts/test-comprehensive.sh
# Add: test_endpoint "GET" "/api/v1/new-endpoint" "" "New feature test"

# 2. Run to verify
./scripts/test-comprehensive.sh
```

### Debugging Issues
```bash
# 1. Reproduce with test script
./scripts/test-kb-operations.sh | grep -A10 "failing test"

# 2. Fix the issue

# 3. Verify fix with same script
./scripts/test-kb-operations.sh
```

## Anti-Patterns to Avoid

### ❌ One-off Curl Commands
```bash
# This knowledge is lost after you close the terminal
curl -X POST http://localhost:8666/api/v0.2/kb/search \
  -H "X-API-Key: abc123" \
  -d '{"message": "test"}'
```

### ❌ Hardcoded Values
```bash
# API keys and URLs should come from environment
API_KEY="hardcoded-key-bad"
curl "http://hardcoded-url-bad.com/api"
```

### ❌ No Error Handling
```bash
# What happens when this fails?
curl $URL | jq '.result'
```

### ✅ Instead: Robust Test Scripts
```bash
# Reusable, environment-aware, error-handling test
./scripts/test.sh --local kb-search "test query"
```

## Adding New Tests

When you need to test something new:

1. **Check if a test script exists**
   ```bash
   ls scripts/test-*.sh
   ```

2. **Extend existing script if appropriate**
   ```bash
   # Add to test-kb-operations.sh for KB features
   # Add to test-comprehensive.sh for general features
   ```

3. **Create new script for new domains**
   ```bash
   # New feature area? New test script
   cp scripts/test-template.sh scripts/test-newfeature.sh
   ```

4. **Document what you're testing**
   ```bash
   # Always include comments explaining the test
   # Test: Verify rate limiting works correctly (max 100 req/min)
   test_endpoint "GET" "/api/v1/rate-limit-test" "" "Rate limit verification"
   ```

## The Payoff

Following this philosophy means:
- **No lost knowledge** - Every test case is preserved
- **Faster debugging** - Reproduce issues instantly
- **Better onboarding** - New developers can understand the system
- **Regression prevention** - Old bugs don't come back
- **Living documentation** - Tests show how the system actually works

Remember: **If you're typing curl, you should be updating a test script instead!**