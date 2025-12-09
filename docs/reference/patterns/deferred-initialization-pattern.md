# Deferred Initialization Pattern


## Problem Statement

Services that need to fetch large datasets or perform time-consuming initialization tasks on startup face a dilemma:
- **Blocking initialization**: Service is unavailable during startup, health checks fail, deployments timeout
- **Ephemeral storage**: Container restarts lose all initialization work, requiring repeated downloads

This was discovered when deploying the KB service with a 1074+ file Git repository that took several minutes to clone.

## Solution: Deferred Initialization with Persistent Volumes

### Architecture

```
┌─────────────────┐
│   Container     │
│  (Ephemeral)    │
│                 │
│  ┌───────────┐  │
│  │  Service  │  │──── Health endpoint reports status
│  │  Process  │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │Background │  │──── Non-blocking initialization
│  │   Task    │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │
   ┌─────▼─────┐
   │Persistent │
   │  Volume   │──── Data survives container restarts
   └───────────┘
```

### Implementation Pattern

1. **Immediate Service Startup**
```python
async def initialize_kb_repository():
    """Fast startup with deferred initialization"""
    data_path = Path(settings.DATA_PATH)
    
    # Always ensure directory exists for immediate startup
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Check if already initialized
    if is_already_initialized(data_path):
        logger.info(f"Data already initialized with {count_files(data_path)} files")
        return True
    
    # Schedule background initialization (non-blocking)
    logger.info("Scheduling background initialization...")
    asyncio.create_task(background_initialize())
    
    return True  # Service starts immediately
```

2. **Background Initialization**
```python
async def background_initialize():
    """Perform initialization in background after startup"""
    try:
        logger.info("Starting background initialization...")
        
        # Perform time-consuming initialization
        await fetch_large_dataset()
        await process_data()
        
        logger.info("✅ Background initialization completed")
        
    except Exception as e:
        logger.error(f"❌ Background initialization failed: {e}")
        # Service continues running even if initialization fails
```

3. **Enhanced Health Endpoint**
```python
@app.get("/health")
async def health_check():
    """Health check with initialization status"""
    data_path = Path(settings.DATA_PATH)
    
    # Determine initialization status
    if not data_path.exists():
        init_status = "not_started"
    elif is_initialized(data_path):
        init_status = f"ready ({count_files(data_path)} files)"
    else:
        init_status = "in_progress"
    
    return {
        "service": "example",
        "status": "healthy",  # Service is healthy even if initializing
        "version": "1.0.0",
        "initialization": {
            "status": init_status,
            "data_path": str(data_path),
            "file_count": count_files(data_path)
        }
    }
```

### Persistent Volume Configuration

**Fly.io Example** (fly.toml):
```toml
[mounts]
  source = "service_data"
  destination = "/data"  # Persistent across deployments

[env]
  DATA_PATH = "/data"  # Point to persistent volume
```

**Docker Compose Example**:
```yaml
services:
  example-service:
    volumes:
      - service_data:/data
    environment:
      DATA_PATH: /data

volumes:
  service_data:  # Named volume persists across container restarts
```

## Benefits

1. **Fast Startup**: Service is immediately available, no deployment timeouts
2. **Persistent Data**: Initialization only happens once, data survives restarts
3. **Observable Status**: Health endpoint reports initialization progress
4. **Graceful Degradation**: Service can operate with partial data during initialization
5. **Platform Friendly**: Works with health checks, rolling deployments, auto-scaling

## Use Cases

This pattern is ideal for services that need to:
- Clone large Git repositories (KB service)
- Download ML models or datasets
- Build search indexes
- Sync from external data sources
- Pre-compute expensive calculations
- Cache data from slow APIs

## Testing the Pattern

```bash
# First deployment - initialization happens in background
./scripts/test.sh --env dev service-health
# Output: {"status": "healthy", "initialization": {"status": "in_progress"}}

# Wait for initialization
sleep 120

# Check again - initialization complete
./scripts/test.sh --env dev service-health
# Output: {"status": "healthy", "initialization": {"status": "ready (1074 files)"}}

# Restart service - uses existing data
fly machine restart <machine-id> -a service-dev

# Immediate availability with existing data
./scripts/test.sh --env dev service-health
# Output: {"status": "healthy", "initialization": {"status": "ready (1074 files)"}}
```

## Implementation Checklist

- [ ] Use persistent volume for initialized data
- [ ] Implement non-blocking initialization with `asyncio.create_task()`
- [ ] Add initialization status to health endpoint
- [ ] Handle initialization failures gracefully
- [ ] Test first deployment (initialization from scratch)
- [ ] Test subsequent deployments (using existing data)
- [ ] Document expected initialization time
- [ ] Consider partial functionality during initialization

## Anti-Patterns to Avoid

1. **Blocking on startup**: Don't wait for initialization in lifespan/startup
2. **Using ephemeral paths**: Don't initialize to `/tmp` or container filesystem
3. **Hiding status**: Always expose initialization progress in health/status endpoints
4. **Failing on partial data**: Design service to work with incomplete data when possible
5. **Re-initializing unnecessarily**: Always check if data already exists

## Real-World Example: KB Service

The KB service implements this pattern with learnings:
- **Problem**: 1074+ file Git repository (1GB) took 2-3 minutes to clone
- **Initial Solution**: Deferred clone with asyncio.create_task() 
- **Issue**: Background task didn't execute reliably
- **Final Solution**: Manual trigger endpoint + persistent volume (3GB)
- **Result**: Service starts instantly, clone triggered on demand
- **Benefit**: Observable, debuggable, reliable

**Key Learning**: Sometimes "deferred" means "on-demand" rather than "automatic in background"

```python
# From kb_startup.py
async def initialize_kb_repository():
    kb_path = Path(getattr(settings, 'KB_PATH', '/kb'))
    
    # Always ensure directory exists
    kb_path.mkdir(parents=True, exist_ok=True)
    
    # Check if already cloned
    if (kb_path / '.git').exists():
        file_count = sum(1 for _ in kb_path.rglob("*") if _.is_file())
        logger.info(f"Repository exists with {file_count} files")
        return True
    
    # Schedule background clone
    logger.info("Scheduling background git clone...")
    asyncio.create_task(_background_clone())
    
    return True  # Start immediately
```

This pattern transformed a blocking 3-minute startup into instant availability with background initialization.