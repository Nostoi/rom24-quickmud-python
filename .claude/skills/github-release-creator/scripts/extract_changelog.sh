#!/usr/bin/env bash
# Extract release notes from CHANGELOG.md for a specific version
# Usage: ./extract_changelog.sh VERSION

set -e

VERSION="${1}"

if [ -z "$VERSION" ]; then
  echo "Usage: $0 VERSION"
  echo "Example: $0 1.0.0"
  exit 1
fi

CHANGELOG="CHANGELOG.md"
OUTPUT="/tmp/release_notes_${VERSION}.md"

if [ ! -f "$CHANGELOG" ]; then
  echo "Error: CHANGELOG.md not found in current directory"
  exit 1
fi

# Extract section between [VERSION] and next [
sed -n "/^## \[${VERSION}\]/,/^## \[/p" "$CHANGELOG" | sed '$d' > "$OUTPUT"

if [ ! -s "$OUTPUT" ]; then
  echo "Error: No entry found for version ${VERSION} in CHANGELOG.md"
  rm -f "$OUTPUT"
  exit 1
fi

echo "✓ Release notes extracted to: $OUTPUT"
echo ""
echo "Preview:"
echo "----------------------------------------"
head -n 20 "$OUTPUT"
if [ $(wc -l < "$OUTPUT") -gt 20 ]; then
  echo "..."
  echo "(${$(wc -l < "$OUTPUT")} total lines)"
fi
echo "----------------------------------------"
