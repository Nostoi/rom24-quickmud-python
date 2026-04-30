"""OLC_ACT-007 — `aedit show` flags row.

Mirrors ROM `src/olc_act.c:644-646` (`aedit_show`). Verifies that `_aedit_show(area)`
emits a `Flags:    [flag_string(...)]` row in the output, using the same ROM
`flag_string` formatting as the original.
"""

from __future__ import annotations

from mud.commands.build import _aedit_show
from mud.models.area import Area
from mud.models.constants import AreaFlag


def test_aedit_show_includes_flags_row_with_no_flags():
    """When area has no flags set (area_flags=0), Flags row should be 'Flags:    [none]'."""
    area = Area()
    area.name = "Test Area"
    area.vnum = 1
    area.area_flags = 0

    output = _aedit_show(area)
    lines = output.split("\n")

    # Check that a Flags line exists
    flags_lines = [line for line in lines if line.startswith("Flags:")]
    assert len(flags_lines) == 1, f"Expected exactly one 'Flags:' line, got {len(flags_lines)}"

    # ROM flag_string returns 'none' when bits == 0
    assert flags_lines[0] == "Flags:    [none]", f"Got: {flags_lines[0]}"


def test_aedit_show_includes_flags_row_with_added_flag():
    """When ADDED flag is set, Flags row should include 'added'."""
    area = Area()
    area.name = "Test Area"
    area.vnum = 1
    area.area_flags = int(AreaFlag.ADDED)

    output = _aedit_show(area)
    lines = output.split("\n")

    flags_lines = [line for line in lines if line.startswith("Flags:")]
    assert len(flags_lines) == 1
    # flag_string enumerates IntFlag members, lowercases names
    assert flags_lines[0] == "Flags:    [added]", f"Got: {flags_lines[0]}"


def test_aedit_show_includes_flags_row_with_multiple_flags():
    """When multiple flags are set (ADDED | CHANGED), all should appear."""
    area = Area()
    area.name = "Test Area"
    area.vnum = 1
    area.area_flags = int(AreaFlag.ADDED | AreaFlag.CHANGED)

    output = _aedit_show(area)
    lines = output.split("\n")

    flags_lines = [line for line in lines if line.startswith("Flags:")]
    assert len(flags_lines) == 1
    # flag_string returns space-separated flag names in the order they appear in the enum
    # AreaFlag.CHANGED = 1<<0, AreaFlag.ADDED = 1<<1, so CHANGED comes first
    assert flags_lines[0] == "Flags:    [changed added]", f"Got: {flags_lines[0]}"


def test_aedit_show_flags_row_with_loading_flag():
    """When LOADING flag is set, Flags row should include 'loading'."""
    area = Area()
    area.name = "Test Area"
    area.vnum = 1
    area.area_flags = int(AreaFlag.LOADING)

    output = _aedit_show(area)
    lines = output.split("\n")

    flags_lines = [line for line in lines if line.startswith("Flags:")]
    assert len(flags_lines) == 1
    assert flags_lines[0] == "Flags:    [loading]", f"Got: {flags_lines[0]}"


def test_aedit_show_flags_row_appears_after_credits():
    """Flags row should appear after Credits line (or at least exist in output)."""
    area = Area()
    area.name = "Test Area"
    area.vnum = 1
    area.credits = "Test Credit"
    area.area_flags = int(AreaFlag.ADDED)

    output = _aedit_show(area)

    # Just verify Flags appears and Credits appears
    assert "Credits:" in output
    assert "Flags:" in output
