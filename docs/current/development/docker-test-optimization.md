# Docker Test Container Optimization Guide

**Created**: July 28, 2025  
**Purpose**: Optimize Docker test builds with proper caching and handle timeout limitations

## Overview

The Gaia test container includes heavyweight dependencies like Playwright and Chromium for browser testing. Without proper optimization, builds can take 5-15 minutes. This guide shows how to optimize builds to under 1 minute for code changes.

## Build Time Optimization

### Layer Caching Strategy

The `Dockerfile.test` is structured to maximize Docker's layer caching:

```dockerfile
# Base requirements (rarely changes) - CACHED after first build
RUN pip install --no-cache-dir -r requirements.txt

# Test-specific dependencies (changes occasionally) - CACHED
RUN pip install --no-cache-dir \
    requests \
    pytest-playwright \
    playwright

# Web test dependencies (newer additions) - CACHED
RUN pip install --no-cache-dir \
    "python-fasthtml>=0.1.0" \
    "httpx>=0.25.0" \
    "websockets>=12.0" \
    "python-multipart>=0.0.6"

# Playwright browsers (most expensive - 280MB+) - CACHED
RUN playwright install --with-deps chromium

# Application code (changes frequently) - REBUILDS
COPY . .
```

### Build Performance

With proper caching:
- **Initial build**: 2-5 minutes (downloads all dependencies)
- **Code changes only**: 30-50 seconds (only COPY step rebuilds)
- **Adding pip packages**: 1-2 minutes (rebuilds from that layer forward)
- **Requirements.txt changes**: 2-5 minutes (rebuilds all pip installs)

## Handling Build Timeouts

### Problem

Claude Code and other CI environments may have command timeouts (e.g., 2 minutes). The initial Docker build with Playwright can exceed this limit.

### Solution: Background Builds

Use `nohup` to run builds in the background:

```bash
# Start build in background
nohup docker compose build test > /tmp/docker-build.log 2>&1 & 
echo "Build started in background with PID $!"

# Monitor progress
tail -f /tmp/docker-build.log

# Check if still running
ps aux | grep $!
```

### Why This Works

- The `nohup` command prevents the process from terminating when the shell exits
- Output is redirected to a log file for monitoring
- The build continues even if the terminal session times out
- You can check progress anytime by reading the log file

## Build Optimization Tips

### 1. Use .dockerignore

Create a `.dockerignore` to exclude unnecessary files:

```
.venv/
venv/
__pycache__/
*.pyc
.git/
.pytest_cache/
htmlcov/
.coverage
*.log
```

This reduces the context size for the COPY step.

### 2. Separate Dockerfile Layers

Keep frequently changing items (like application code) at the bottom of the Dockerfile.

### 3. Use BuildKit

Enable Docker BuildKit for better caching and parallel builds:

```bash
DOCKER_BUILDKIT=1 docker compose build test
```

### 4. Clean Up Old Images

Remove old test images to save disk space:

```bash
docker images | grep gaia-test | grep -v latest | awk '{print $3}' | xargs docker rmi
```

## Troubleshooting

### Build Stuck on COPY

If the build appears stuck on `COPY . .`:
- Check directory size: `du -sh .`
- Look for large files: `find . -size +10M`
- Ensure .dockerignore is working: `docker build --no-cache -f Dockerfile.test .`

### Cache Not Working

If builds aren't using cache:
- Check if Dockerfile was modified (invalidates cache from that line)
- Ensure consistent line endings (CRLF vs LF)
- Use `docker history gaia-test` to inspect layers

### Playwright Installation Fails

Common issues:
- Insufficient disk space (needs ~500MB for browsers)
- Network timeouts (retry the build)
- Architecture mismatch (ensure correct platform)

## Example Build Session

```bash
# First build (no cache)
$ time docker compose build test
...installing all dependencies...
real    2m 35s

# Make a code change
$ echo "# comment" >> app/main.py

# Rebuild (with cache)  
$ time docker compose build test
...
#7 CACHED
#8 CACHED
#9 CACHED
#10 CACHED  # Playwright still cached!
#11 [10/10] COPY . .
#11 DONE 30.9s
...
real    0m 47s  # Much faster!
```

## Best Practices

1. **Run builds in background** for initial setup or CI environments with timeouts
2. **Structure Dockerfile** with stable dependencies first
3. **Use .dockerignore** to minimize context size
4. **Monitor disk space** - test images can be 2-3GB each
5. **Clean up regularly** - remove old test images
6. **Document heavy dependencies** like Playwright in your README

## Related Documentation

- [Testing and Quality Assurance Guide](testing-and-quality-assurance.md)
- [Command Reference](command-reference.md)
- [Development Environment Setup](dev-environment-setup.md)