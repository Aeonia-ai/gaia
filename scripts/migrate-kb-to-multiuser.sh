#!/bin/bash
# Migrate existing KB content to multi-user structure
# This script moves existing KB content to Jason's namespace

set -e

echo "🚀 KB Multi-User Migration Script"
echo "================================="

# Jason's user ID from the database
JASON_USER_ID="e3a5ca05-d65c-416c-8b9b-5b3eaca8559b"

# Source and target paths
SOURCE_PATH="/kb"
TARGET_PATH="/kb/users/${JASON_USER_ID}"

echo "📋 Migration Plan:"
echo "  Source: ${SOURCE_PATH}/"
echo "  Target: ${TARGET_PATH}/"
echo ""

# Function to migrate content in Docker container
migrate_in_container() {
    echo "🔄 Migrating KB content in container..."
    
    # Create backup first
    docker compose exec kb-service bash -c "
        set -e
        
        # Create backup
        echo '📦 Creating backup...'
        if [ -d ${SOURCE_PATH} ]; then
            cp -r ${SOURCE_PATH} ${SOURCE_PATH}.backup-\$(date +%Y%m%d-%H%M%S)
            echo '✓ Backup created'
        fi
        
        # Create user namespace directory
        echo '📁 Creating user namespace...'
        mkdir -p ${TARGET_PATH}
        
        # Get list of items to migrate (exclude special directories)
        echo '🔍 Analyzing content to migrate...'
        cd ${SOURCE_PATH}
        
        # Count items
        TOTAL_ITEMS=0
        for item in *; do
            if [[ \"\$item\" != \"users\" && \"\$item\" != \"teams\" && \"\$item\" != \"workspaces\" && \"\$item\" != \"shared\" && \"\$item\" != \"public\" && -e \"\$item\" ]]; then
                ((TOTAL_ITEMS++))
            fi
        done
        
        echo \"📊 Found \$TOTAL_ITEMS items to migrate\"
        
        # Migrate each item
        MIGRATED=0
        for item in *; do
            # Skip special multi-user directories
            if [[ \"\$item\" == \"users\" || \"\$item\" == \"teams\" || \"\$item\" == \"workspaces\" || \"\$item\" == \"shared\" || \"\$item\" == \"public\" ]]; then
                echo \"⏭️  Skipping multi-user directory: \$item\"
                continue
            fi
            
            # Skip if not exists (handles empty glob)
            if [ ! -e \"\$item\" ]; then
                continue
            fi
            
            # Move the item
            if [ -e \"${TARGET_PATH}/\$item\" ]; then
                echo \"⚠️  Already exists in target: \$item (skipping)\"
            else
                echo \"📦 Moving: \$item -> ${TARGET_PATH}/\$item\"
                mv \"\$item\" \"${TARGET_PATH}/\"
                ((MIGRATED++))
            fi
        done
        
        echo \"\"
        echo \"✅ Migration complete!\"
        echo \"   Items migrated: \$MIGRATED\"
        echo \"   Target location: ${TARGET_PATH}\"
        
        # Create standard multi-user directories if they don't exist
        echo \"\"
        echo \"📁 Setting up multi-user directory structure...\"
        mkdir -p ${SOURCE_PATH}/users
        mkdir -p ${SOURCE_PATH}/teams
        mkdir -p ${SOURCE_PATH}/workspaces
        mkdir -p ${SOURCE_PATH}/shared
        mkdir -p ${SOURCE_PATH}/public
        
        # Create README files
        echo '# User Namespaces' > ${SOURCE_PATH}/users/README.md
        echo 'Private user knowledge bases. Each user has full control over their namespace.' >> ${SOURCE_PATH}/users/README.md
        
        echo '# Team Spaces' > ${SOURCE_PATH}/teams/README.md
        echo 'Collaborative knowledge bases for teams.' >> ${SOURCE_PATH}/teams/README.md
        
        echo '# Workspaces' > ${SOURCE_PATH}/workspaces/README.md
        echo 'Project-specific temporary collaboration spaces.' >> ${SOURCE_PATH}/workspaces/README.md
        
        echo '# Shared Content' > ${SOURCE_PATH}/shared/README.md
        echo 'Organization-wide shared knowledge. All authenticated users can read.' >> ${SOURCE_PATH}/shared/README.md
        
        echo '# Public Content' > ${SOURCE_PATH}/public/README.md
        echo 'Publicly accessible knowledge base content.' >> ${SOURCE_PATH}/public/README.md
        
        echo \"✓ Multi-user directory structure created\"
        
        # Show final structure
        echo \"\"
        echo \"📊 Final KB structure:\"
        ls -la ${SOURCE_PATH}/
    "
}

# Function to update Git if using Git storage
update_git() {
    echo ""
    echo "📝 Updating Git repository..."
    
    docker compose exec kb-service bash -c "
        cd ${SOURCE_PATH}
        
        # Check if it's a git repo
        if [ -d .git ]; then
            echo '✓ Git repository detected'
            
            # Create a feature branch
            BRANCH_NAME='feature/multiuser-structure'
            echo \"🌿 Creating branch: \$BRANCH_NAME\"
            git checkout -b \$BRANCH_NAME
            
            # Add and commit changes
            git add -A
            git commit -m 'Migrate KB to multi-user structure
            
            - Moved existing content to Jason'\''s namespace (${TARGET_PATH})
            - Created multi-user directory structure
            - Added README files for each namespace type
            
            This preserves all existing content under the original author'\''s account.'
            
            echo '✓ Changes committed to Git'
            
            # Push to remote branch
            echo '📤 Pushing to remote branch...'
            git push -u origin \$BRANCH_NAME
            
            echo '✓ Branch pushed to remote'
            echo ''
            echo '🔗 Next steps:'
            echo '   1. Review changes at: https://github.com/Aeonia-ai/Obsidian-Vault/compare/\$BRANCH_NAME'
            echo '   2. Create a Pull Request when ready'
            echo '   3. Merge to main after review'
        else
            echo '⚠️  Not a Git repository - skipping Git update'
        fi
    "
}

# Main execution
echo "🔍 Checking current KB structure..."
docker compose exec kb-service ls -la ${SOURCE_PATH}/ || true

echo ""
read -p "⚠️  This will reorganize the KB for multi-user mode. Continue? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    migrate_in_container
    update_git
    
    echo ""
    echo "🎉 Migration complete!"
    echo ""
    echo "📋 Summary:"
    echo "  • Existing content moved to: ${TARGET_PATH}/"
    echo "  • Multi-user directories created in: ${SOURCE_PATH}/"
    echo "  • Jason (jason@aeonia.ai) owns all migrated content"
    echo ""
    echo "🔗 Next steps:"
    echo "  1. Restart KB service to ensure all changes are loaded"
    echo "  2. Test access with different user accounts"
    echo "  3. Update web UI to support user namespace switching"
    echo ""
    echo "📊 User namespaces:"
    echo "  • Jason: /kb/users/e3a5ca05-d65c-416c-8b9b-5b3eaca8559b/"
    echo "  • Alice: /kb/users/07d45546-5031-4d4a-9198-24e9e0909cfb/"
    echo "  • Bob:   /kb/users/2fcc817b-e691-47ff-9b56-08717c6c6cd2/"
else
    echo "❌ Migration cancelled"
fi