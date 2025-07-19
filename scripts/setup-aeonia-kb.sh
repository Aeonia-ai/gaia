#!/bin/bash

# Setup Aeonia KB Git Sync
# 
# This script configures the KB service to sync with the Aeonia Obsidian vault
# Repository: https://github.com/Aeonia-ai/Obsidian-Vault.git

set -e

echo "🔧 Setting up Aeonia KB Git Sync"
echo "================================="
echo "Repository: https://github.com/Aeonia-ai/Obsidian-Vault.git"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run this script from the project root."
    exit 1
fi

# Check if already configured
if grep -q "KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git" .env; then
    echo "✅ Aeonia KB repository already configured in .env"
else
    echo "📝 Adding Aeonia KB repository configuration to .env..."
    
    # Remove any existing KB Git repo URL
    sed -i.bak '/^KB_GIT_REPO_URL=/d' .env 2>/dev/null || true
    sed -i.bak '/^KB_GIT_AUTO_CLONE=/d' .env 2>/dev/null || true
    
    # Add Aeonia-specific configuration
    echo "" >> .env
    echo "# Aeonia KB Git Repository Configuration" >> .env
    echo "KB_GIT_REPO_URL=https://github.com/Aeonia-ai/Obsidian-Vault.git" >> .env
    echo "KB_GIT_AUTO_CLONE=true" >> .env
    
    # Clean up backup
    rm -f .env.bak
    
    echo "✅ Configuration added to .env"
fi

# Prompt for authentication token if repository is private
echo ""
echo "🔐 Authentication Setup"
echo "If the Aeonia repository is private, you'll need a GitHub personal access token."

if grep -q "^KB_GIT_AUTH_TOKEN=" .env; then
    echo "✅ Auth token already configured"
    read -p "Update auth token? (y/n) [n]: " update_token
    update_token=${update_token:-n}
else
    echo "No auth token found in .env"
    update_token="y"
fi

if [ "$update_token" = "y" ]; then
    echo ""
    echo "To create a GitHub token:"
    echo "1. Go to: https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Select scope: 'repo' (for private repos)"
    echo "4. Copy the generated token"
    echo ""
    read -p "Enter GitHub personal access token (or press Enter to skip): " auth_token
    
    if [ -n "$auth_token" ]; then
        # Remove existing token
        sed -i.bak '/^KB_GIT_AUTH_TOKEN=/d' .env 2>/dev/null || true
        echo "KB_GIT_AUTH_TOKEN=$auth_token" >> .env
        rm -f .env.bak
        echo "✅ Auth token configured"
    else
        echo "⚠️  No auth token set - only works if repository is public"
    fi
fi

# Set up storage mode
echo ""
echo "📊 Storage Mode Configuration"
current_mode=$(grep '^KB_STORAGE_MODE=' .env 2>/dev/null | cut -d'=' -f2 || echo 'not set')
echo "Current storage mode: $current_mode"

if [ "$current_mode" != "hybrid" ]; then
    read -p "Enable hybrid mode for Git sync? (y/n) [y]: " enable_hybrid
    enable_hybrid=${enable_hybrid:-y}
    
    if [ "$enable_hybrid" = "y" ]; then
        sed -i.bak 's/^KB_STORAGE_MODE=.*/KB_STORAGE_MODE=hybrid/' .env
        rm -f .env.bak
        echo "✅ Hybrid mode enabled"
        
        echo ""
        echo "📋 Applying database migration for hybrid mode..."
        if docker compose exec db psql -U postgres -d llm_platform < migrations/003_create_kb_tables.sql > /dev/null 2>&1; then
            echo "✅ Database migration applied"
        else
            echo "⚠️  Database migration may have already been applied"
        fi
    fi
fi

echo ""
echo "✅ Aeonia KB Git Sync Setup Complete!"
echo ""
echo "📋 Configuration Summary:"
echo "   • Repository: https://github.com/Aeonia-ai/Obsidian-Vault.git"
echo "   • Storage Mode: $(grep '^KB_STORAGE_MODE=' .env | cut -d'=' -f2)"
echo "   • Auto Sync: $(grep '^KB_GIT_AUTO_SYNC=' .env | cut -d'=' -f2)"
echo "   • Auth Token: $([ -n "$(grep '^KB_GIT_AUTH_TOKEN=' .env 2>/dev/null)" ] && echo 'configured' || echo 'not set')"
echo ""

# Offer to restart services
read -p "🔄 Restart KB service to apply changes? (y/n) [y]: " restart
restart=${restart:-y}

if [ "$restart" = "y" ]; then
    echo "Restarting KB service..."
    docker compose restart kb-service
    echo "✅ KB service restarted"
    
    # Wait and test
    echo "🧪 Testing KB service..."
    sleep 5
    
    if ./scripts/test-kb-git-sync.sh > /dev/null 2>&1; then
        echo "✅ KB service is responding and Git sync is configured"
    else
        echo "⚠️  KB service may still be starting. Run './scripts/test-kb-git-sync.sh' to test."
    fi
fi

echo ""
echo "🎯 Your Daily Workflow:"
echo "   1. Edit files in your local Obsidian vault"
echo "   2. Git commit and push to Aeonia-ai/Obsidian-Vault"
echo "   3. KB service auto-syncs within 1 hour"
echo "   4. AI agents access your latest knowledge immediately"
echo ""
echo "🔧 Manual Commands:"
echo "   • Test sync: ./scripts/test-kb-git-sync.sh"
echo "   • Force sync: curl -X POST -H 'X-API-Key: \$API_KEY' http://kb-service:8000/sync/from-git"
echo "   • Check status: curl -H 'X-API-Key: \$API_KEY' http://kb-service:8000/sync/status"