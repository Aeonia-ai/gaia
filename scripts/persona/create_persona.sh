#!/bin/bash
#
# create_persona.sh - Create a new persona in the database
#
# Usage: ./create_persona.sh [-y] <persona-file> <name> <description>
# Example: ./create_persona.sh zoe.txt "Zoe" "AUDHD cognitive companion"
#          ./create_persona.sh -y zoe.txt "Zoe" "AUDHD cognitive companion"  # Skip confirmation
#
# The persona file should contain only the system prompt text.
# The script will INSERT a new persona and output the generated UUID.
#
# Options:
#   -y, --yes    Skip confirmation prompt (for automated use)
#

set -e  # Exit on error

# Parse flags
SKIP_CONFIRM=false
while [[ "$1" == -* ]]; do
    case "$1" in
        -y|--yes)
            SKIP_CONFIRM=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

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
if [ $# -ne 3 ]; then
    echo "Usage: $0 <persona-file> <name> <description>"
    echo ""
    echo "Arguments:"
    echo "  persona-file   Path to .txt file containing system prompt"
    echo "  name           Unique persona name (e.g., 'Zoe')"
    echo "  description    Brief description of the persona"
    echo ""
    echo "Example:"
    echo "  $0 zoe.txt \"Zoe\" \"AUDHD cognitive companion\""
    echo ""
    exit 1
fi

PERSONA_FILE="$1"
PERSONA_NAME="$2"
PERSONA_DESCRIPTION="$3"

# Validate persona file exists
if [ ! -f "$PERSONA_FILE" ]; then
    error "Persona file not found: $PERSONA_FILE"
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
echo "  Persona Database Create Script"
echo "════════════════════════════════════════════════════════════"
echo ""
info "Persona file: $PERSONA_FILE"
info "Persona name: $PERSONA_NAME"
info "Description: $PERSONA_DESCRIPTION"
echo ""

# Step 1: Check if persona already exists
info "Checking if persona '$PERSONA_NAME' already exists..."
EXISTING_ID=$(docker exec gaia-db-1 psql -U postgres -d llm_platform -t -c \
    "SELECT id FROM personas WHERE name = '$PERSONA_NAME';" | xargs)

if [ -n "$EXISTING_ID" ]; then
    error "Persona '$PERSONA_NAME' already exists with ID: $EXISTING_ID\nUse update_persona.sh to modify existing personas."
fi

success "Persona name is available"

# Step 2: Escape quotes for SQL
info "Escaping single quotes for SQL..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ESCAPED_FILE="/tmp/persona_escaped_${TIMESTAMP}.txt"
sed "s/'/''/g" "$PERSONA_FILE" > "$ESCAPED_FILE"

# Also escape the description
ESCAPED_DESCRIPTION=$(echo "$PERSONA_DESCRIPTION" | sed "s/'/''/g")

success "Quotes escaped"

# Step 3: Generate SQL script
info "Generating SQL insert script..."
SQL_FILE="/tmp/create_persona_${TIMESTAMP}.sql"

cat > "$SQL_FILE" << OUTER_EOF
INSERT INTO personas (name, description, system_prompt, personality_traits, capabilities, created_by)
VALUES (
    '$PERSONA_NAME',
    '$ESCAPED_DESCRIPTION',
    '
OUTER_EOF

cat "$ESCAPED_FILE" >> "$SQL_FILE"

cat >> "$SQL_FILE" << 'OUTER_EOF'
',
    '{}',
    '{}',
    'system'
)
RETURNING id, name, description, created_at;
OUTER_EOF

success "SQL script generated"

# Step 4: Show preview and ask for confirmation
echo ""
warn "About to create persona '$PERSONA_NAME' in database"
info "System prompt file: $PERSONA_FILE ($(wc -l < "$PERSONA_FILE") lines, $(wc -c < "$PERSONA_FILE" | xargs) bytes)"
echo ""

if [ "$SKIP_CONFIRM" = false ]; then
    read -p "Continue with creation? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warn "Creation cancelled by user"
        rm -f "$ESCAPED_FILE" "$SQL_FILE"
        exit 0
    fi
else
    info "Skipping confirmation (-y flag)"
fi

# Step 5: Execute SQL insert
info "Executing database insert..."
INSERT_RESULT=$(docker exec -i gaia-db-1 psql -U postgres -d llm_platform < "$SQL_FILE" 2>&1)

if echo "$INSERT_RESULT" | grep -q "INSERT 0 1"; then
    success "Database insert successful"
else
    error "Database insert failed:\n$INSERT_RESULT"
fi

# Step 6: Get the new UUID
NEW_UUID=$(docker exec gaia-db-1 psql -U postgres -d llm_platform -t -c \
    "SELECT id FROM personas WHERE name = '$PERSONA_NAME';" | xargs)

if [ -z "$NEW_UUID" ]; then
    error "Failed to retrieve new persona UUID"
fi

success "Created persona with UUID: $NEW_UUID"

# Step 7: Verify creation
info "Verifying creation..."
VERIFY_RESULT=$(docker exec gaia-db-1 psql -U postgres -d llm_platform -c \
    "SELECT id, name, LEFT(description, 50) as description, created_at FROM personas WHERE id = '$NEW_UUID';")

echo ""
echo "════════════════════════════════════════════════════════════"
echo "$VERIFY_RESULT"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 8: Clean up temp files
info "Cleaning up temporary files..."
rm -f "$ESCAPED_FILE" "$SQL_FILE"
success "Cleanup complete"

# Final summary
echo ""
success "Persona created successfully!"
echo ""
info "Persona: $PERSONA_NAME"
info "UUID: $NEW_UUID"
info "File: $PERSONA_FILE"
echo ""
echo "To update this persona in the future, run:"
echo "  ./update_persona.sh $PERSONA_FILE $NEW_UUID"
echo ""
echo "Add this to scripts/persona/README.md:"
echo "| $PERSONA_NAME | \`$NEW_UUID\` | \`$(basename $PERSONA_FILE)\` |"
echo ""
