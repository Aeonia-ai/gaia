# KB Remote Hosting Strategy



## Overview
Strategy for hosting Knowledge Base content in production environments while maintaining security, performance, and ease of updates.

## Recommended Approach: Git + Caching

### 1. Primary Storage: Private Git Repository
- Create private repository: `github.com/aeonia/aeonia-kb`
- Use GitHub Actions for validation
- Deploy keys for read-only access
- Webhook triggers for updates

### 2. Deployment Configuration

#### Environment Variables
```bash
# Production secrets
KB_GIT_URL=https://github.com/aeonia/aeonia-kb.git
KB_GIT_TOKEN=ghp_xxxxxxxxxxxxx  # Read-only deploy token
KB_SYNC_INTERVAL=300  # Sync every 5 minutes
KB_CACHE_TTL=3600     # Cache for 1 hour
```

#### Docker Implementation
```dockerfile
# Dockerfile.kb (production)
FROM python:3.11-slim

# Install git for KB sync
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ripgrep \
    && apt-get clean

# Create KB directory
RUN mkdir -p /kb

# Add sync script
COPY scripts/sync-kb.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/sync-kb.sh

# Set up cron for periodic sync (optional)
RUN echo "*/5 * * * * /usr/local/bin/sync-kb.sh" | crontab -

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Initial KB sync on startup
ENTRYPOINT ["/usr/local/bin/sync-kb.sh", "&&", "uvicorn", "app.services.kb.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Sync Script
```bash
#!/bin/bash
# scripts/sync-kb.sh

KB_DIR="/kb"
LOCK_FILE="/tmp/kb-sync.lock"

# Prevent concurrent syncs
if [ -f "$LOCK_FILE" ]; then
    echo "KB sync already in progress"
    exit 0
fi

touch "$LOCK_FILE"

# Clone or update KB
if [ -d "$KB_DIR/.git" ]; then
    cd "$KB_DIR"
    git pull origin main --quiet
else
    git clone --depth 1 "$KB_GIT_URL" "$KB_DIR"
fi

# Update cache invalidation timestamp
date +%s > "$KB_DIR/.last-sync"

rm -f "$LOCK_FILE"
```

### 3. Performance Optimization

#### Redis Caching Layer
```python
# app/services/kb/kb_cache.py
import hashlib
from typing import Optional, Dict, Any
from app.shared.redis_client import redis_client

class KBCache:
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.prefix = "kb:cache:"
    
    async def get_search_results(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached search results"""
        key = f"{self.prefix}search:{hashlib.md5(query.encode()).hexdigest()}"
        return await redis_client.get_json(key)
    
    async def set_search_results(self, query: str, results: Dict[str, Any]):
        """Cache search results"""
        key = f"{self.prefix}search:{hashlib.md5(query.encode()).hexdigest()}"
        await redis_client.set_json(key, results, ex=self.ttl)
    
    async def get_file_content(self, path: str) -> Optional[str]:
        """Get cached file content"""
        key = f"{self.prefix}file:{path}"
        return await redis_client.get(key)
    
    async def set_file_content(self, path: str, content: str):
        """Cache file content"""
        key = f"{self.prefix}file:{path}"
        await redis_client.set(key, content, ex=self.ttl)
```

### 4. Platform-Specific Configurations

#### Fly.io Deployment
```toml
# fly.toml
[env]
  KB_GIT_URL = "https://github.com/aeonia/aeonia-kb.git"
  KB_SYNC_INTERVAL = "300"

[secrets]
  KB_GIT_TOKEN = "ghp_xxxxxxxxxxxxx"

# Optional: Persistent volume for KB cache
[[mounts]]
  source = "kb_cache"
  destination = "/kb_cache"
  processes = ["kb"]
```

#### AWS ECS/Fargate
```json
{
  "taskDefinition": {
    "volumes": [{
      "name": "kb-efs",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-12345678",
        "rootDirectory": "/kb"
      }
    }],
    "containerDefinitions": [{
      "name": "kb-service",
      "mountPoints": [{
        "sourceVolume": "kb-efs",
        "containerPath": "/kb"
      }]
    }]
  }
}
```

### 5. Security Considerations

1. **Access Control**
   - Use read-only deploy tokens
   - Rotate tokens regularly
   - Audit access logs

2. **Content Protection**
   - Encrypt sensitive KB content
   - Use signed URLs for assets
   - Implement rate limiting

3. **Network Security**
   - KB service only accessible internally
   - TLS for all Git operations
   - VPC/private networking

### 6. Update Workflow

1. **Development**: Edit KB locally
2. **Commit**: Push changes to Git
3. **CI/CD**: Validate KB structure
4. **Deploy**: Trigger KB sync on services
5. **Cache**: Invalidate affected caches

### 7. Monitoring

- Track sync success/failure
- Monitor cache hit rates
- Alert on sync delays
- Log KB access patterns

## Alternative Approaches

### For Large Binary Assets
Use S3 + CloudFront:
```python
# Hybrid approach
if file_size > 10_000_000:  # 10MB
    return redirect(f"https://cdn.aeonia.com/kb/{file_path}")
else:
    return read_from_git(file_path)
```

### For Frequently Updated Content
Use streaming updates:
```python
# WebSocket for real-time KB updates
async def kb_updates_websocket(websocket):
    await manager.connect(websocket)
    while True:
        update = await kb_update_queue.get()
        await websocket.send_json(update)
```

## Implementation Checklist

- [ ] Create private KB repository
- [ ] Set up deploy keys/tokens
- [ ] Implement sync script
- [ ] Add Redis caching layer
- [ ] Configure platform-specific storage
- [ ] Set up monitoring/alerts
- [ ] Document update procedures
- [ ] Test failover scenarios