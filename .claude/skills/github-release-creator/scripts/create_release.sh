#!/usr/bin/env bash
# Create GitHub release from CHANGELOG.md
# Usage: ./create_release.sh VERSION TITLE

set -e

VERSION="${1}"
TITLE="${2}"

if [ -z "$VERSION" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 VERSION TITLE"
  echo "Example: $0 1.0.0 'Release v1.0.0: New Features'"
  exit 1
fi

# Check if gh is installed
if ! command -v gh &> /dev/null; then
  echo "Error: GitHub CLI (gh) is not installed"
  echo "Install: brew install gh"
  exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
  echo "Error: Not authenticated with GitHub"
  echo "Run: gh auth login"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NOTES_FILE="/tmp/release_notes_${VERSION}.md"

# Extract changelog
echo "Extracting release notes from CHANGELOG.md..."
"${SCRIPT_DIR}/extract_changelog.sh" "$VERSION"

# Verify tag exists
if ! git tag -l | grep -q "^v${VERSION}$"; then
  echo "Warning: Tag v${VERSION} does not exist locally"
  read -p "Create tag now? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
    git push origin "v${VERSION}"
  else
    echo "Aborted. Create tag first: git tag -a v${VERSION} -m 'Release v${VERSION}'"
    exit 1
  fi
fi

# Create release
echo "Creating GitHub release..."
gh release create "v${VERSION}" \
  --title "${TITLE}" \
  --notes-file "${NOTES_FILE}"

echo "✓ Release v${VERSION} created successfully!"
echo "View at: $(gh release view v${VERSION} --json url -q .url)"

# Cleanup
rm -f "${NOTES_FILE}"
