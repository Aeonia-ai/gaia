# Distributed Systems Debugging Guide



## The Right Order of Investigation

### 1. Check Existing Tests First
```bash
# Search for tests related to your issue
grep -r "test.*persist" tests/
grep -r "TODO\|FIXME\|Known issue" tests/

# Run existing tests
./scripts/pytest-for-claude.sh tests/e2e/test_specific_issue.py -v
```

**Why**: Tests often document known issues with TODO comments

### 2. Use Docker, Not Local
```bash
# ❌ WRONG: Running locally
python test_something.py

# ✅ RIGHT: Run in the actual environment
docker compose exec -T web-service python test_something.py
docker compose exec -T web-service pytest tests/...
```

**Why**: Local environment lacks services, uses different configs

### 3. Check Git History
```bash
# Find when something changed
git log --oneline -- path/to/file.py

# See what changed in a specific commit
git show <commit-hash>

# Find when a pattern was introduced/removed
git log -S "pattern_to_search" --oneline
```

**Why**: Architectural changes often introduce bugs

### 4. Simple Monitoring First
```bash
# ❌ OVERENGINEERED: Complex monitoring setup
python monitor_all_the_things.py &

# ✅ SIMPLE: Grep logs for specific patterns
docker compose logs -f service | grep "pattern"
docker compose logs --since 5m service | grep -E "(error|failed|success)"
```

### 5. Look for Missing Logs
```bash
# Check if code is being reached
docker compose logs service | grep "Expected log message"

# If log is missing, the code isn't executing
```

**Key Insight**: Missing logs are as diagnostic as errors

## Debugging Distributed Systems Checklist

### Before Starting
- [ ] Is there an existing test for this issue?
- [ ] What does the test's output/comments say?
- [ ] When did this last work? (check git history)

### Investigation
- [ ] Run tests in Docker, not locally
- [ ] Check logs for MISSING messages, not just errors
- [ ] Verify each service is running: `docker compose ps`
- [ ] Test service-to-service communication

### Common Patterns

#### Pattern: "It works locally but not in Docker"
- **Cause**: Different environment, missing services
- **Fix**: Always test in Docker

#### Pattern: "The test exists but is commented out"
- **Cause**: Known issue not yet fixed
- **Fix**: Fix the issue, uncomment the test

#### Pattern: "No error logs but feature doesn't work"
- **Cause**: Code not being reached
- **Fix**: Trace execution flow, find where it stops

## Quick Commands Reference

```bash
# Service logs
docker compose logs -f <service>           # Follow logs
docker compose logs --since 10m <service>  # Recent logs
docker compose logs <service> | grep -E "pattern1|pattern2"

# Run tests in container
docker compose exec -T <service> pytest tests/...
docker compose exec -T <service> python script.py

# Check service health
docker compose ps
curl http://localhost:<port>/health

# Git investigation
git log --oneline -20 -- <file>
git blame <file> | grep <pattern>
```

## Anti-Patterns to Avoid

1. **Creating multiple test files for the same issue**
   - Sign you don't understand the problem
   - Use existing tests first

2. **Testing locally when services are Dockerized**
   - Will give false results
   - Always use Docker

3. **Adding complex debugging before simple checks**
   - Start with log grep
   - Add complexity only if needed

4. **Ignoring existing test comments**
   - TODOs often document known issues
   - Read test files like documentation

## The Meta-Lesson

> "When debugging distributed systems, the tooling and environment matter as much as the code."

Use the right tools in the right environment, and a complex problem often has a simple solution.