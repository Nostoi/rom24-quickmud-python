# GitHub Release Creator Skill

Comprehensive tools and documentation for creating professional GitHub releases.

## Quick Start

### Install GitHub CLI
```bash
# macOS
brew install gh

# Authenticate
gh auth login
```

### Create a Release

**Option 1: Using scripts (recommended)**
```bash
# Validate prerequisites
./.claude/skills/github-release-creator/scripts/validate_release.sh 1.0.0

# Create release from CHANGELOG.md
./.claude/skills/github-release-creator/scripts/create_release.sh 1.0.0 "v1.0.0 - Feature Name"
```

**Option 2: Using Python script**
```bash
# Auto-extracts from CHANGELOG.md or auto-generates
./.claude/skills/github-release-creator/scripts/create_release.py 1.0.0 \
  -t "v1.0.0 - Feature Name"

# With custom notes
./.claude/skills/github-release-creator/scripts/create_release.py 1.0.0 \
  -t "Release v1.0.0" \
  -n "Custom release notes here"

# Draft release
./.claude/skills/github-release-creator/scripts/create_release.py 1.0.0 --draft

# Pre-release
./.claude/skills/github-release-creator/scripts/create_release.py 1.0.0-beta.1 --prerelease
```

**Option 3: Using gh directly**
```bash
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes-file /tmp/notes.md
```

## Files

### Scripts
- **validate_release.sh** - Check prerequisites before release
- **extract_changelog.sh** - Extract version section from CHANGELOG.md
- **create_release.sh** - Create release from CHANGELOG.md
- **create_release.py** - Python script with advanced options

### Documentation
- **SKILL.md** - Complete skill documentation
- **references/workflows.md** - Common release workflows
- **references/release-notes-guide.md** - Best practices for release notes

## Common Commands

```bash
# List releases
gh release list

# View specific release
gh release view v1.0.0

# Edit release
gh release edit v1.0.0 --notes "Updated notes"

# Delete release
gh release delete v1.0.0 --yes

# Upload assets
gh release upload v1.0.0 file.zip
```

## Workflow Example

```bash
# 1. Update version in files
# pyproject.toml, package.json, README.md

# 2. Update CHANGELOG.md
# Add version section with changes

# 3. Commit and tag
git add -A
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 4. Validate
./scripts/validate_release.sh 1.0.0

# 5. Create release
./scripts/create_release.sh 1.0.0 "v1.0.0 - New Features"
```

## Features

- ✅ Automatic CHANGELOG.md extraction
- ✅ Auto-generated release notes
- ✅ Draft and pre-release support
- ✅ Asset upload support
- ✅ Validation checks
- ✅ Multiple script options (Bash, Python)
- ✅ Comprehensive documentation

## Requirements

- GitHub CLI (`gh`)
- Git
- Bash (for .sh scripts)
- Python 3.6+ (for .py scripts)

---

**Skill Version**: 1.0.0  
**Last Updated**: 2025-12-27
