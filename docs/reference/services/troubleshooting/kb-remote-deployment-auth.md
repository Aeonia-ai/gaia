# KB Remote Deployment Authentication Guide

This guide covers how to handle Git authentication for KB sync in remote deployments (Fly.io, AWS, etc.).

## Authentication Challenge

**Local Development**: Uses SSH keys, stored credentials, or GitHub CLI
**Remote Containers**: Have no access to your local authentication

## Solution: Personal Access Tokens

### 1. GitHub Personal Access Token (Recommended)

**Create Token:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories)
4. Copy the generated token

**Configure for Remote Deployment:**
```bash
# In your deployment environment
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. Platform-Specific Token Authentication

The KB service automatically handles different Git platforms:

```bash
# GitHub
https://token@github.com/Aeonia-ai/Obsidian-Vault.git

# GitLab  
https://oauth2:token@gitlab.com/user/repo.git

# Bitbucket
https://x-token-auth:token@bitbucket.org/user/repo.git
```

## Remote Deployment Scenarios

### Fly.io Deployment

**Set Secrets:**
```bash
# Set the Git authentication token as a Fly.io secret
fly secrets set KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx -a gaia-kb-dev

# Set repository URL
fly secrets set KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git -a gaia-kb-dev

# Enable Git sync
fly secrets set KB_STORAGE_MODE=hybrid -a gaia-kb-dev
fly secrets set KB_GIT_AUTO_SYNC=true -a gaia-kb-dev
```

**Deployment Flow:**
1. Container starts with empty `/kb` directory
2. KB service reads `KB_GIT_REPO_URL` and `KB_GIT_AUTH_TOKEN`
3. Automatically clones repository using token authentication
4. Sets up Git remote with authenticated URL
5. Starts automatic sync monitoring

### AWS/Docker Deployment

**Environment Variables:**
```bash
# Docker Compose
environment:
  - KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git
  - KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - KB_STORAGE_MODE=hybrid
  - KB_GIT_AUTO_SYNC=true

# Or via .env file
echo "KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> .env
```

**AWS Secrets Manager Integration:**
```python
# Optional: Load from AWS Secrets Manager
import boto3

def get_github_token():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='gaia/github-token')
    return response['SecretString']

# In KB service startup
if not settings.KB_GIT_AUTH_TOKEN and 'AWS' in environment:
    settings.KB_GIT_AUTH_TOKEN = get_github_token()
```

## Security Best Practices

### 1. Token Permissions
**Minimal Scope:**
- For public repos: `public_repo` scope only
- For private repos: `repo` scope only
- **Never** use tokens with admin or delete permissions

### 2. Token Rotation
```bash
# Rotate tokens every 90 days
# Create new token → Update deployment secrets → Delete old token

# Fly.io example
fly secrets set KB_GIT_AUTH_TOKEN=new_token_here -a gaia-kb-dev
```

### 3. Environment Isolation
```bash
# Different tokens for different environments
KB_GIT_AUTH_TOKEN_DEV=ghp_dev_token_here
KB_GIT_AUTH_TOKEN_STAGING=ghp_staging_token_here  
KB_GIT_AUTH_TOKEN_PROD=ghp_prod_token_here
```

### 4. Secret Detection Prevention
```bash
# ✅ GOOD: Environment variable
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ❌ BAD: Hardcoded in code
git_token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # NEVER DO THIS

# ❌ BAD: In version control
git commit -m "Add GitHub token: ghp_xxxxx"  # NEVER COMMIT TOKENS
```

## Alternative Authentication Methods

### 1. GitHub App Authentication (Advanced)
```python
# For organizations with high security requirements
class GitHubAppAuth:
    def __init__(self, app_id, private_key):
        self.app_id = app_id
        self.private_key = private_key
    
    async def get_installation_token(self, installation_id):
        # Generate JWT, request installation token
        # More secure than personal access tokens
        pass
```

### 2. Deploy Keys (Repository-Specific)
```bash
# Generate deploy key pair
ssh-keygen -t ed25519 -f kb_deploy_key -C "kb-service@gaia.dev"

# Add public key to GitHub repository settings
# Use private key in container (more complex setup)
```

### 3. Machine User Account
```bash
# Create dedicated GitHub user for automation
# Invite to organization with minimal permissions
# Use that user's personal access token
```

## Deployment Configuration Examples

### Complete Fly.io Setup
```bash
# 1. Set all required secrets
fly secrets set \
  KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git \
  KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  KB_STORAGE_MODE=hybrid \
  KB_GIT_AUTO_SYNC=true \
  KB_SYNC_INTERVAL=3600 \
  -a gaia-kb-dev

# 2. Deploy
fly deploy -a gaia-kb-dev

# 3. Monitor logs for successful clone
fly logs -a gaia-kb-dev | grep "Git repository initialized"
```

### Complete Docker Compose Setup
```yaml
# docker compose.yml
services:
  kb-service:
    build: .
    environment:
      - KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git
      - KB_GIT_AUTH_TOKEN=${KB_GIT_AUTH_TOKEN}
      - KB_STORAGE_MODE=hybrid
    env_file:
      - .env.production  # Contains sensitive tokens
```

## Troubleshooting Remote Authentication

### Common Issues

#### 1. "Authentication failed"
```bash
# Check token validity
curl -H "Authorization: token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  https://api.github.com/user

# Expected: {"login": "your-username", ...}
# Error: {"message": "Bad credentials"}
```

#### 2. "Repository not found" 
```bash
# Check repository access
curl -H "Authorization: token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  https://api.github.com/repos/Aeonia-ai/Obsidian-Vault

# If private repo, ensure token has 'repo' scope
```

#### 3. "Permission denied"
```bash
# Check if token can access repository
# For organization repos, may need organization approval
```

### Debugging Commands

```bash
# Test Git clone with token (in container)
git clone https://ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx@github.com/Aeonia-ai/Obsidian-Vault.git /tmp/test

# Check KB service logs
docker compose logs kb-service | grep -i git
fly logs -a gaia-kb-dev | grep -i "git\|clone\|auth"

# Test sync endpoints
curl -H "X-API-Key: $API_KEY" http://kb-service:8000/sync/status
```

## Token Management Automation

### Automated Token Rotation
```bash
#!/bin/bash
# scripts/rotate-github-token.sh

NEW_TOKEN=$(gh auth token)  # Get new token from GitHub CLI
OLD_TOKEN_LAST_4=$(echo $KB_GIT_AUTH_TOKEN | tail -c 5)

# Update deployment
fly secrets set KB_GIT_AUTH_TOKEN=$NEW_TOKEN -a gaia-kb-dev

# Verify deployment
sleep 30
if curl -s http://kb-service:8000/health | grep -q "healthy"; then
    echo "✅ Token rotation successful"
    # Revoke old token via GitHub API
else
    echo "❌ Token rotation failed"
    # Rollback
fi
```

## Summary: Remote Deployment Best Practices

1. **Use Personal Access Tokens** for authentication
2. **Store tokens in environment variables** or secrets management
3. **Use minimal token permissions** (public_repo/repo only)
4. **Rotate tokens regularly** (every 90 days)
5. **Monitor authentication in logs** during deployment
6. **Test token validity** before deployment
7. **Use different tokens** for different environments
8. **Never commit tokens** to version control

With proper token authentication, the KB service will seamlessly clone and sync your repository in any remote deployment environment.