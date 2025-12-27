# GitHub Release Workflows

Common workflows for creating and managing GitHub releases.

## Workflow 1: Standard Release

**Use Case**: Regular version release with CHANGELOG.md

```bash
# 1. Update version numbers
# Update pyproject.toml, package.json, README.md, etc.

# 2. Update CHANGELOG.md
# Add new version section with changes

# 3. Commit changes
git add -A
git commit -m "Release v1.0.0: Feature description"

# 4. Create and push tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 5. Validate prerequisites
./scripts/validate_release.sh 1.0.0

# 6. Create release
./scripts/create_release.sh 1.0.0 "v1.0.0 - Feature Name"

# Alternative: Use Python script
./scripts/create_release.py 1.0.0 -t "v1.0.0 - Feature Name"
```

## Workflow 2: Auto-Generated Release Notes

**Use Case**: Quick release using conventional commits

```bash
# 1. Commit and tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 2. Create release with auto-generated notes
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --generate-notes

# Or using Python script:
./scripts/create_release.py 1.0.0 \
  -t "Release v1.0.0" \
  --generate-notes
```

## Workflow 3: Pre-release (Beta/RC)

**Use Case**: Testing release before final version

```bash
# 1. Create pre-release tag
git tag -a v1.0.0-beta.1 -m "Beta release v1.0.0-beta.1"
git push origin main --tags

# 2. Create pre-release
gh release create v1.0.0-beta.1 \
  --title "Beta Release v1.0.0-beta.1" \
  --notes "Beta testing release - not for production" \
  --prerelease

# Or using Python script:
./scripts/create_release.py 1.0.0-beta.1 \
  -t "Beta Release v1.0.0-beta.1" \
  -n "Beta testing release" \
  --prerelease
```

## Workflow 4: Draft Release for Review

**Use Case**: Create release but don't publish yet

```bash
# 1. Create draft release
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes-file CHANGELOG.md \
  --draft

# 2. Review release on GitHub

# 3. Publish when ready
gh release edit v1.0.0 --draft=false

# Or using Python script:
./scripts/create_release.py 1.0.0 \
  -t "Release v1.0.0" \
  --draft
```

## Workflow 5: Release with Binary Assets

**Use Case**: Release with compiled binaries, packages, etc.

```bash
# 1. Build assets
npm run build
# or
python -m build

# 2. Create release with assets
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes "Release with binaries" \
  dist/*.tar.gz \
  dist/*.whl \
  dist/*.zip

# Or using Python script:
./scripts/create_release.py 1.0.0 \
  -t "Release v1.0.0" \
  -n "Release with binaries" \
  -a dist/*.tar.gz dist/*.whl
```

## Workflow 6: Hotfix Release

**Use Case**: Emergency bug fix release

```bash
# 1. Fix bug and commit
git commit -am "fix: Critical bug fix"

# 2. Bump patch version
# Update version 1.0.0 -> 1.0.1

# 3. Tag and push
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin main --tags

# 4. Quick release
gh release create v1.0.1 \
  --title "Hotfix v1.0.1" \
  --notes "Critical bug fixes" \
  --latest
```

## Workflow 7: Fix/Update Existing Release

**Use Case**: Update release notes or re-upload assets

```bash
# Update release notes
gh release edit v1.0.0 \
  --notes "Updated release notes"

# Upload additional assets
gh release upload v1.0.0 new-file.zip

# Mark as latest
gh release edit v1.0.0 --latest

# Convert draft to published
gh release edit v1.0.0 --draft=false
```

## Workflow 8: Delete and Recreate Release

**Use Case**: Major mistakes in release

```bash
# 1. Delete release (keeps tag)
gh release delete v1.0.0 --yes

# 2. Recreate release
gh release create v1.0.0 \
  --title "Corrected Release v1.0.0" \
  --notes "Fixed release notes"

# 3. Or delete tag too and start fresh
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
# Then create new tag and release
```

## Workflow 9: Batch Release Creation

**Use Case**: Create releases for multiple versions

```bash
#!/bin/bash
# Create releases for all tags without releases

for tag in $(git tag -l); do
  # Check if release exists
  if ! gh release view "$tag" &>/dev/null; then
    echo "Creating release for $tag..."
    gh release create "$tag" \
      --title "Release $tag" \
      --generate-notes
  fi
done
```

## Workflow 10: Release from CI/CD

**Use Case**: Automated release in GitHub Actions

```yaml
# .github/workflows/release.yml
name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
      
      - name: Extract changelog
        run: |
          sed -n "/^## \[${{ steps.version.outputs.VERSION }}\]/,/^## \[/p" CHANGELOG.md | sed '$d' > /tmp/notes.md
      
      - name: Create release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create ${{ github.ref_name }} \
            --title "Release ${{ github.ref_name }}" \
            --notes-file /tmp/notes.md
```

## Decision Matrix

| Scenario | Workflow | Command |
|----------|----------|---------|
| Regular release with CHANGELOG | #1 Standard Release | `./scripts/create_release.sh` |
| Quick release, auto notes | #2 Auto-Generated | `gh release create --generate-notes` |
| Beta/RC testing | #3 Pre-release | `--prerelease` flag |
| Review before publish | #4 Draft | `--draft` flag |
| Binary distribution | #5 With Assets | Include file paths |
| Emergency bug fix | #6 Hotfix | Patch version bump |
| Fix release notes | #7 Update | `gh release edit` |
| Start over | #8 Delete/Recreate | `gh release delete` |
| Multiple versions | #9 Batch | Loop script |
| Automated CI/CD | #10 GitHub Actions | Workflow file |

## Best Practices

1. **Always validate** before creating release
2. **Use semantic versioning** consistently
3. **Write clear release notes** with changes
4. **Test pre-releases** before final release
5. **Include migration guides** for breaking changes
6. **Upload checksums** with binary assets
7. **Tag consistently** (always use `v` prefix or never)
8. **Review drafts** before publishing
9. **Keep CHANGELOG.md** synchronized
10. **Automate when possible** but review outputs
