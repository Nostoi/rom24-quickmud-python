"""OLC_ACT-004 — `redit <vnum>` silent-teleport subcommand.

Mirrors ROM `src/olc.c:789-808` (`do_redit` vnum branch). Builder names a
target vnum, gets validated for existence and IS_BUILDER, then is silently
relocated into the target room via char_from_room/char_to_room (no act()
broadcasts — exactly what ROM does). The descriptor's edit pointer is then
set to the target room.

Locked decision (audit doc): reuse the existing silent primitives
`_char_from_room`/`_char_to_room` from `mud.commands.imm_commands` — these
are exactly what ROM uses (no broadcasts), so no new movement infra needed.
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
def restricted_area():
    area = Area(
        vnum=2,
        name="Restricted Area",
        file_name="restricted.are",
        min_vnum=2000,
        max_vnum=2099,
        security=9,
        builders="someone_else",
    )
    area_registry[2] = area
    return area


@pytest.fixture
def home_room(builder_area):
    room = Room(vnum=1000, name="Home", area=builder_area)
    room_registry[1000] = room
    return room


@pytest.fixture
def target_room(builder_area):
    room = Room(vnum=1050, name="Target", area=builder_area)
    room_registry[1050] = room
    return room


@pytest.fixture
def restricted_room(restricted_area):
    room = Room(vnum=2050, name="Restricted", area=restricted_area)
    room_registry[2050] = room
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


def test_redit_vnum_nonexistent_room(builder_char):
    # mirrors ROM src/olc.c:793-797.
    result = cmd_redit(builder_char, "9999")
    assert result == "REdit : Nonexistant room.\n\r"


def test_redit_vnum_security_gate(builder_char, restricted_room):
    # mirrors ROM src/olc.c:799-804 — IS_BUILDER on TARGET area.
    builder_char.pcdata.security = 0  # downgrade so restricted_area (sec=9) blocks
    result = cmd_redit(builder_char, "2050")
    assert result == "REdit : Insufficient security to modify room.\n\r"


def test_redit_vnum_relocates_builder(builder_char, target_room, home_room):
    # mirrors ROM src/olc.c:806-807 — char_from_room + char_to_room.
    cmd_redit(builder_char, "1050")
    assert builder_char.room is target_room
    assert builder_char in target_room.people
    assert builder_char not in home_room.people


def test_redit_vnum_silent_no_broadcasts(builder_char, target_room, home_room, monkeypatch):
    # mirrors ROM — uses raw `char_from_room`/`char_to_room`, NOT a noisy
    # movement helper. No "$n leaves north" / "$n has arrived" act() calls.
    broadcasts: list[str] = []

    def capture_act(*args, **kwargs):
        broadcasts.append(str(args))

    import mud.utils.act as act_mod

    monkeypatch.setattr(act_mod, "act", capture_act, raising=False)
    cmd_redit(builder_char, "1050")
    # The teleport must not emit any messages.
    assert broadcasts == []


def test_redit_vnum_sets_edit_pointer(builder_char, target_room):
    # mirrors ROM src/olc.c:817 — desc->pEdit = pRoom (after teleport).
    cmd_redit(builder_char, "1050")
    session = builder_char.desc
    assert session.editor == "redit"
    assert session.editor_state.get("room") is target_room
