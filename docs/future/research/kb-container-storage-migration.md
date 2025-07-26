# KB Container Storage Migration Guide

## Overview

As of July 2025, the KB service has migrated from local volume mounts to container-only storage for true local-remote parity. This ensures that local Docker testing accurately reflects production behavior.

## What Changed

### Before (Volume Mount)
```yaml
kb-service:
  volumes:
    - ./kb-data:/kb:rw  # Local directory mounted to container
```
- KB data persisted on host machine
- Local edits immediately visible in container
- Different behavior from production

### After (Container-Only)
```yaml
kb-service:
  volumes:
    # NO local KB mount - container storage only
```
- KB data stored only inside container at `/kb`
- Repository cloned fresh on every container start
- Identical behavior in local and production

## Why This Change?

1. **Testing Accuracy**: Local tests now validate exact production behavior
2. **No False Positives**: Eliminates "works on my machine" issues
3. **Simplified Deployment**: No volume management or permissions issues
4. **Consistent Initialization**: Same startup flow everywhere

## Migration Steps

If you were using the old volume mount approach:

### 1. Remove Local KB Directory
```bash
# If you have local changes, push them to Git first!
cd ./kb-data
git add . && git commit -m "Save local changes" && git push

# Then remove the local directory
cd ..
rm -rf ./kb-data
```

### 2. Update docker-compose.yml
Remove the volume mount line:
```yaml
# Remove this line:
- ./kb-data:/kb:rw
```

### 3. Ensure Git Repository Configuration
In `.env`:
```bash
KB_GIT_REPO_URL=https://github.com/your-org/your-kb.git
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxx  # For private repos
KB_GIT_AUTO_CLONE=true
```

### 4. Restart Services
```bash
docker compose down kb-service
docker compose up kb-service
```

## New Workflow

### Daily Development
1. **Edit files** in your actual Git repository (not in Docker)
2. **Commit and push** changes to GitHub/GitLab
3. **Restart KB service** to pull latest changes
4. **Test locally** with confidence it matches production

### Key Differences
- **No more `./kb-data`** directory
- **Edit in your Git repo**, not in Docker volumes
- **Container restarts** required to see changes
- **Ephemeral storage** - data lost on container removal

## Benefits

### For Development
- Catch deployment issues early
- No volume permission problems
- Clean, reproducible environments

### For Testing
- Accurate production simulation
- Consistent initialization testing
- No cached state issues

### For Operations
- Simpler deployment scripts
- No volume management
- Identical behavior everywhere

## Troubleshooting

### "KB path does not exist"
**Normal** - The service creates it and clones the repository on startup.

### "Repository already exists"
**Normal** - On restart, the service detects existing repo and skips re-cloning.

### Need to Force Fresh Clone
```bash
docker compose down kb-service
docker compose up kb-service
# This creates a new container with fresh clone
```

### Viewing KB Contents
```bash
# Check what's in the container
docker compose exec kb-service ls -la /kb/

# View Git status
docker compose exec kb-service git -C /kb status
```

## Summary

This migration ensures that your local Docker environment behaves exactly like production deployments. While it requires adjusting your workflow slightly (editing in Git repos instead of Docker volumes), it provides much more reliable testing and deployment experiences.