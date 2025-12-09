# KB Git Secrets Setup



## Issue Identified
The KB service deployed successfully but never cloned the git repository because the required secrets are missing from the Fly.io deployment.

## Root Cause
- KB startup code checks for `KB_GIT_REPO_URL` and `KB_GIT_AUTH_TOKEN` 
- If `KB_GIT_REPO_URL` is missing, it logs "No KB_GIT_REPO_URL configured, skipping repository initialization"
- Local .env has the values but they were never set as Fly.io secrets

## Solution Commands

### Set the Missing Secrets
```bash
fly secrets set \
  KB_GIT_REPO_URL="https://github.com/Aeonia-ai/Obsidian-Vault.git" \
  KB_GIT_AUTH_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -a gaia-kb-dev
```

### Redeploy to Trigger Git Clone
```bash
./scripts/deploy.sh --env dev --services kb --remote-only
```

### Verify the Fix
```bash
# Check secrets are set
fly secrets list -a gaia-kb-dev

# Wait for deployment to complete, then check repository
fly ssh console -a gaia-kb-dev --command "ls -la /kb/repository"

# Should show cloned repository with files like:
# drwxr-xr-x  3 root root 4096 Jul 20 20:30 .git
# -rw-r--r--  1 root root 1234 Jul 20 20:30 README.md
# (and 1000+ other files from Obsidian vault)

# Test KB functionality
./scripts/test.sh --url https://gaia-kb-dev.fly.dev search "test query"
```

## Expected Outcome
After setting the secrets and redeploying:
1. KB service will clone the Aeonia Obsidian Vault on startup (1074+ files)
2. Repository will be available at `/kb/repository` 
3. KB search and other operations will work with actual content
4. Service logs will show "Successfully cloned repository with XXXX files"

## Status
- **Blocked by**: Network connectivity issues preventing Fly.io API access
- **Next Action**: Run the secret setup commands when connectivity is restored