# KB Git Clone Learnings



## Problem Evolution
We went through several iterations to get git clone working properly for the KB service:

1. **Initial Problem**: Service timeout during startup due to blocking git clone
2. **First Solution**: Deferred/background clone - but it didn't work
3. **Real Issues Discovered**: 
   - Background asyncio task wasn't executing
   - Volume size too small (1GB for 1GB repo)
   - Mount point permissions

## Key Learnings

### 1. Volume Sizing
**Learning**: Always provision volumes at least 2-3x the size of your data
- Git repository: 1GB
- Initial volume: 1GB (failed - no overhead)
- Solution: 3GB minimum (3x size for git operations, temp files, growth)

**Why it matters**: Git clone needs temp space, the filesystem needs overhead, and repos grow over time.

### 2. Mount Point Restrictions
**Learning**: You cannot delete or recreate a mount point directory
```bash
# ❌ This fails
rm -rf /kb  # Error: Device or resource busy

# ✅ This works
rm -rf /kb/*
rm -rf /kb/.[^.]*
```

**Solution**: Clone to temp directory, then move contents into mount point.

### 3. Async Background Tasks Can Be Tricky
**Learning**: `asyncio.create_task()` in startup may not execute as expected

**What didn't work**:
```python
asyncio.create_task(_background_clone())  # Task never ran
```

**What worked**:
```python
# Simple synchronous endpoint for manual trigger
subprocess.run(['git', 'clone', url, '.'], cwd=kb_path)
```

### 4. Debugging Remote Services
**Learning**: When automation fails, add manual triggers for debugging

**Pattern**:
```python
@app.post("/trigger-clone")
async def trigger_clone():
    """Manual trigger endpoint for debugging"""
    # Simple, synchronous, observable
```

This allowed us to:
- Test git authentication
- See actual error messages
- Trigger clone on demand
- Verify configuration

### 5. Service Health Should Show Data Status
**Learning**: Health endpoints should report data initialization status

**Good health endpoint**:
```json
{
  "service": "kb",
  "status": "healthy",
  "repository": {
    "status": "ready (1234 files)",
    "file_count": 1234,
    "has_git": true,
    "git_url_configured": true,
    "git_token_configured": true
  }
}
```

This immediately tells us:
- Is the service up? ✓
- Is the data ready? ✓
- Are secrets configured? ✓

### 6. Network Filesystem Limitations
**Learning**: Fly.io internal DNS and standard git operations can conflict

**Issues encountered**:
- SSH operations timeout
- Complex git operations fail
- Background tasks unreliable

**Solution**: Keep it simple - basic git clone in controlled environment

### 7. Persistent Volume Best Practices
**Learning**: Design for persistence from the start

**Good patterns**:
- Check if data already exists before cloning
- Use volume for data, not code
- Plan for volume growth
- Document volume requirements

### 8. Error Messages Are Gold
**Learning**: Preserve and surface actual error messages

**Key discovery**: "No space left on device" - immediately told us the real issue

**Implementation**:
```python
if result.returncode != 0:
    error_msg = result.stderr
    # Hide secrets but preserve error
    if git_token:
        error_msg = error_msg.replace(git_token, "***")
    return {"error": "Clone failed", "details": error_msg}
```

## Final Architecture

```
┌─────────────────┐
│   KB Service    │
│                 │
│  ┌───────────┐  │
│  │  Startup  │  │──── Creates /kb directory
│  │           │  │──── Returns immediately
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │  Health   │  │──── Reports repository status
│  │ Endpoint  │  │──── Shows file count
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Trigger   │  │──── Manual clone endpoint
│  │ Endpoint  │  │──── Synchronous execution
│  └─────┬─────┘  │
└────────┼────────┘
         │
   ┌─────▼─────┐
   │    /kb    │
   │  Volume   │──── 3GB persistent storage
   │  (3x repo)│──── Survives restarts
   └───────────┘
```

## Deployment Checklist

1. **Size the volume**: 3x your repository size minimum
2. **Set secrets**: `KB_GIT_REPO_URL` and `KB_GIT_AUTH_TOKEN`
3. **Deploy service**: Starts immediately (empty)
4. **Trigger clone**: Manual endpoint or restart
5. **Verify**: Check health endpoint for file count

## What We'd Do Differently

1. **Start with manual trigger**: Don't overcomplicate with async
2. **Add clone status endpoint**: Show progress during clone
3. **Size volume generously**: Storage is cheap, debugging is expensive
4. **Test with large repos early**: Find size issues before production
5. **Add sparse checkout option**: For repos with large binary files

## Commands That Worked

```bash
# Create properly sized volume
fly volumes create gaia_kb_dev_3gb --size 3 -a gaia-kb-dev --region lax --yes

# Trigger manual clone
curl -X POST https://gaia-kb-dev.fly.dev/trigger-clone

# Check status
curl https://gaia-kb-dev.fly.dev/health | jq '.repository'

# SSH debugging (when it works)
fly ssh console -a gaia-kb-dev --command "ls -la /kb/"
```

## Summary

The journey from "deferred initialization" to "manual trigger with proper volume" taught us:
- **Simple > Clever**: Synchronous manual trigger worked better than async magic
- **Observable > Automatic**: Being able to trigger and watch is invaluable  
- **Space > Optimization**: 3x overhead prevents mysterious failures
- **Explicit > Implicit**: Clear error messages and status reporting

The final solution is simpler and more reliable than our initial "clever" approach.