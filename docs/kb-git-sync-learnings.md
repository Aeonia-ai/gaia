# KB Git Sync Implementation Learnings

This document captures key learnings from implementing Git repository synchronization for the KB (Knowledge Base) service, including challenges faced and solutions discovered.

## Overview

We successfully implemented Git repository synchronization for the KB service, allowing it to automatically clone and serve content from external Git repositories (like Obsidian vaults). The implementation uses container-only storage for perfect local-remote parity.

## Key Implementation Details

### 1. Deferred Initialization Pattern

**Problem**: Git clone operations can take 30+ seconds for large repositories, causing service startup timeouts.

**Solution**: Implement deferred (non-blocking) initialization:
```python
async def initialize_kb_repository():
    """Initialize KB repository with deferred cloning"""
    kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
    kb_path.mkdir(parents=True, exist_ok=True)
    
    if (kb_path / '.git').exists():
        logger.info(f"Repository exists with {file_count} files")
        return True
    
    # Don't block startup - schedule background clone
    logger.info("Scheduling background git clone...")
    asyncio.create_task(_background_clone())
    return True  # Return immediately
```

**Benefits**:
- Service starts immediately and passes health checks
- Clone happens in background without blocking
- Service remains available during clone operation

### 2. Manual Clone Trigger Endpoint

**Problem**: Background tasks in FastAPI can be unreliable, especially in containerized environments.

**Solution**: Add a manual trigger endpoint for explicit control:
```python
@app.post("/trigger-clone")
async def trigger_clone():
    """Manually trigger git clone (public endpoint for testing)"""
    if (kb_path / '.git').exists():
        return {"status": "already_cloned", "file_count": file_count}
    
    # Use subprocess.run for reliability
    cmd = ["git", "clone", repo_url, ".", "--depth", "1"]
    result = subprocess.run(cmd, cwd=str(kb_path), capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        return {"status": "success", "message": "Repository cloned"}
    else:
        return {"status": "error", "error": result.stderr}
```

**Benefits**:
- Explicit control over when cloning happens
- Easy to test and debug
- Can be called from deployment scripts
- Works reliably in all environments

### 3. Volume Sizing Considerations

**Problem**: "No space left on device" error when cloning 1GB repository into 1GB volume.

**Solution**: Use 3x repository size for volumes:
```toml
[mounts]
  source = "gaia_kb_dev_3gb"  # 3GB for 1GB repository
  destination = "/kb"
```

**Why 3x?**:
- Git objects and pack files add overhead
- Need space for temporary files during clone
- Future growth accommodation
- Safe margin for operations

### 4. Container-Only Storage Pattern

**Problem**: Local volume mounts behave differently than production volumes, causing deployment surprises.

**Solution**: Use container-only storage (no local mounts):
```yaml
# docker-compose.yml
kb-service:
  volumes:
    # DON'T mount local directory
    # - ./kb_data:/kb  # This breaks local-remote parity
    
    # DO use container-only storage
    # Data is ephemeral and re-cloned on each start
```

**Benefits**:
- Perfect local-remote parity
- Forces proper Git workflow (all changes through Git)
- Simplifies deployment configuration
- Matches production behavior exactly

### 5. Path Configuration Gotchas

**Problem**: Confusion between volume mount point and repository subdirectory.

**Wrong**:
```toml
KB_PATH = "/kb/repository"  # Creates /kb/repository/repository!
```

**Right**:
```toml
KB_PATH = "/kb"  # Clone directly into mount point
```

**Lesson**: When mounting a volume for Git, clone directly into the mount point, not a subdirectory.

### 6. Authentication Token Management

**Problem**: Private repositories require authentication tokens.

**Solution**: Use personal access tokens with minimal permissions:
```bash
# GitHub
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Set in production
fly secrets set KB_GIT_AUTH_TOKEN=ghp_xxxxx -a gaia-kb-prod
```

**Security Best Practices**:
- Use read-only tokens when possible
- Rotate tokens regularly
- Never commit tokens to Git
- Use environment-specific tokens

### 7. Deployment Automation

**Problem**: Need to trigger clone after deployment.

**Solution**: Add to deployment script:
```bash
# scripts/deploy.sh
if [[ "$service" == "kb" ]]; then
    log_step "Checking KB repository status..."
    sleep 30  # Wait for service to start
    
    # Trigger clone if needed
    response=$(curl -s -X POST "$app_url/trigger-clone")
    echo "Clone trigger response: $response"
fi
```

### 8. Health Check Integration

**Problem**: Need to know repository status without checking logs.

**Solution**: Include repository info in health endpoint:
```python
@app.get("/health")
async def health():
    kb_path = Path(settings.KB_PATH)
    repo_status = {
        "initialized": (kb_path / '.git').exists(),
        "file_count": sum(1 for _ in kb_path.rglob("*") if _.is_file())
    }
    
    return {
        "status": "healthy",
        "storage_mode": settings.KB_STORAGE_MODE,
        "repository": repo_status
    }
```

## Common Issues and Solutions

### 1. "Device or resource busy" Error
**Cause**: Trying to delete or modify the mount point directory.
**Solution**: Clone to temp directory first, then move contents.

### 2. Clone Hangs Forever
**Cause**: Large repository + slow network + no timeout.
**Solution**: Use `--depth 1` for shallow clone and set timeout:
```python
subprocess.run(cmd, timeout=300)  # 5 minute timeout
```

### 3. Background Task Not Executing
**Cause**: FastAPI lifespan context issues with async tasks.
**Solution**: Use manual trigger endpoint instead of background tasks.

### 4. Authentication Failures
**Cause**: Wrong token format or insufficient permissions.
**Solution**: Test token locally first:
```bash
git clone https://${TOKEN}@github.com/org/repo.git
```

## Best Practices

1. **Always Use Shallow Clones**: `--depth 1` for faster cloning
2. **Set Reasonable Timeouts**: 5 minutes is usually enough
3. **Log Everything**: Verbose logging helps debug remote issues
4. **Test Locally First**: Use same container-only pattern locally
5. **Monitor Disk Usage**: Check volume usage in health endpoints
6. **Handle Failures Gracefully**: Service should work even if clone fails

## Testing Strategy

### Local Testing
```bash
# Start service
docker compose up kb-service

# Check health
curl http://localhost:8000/health

# Trigger clone
curl -X POST http://localhost:8000/trigger-clone

# Verify files
docker compose exec kb-service ls -la /kb/
```

### Remote Testing
```bash
# Deploy
fly deploy -a gaia-kb-dev --config fly.kb.dev.toml --remote-only

# Check status
./scripts/test.sh --url https://gaia-kb-dev.fly.dev health

# Trigger clone
curl -X POST https://gaia-kb-dev.fly.dev/trigger-clone
```

## Future Improvements

1. **Incremental Updates**: Implement `git pull` for updates instead of full re-clone
2. **Multi-Branch Support**: Allow switching between branches
3. **Webhook Integration**: Auto-pull on GitHub webhook
4. **Clone Progress API**: WebSocket endpoint for real-time clone progress
5. **Sparse Checkout**: Clone only specific directories for large repos

## Key Takeaways

1. **Deferred initialization** is crucial for services with slow startup operations
2. **Container-only storage** ensures consistent behavior across environments
3. **Manual triggers** are more reliable than background tasks in containers
4. **Volume sizing** needs 3x headroom for Git operations
5. **Health endpoints** should expose operational status, not just service health
6. **Deployment scripts** should handle post-deployment initialization
7. **Path configuration** mistakes are common - always verify with logs

## References

- [Git Clone Documentation](https://git-scm.com/docs/git-clone)
- [Fly.io Volumes Guide](https://fly.io/docs/volumes/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Docker Volume Best Practices](https://docs.docker.com/storage/volumes/)