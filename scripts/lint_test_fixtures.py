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
    any_place_re = re.compile(r"\broom\.add_object\(")
    create_char_re = re.compile(r"create_test_character\(.*\)")
    spawn_mob_re = re.compile(r"spawn_mob\(.*\)")
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
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            if import_re.search(line):
                bad.append((path, i, line.strip()))
            if place_re.search(line):
                bad.append((path, i, line.strip() + "  # prefer place_object_factory(room_vnum, vnum=...)"))
            elif any_place_re.search(line):
                # Direct placement without spawn_object; suggest place_object_factory with proto_kwargs
                bad.append((path, i, line.strip() + "  # prefer place_object_factory(room_vnum, proto_kwargs={...})"))
            # Detect manual movement fields initializations in non-allowlisted files
            if path.name not in allow_move_files:
                if re.search(r"\b(move|max_move|affected_by|wait)\s*=\s*\d+", line):
                    bad.append((path, i, line.strip()))
            # Suggest movable_char_factory if char creation is followed by movement tweaks
            if create_char_re.search(line) and path.name not in allow_move_files:
                window = "\n".join(lines[i : i + 5])
                if re.search(r"\b(move|max_move|affected_by|wait)\s*=", window):
                    bad.append((path, i, line.strip() + "  # consider movable_char_factory"))
            # Suggest movable_mob_factory similarly for mobs
            if spawn_mob_re.search(line) and path.name not in allow_move_files:
                window = "\n".join(lines[i : i + 5])
                if re.search(r"\b(move|max_move|affected_by|wait)\s*=", window):
                    bad.append((path, i, line.strip() + "  # consider movable_mob_factory"))
    if bad:
        print("Test fixture lint failures (prefer fixtures over raw constructs):", file=sys.stderr)
        for p, i, line in bad:
            print(f"- {p}:{i}: {line}", file=sys.stderr)
        print(
            "\nUse fixtures: ensure_can_move/movable_char_factory/movable_mob_factory and object_factory/place_object_factory/portal_factory.",
            file=sys.stderr,
        )
        return 1
    print("OK: test fixture usage looks clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
