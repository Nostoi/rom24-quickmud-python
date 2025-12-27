---
name: github-release-creator
description: Automates the creation of GitHub releases using the GitHub CLI (gh)
license: Apache-2.0
metadata:
  version: 1.0.0
  author: QuickMUD Project
  tags:
    - github
    - releases
    - automation
    - ci-cd
  requirements:
    - GitHub CLI (gh) installed and authenticated
    - Git repository with remote origin
    - CHANGELOG.md file (optional but recommended)
---

# GitHub Release Creator Skill

A comprehensive Claude Desktop skill for creating, managing, and publishing GitHub releases with proper versioning, release notes, and asset management.

## Skill Purpose

This skill enables AI assistants to efficiently create professional GitHub releases using the GitHub CLI (`gh`), including generating release notes, managing tags, and attaching release assets.

## Key Capabilities

### Release Creation
- Create GitHub releases from existing tags or create new tags
- Generate release notes from commit history
- Support for pre-releases and draft releases
- Automatic release note generation from conventional commits
- Asset attachment and management

### Version Management
- Semantic versioning (SemVer) compliance
- Tag creation and management
- Version number validation
- Changelog integration

### Release Notes
- Extract from CHANGELOG.md
- Generate from git commit history
- Support for conventional commit format
- Custom templates and formatting
- Highlight breaking changes and new features

## Prerequisites

### Required Tools
- **GitHub CLI** (`gh`): https://cli.github.com/
  ```bash
  # macOS
  brew install gh
  
  # Linux
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update
  sudo apt install gh
  ```

- **Git**: Version control (usually pre-installed)

### Authentication
```bash
# Login to GitHub
gh auth login

# Verify authentication
gh auth status
```

## Common Workflows

### 1. Create Release from Existing Tag

```bash
# List existing tags
git tag -l

# Create release from tag
gh release create v1.0.0 \
  --title "Release v1.0.0: Feature Name" \
  --notes-file RELEASE_NOTES.md
```

### 2. Create Release with New Tag

```bash
# Create tag and release together
gh release create v1.0.0 \
  --title "Release v1.0.0: Feature Name" \
  --notes "Release description here" \
  --target main
```

### 3. Generate Release Notes from Git History

```bash
# Generate release notes automatically
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --generate-notes
```

### 4. Create Pre-release

```bash
gh release create v1.0.0-beta.1 \
  --title "Beta Release v1.0.0-beta.1" \
  --notes "Beta testing release" \
  --prerelease
```

### 5. Create Draft Release

```bash
# Create draft for review before publishing
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes-file CHANGELOG.md \
  --draft
```

### 6. Attach Release Assets

```bash
# Upload binary files, packages, etc.
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes "Release with assets" \
  dist/*.tar.gz dist/*.zip
```

## Release Notes Best Practices

### Extract from CHANGELOG.md

```bash
# Extract specific version section
sed -n '/^## \[1.0.0\]/,/^## \[/p' CHANGELOG.md | sed '$d' > RELEASE_NOTES.md

# Create release with extracted notes
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes-file RELEASE_NOTES.md
```

### Conventional Commit Format

Release notes generated from conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `perf:` - Performance improvements

Example:
```bash
# Commits like:
# feat: Add user authentication
# fix: Resolve memory leak in parser
# docs: Update API documentation

# Generate notes:
gh release create v1.0.0 --generate-notes
```

### Custom Release Notes Template

```markdown
## What's Changed

### 🚀 New Features
- Feature 1 description
- Feature 2 description

### 🐛 Bug Fixes
- Fix 1 description
- Fix 2 description

### 📚 Documentation
- Doc update 1
- Doc update 2

### 🔧 Maintenance
- Chore 1
- Chore 2

**Full Changelog**: https://github.com/owner/repo/compare/v0.9.0...v1.0.0
```

## Complete Release Workflow

### Step-by-Step Process

1. **Update Version Numbers**
   ```bash
   # Update pyproject.toml, package.json, etc.
   # Update README.md badges
   ```

2. **Update CHANGELOG.md**
   ```bash
   # Add new version section
   # Document all changes
   ```

3. **Commit Changes**
   ```bash
   git add -A
   git commit -m "Release v1.0.0: Description"
   ```

4. **Create and Push Tag**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0: Description"
   git push origin main --tags
   ```

5. **Extract Release Notes**
   ```bash
   # From CHANGELOG.md
   sed -n '/^## \[1.0.0\]/,/^## \[/p' CHANGELOG.md | sed '$d' > /tmp/release_notes.md
   ```

6. **Create GitHub Release**
   ```bash
   gh release create v1.0.0 \
     --title "v1.0.0 - Feature Name" \
     --notes-file /tmp/release_notes.md
   ```

7. **Verify Release**
   ```bash
   # View release
   gh release view v1.0.0
   
   # List all releases
   gh release list
   ```

## Advanced Usage

### Edit Existing Release

```bash
# Edit release notes
gh release edit v1.0.0 --notes "Updated release notes"

# Change title
gh release edit v1.0.0 --title "New Title"

# Convert draft to published
gh release edit v1.0.0 --draft=false

# Mark as latest
gh release edit v1.0.0 --latest
```

### Delete Release (Keep Tag)

```bash
# Delete release but keep git tag
gh release delete v1.0.0 --yes
```

### Delete Release and Tag

```bash
# Delete release
gh release delete v1.0.0 --yes

# Delete tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

### Upload Additional Assets

```bash
# Upload to existing release
gh release upload v1.0.0 path/to/asset.zip
```

### Download Release Assets

```bash
# Download all assets
gh release download v1.0.0

# Download specific asset
gh release download v1.0.0 --pattern "*.tar.gz"
```

## Semantic Versioning (SemVer)

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

### Pre-release Versions
- Alpha: `1.0.0-alpha.1`
- Beta: `1.0.0-beta.1`
- Release Candidate: `1.0.0-rc.1`

### Version Bumping Decision Tree

```
Breaking changes? → MAJOR version
  └─ No → New features? → MINOR version
           └─ No → Bug fixes only? → PATCH version
```

## Script Helpers

### 1. Extract CHANGELOG Section

```bash
#!/bin/bash
# scripts/extract_changelog.sh
VERSION=$1
sed -n "/^## \[$VERSION\]/,/^## \[/p" CHANGELOG.md | sed '$d' > /tmp/release_notes_$VERSION.md
echo "Release notes extracted to /tmp/release_notes_$VERSION.md"
```

### 2. Create Release from CHANGELOG

```bash
#!/bin/bash
# scripts/create_release.sh
VERSION=$1
TITLE=$2

# Extract notes
./scripts/extract_changelog.sh $VERSION

# Create release
gh release create v$VERSION \
  --title "$TITLE" \
  --notes-file /tmp/release_notes_$VERSION.md

echo "Release v$VERSION created!"
```

### 3. Validate Release Prerequisites

```bash
#!/bin/bash
# scripts/validate_release.sh
VERSION=$1

echo "Validating release prerequisites for v$VERSION..."

# Check if tag exists
if git tag -l | grep -q "^v$VERSION$"; then
  echo "✓ Tag v$VERSION exists"
else
  echo "✗ Tag v$VERSION does not exist"
  exit 1
fi

# Check if CHANGELOG has version
if grep -q "## \[$VERSION\]" CHANGELOG.md; then
  echo "✓ CHANGELOG.md has entry for $VERSION"
else
  echo "✗ CHANGELOG.md missing entry for $VERSION"
  exit 1
fi

# Check if committed
if git diff-index --quiet HEAD --; then
  echo "✓ No uncommitted changes"
else
  echo "✗ Uncommitted changes exist"
  exit 1
fi

echo "All checks passed! Ready to create release."
```

## Common Issues and Solutions

### Issue: Tag Already Exists
```bash
# Solution: Delete and recreate tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Issue: Release Already Exists
```bash
# Solution: Delete and recreate release
gh release delete v1.0.0 --yes
gh release create v1.0.0 --title "..." --notes "..."
```

### Issue: gh Command Not Found
```bash
# Solution: Install GitHub CLI
brew install gh  # macOS
# or follow installation instructions above
```

### Issue: Authentication Failed
```bash
# Solution: Re-authenticate
gh auth login
gh auth status
```

## Environment Variables

```bash
# GitHub token (if not using gh auth)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Default repository (optional)
export GH_REPO="owner/repo"
```

## Integration Examples

### Python Project (pyproject.toml)

```bash
# 1. Update version in pyproject.toml
sed -i '' 's/version = ".*"/version = "1.0.0"/' pyproject.toml

# 2. Update CHANGELOG.md
# (manual or automated)

# 3. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 4. Create release
./scripts/create_release.sh 1.0.0 "v1.0.0 - Feature Name"
```

### Node.js Project (package.json)

```bash
# Use npm version to bump
npm version minor  # Creates tag automatically

# Push tag
git push origin main --tags

# Create release
gh release create $(git describe --tags --abbrev=0) \
  --title "Release $(git describe --tags --abbrev=0)" \
  --generate-notes
```

## Best Practices Checklist

- [ ] Version follows SemVer format
- [ ] CHANGELOG.md updated with version entry
- [ ] All code committed and pushed
- [ ] Tag created and pushed
- [ ] Release notes are clear and comprehensive
- [ ] Breaking changes are highlighted
- [ ] Migration guide included (if needed)
- [ ] Assets built and tested
- [ ] Release reviewed before publishing
- [ ] Release announcement prepared

## Quick Reference

```bash
# List releases
gh release list

# View specific release
gh release view v1.0.0

# Create release
gh release create v1.0.0 --title "Title" --notes "Notes"

# Create with assets
gh release create v1.0.0 --notes "Notes" dist/*

# Create draft
gh release create v1.0.0 --notes "Notes" --draft

# Create pre-release
gh release create v1.0.0-beta --notes "Notes" --prerelease

# Generate notes automatically
gh release create v1.0.0 --generate-notes

# Edit release
gh release edit v1.0.0 --notes "Updated notes"

# Delete release
gh release delete v1.0.0 --yes

# Upload asset
gh release upload v1.0.0 file.zip

# Download release
gh release download v1.0.0
```

## Related Documentation

- GitHub CLI: https://cli.github.com/manual/
- GitHub Releases API: https://docs.github.com/en/rest/releases
- Semantic Versioning: https://semver.org/
- Conventional Commits: https://www.conventionalcommits.org/

---

**Skill Version**: 1.0.0  
**Last Updated**: 2025-12-27  
**Maintainer**: GitHub Release Automation
