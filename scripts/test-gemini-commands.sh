#!/bin/bash
# Test Gemini CLI doc-health commands
# Usage: ./scripts/test-gemini-commands.sh [verify|fix|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMMANDS_DIR="$PROJECT_ROOT/.gemini/commands/doc-health"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Testing Gemini CLI Doc-Health Commands"
echo "=========================================="

# Test 1: Validate TOML syntax
echo -e "\n${YELLOW}Test 1: TOML Syntax Validation${NC}"
echo "-------------------------------------------"

validate_toml() {
    local file=$1
    if python3 -c "import tomllib; tomllib.load(open('$file', 'rb'))" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $file - Valid TOML"
        return 0
    else
        echo -e "${RED}✗${NC} $file - Invalid TOML"
        return 1
    fi
}

for toml in "$COMMANDS_DIR"/*.toml; do
    validate_toml "$toml"
done

# Test 2: Check required fields
echo -e "\n${YELLOW}Test 2: Required Fields Check${NC}"
echo "-------------------------------------------"

check_fields() {
    local file=$1
    local has_description=$(python3 -c "import tomllib; d=tomllib.load(open('$file', 'rb')); print('yes' if 'description' in d else 'no')")
    local has_prompt=$(python3 -c "import tomllib; d=tomllib.load(open('$file', 'rb')); print('yes' if 'prompt' in d else 'no')")

    if [[ "$has_description" == "yes" && "$has_prompt" == "yes" ]]; then
        echo -e "${GREEN}✓${NC} $(basename $file) - Has required fields (description, prompt)"
        return 0
    else
        echo -e "${RED}✗${NC} $(basename $file) - Missing fields (description=$has_description, prompt=$has_prompt)"
        return 1
    fi
}

for toml in "$COMMANDS_DIR"/*.toml; do
    check_fields "$toml"
done

# Test 3: Check {{args}} placeholder
echo -e "\n${YELLOW}Test 3: Args Placeholder Check${NC}"
echo "-------------------------------------------"

check_args() {
    local file=$1
    if grep -q '{{args}}' "$file"; then
        echo -e "${GREEN}✓${NC} $(basename $file) - Contains {{args}} placeholder"
        return 0
    else
        echo -e "${YELLOW}!${NC} $(basename $file) - No {{args}} placeholder (may be intentional)"
        return 0
    fi
}

for toml in "$COMMANDS_DIR"/*.toml; do
    check_args "$toml"
done

# Test 4: Simulate prompt substitution
echo -e "\n${YELLOW}Test 4: Prompt Substitution Simulation${NC}"
echo "-------------------------------------------"

simulate_verify() {
    echo "Simulating: /doc-health:verify docs/reference/services/llm-service.md"
    echo ""
    echo "The prompt would expand to:"
    echo "---"
    python3 << 'EOF'
import tomllib
with open('.gemini/commands/doc-health/verify.toml', 'rb') as f:
    data = tomllib.load(f)
prompt = data['prompt']
substituted = prompt.replace('{{args}}', 'docs/reference/services/llm-service.md')
# Show first 500 chars
print(substituted[:500] + "...\n[truncated - full prompt is " + str(len(substituted)) + " chars]")
EOF
    echo "---"
}

simulate_fix() {
    echo "Simulating: /doc-health:fix with sample JSON"
    echo ""
    echo "The prompt would expand to:"
    echo "---"
    python3 << 'EOF'
import tomllib
with open('.gemini/commands/doc-health/fix.toml', 'rb') as f:
    data = tomllib.load(f)
prompt = data['prompt']
sample_json = '[{"issue_id": "001", "approved": true, "file_path": "docs/test.md", "affected_text": "old text", "replacement_text": "new text"}]'
substituted = prompt.replace('{{args}}', sample_json)
# Show first 500 chars
print(substituted[:500] + "...\n[truncated - full prompt is " + str(len(substituted)) + " chars]")
EOF
    echo "---"
}

simulate_verify
echo ""
simulate_fix

# Test 5: Check if Gemini CLI is available
echo -e "\n${YELLOW}Test 5: Gemini CLI Availability${NC}"
echo "-------------------------------------------"

if command -v gemini &> /dev/null; then
    echo -e "${GREEN}✓${NC} Gemini CLI is installed at: $(which gemini)"
    echo -e "${GREEN}✓${NC} Version: $(gemini --version 2>/dev/null || echo 'unknown')"
    echo ""
    echo "To run an actual test:"
    echo "  cd $PROJECT_ROOT"
    echo "  gemini"
    echo "  /doc-health:verify docs/reference/services/llm-service.md"
else
    echo -e "${YELLOW}!${NC} Gemini CLI not found in PATH"
    echo "Install with: npm install -g @anthropic-ai/gemini-cli"
fi

echo ""
echo "=========================================="
echo "All automated tests passed!"
echo "=========================================="
echo ""
echo "For full integration testing, run commands in Gemini CLI:"
echo "  1. gemini  (start interactive session)"
echo "  2. /doc-health:verify docs/reference/services/llm-service.md"
echo "  3. Review output, mark approved: true/false on issues"
echo "  4. /doc-health:fix [paste approved JSON]"
