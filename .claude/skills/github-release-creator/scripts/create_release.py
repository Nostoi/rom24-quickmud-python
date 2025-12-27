#!/usr/bin/env python3
"""
Create GitHub release with auto-generated notes or from CHANGELOG.md
Supports draft releases, pre-releases, and asset uploads
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run shell command and return output"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    if result.returncode != 0 and capture_output:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip() if capture_output else None


def check_prerequisites():
    """Check if required tools are installed"""
    # Check gh CLI
    try:
        run_command("gh --version")
    except:
        print("Error: GitHub CLI (gh) not installed")
        print("Install: brew install gh")
        sys.exit(1)
    
    # Check authentication
    try:
        run_command("gh auth status")
    except:
        print("Error: Not authenticated with GitHub")
        print("Run: gh auth login")
        sys.exit(1)


def extract_changelog_notes(version):
    """Extract release notes from CHANGELOG.md"""
    changelog = Path("CHANGELOG.md")
    if not changelog.exists():
        return None
    
    content = changelog.read_text()
    lines = content.split('\n')
    
    # Find section for this version
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if f"## [{version}]" in line:
            start_idx = i + 1
        elif start_idx is not None and line.startswith("## ["):
            end_idx = i
            break
    
    if start_idx is None:
        return None
    
    if end_idx is None:
        end_idx = len(lines)
    
    notes = '\n'.join(lines[start_idx:end_idx]).strip()
    return notes if notes else None


def create_release(args):
    """Create GitHub release"""
    version = args.version
    if not version.startswith('v'):
        version = f"v{version}"
    
    # Build gh release create command
    cmd_parts = ["gh", "release", "create", version]
    
    # Title
    if args.title:
        cmd_parts.extend(["--title", f'"{args.title}"'])
    else:
        cmd_parts.extend(["--title", f'"{version}"'])
    
    # Release notes
    if args.notes:
        cmd_parts.extend(["--notes", f'"{args.notes}"'])
    elif args.notes_file:
        cmd_parts.extend(["--notes-file", args.notes_file])
    elif args.generate_notes:
        cmd_parts.append("--generate-notes")
    else:
        # Try to extract from CHANGELOG.md
        notes = extract_changelog_notes(version.lstrip('v'))
        if notes:
            # Save to temp file
            notes_file = f"/tmp/release_notes_{version}.md"
            Path(notes_file).write_text(notes)
            cmd_parts.extend(["--notes-file", notes_file])
            print(f"Using release notes from CHANGELOG.md")
        else:
            cmd_parts.append("--generate-notes")
            print("No CHANGELOG.md entry found, using auto-generated notes")
    
    # Options
    if args.draft:
        cmd_parts.append("--draft")
    if args.prerelease:
        cmd_parts.append("--prerelease")
    if args.target:
        cmd_parts.extend(["--target", args.target])
    
    # Assets
    if args.assets:
        cmd_parts.extend(args.assets)
    
    # Execute command
    cmd = ' '.join(cmd_parts)
    print(f"Creating release: {version}")
    print(f"Command: {cmd}")
    print()
    
    run_command(cmd, capture_output=False)
    
    print(f"\n✓ Release {version} created successfully!")
    
    # Show release URL
    url = run_command(f"gh release view {version} --json url -q .url")
    print(f"View at: {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub release with smart defaults"
    )
    parser.add_argument(
        "version",
        help="Version number (with or without 'v' prefix)"
    )
    parser.add_argument(
        "-t", "--title",
        help="Release title"
    )
    parser.add_argument(
        "-n", "--notes",
        help="Release notes (inline)"
    )
    parser.add_argument(
        "-f", "--notes-file",
        help="Release notes from file"
    )
    parser.add_argument(
        "-g", "--generate-notes",
        action="store_true",
        help="Auto-generate release notes from commits"
    )
    parser.add_argument(
        "-d", "--draft",
        action="store_true",
        help="Create as draft release"
    )
    parser.add_argument(
        "-p", "--prerelease",
        action="store_true",
        help="Mark as pre-release"
    )
    parser.add_argument(
        "--target",
        help="Target branch or commit SHA"
    )
    parser.add_argument(
        "-a", "--assets",
        nargs="+",
        help="Asset files to upload"
    )
    
    args = parser.parse_args()
    
    check_prerequisites()
    create_release(args)


if __name__ == "__main__":
    main()
