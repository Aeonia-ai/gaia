#!/bin/bash

# Extract LLM Platform Components Script
# This script helps extract and adapt components from the LLM Platform

set -e

echo "🔄 Extracting components from LLM Platform..."

LLM_PLATFORM_PATH="/Users/jasbahr/Development/Aeonia/server/llm-platform"
GAIA_PATH="/Users/jasbahr/Development/Aeonia/server/gaia"

# Check if LLM Platform exists
if [ ! -d "$LLM_PLATFORM_PATH" ]; then
    echo "❌ Error: LLM Platform not found at $LLM_PLATFORM_PATH"
    exit 1
fi

echo "📋 Available extraction tasks:"
echo "1. Extract Asset Service components"
echo "2. Extract Chat Service components" 
echo "3. Extract shared utilities"
echo "4. Extract database models"
echo "5. Extract all components"
echo ""
read -p "Select task (1-5): " task

extract_asset_service() {
    echo "📦 Extracting Asset Service components..."
    
    # Create asset service directory if it doesn't exist
    mkdir -p "$GAIA_PATH/app/services/asset"
    
    # Copy asset API endpoints
    if [ -d "$LLM_PLATFORM_PATH/app/api/v1/assets" ]; then
        echo "  - Copying asset API endpoints..."
        cp -r "$LLM_PLATFORM_PATH/app/api/v1/assets/"* "$GAIA_PATH/app/services/asset/" 2>/dev/null || true
    fi
    
    # Copy asset service logic
    if [ -d "$LLM_PLATFORM_PATH/app/services/assets" ]; then
        echo "  - Copying asset service logic..."
        cp -r "$LLM_PLATFORM_PATH/app/services/assets/"* "$GAIA_PATH/app/services/asset/" 2>/dev/null || true
    fi
    
    # Copy asset models
    if [ -d "$LLM_PLATFORM_PATH/app/models/assets" ]; then
        echo "  - Copying asset models..."
        mkdir -p "$GAIA_PATH/app/services/asset/models"
        cp -r "$LLM_PLATFORM_PATH/app/models/assets/"* "$GAIA_PATH/app/services/asset/models/" 2>/dev/null || true
    fi
    
    # Create __init__.py if it doesn't exist
    if [ ! -f "$GAIA_PATH/app/services/asset/__init__.py" ]; then
        touch "$GAIA_PATH/app/services/asset/__init__.py"
    fi
    
    echo "✅ Asset Service components extracted"
}

extract_chat_service() {
    echo "💬 Extracting Chat Service components..."
    
    # Copy chat endpoints
    if [ -f "$LLM_PLATFORM_PATH/app/api/v1/endpoints/chat.py" ]; then
        echo "  - Copying chat endpoints..."
        cp "$LLM_PLATFORM_PATH/app/api/v1/endpoints/chat.py" "$GAIA_PATH/app/services/chat/"
    fi
    
    if [ -f "$LLM_PLATFORM_PATH/app/api/v1/endpoints/personas.py" ]; then
        echo "  - Copying persona endpoints..."
        cp "$LLM_PLATFORM_PATH/app/api/v1/endpoints/personas.py" "$GAIA_PATH/app/services/chat/"
    fi
    
    # Copy MCP and tool provider
    if [ -d "$LLM_PLATFORM_PATH/app/services/mcp" ]; then
        echo "  - Copying MCP components..."
        cp -r "$LLM_PLATFORM_PATH/app/services/mcp" "$GAIA_PATH/app/services/chat/"
    fi
    
    if [ -f "$LLM_PLATFORM_PATH/app/core/tool_provider.py" ]; then
        echo "  - Copying tool provider..."
        cp "$LLM_PLATFORM_PATH/app/core/tool_provider.py" "$GAIA_PATH/app/services/chat/"
    fi
    
    echo "✅ Chat Service components extracted"
}

extract_shared_utilities() {
    echo "🔧 Extracting shared utilities..."
    
    # Copy useful utilities that aren't already in shared
    if [ -f "$LLM_PLATFORM_PATH/app/core/prompt_manager.py" ]; then
        echo "  - Copying prompt manager..."
        cp "$LLM_PLATFORM_PATH/app/core/prompt_manager.py" "$GAIA_PATH/app/shared/"
    fi
    
    if [ -d "$LLM_PLATFORM_PATH/app/core/prompts" ]; then
        echo "  - Copying prompts..."
        cp -r "$LLM_PLATFORM_PATH/app/core/prompts" "$GAIA_PATH/app/shared/"
    fi
    
    echo "✅ Shared utilities extracted"
}

extract_database_models() {
    echo "🗄️  Extracting database models..."
    
    if [ -d "$LLM_PLATFORM_PATH/app/models" ]; then
        echo "  - Copying database models..."
        cp -r "$LLM_PLATFORM_PATH/app/models" "$GAIA_PATH/app/shared/"
    fi
    
    if [ -d "$LLM_PLATFORM_PATH/migrations" ]; then
        echo "  - Copying database migrations..."
        cp -r "$LLM_PLATFORM_PATH/migrations" "$GAIA_PATH/"
    fi
    
    echo "✅ Database models extracted"
}

case $task in
    1)
        extract_asset_service
        ;;
    2)
        extract_chat_service
        ;;
    3)
        extract_shared_utilities
        ;;
    4)
        extract_database_models
        ;;
    5)
        echo "🔄 Extracting all components..."
        extract_asset_service
        extract_chat_service
        extract_shared_utilities
        extract_database_models
        ;;
    *)
        echo "❌ Invalid selection"
        exit 1
        ;;
esac

echo ""
echo "📝 Next steps:"
echo "1. Review extracted files and adapt them for microservices architecture"
echo "2. Update imports to use shared Gaia utilities"
echo "3. Add NATS coordination where appropriate"
echo "4. Test the extracted components"
echo ""
echo "🔍 Files extracted to:"
echo "- Asset Service: $GAIA_PATH/app/services/asset/"
echo "- Chat Service: $GAIA_PATH/app/services/chat/"
echo "- Shared utilities: $GAIA_PATH/app/shared/"
