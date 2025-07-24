#!/bin/bash

# Setup KB Git Repository Configuration
# 
# This script helps configure the KB service to sync with your Git repository.
# It prompts for repository URL and sets up the environment variables.

set -e

echo "🔧 KB Git Repository Setup"
echo "=========================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run this script from the project root."
    exit 1
fi

echo "This script will configure KB Git sync to pull from your repository."
echo ""

# Prompt for repository URL
read -p "📦 Enter your KB Git repository URL (e.g., https://github.com/user/kb.git): " repo_url

if [ -z "$repo_url" ]; then
    echo "❌ Repository URL is required"
    exit 1
fi

# Prompt for authentication if needed
echo ""
echo "🔐 Authentication Setup"
echo "If your repository is private, you'll need a personal access token."
echo "For GitHub: Settings → Developer settings → Personal access tokens"
echo ""
read -p "Enter GitHub personal access token (leave empty for public repos): " auth_token

# Prompt for other settings
echo ""
echo "⚙️ Sync Configuration"
read -p "Auto-sync from Git every hour? (y/n) [y]: " auto_sync
auto_sync=${auto_sync:-y}

read -p "Git branch to sync from [main]: " git_branch
git_branch=${git_branch:-main}

# Update .env file
echo ""
echo "📝 Updating .env configuration..."

# Remove existing KB Git settings if they exist
sed -i.bak '/^KB_GIT_REPO_URL=/d' .env 2>/dev/null || true
sed -i.bak '/^KB_GIT_AUTH_TOKEN=/d' .env 2>/dev/null || true
sed -i.bak '/^KB_GIT_AUTO_CLONE=/d' .env 2>/dev/null || true

# Add new settings to .env
echo "" >> .env
echo "# KB Git Repository Configuration (added by setup script)" >> .env
echo "KB_GIT_REPO_URL=$repo_url" >> .env

if [ -n "$auth_token" ]; then
    echo "KB_GIT_AUTH_TOKEN=$auth_token" >> .env
fi

echo "KB_GIT_AUTO_CLONE=true" >> .env

# Update existing settings
if grep -q "^KB_GIT_AUTO_SYNC=" .env; then
    if [ "$auto_sync" = "y" ]; then
        sed -i.bak 's/^KB_GIT_AUTO_SYNC=.*/KB_GIT_AUTO_SYNC=true/' .env
    else
        sed -i.bak 's/^KB_GIT_AUTO_SYNC=.*/KB_GIT_AUTO_SYNC=false/' .env
    fi
else
    echo "KB_GIT_AUTO_SYNC=$([ "$auto_sync" = "y" ] && echo "true" || echo "false")" >> .env
fi

if grep -q "^KB_GIT_BRANCH=" .env; then
    sed -i.bak "s/^KB_GIT_BRANCH=.*/KB_GIT_BRANCH=$git_branch/" .env
else
    echo "KB_GIT_BRANCH=$git_branch" >> .env
fi

# Clean up backup file
rm -f .env.bak

echo ""
echo "✅ Configuration complete!"
echo ""
echo "📋 Settings applied:"
echo "   Repository URL: $repo_url"
echo "   Branch: $git_branch"
echo "   Auto-sync: $([ "$auto_sync" = "y" ] && echo "enabled" || echo "disabled")"
echo "   Auth token: $([ -n "$auth_token" ] && echo "configured" || echo "not needed")"
echo ""
echo "🚀 Next steps:"
echo "   1. Set KB_STORAGE_MODE=hybrid in .env (for full Git sync)"
echo "   2. Restart KB service: docker compose restart kb-service"
echo "   3. Test sync: ./scripts/test-kb-git-sync.sh"
echo ""
echo "📖 Your daily workflow:"
echo "   • Edit KB files locally"
echo "   • git commit && git push"
echo "   • KB service auto-syncs within 1 hour"
echo "   • Or manual sync: curl -X POST http://kb-service:8000/sync/from-git"
echo ""

# Offer to restart services
read -p "🔄 Restart KB service now to apply changes? (y/n) [y]: " restart
restart=${restart:-y}

if [ "$restart" = "y" ]; then
    echo "Restarting KB service..."
    docker compose restart kb-service
    echo "✅ KB service restarted"
    
    # Wait a moment and test
    echo "🧪 Testing configuration..."
    sleep 3
    
    if ./scripts/test-kb-git-sync.sh > /dev/null 2>&1; then
        echo "✅ KB service is responding"
    else
        echo "⚠️  KB service may still be starting. Run './scripts/test-kb-git-sync.sh' to test."
    fi
fi

echo ""
echo "🎯 Setup complete! Your KB is now configured to sync with Git."