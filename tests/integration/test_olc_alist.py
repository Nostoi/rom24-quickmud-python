"""OLC-023 — `do_alist` lists registered areas.

ROM Reference: src/olc.c:1478-1502.

Pre-fix bug: `do_alist` iterated `getattr(registry, "areas", [])` which
does not exist on `mud.registry` (the real attribute is `area_registry`,
a vnum→Area dict). The pre-fix command returned only a header row on a
live system. Also drifted on field names (`filename` vs `file_name`) and
used a 1-indexed counter for the first column where ROM emits
`pArea->vnum`.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_olc import do_alist
from mud.models.area import Area
from mud.models.character import Character
from mud.registry import area_registry


@pytest.fixture
def player_char():
    char = Character()
    char.name = "Tester"
    char.is_npc = False
    return char


@pytest.fixture
def alist_areas():
    a1 = Area(
        vnum=42,
        name="Mirror Lake",
        file_name="mirror.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="Bob",
    )
    a2 = Area(
        vnum=7,
        name="Grim Fortress",
        file_name="grim.are",
        min_vnum=2000,
        max_vnum=2099,
        security=9,
        builders="Alice",
    )
    area_registry[42] = a1
    area_registry[7] = a2
    yield [a1, a2]
    area_registry.pop(42, None)
    area_registry.pop(7, None)


def test_do_alist_lists_registered_areas(player_char, alist_areas) -> None:
    out = do_alist(player_char, "")
    # Header row present.
    assert "Num" in out and "Area Name" in out and "Builders" in out
    # Both areas listed by name + filename.
    assert "Mirror Lake" in out
    assert "mirror.are" in out
    assert "Grim Fortress" in out
    assert "grim.are" in out
    # mirrors ROM src/olc.c:1494 — first column is `pArea->vnum`, not a counter.
    assert "[ 42]" in out or "[42]" in out
    assert "[  7]" in out or "[ 7]" in out


def test_do_alist_npc_returns_empty(alist_areas) -> None:
    npc = Character()
    npc.name = "Mob"
    npc.is_npc = True
    assert do_alist(npc, "") == ""


def test_do_alist_empty_registry_returns_header_only(player_char) -> None:
    # mirrors ROM src/olc.c:1487-1490 — header always emitted.
    original = dict(area_registry)
    area_registry.clear()
    try:
        out = do_alist(player_char, "")
        assert "Area Name" in out
        # No area rows beyond the header.
        lines = [ln for ln in out.split("\n") if ln.strip()]
        assert len(lines) == 1
    finally:
        area_registry.update(original)


def test_do_alist_uses_file_name_not_filename(player_char) -> None:
    # Regression: pre-fix code used `area.filename` (does not exist on Area model).
    a = Area(vnum=99, name="Probe", file_name="probe.are", min_vnum=0, max_vnum=0, security=0, builders="")
    area_registry[99] = a
    try:
        out = do_alist(player_char, "")
        assert "probe.are" in out
    finally:
        area_registry.pop(99, None)
