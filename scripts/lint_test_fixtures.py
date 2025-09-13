#!/usr/bin/env python3
"""Fail if tests bypass standard fixtures for objects/placement.

Looks for these anti-patterns in tests/ (excluding conftest and README):
- Direct imports of ObjIndex or Object from mud.models.*
- room.add_object(spawn_object(...)) inline placement
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def main() -> int:
    bad: list[tuple[Path, int, str]] = []
    import_re = re.compile(r"^\s*from\s+mud\.models\.(obj|object)\s+import\s+(ObjIndex|Object)")
    place_re = re.compile(r"room\.add_object\(\s*spawn_object\(")
    allow_move_files = {
        "test_movement_costs.py",
        "test_healer.py",
        "test_game_loop.py",
        "test_game_loop_wait_daze.py",
        "test_player_save_format.py",
        "test_advancement.py",
    }
    for path in TESTS.rglob("*.py"):
        # allow in conftest where fixtures are defined
        if path.name in {"conftest.py"}:
            continue
        # skip docs
        if path.name == "README.md":
            continue
        try:
            text = path.read_text()
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if import_re.search(line):
                bad.append((path, i, line.strip()))
            if place_re.search(line):
                bad.append((path, i, line.strip()))
            # Detect manual movement fields initializations in non-allowlisted files
            if path.name not in allow_move_files:
                if re.search(r"\b(move|max_move|affected_by|wait)\s*=\s*\d+", line):
                    bad.append((path, i, line.strip()))
    if bad:
        print("Test fixture lint failures (prefer fixtures over raw constructs):", file=sys.stderr)
        for p, i, l in bad:
            print(f"- {p}:{i}: {l}", file=sys.stderr)
        print("\nUse fixtures: object_factory/place_object_factory/portal_factory.", file=sys.stderr)
        return 1
    print("OK: test fixture usage looks clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
