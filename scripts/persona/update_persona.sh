#!/bin/bash
#
# update_persona.sh - Automated persona database update script
#
# Usage: ./update_persona.sh <persona-file> <persona-uuid>
# Example: ./update_persona.sh game-master-strict.txt 7b197909-8837-4ed5-a67a-a05c90e817f1
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Validate arguments
if [ $# -ne 2 ]; then
    error "Usage: $0 <persona-file> <persona-uuid>\n  Example: $0 game-master-strict.txt 7b197909-8837-4ed5-a67a-a05c90e817f1"
fi

PERSONA_FILE="$1"
PERSONA_UUID="$2"

# Validate persona file exists
if [ ! -f "$PERSONA_FILE" ]; then
    error "Persona file not found: $PERSONA_FILE"
fi

# Validate UUID format (basic check)
if ! [[ "$PERSONA_UUID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    error "Invalid UUID format: $PERSONA_UUID"
fi

# Check Docker is running
if ! docker ps > /dev/null 2>&1; then
    error "Docker is not running or not accessible"
fi

# Check database container exists
if ! docker ps | grep -q gaia-db-1; then
    error "Database container 'gaia-db-1' is not running"
fi

echo "════════════════════════════════════════════════════════════"
echo "  Persona Database Update Script"
echo "════════════════════════════════════════════════════════════"
echo ""
info "Persona file: $PERSONA_FILE"
info "Persona UUID: $PERSONA_UUID"
echo ""

# Step 1: Create backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${PERSONA_FILE%.txt}-backup-${TIMESTAMP}.txt"

info "Creating backup: $BACKUP_FILE"
cp "$PERSONA_FILE" "$BACKUP_FILE"
success "Backup created"

# Step 2: Verify persona exists in database
info "Verifying persona exists in database..."
PERSONA_NAME=$(docker exec gaia-db-1 psql -U postgres -d llm_platform -t -c \
    "SELECT name FROM personas WHERE id = '$PERSONA_UUID';" | xargs)

if [ -z "$PERSONA_NAME" ]; then
    error "Persona with UUID $PERSONA_UUID not found in database"
fi

success "Found persona: $PERSONA_NAME"

# Step 3: Escape quotes for SQL
info "Escaping single quotes for SQL..."
ESCAPED_FILE="/tmp/persona_escaped_${TIMESTAMP}.txt"
sed "s/'/''/g" "$PERSONA_FILE" > "$ESCAPED_FILE"
success "Quotes escaped"

# Step 4: Generate SQL script
info "Generating SQL update script..."
SQL_FILE="/tmp/update_persona_${TIMESTAMP}.sql"

cat > "$SQL_FILE" << 'OUTER_EOF'
UPDATE personas
SET system_prompt = '
OUTER_EOF

cat "$ESCAPED_FILE" >> "$SQL_FILE"

cat >> "$SQL_FILE" << OUTER_EOF
',
    updated_at = NOW()
WHERE id = '$PERSONA_UUID';

-- Verify the update
SELECT id, name, LEFT(system_prompt, 150) as prompt_preview
FROM personas
WHERE id = '$PERSONA_UUID';
OUTER_EOF

success "SQL script generated: $SQL_FILE"

# Step 5: Show preview and ask for confirmation
echo ""
warn "About to update persona '$PERSONA_NAME' in database"
info "Persona file: $PERSONA_FILE ($(wc -l < "$PERSONA_FILE") lines)"
info "Backup saved: $BACKUP_FILE"
echo ""

read -p "Continue with update? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warn "Update cancelled by user"
    # Clean up temp files
    rm -f "$ESCAPED_FILE" "$SQL_FILE"
    exit 0
fi

# Step 6: Execute SQL update
info "Executing database update..."
UPDATE_RESULT=$(docker exec -i gaia-db-1 psql -U postgres -d llm_platform < "$SQL_FILE" 2>&1)

if echo "$UPDATE_RESULT" | grep -q "UPDATE 1"; then
    success "Database update successful"
else
    error "Database update failed:\n$UPDATE_RESULT"
fi

# Step 7: Clear Redis cache
info "Clearing Redis cache..."

# Get Redis password from chat service environment
REDIS_PASSWORD=$(docker exec gaia-chat-service-1 printenv REDIS_PASSWORD 2>/dev/null)

if [ -n "$REDIS_PASSWORD" ] && docker ps | grep -q gaia-redis-1; then
    # Clear persona cache
    docker exec gaia-redis-1 redis-cli -a "$REDIS_PASSWORD" DEL "persona:$PERSONA_UUID" 2>/dev/null || true
    # Clear personas list caches
    docker exec gaia-redis-1 redis-cli -a "$REDIS_PASSWORD" DEL "personas:list:active" 2>/dev/null || true
    docker exec gaia-redis-1 redis-cli -a "$REDIS_PASSWORD" DEL "personas:list:all" 2>/dev/null || true
    success "Redis cache cleared"
else
    warn "Could not clear Redis cache (Redis not running or no password found)"
fi

# Step 8: Verify database update
info "Verifying update..."
VERIFY_RESULT=$(docker exec gaia-db-1 psql -U postgres -d llm_platform -t -c \
    "SELECT name, updated_at, LENGTH(system_prompt) as prompt_length FROM personas WHERE id = '$PERSONA_UUID';")

success "Update verified"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "$VERIFY_RESULT"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 9: Clean up temp files
info "Cleaning up temporary files..."
rm -f "$ESCAPED_FILE" "$SQL_FILE"
success "Cleanup complete"

# Final summary
echo ""
success "Persona update complete!"
info "Backup file: $BACKUP_FILE"
info "Updated persona: $PERSONA_NAME"
info "Redis cache: cleared"
echo ""
