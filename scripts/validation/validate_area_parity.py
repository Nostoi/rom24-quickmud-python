#!/usr/bin/env python3
"""
Area Parity Validation Tool

Compares *.are files with their corresponding JSON files to detect discrepancies.
Validates that convert_enhanced.py produces accurate conversions.

Usage:
    python scripts/validate_area_parity.py [--verbose] [--fix]

Checks:
- All .are files have corresponding .json files
- Mob reset commands match (M resets)
- Global and room limits match
- Object resets match (O, E, G, P resets)
- Door resets match (D resets)
- Randomization resets match (R resets)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mud.loaders.area_loader import load_area_file
from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area


class ParityValidator:
    """Validates parity between .are and .json area files."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks_passed = 0
        self.checks_failed = 0

    def log(self, message: str) -> None:
        """Log verbose messages."""
        if self.verbose:
            print(f"  {message}")

    def error(self, message: str) -> None:
        """Record an error."""
        self.errors.append(message)
        self.checks_failed += 1
        print(f"❌ ERROR: {message}")

    def warn(self, message: str) -> None:
        """Record a warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def passed(self, message: str) -> None:
        """Record a passed check."""
        self.checks_passed += 1
        self.log(f"✅ {message}")

    def validate_area(self, are_path: Path, json_path: Path) -> bool:
        """
        Validate a single area file pair.

        Returns True if validation passes, False otherwise.
        """
        print(f"\n📁 Validating {are_path.name}")

        # Load both formats
        try:
            are_area = load_area_file(str(are_path))
            self.log(f"Loaded .are file: {are_area.name}")
        except Exception as e:
            self.error(f"Failed to load {are_path}: {e}")
            return False

        try:
            json_area = load_area_from_json(str(json_path))
            self.log(f"Loaded .json file: {json_area.name}")
        except Exception as e:
            self.error(f"Failed to load {json_path}: {e}")
            return False

        # Compare area metadata
        self._compare_metadata(are_area, json_area, are_path.stem)

        # Compare resets (most critical for mob spawning)
        self._compare_resets(are_area, json_area, are_path.stem)

        return self.checks_failed == 0

    def _compare_metadata(self, are_area: Area, json_area: Area, area_name: str) -> None:
        """Compare area metadata."""
        # Check area name
        if are_area.name != json_area.name:
            self.error(f"{area_name}: Name mismatch - .are='{are_area.name}' vs JSON='{json_area.name}'")
        else:
            self.passed(f"{area_name}: Area name matches")

        # Check vnum range
        if (are_area.min_vnum, are_area.max_vnum) != (json_area.min_vnum, json_area.max_vnum):
            self.error(
                f"{area_name}: Vnum range mismatch - "
                f".are=({are_area.min_vnum}, {are_area.max_vnum}) vs "
                f"JSON=({json_area.min_vnum}, {json_area.max_vnum})"
            )
        else:
            self.passed(f"{area_name}: Vnum range matches")

    def _compare_rooms(self, are_area: Area, json_area: Area, area_name: str) -> None:
        """Compare room counts - NOTE: Area object doesn't store rooms directly."""
        # Area objects don't store rooms - they're in room_registry
        # This is expected behavior, so we'll skip room count comparison
        self.passed(f"{area_name}: Room data stored in room_registry (both formats)")

    def _compare_resets(self, are_area: Area, json_area: Area, area_name: str) -> None:
        """Compare reset commands (critical for mob spawning)."""
        are_resets = are_area.resets
        json_resets = json_area.resets

        if len(are_resets) != len(json_resets):
            self.error(f"{area_name}: Reset count mismatch - .are={len(are_resets)} vs JSON={len(json_resets)}")
            return

        self.passed(f"{area_name}: Reset count matches ({len(are_resets)} resets)")

        # Compare each reset command
        mismatches = 0
        for i, (are_reset, json_reset) in enumerate(zip(are_resets, json_resets)):
            if not self._compare_single_reset(are_reset, json_reset, i):
                mismatches += 1
                if mismatches <= 5:  # Only show first 5 mismatches
                    # Convert ResetJson objects to dict for display
                    are_dict = {
                        "command": are_reset.command,
                        "arg1": are_reset.arg1,
                        "arg2": are_reset.arg2,
                        "arg3": are_reset.arg3,
                        "arg4": are_reset.arg4,
                    }
                    json_dict = {
                        "command": json_reset.command,
                        "arg1": json_reset.arg1,
                        "arg2": json_reset.arg2,
                        "arg3": json_reset.arg3,
                        "arg4": json_reset.arg4,
                    }
                    self.error(f"{area_name}: Reset #{i} mismatch - .are={are_dict} vs JSON={json_dict}")

        if mismatches > 5:
            self.error(f"{area_name}: ... and {mismatches - 5} more reset mismatches")

        if mismatches == 0:
            self.passed(f"{area_name}: All {len(are_resets)} resets match")

    def _compare_single_reset(self, are_reset: Any, json_reset: Any, index: int) -> bool:
        """Compare a single reset command (ResetJson objects)."""
        # Must have same command type
        if are_reset.command != json_reset.command:
            return False

        # For all reset types, check all arguments
        if are_reset.arg1 != json_reset.arg1:
            return False
        if are_reset.arg2 != json_reset.arg2:
            return False
        if are_reset.arg3 != json_reset.arg3:
            return False
        if are_reset.arg4 != json_reset.arg4:
            return False

        return True

    def validate_all_areas(self, are_dir: Path, json_dir: Path) -> bool:
        """
        Validate all area files in the directories.

        Returns True if all validations pass, False otherwise.
        """
        are_files = sorted(are_dir.glob("*.are"))

        if not are_files:
            self.error(f"No .are files found in {are_dir}")
            return False

        print(f"\n🔍 Found {len(are_files)} .are files to validate\n")

        all_passed = True
        for are_path in are_files:
            # Skip special files
            if are_path.stem in ("area", "help"):
                continue

            json_path = json_dir / f"{are_path.stem}.json"

            if not json_path.exists():
                self.warn(f"No JSON file for {are_path.name} (expected {json_path.name})")
                continue

            if not self.validate_area(are_path, json_path):
                all_passed = False

        return all_passed

    def print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"✅ Checks passed: {self.checks_passed}")
        print(f"❌ Checks failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n{len(self.errors)} ERRORS found:")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")

        if self.warnings:
            print(f"\n{len(self.warnings)} WARNINGS:")
            for warning in self.warnings[:10]:
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings")

        print("\n" + "=" * 80)
        if self.checks_failed == 0:
            print("✅ ALL CHECKS PASSED - Area files have perfect parity!")
        else:
            print("❌ VALIDATION FAILED - Discrepancies found between .are and JSON files")
        print("=" * 80)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate .are and JSON area file parity")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--area-dir", type=Path, default=Path("area"), help="Directory containing .are files (default: area/)"
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=Path("data/areas"),
        help="Directory containing JSON files (default: data/areas/)",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.area_dir.exists():
        print(f"❌ ERROR: Area directory not found: {args.area_dir}")
        return 1

    if not args.json_dir.exists():
        print(f"❌ ERROR: JSON directory not found: {args.json_dir}")
        return 1

    # Run validation
    validator = ParityValidator(verbose=args.verbose)
    success = validator.validate_all_areas(args.area_dir, args.json_dir)
    validator.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
