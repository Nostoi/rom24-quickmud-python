"""OLC_ACT-003 — `redit reset` subcommand (dispatcher gap, not a builder).

Mirrors ROM `src/olc.c:757-769` (`do_redit` reset branch). Validates that
the builder's current room has its resets re-applied. Verifies ROM message,
security gate, and reset side-effect.

Note: ROM calls `reset_room(pRoom)` (per src/olc.c:765); Python reuses the
existing `apply_resets(area)` since no per-room helper exists yet. This is a
documented broader-scope divergence — fully closing it would require porting
ROM's `src/db.c:reset_room`.
"""

from __future__ import annotations

import pytest

from mud.commands.build import cmd_redit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO
from mud.models.room import Room
from mud.net.session import Session
from mud.registry import area_registry, room_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    area_snap = dict(area_registry)
    room_snap = dict(room_registry)
    area_registry.clear()
    room_registry.clear()
    yield
    area_registry.clear()
    area_registry.update(area_snap)
    room_registry.clear()
    room_registry.update(room_snap)


@pytest.fixture
def builder_area():
    area = Area(
        vnum=1,
        name="Builder Area",
        file_name="builder.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder",
    )
    area_registry[1] = area
    return area


@pytest.fixture
def home_room(builder_area):
    room = Room(vnum=1000, name="Home", area=builder_area)
    room_registry[1000] = room
    return room


@pytest.fixture
def builder_char(home_room):
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    char.room = home_room
    home_room.people.append(char)
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture
def non_builder_char(home_room):
    from mud.models.character import Character

    char = Character()
    char.name = "Visitor"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    char.room = home_room
    home_room.people.append(char)
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


def test_redit_reset_returns_rom_message(builder_char):
    # mirrors ROM src/olc.c:766 — verbatim "Room reset.\n\r".
    result = cmd_redit(builder_char, "reset")
    assert result == "Room reset.\n\r"


def test_redit_reset_security_gate_blocks_non_builder(non_builder_char):
    # mirrors ROM src/olc.c:759-763.
    result = cmd_redit(non_builder_char, "reset")
    assert result == "Insufficient security to modify room.\n\r"


def test_redit_reset_marks_area_changed(builder_char, builder_area):
    builder_area.changed = False
    cmd_redit(builder_char, "reset")
    assert builder_area.changed is True


def test_redit_reset_invokes_reset_machinery(builder_char, builder_area, monkeypatch):
    """Verify the reset is actually attempted (calls `apply_resets`)."""
    # mirrors ROM src/olc.c:765 `reset_room(pRoom)` — Python calls
    # `apply_resets(area)` as the closest existing equivalent (broader scope).
    calls: list[Area] = []

    def fake_apply_resets(area):
        calls.append(area)

    import mud.commands.build as build_mod

    monkeypatch.setattr(build_mod, "_apply_resets_for_redit", fake_apply_resets)
    cmd_redit(builder_char, "reset")
    assert calls == [builder_area]
