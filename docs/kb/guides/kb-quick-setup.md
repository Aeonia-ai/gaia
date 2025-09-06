# KB Service Quick Setup

## Aeonia Team Setup (Obsidian Vault)

### 1. Add to `.env`:
```bash
KB_STORAGE_MODE=hybrid
KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your token
KB_GIT_AUTO_CLONE=true
```

### 2. Start the Service:
```bash
docker compose up kb-service
# Service automatically clones your repository on startup
```

### 3. Access Your KB:
```bash
# Check repository inside container:
docker compose exec kb-service ls -la /kb/

# Test search:
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "gaia"}' \
  http://localhost:8666/api/v0.2/kb/search
```

## GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens/new
2. Name: "KB Service - Obsidian Vault"
3. Expiration: 90 days
4. Scopes: ✅ `repo` (for private) or `public_repo` (for public)
5. Generate and copy token
6. Add to `.env` as `KB_GIT_AUTH_TOKEN`

## Troubleshooting

### Git Not Found
```bash
docker compose build kb-service --no-cache
```

### Volume Mount Error
```bash
# Update docker compose.yml:
volumes:
  - ./kb-data:/kb:rw
```

### Test Authentication
```bash
docker compose exec kb-service \
  git clone https://TOKEN@github.com/Aeonia-ai/Obsidian-Vault.git /tmp/test
```

## Daily Workflow

1. **Edit in your Git repository**: `~/your-obsidian-vault/your-file.md`
2. **Commit & push**: 
   ```bash
   cd ~/your-obsidian-vault
   git add . && git commit -m "Update" && git push
   ```
3. **Restart KB service**: `docker compose restart kb-service`
4. **AI agents** see latest content after restart

## Full Documentation

See [KB Git Sync Guide](kb-git-sync-guide.md) for complete details.