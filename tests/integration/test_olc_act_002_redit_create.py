"""OLC_ACT-002 — `redit create <vnum>` subcommand.

Mirrors ROM `src/olc_act.c:1716-1766` (`redit_create`) and `src/olc.c:770-787`
(`do_redit` create branch). Defaults from `src/mem.c:181-218` (`new_room_index`):
heal_rate=100, mana_rate=100, all other fields zeroed/empty. After successful
create, ROM moves the builder INTO the new room via char_from_room/char_to_room.
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

    char.is_npc = False
    char.room = home_room
    home_room.people.append(char)
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


def test_redit_create_requires_vnum(builder_char):
    # mirrors ROM src/olc.c:772-775.
    result = cmd_redit(builder_char, "create")
    assert result == "Syntax:  edit room create [vnum]\n\r"


def test_redit_create_zero_vnum_rejected(builder_char):
    result = cmd_redit(builder_char, "create 0")
    assert result == "Syntax:  edit room create [vnum]\n\r"


def test_redit_create_unassigned_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:1733-1738.
    result = cmd_redit(builder_char, "create 5000")
    assert result == "REdit:  That vnum is not assigned an area.\n\r"


def test_redit_create_existing_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:1746-1750.
    result = cmd_redit(builder_char, "create 1000")
    assert result == "REdit:  Room vnum already exists.\n\r"


def test_redit_create_returns_rom_message(builder_char):
    # mirrors ROM src/olc_act.c:1764.
    result = cmd_redit(builder_char, "create 1050")
    assert result == "Room created.\n\r"


def test_redit_create_registers_room(builder_char, builder_area):
    cmd_redit(builder_char, "create 1050")
    assert 1050 in room_registry
    new_room = room_registry[1050]
    assert isinstance(new_room, Room)
    assert new_room.vnum == 1050
    assert new_room.area is builder_area


def test_redit_create_uses_rom_defaults(builder_char):
    cmd_redit(builder_char, "create 1050")
    new_room = room_registry[1050]
    # mirrors ROM src/mem.c:206-215 — new_room_index defaults.
    assert new_room.heal_rate == 100
    assert new_room.mana_rate == 100
    assert new_room.room_flags == 0
    assert new_room.light == 0
    assert new_room.sector_type == 0
    assert new_room.clan == 0
    assert new_room.exits == [None] * 6
    # `people` is non-empty after create because ROM relocates the builder
    # into the new room (src/olc.c:781-782); `contents` should be empty.
    assert new_room.contents == []


def test_redit_create_moves_builder_into_new_room(builder_char, home_room):
    # mirrors ROM src/olc.c:781-782 — char_from_room + char_to_room after create.
    cmd_redit(builder_char, "create 1050")
    new_room = room_registry[1050]
    assert builder_char.room is new_room
    assert builder_char in new_room.people
    assert builder_char not in home_room.people


def test_redit_create_descriptor_edits_new_room(builder_char):
    cmd_redit(builder_char, "create 1050")
    session = builder_char.desc
    new_room = room_registry[1050]
    # mirrors ROM src/olc.c:780 — desc->editor = ED_ROOM.
    assert session.editor == "redit"
    assert session.editor_state.get("room") is new_room
