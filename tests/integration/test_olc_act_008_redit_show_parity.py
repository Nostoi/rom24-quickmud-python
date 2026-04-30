"""OLC_ACT-008: `redit show` byte-parity with ROM `redit_show`.

Mirrors ROM `src/olc_act.c:1068-1236` and the per-table name strings in
`src/tables.c:339-397` (sector_flags, room_flags, exit_flags).
"""

from __future__ import annotations

from mud.commands.build import _room_summary
from mud.models.area import Area
from mud.models.constants import Direction, RoomFlag, Sector
from mud.models.room import Exit, Room


def _make_room(**overrides) -> Room:
    area = Area(vnum=42, name="Test Area")
    room = Room(vnum=4205, name="A Test Room")
    room.area = area
    room.description = "A plain stone chamber.\n"
    room.sector_type = int(Sector.WATER_SWIM)
    room.room_flags = int(RoomFlag.ROOM_DARK | RoomFlag.ROOM_SAFE)
    room.heal_rate = 100
    room.mana_rate = 100
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def test_sector_label_matches_rom_table_swim() -> None:
    """ROM tables.c:391 — SECT_WATER_SWIM emits "swim", not "water_swim"."""
    room = _make_room(sector_type=int(Sector.WATER_SWIM))
    output = _room_summary(room)
    assert "Sector:     [swim]" in output
    assert "water_swim" not in output


def test_sector_label_matches_rom_table_noswim() -> None:
    """ROM tables.c:392 — SECT_WATER_NOSWIM emits "noswim", not "water_noswim"."""
    room = _make_room(sector_type=int(Sector.WATER_NOSWIM))
    output = _room_summary(room)
    assert "Sector:     [noswim]" in output
    assert "water_noswim" not in output


def test_exit_line_has_leading_space_before_exit_flags() -> None:
    """ROM olc_act.c:1184-1196 — exit line is `... Key: [%5d]  Exit flags: [...]`
    with TWO spaces between `]` and `Exit flags` because ROM's first sprintf
    ends in `] ` and then strcat appends ` Exit flags: [`.
    """
    room = _make_room()
    target = Room(vnum=4206, name="Other")
    exit_obj = Exit(to_room=target, vnum=4206, exit_info=0, rs_flags=0, key=0)
    room.exits[int(Direction.NORTH)] = exit_obj
    output = _room_summary(room)
    assert "Key: [    0]  Exit flags:" in output


def test_exit_line_capitalizes_non_reset_flags() -> None:
    """ROM olc_act.c:1190-1219 — flags present in exit_info but not in rs_flags
    (i.e. set by transient state, not the default reset state) are UPPERCASED.
    """
    from mud.models.constants import EX_CLOSED, EX_ISDOOR, EX_LOCKED

    room = _make_room()
    target = Room(vnum=4207, name="Other")
    # rs_flags has door+closed; exit_info adds locked transiently.
    exit_obj = Exit(
        to_room=target,
        vnum=4207,
        exit_info=EX_ISDOOR | EX_CLOSED | EX_LOCKED,
        rs_flags=EX_ISDOOR | EX_CLOSED,
        key=0,
    )
    room.exits[int(Direction.EAST)] = exit_obj
    output = _room_summary(room)
    assert "Exit flags: [door closed LOCKED]" in output
