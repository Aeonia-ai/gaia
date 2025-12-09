#!/bin/bash
# Check for broken markdown links in docs

DOCS_DIR="/Users/jasbahr/Development/Aeonia/server/gaia/docs"
BROKEN_COUNT=0
CHECKED_COUNT=0

# Function to resolve relative path
resolve_path() {
    local source_file="$1"
    local link_path="$2"
    local source_dir=$(dirname "$source_file")

    # Handle ../ relative paths
    if [[ "$link_path" == ../* ]]; then
        echo "$(cd "$source_dir" && cd "$(dirname "$link_path")" 2>/dev/null && pwd)/$(basename "$link_path")"
    else
        echo "$source_dir/$link_path"
    fi
}

# Find all markdown files with ../ links
while IFS= read -r file; do
    while IFS= read -r line; do
        # Extract markdown links with ../ pattern
        if echo "$line" | grep -q '\](\.\./.*.md)'; then
            links=$(echo "$line" | grep -o '\](\.\./.*.md)' | sed 's/](//;s/)//')

            for link in $links; do
                CHECKED_COUNT=$((CHECKED_COUNT + 1))
                resolved=$(resolve_path "$file" "$link")

                if [ ! -f "$resolved" ]; then
                    echo "BROKEN: $file"
                    echo "  Link: $link"
                    echo "  Resolved to: $resolved"
                    echo ""
                    BROKEN_COUNT=$((BROKEN_COUNT + 1))
                fi
            done
        fi
    done < "$file"
done < <(find "$DOCS_DIR" -name "*.md" -type f)

echo "======================================"
echo "Checked: $CHECKED_COUNT links"
echo "Broken: $BROKEN_COUNT links"
echo "======================================"
