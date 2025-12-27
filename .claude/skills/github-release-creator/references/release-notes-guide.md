# Release Notes Best Practices

Guidelines for writing effective GitHub release notes that users will actually read and appreciate.

## Structure Template

```markdown
## What's Changed

### 🚀 New Features
- Feature 1: Description with benefit to users
- Feature 2: Description with benefit to users

### 🐛 Bug Fixes
- Fix 1: What was broken and how it's fixed
- Fix 2: What was broken and how it's fixed

### 💥 Breaking Changes
- Breaking change 1 with migration guide
- Breaking change 2 with migration guide

### 📚 Documentation
- Documentation improvements
- README updates

### 🔧 Maintenance
- Dependency updates
- Code refactoring
- Test improvements

### ⚠️ Deprecations
- Deprecated feature 1 (will be removed in v2.0)
- Alternative: Use new feature instead

**Full Changelog**: https://github.com/owner/repo/compare/v1.0.0...v1.1.0
```

## Emoji Guide

Use emojis to make sections scannable:

- 🚀 New Features
- 🐛 Bug Fixes
- 💥 Breaking Changes
- 📚 Documentation
- 🔧 Maintenance / Chores
- ⚡️ Performance
- 🔒 Security
- ♻️ Refactoring
- ✅ Tests
- 🎨 UI/UX
- ⚠️ Deprecations
- 🗑️ Removals
- 📦 Dependencies

## Writing Guidelines

### 1. User-Centric Language

❌ **Bad**: "Refactored authentication module"  
✅ **Good**: "Improved login speed by 50% through authentication optimization"

❌ **Bad**: "Fixed bug in parser"  
✅ **Good**: "Fixed crash when processing large files (>100MB)"

### 2. Be Specific

❌ **Bad**: "Various improvements"  
✅ **Good**: "Reduced memory usage by 30% in data processing"

❌ **Bad**: "Updated dependencies"  
✅ **Good**: "Updated security dependencies (OpenSSL 1.1 → 3.0)"

### 3. Include Context

❌ **Bad**: "Added caching"  
✅ **Good**: "Added response caching to reduce API calls by 80%"

### 4. Highlight Impact

Always answer: "Why should users care?"

❌ **Bad**: "Implemented connection pooling"  
✅ **Good**: "Improved database performance by 3x through connection pooling"

### 5. Provide Migration Path

For breaking changes, always include migration steps:

```markdown
### 💥 Breaking Changes

**Authentication API Change**

The `login()` method now requires an email parameter.

**Before**:
```python
client.login(username="user", password="pass")
```

**After**:
```python
client.login(email="user@example.com", password="pass")
```

**Migration**: Update all login calls to use email instead of username.
```

## Changelog Extraction

### From Git Commits (Conventional Commits)

```bash
# Generate changelog from commits
git log v1.0.0..v1.1.0 --pretty=format:"- %s" --no-merges | grep -E "^- (feat|fix|docs|perf|refactor):"

# Format by type
echo "### Features"
git log v1.0.0..v1.1.0 --oneline --no-merges | grep "^.* feat:" | sed 's/^[a-f0-9]* feat: /- /'

echo "### Bug Fixes"
git log v1.0.0..v1.1.0 --oneline --no-merges | grep "^.* fix:" | sed 's/^[a-f0-9]* fix: /- /'
```

### From CHANGELOG.md

```bash
# Extract specific version
sed -n '/^## \[1.0.0\]/,/^## \[/p' CHANGELOG.md | sed '$d'
```

### Auto-generated (GitHub)

```bash
gh release create v1.0.0 --generate-notes
```

Generates notes from:
- Pull requests merged since last release
- Commit messages
- Contributors list

## Examples

### Good Release Notes

```markdown
## v1.2.0 - Performance and Security Update

### 🚀 New Features

- **Batch Processing**: Process multiple files simultaneously for 5x faster imports
- **Auto-save**: Automatically save work every 30 seconds (configurable)
- **Dark Mode**: New dark theme option in settings

### 🐛 Bug Fixes

- Fixed crash when exporting large datasets (>1GB) - #234
- Resolved memory leak in background sync - #245
- Fixed incorrect date formatting in European locales - #251

### 🔒 Security

- Updated OpenSSL to 3.0.8 (CVE-2023-XXXX)
- Added rate limiting to API endpoints
- Improved password validation (now requires 12+ characters)

### 💥 Breaking Changes

**API Response Format Changed**

The `/api/users` endpoint now returns paginated results.

**Before**:
```json
{
  "users": [...]
}
```

**After**:
```json
{
  "data": [...],
  "page": 1,
  "total_pages": 10
}
```

**Migration**: Update code to handle `data` field and pagination.

### 📚 Documentation

- Added getting started tutorial
- Updated API documentation with examples
- New troubleshooting guide

### Contributors

Thanks to @user1, @user2, and @user3 for their contributions!

**Full Changelog**: https://github.com/org/repo/compare/v1.1.0...v1.2.0
```

### Bad Release Notes

```markdown
## v1.2.0

- Various bug fixes
- Performance improvements
- Updated dependencies
- Code cleanup
- Refactoring
- Minor changes
```

Problems:
- Too vague
- No details about what changed
- No user benefit explained
- No migration guide
- Boring to read

## Version-Specific Guidance

### Major Version (1.0.0 → 2.0.0)

- **Emphasize** breaking changes
- **Provide** detailed migration guide
- **List** removed/deprecated features
- **Highlight** major new capabilities
- **Include** upgrade checklist

### Minor Version (1.0.0 → 1.1.0)

- **Focus on** new features
- **Mention** notable bug fixes
- **Include** any deprecation notices
- **Highlight** improvements

### Patch Version (1.0.0 → 1.0.1)

- **List** all bug fixes
- **Include** any security fixes
- **Keep it** brief and focused
- **Note** if critical/urgent

### Pre-release (1.0.0-beta.1)

- **Mark clearly** as pre-release
- **Warn** about stability
- **List** known issues
- **Encourage** feedback
- **Specify** testing scope

## Checklist

Before publishing release notes:

- [ ] Clear title with version number
- [ ] Breaking changes highlighted and explained
- [ ] Migration guide for breaking changes
- [ ] New features with user benefit
- [ ] Bug fixes with issue numbers
- [ ] Security updates clearly marked
- [ ] Contributors acknowledged
- [ ] Link to full changelog
- [ ] Emojis for visual scanning
- [ ] Spell checked
- [ ] Technical accuracy verified
- [ ] User-centric language
- [ ] No jargon without explanation

## Anti-Patterns

Avoid these common mistakes:

1. **Too Technical**: "Refactored AbstractFactoryBean"  
   → Use: "Improved startup time by 40%"

2. **Missing Context**: "Fixed bug"  
   → Use: "Fixed crash when uploading files >100MB"

3. **Internal Jargon**: "Updated CI pipeline"  
   → Use: "Faster release cycle (weekly instead of monthly)"

4. **No User Benefit**: "Implemented feature X"  
   → Use: "Added feature X to reduce manual work by 50%"

5. **Vague**: "Various improvements"  
   → Use: Specific list of improvements

6. **Missing Migration**: "Changed API endpoint"  
   → Use: Include before/after examples and steps

## Resources

- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Release Notes Guide](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
