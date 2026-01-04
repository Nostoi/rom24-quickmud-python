"""Integration tests for do_exits command ROM C parity.

Tests verify do_exits implements all ROM C features from act_info.c lines 1393-1451.

ROM C Features Tested:
- Blindness check (blind characters see nothing)
- Auto-exit mode (`exits auto` shows compact format)
- Closed door hiding (exits with closed doors are hidden)
- Room visibility checks (can_see_room integration)
- Detailed room names per exit
- Dark room handling ("Too dark to tell" message)
- Immortal room vnum display
- Direction name capitalization
- "None" message when no exits
- All 6 directions (N, E, S, W, U, D)
"""

from __future__ import annotations

import pytest

from mud.commands.inspection import do_exits
from mud.models.character import Character
from mud.models.constants import (
    AffectFlag,
    Direction,
    EX_CLOSED,
    EX_ISDOOR,
    RoomFlag,
    Sector,
)
from mud.models.room import Exit, Room


@pytest.fixture
def test_character():
    """Create a test character with basic setup."""
    char = Character()
    char.name = "TestPlayer"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    return char


@pytest.fixture
def immortal_character():
    """Create an immortal character for trust testing."""
    char = Character()
    char.name = "TestImmortal"
    char.level = 60
    char.trust = 60
    char.is_npc = False
    return char


@pytest.fixture
def temple_room():
    """Create Midgaard Temple room with exits."""
    room = Room(vnum=3001)
    room.name = "Midgaard Temple"
    room.description = "You are in the temple."
    room.sector_type = int(Sector.INSIDE)
    room.light = 1
    return room


@pytest.fixture
def north_room():
    """Create north room (Temple Square)."""
    room = Room(vnum=3002)
    room.name = "Temple Square"
    room.description = "A busy square."
    room.sector_type = int(Sector.CITY)
    room.light = 1
    return room


@pytest.fixture
def south_room():
    """Create south room (Dark Alley)."""
    room = Room(vnum=3003)
    room.name = "Dark Alley"
    room.description = "A dark alley."
    room.sector_type = int(Sector.CITY)
    room.light = 0  # Dark room
    room.room_flags = int(RoomFlag.ROOM_DARK)
    return room


@pytest.fixture
def east_room():
    """Create east room (Main Street)."""
    room = Room(vnum=3004)
    room.name = "Main Street"
    room.description = "A main street."
    room.sector_type = int(Sector.CITY)
    room.light = 1
    return room


# ==================== P0 TESTS (CRITICAL) ====================


def test_exits_shows_available_exits(test_character, temple_room, north_room, east_room, south_room):
    """P0: Test exits shows room names for available exits.

    ROM C Reference: act_info.c lines 1417-1421
    sprintf (buf + strlen (buf), "%-5s - %s", capitalize (dir_name[door]), room->name)
    """
    # Setup room with 3 exits
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(to_room=north_room, exit_info=0)
    temple_room.exits[int(Direction.EAST)] = Exit(to_room=east_room, exit_info=0)
    temple_room.exits[int(Direction.SOUTH)] = Exit(to_room=south_room, exit_info=0)

    test_character.room = temple_room

    # Execute command
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "North - Temple Square" in result
    assert "East  - Main Street" in result
    assert "South - Dark Alley" in result or "South - Too dark to tell" in result
    # Should NOT show west, up, down
    assert "West" not in result
    assert "Up" not in result
    assert "Down" not in result


def test_exits_closed_door_hidden(test_character, temple_room, north_room):
    """P0: Test closed doors are hidden from exit list.

    ROM C Reference: act_info.c lines 1414-1416
    && !IS_SET (pexit->exit_info, EX_CLOSED)
    """
    # Setup room with closed door to north
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(
        to_room=north_room,
        exit_info=EX_ISDOOR | EX_CLOSED,  # Door exists and is closed
    )

    test_character.room = temple_room

    # Execute command
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "None." in result  # No visible exits
    assert "North" not in result  # Closed door is hidden


def test_exits_auto_mode(test_character, temple_room, north_room, east_room):
    """P0: Test auto-exit mode shows compact format.

    ROM C Reference: act_info.c lines 1403-1405, 1425-1431, 1445-1446
    fAuto = !str_cmp (argument, "auto");
    if (fAuto) sprintf (buf, "{o[Exits:");
    if (fAuto) strcat (buf, " "); strcat (buf, dir_name[door]);
    if (fAuto) strcat (buf, "]{x\n\r");
    """
    # Setup room with 2 exits
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(to_room=north_room, exit_info=0)
    temple_room.exits[int(Direction.EAST)] = Exit(to_room=east_room, exit_info=0)

    test_character.room = temple_room

    # Execute command with "auto" argument
    result = do_exits(test_character, "auto")

    # Verify output
    assert result.startswith("{o[Exits:")
    assert result.endswith("]{x\n")
    assert "north" in result
    assert "east" in result
    # Should NOT contain room names in auto mode
    assert "Temple Square" not in result
    assert "Main Street" not in result


def test_exits_blind_check(test_character, temple_room, north_room):
    """P0: Test blind characters cannot see exits.

    ROM C Reference: act_info.c lines 1401-1402
    if (!check_blind (ch))
        return;
    """
    # Setup room with exits
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(to_room=north_room, exit_info=0)

    test_character.room = temple_room

    # Make character blind
    test_character.affected_by = int(AffectFlag.BLIND)

    # Execute command
    result = do_exits(test_character, "")

    # Verify output
    assert "You can't see a thing!" in result
    # Should NOT show exits
    assert "Obvious exits:" not in result
    assert "North" not in result


def test_exits_no_exits_message(test_character, temple_room):
    """P0: Test "None" message when no exits available.

    ROM C Reference: act_info.c line 1443
    if (!found) strcat (buf, fAuto ? " none" : "None.\n\r");
    """
    # Setup room with no exits
    temple_room.exits = [None] * 6
    test_character.room = temple_room

    # Execute command (non-auto mode)
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "None." in result


# ==================== P1 TESTS (IMPORTANT) ====================


def test_exits_immortal_room_vnums(immortal_character, temple_room, north_room, east_room):
    """P1: Test immortals see room vnums in header and per exit.

    ROM C Reference: act_info.c lines 1407-1408, 1422-1423
    if (IS_IMMORTAL (ch))
        sprintf (buf, "Obvious exits from room %d:\n\r", ch->in_room->vnum);
    if (IS_IMMORTAL (ch))
        sprintf (buf + strlen (buf), " (room %d)\n\r", pexit->u1.to_room->vnum);
    """
    # Setup room with 2 exits
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(to_room=north_room, exit_info=0)
    temple_room.exits[int(Direction.EAST)] = Exit(to_room=east_room, exit_info=0)

    immortal_character.room = temple_room

    # Execute command
    result = do_exits(immortal_character, "")

    # Verify output
    assert f"Obvious exits from room {temple_room.vnum}:" in result
    assert f"(room {north_room.vnum})" in result
    assert f"(room {east_room.vnum})" in result


def test_exits_dark_room_message(test_character, temple_room, south_room):
    """P1: Test dark rooms show "Too dark to tell" instead of room name.

    ROM C Reference: act_info.c lines 1419-1420
    room_is_dark (pexit->u1.to_room)
    ? "Too dark to tell" : pexit->u1.to_room->name
    """
    # Setup room with exit to dark room
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.SOUTH)] = Exit(to_room=south_room, exit_info=0)

    test_character.room = temple_room

    # Execute command
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "South - Too dark to tell" in result
    # Should NOT show actual room name
    assert "Dark Alley" not in result


def test_exits_can_see_room_check(test_character, temple_room):
    """P1: Test exits to forbidden rooms are hidden.

    ROM C Reference: act_info.c line 1415
    && can_see_room (ch, pexit->u1.to_room)
    """
    # Create immortal-only room
    immortal_room = Room(vnum=3999)
    immortal_room.name = "Immortal Room"
    immortal_room.room_flags = int(RoomFlag.ROOM_GODS_ONLY)
    immortal_room.light = 1

    # Setup room with exit to immortal room
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.UP)] = Exit(to_room=immortal_room, exit_info=0)

    test_character.room = temple_room

    # Execute command as mortal
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "None." in result  # No visible exits (immortal room hidden)
    assert "Up" not in result


def test_exits_direction_capitalization(test_character, temple_room, north_room):
    """P1: Test direction names are capitalized in non-auto mode.

    ROM C Reference: act_info.c line 1418
    capitalize (dir_name[door])
    """
    # Setup room with north exit
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(to_room=north_room, exit_info=0)

    test_character.room = temple_room

    # Execute command (non-auto mode)
    result = do_exits(test_character, "")

    # Verify output
    assert "North - " in result  # Capital N
    assert "north -" not in result  # NOT lowercase


# ==================== EDGE CASES ====================


def test_exits_auto_mode_no_exits(test_character, temple_room):
    """Edge Case: Test auto mode with no exits shows "[Exits: none]".

    ROM C Reference: act_info.c line 1443
    if (!found) strcat (buf, fAuto ? " none" : "None.\n\r");
    """
    # Setup room with no exits
    temple_room.exits = [None] * 6
    test_character.room = temple_room

    # Execute command (auto mode)
    result = do_exits(test_character, "auto")

    # Verify output
    assert "{o[Exits: none]{x" in result


def test_exits_all_six_directions(test_character, temple_room):
    """Edge Case: Test all 6 directions (N, E, S, W, U, D) work correctly.

    ROM C Reference: act_info.c line 1413
    for (door = 0; door <= 5; door++)
    """
    # Create rooms for all 6 directions
    rooms = {
        Direction.NORTH: Room(vnum=3010, name="North Room"),
        Direction.EAST: Room(vnum=3011, name="East Room"),
        Direction.SOUTH: Room(vnum=3012, name="South Room"),
        Direction.WEST: Room(vnum=3013, name="West Room"),
        Direction.UP: Room(vnum=3014, name="Up Room"),
        Direction.DOWN: Room(vnum=3015, name="Down Room"),
    }

    # Set light for all rooms
    for room in rooms.values():
        room.light = 1
        room.sector_type = int(Sector.INSIDE)

    # Setup exits for all directions
    temple_room.exits = [None] * 6
    for direction, room in rooms.items():
        temple_room.exits[int(direction)] = Exit(to_room=room, exit_info=0)

    test_character.room = temple_room

    # Execute command
    result = do_exits(test_character, "")

    # Verify all directions appear
    assert "North - North Room" in result
    assert "East  - East Room" in result
    assert "South - South Room" in result
    assert "West  - West Room" in result
    assert "Up    - Up Room" in result
    assert "Down  - Down Room" in result


def test_exits_mixed_open_closed_doors(test_character, temple_room, north_room, east_room):
    """Edge Case: Test only open doors are shown (closed doors hidden).

    ROM C Reference: act_info.c line 1416
    && !IS_SET (pexit->exit_info, EX_CLOSED)
    """
    # Setup room with 2 exits: one open, one closed
    temple_room.exits = [None] * 6
    temple_room.exits[int(Direction.NORTH)] = Exit(
        to_room=north_room,
        exit_info=EX_ISDOOR | EX_CLOSED,  # Closed door
    )
    temple_room.exits[int(Direction.EAST)] = Exit(
        to_room=east_room,
        exit_info=0,  # Open passage
    )

    test_character.room = temple_room

    # Execute command
    result = do_exits(test_character, "")

    # Verify output
    assert "Obvious exits:" in result
    assert "East  - Main Street" in result  # Open exit shown
    assert "North" not in result  # Closed door hidden
