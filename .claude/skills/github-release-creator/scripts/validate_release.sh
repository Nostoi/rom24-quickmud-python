#!/usr/bin/env bash
# Validate prerequisites before creating a release
# Usage: ./validate_release.sh VERSION

set -e

VERSION="${1}"

if [ -z "$VERSION" ]; then
  echo "Usage: $0 VERSION"
  echo "Example: $0 1.0.0"
  exit 1
fi

ERRORS=0

echo "Validating release prerequisites for v${VERSION}..."
echo ""

# Check if tag exists
if git tag -l | grep -q "^v${VERSION}$"; then
  echo "✓ Tag v${VERSION} exists"
else
  echo "✗ Tag v${VERSION} does not exist"
  ERRORS=$((ERRORS + 1))
fi

# Check if CHANGELOG has version
if [ -f "CHANGELOG.md" ]; then
  if grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    echo "✓ CHANGELOG.md has entry for ${VERSION}"
  else
    echo "✗ CHANGELOG.md missing entry for ${VERSION}"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "✗ CHANGELOG.md not found"
  ERRORS=$((ERRORS + 1))
fi

# Check for uncommitted changes
if git diff-index --quiet HEAD --; then
  echo "✓ No uncommitted changes"
else
  echo "✗ Uncommitted changes exist"
  ERRORS=$((ERRORS + 1))
fi

# Check if on correct branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "✓ On main/master branch"
else
  echo "⚠ Warning: On branch '$BRANCH' (not main/master)"
fi

# Check if tag is pushed
if git ls-remote --tags origin | grep -q "refs/tags/v${VERSION}$"; then
  echo "✓ Tag v${VERSION} pushed to origin"
else
  echo "⚠ Warning: Tag v${VERSION} not pushed to origin yet"
fi

# Check GitHub CLI
if command -v gh &> /dev/null; then
  echo "✓ GitHub CLI (gh) installed"
  
  if gh auth status &> /dev/null; then
    echo "✓ Authenticated with GitHub"
  else
    echo "✗ Not authenticated with GitHub (run: gh auth login)"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "✗ GitHub CLI (gh) not installed"
  ERRORS=$((ERRORS + 1))
fi

echo ""

if [ $ERRORS -eq 0 ]; then
  echo "✅ All checks passed! Ready to create release."
  exit 0
else
  echo "❌ $ERRORS error(s) found. Fix issues before creating release."
  exit 1
fi
