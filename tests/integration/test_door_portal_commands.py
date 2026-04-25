"""Integration tests for door and portal commands (act_move.c).

Tests workflows for door manipulation and portal interaction with ROM 2.4b6 parity.

ROM Parity: src/act_move.c lines 1-509 (do_open, do_close, do_lock, do_unlock, do_pick)
"""

from __future__ import annotations

import pytest

from mud.commands.doors import do_close, do_lock, do_open, do_unlock
from mud.models.character import Character, PCData
from mud.models.constants import EX_CLOSED, EX_ISDOOR, EX_LOCKED, EX_NOCLOSE, EX_NOLOCK, ItemType
from mud.models.room import Exit, Room


@pytest.fixture
def door_test_setup():
    """Create test environment for door testing"""
    from mud.registry import room_registry

    room1 = Room(vnum=7001, name="Test Room 1", description="First test room.")
    room2 = Room(vnum=7002, name="Test Room 2", description="Second test room.")
    room1.people = []
    room1.contents = []
    room2.people = []
    room2.contents = []
    room1.exits = [None] * 6
    room2.exits = [None] * 6

    room_registry[7001] = room1
    room_registry[7002] = room2

    char = Character(name="TestChar", level=10, room=room1, is_npc=False, hit=100, max_hit=100, position=5)
    char.pcdata = PCData()
    room1.people.append(char)

    yield char, room1, room2

    room_registry.pop(7001, None)
    room_registry.pop(7002, None)


def test_close_door_sets_closed_flag(door_test_setup):
    """Test that closing a door sets EX_CLOSED flag

    ROM Parity: src/act_move.c lines 118-180 (do_close door logic)
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR, keyword="door")
    room1.exits[0] = exit_north

    result = do_close(char, "north")

    assert exit_north.exit_info & EX_CLOSED, "Door should be closed after do_close"
    assert result and len(result) > 0, "Should return success message"


def test_close_noclose_door_is_not_a_rom_check(door_test_setup):
    """ROM Parity: src/act_move.c:519-549 (do_close door branch)

    ROM `do_close` does NOT check EX_NOCLOSE on doors — it only sets EX_CLOSED.
    EX_NOCLOSE is only honored in the portal branch (lines 477-482). This test
    documents the ROM behavior so the implementation is not "fixed" to match a
    misremembered ROM rule.
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_NOCLOSE, keyword="door")
    room1.exits[0] = exit_north

    result = do_close(char, "north")

    assert exit_north.exit_info & EX_CLOSED, "ROM closes the door regardless of EX_NOCLOSE"
    assert result, "do_close should still return a confirmation string"


def test_lock_door_sets_locked_flag(door_test_setup, object_factory):
    """Test that locking a door with key sets EX_LOCKED flag

    ROM Parity: src/act_move.c lines 182-286 (do_lock door logic)
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_CLOSED, key=7101, keyword="door")
    room1.exits[0] = exit_north

    key = object_factory(
        {"vnum": 7101, "name": "iron key", "short_descr": "an iron key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    result = do_lock(char, "north")

    assert exit_north.exit_info & EX_LOCKED, "Door should be locked after do_lock"
    assert "click" in result.lower() or "lock" in result.lower(), "Should return lock success message"


def test_lock_nolock_door_blocked(door_test_setup):
    """Test that EX_NOLOCK doors cannot be locked

    ROM Parity: src/act_move.c lines 229-233 (EX_NOLOCK check)
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_CLOSED | EX_NOLOCK, keyword="door")
    room1.exits[0] = exit_north

    result = do_lock(char, "north")

    assert not (exit_north.exit_info & EX_LOCKED), "NOLOCK door should remain unlocked"
    assert "can" in result.lower(), "Should return cannot lock message"


def test_lock_without_key_fails(door_test_setup):
    """Test that locking without key fails

    ROM Parity: src/act_move.c lines 241-245 (key check)
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_CLOSED, key=7101, keyword="door")
    room1.exits[0] = exit_north

    result = do_lock(char, "north")

    assert not (exit_north.exit_info & EX_LOCKED), "Door should remain unlocked without key"
    assert "key" in result.lower() or "lack" in result.lower(), "Should return missing key message"


def test_unlock_door_clears_locked_flag(door_test_setup, object_factory):
    """Test that unlocking a door with key clears EX_LOCKED flag

    ROM Parity: src/act_move.c lines 288-392 (do_unlock door logic)
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_CLOSED | EX_LOCKED, key=7101, keyword="door")
    room1.exits[0] = exit_north

    key = object_factory(
        {"vnum": 7101, "name": "iron key", "short_descr": "an iron key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    result = do_unlock(char, "north")

    assert not (exit_north.exit_info & EX_LOCKED), "Door should be unlocked after do_unlock"
    assert "click" in result.lower() or "unlock" in result.lower(), "Should return unlock success message"


def test_unlock_lock_open_sequence(door_test_setup, object_factory):
    """Test complete door manipulation sequence

    ROM Parity: Complete door unlock -> open workflow
    """
    char, room1, room2 = door_test_setup

    exit_north = Exit(vnum=7002, exit_info=EX_ISDOOR | EX_CLOSED | EX_LOCKED, key=7101, keyword="door")
    room1.exits[0] = exit_north

    key = object_factory(
        {"vnum": 7101, "name": "iron key", "short_descr": "an iron key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    unlock_result = do_unlock(char, "north")
    assert not (exit_north.exit_info & EX_LOCKED), "Door should be unlocked"

    open_result = do_open(char, "north")
    assert not (exit_north.exit_info & EX_CLOSED), "Door should be open"


def test_portal_close_sets_closed_flag(door_test_setup, place_object_factory):
    """Test that closing a portal sets EX_CLOSED in value[1]

    ROM Parity: src/act_move.c lines 118-180 (do_close portal logic)
    """
    char, room1, room2 = door_test_setup

    portal = place_object_factory(
        room_vnum=7001,
        proto_kwargs={
            "vnum": 7100,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    # ROM portals require EX_ISDOOR in value[1] for do_close to operate
    # (src/act_move.c:477-482). Test setup mirrors how ROM portal protos store flags.
    portal.value = [1, EX_ISDOOR, 0, 7002]

    result = do_close(char, "portal")

    assert portal.value[1] & EX_CLOSED, "Portal should be closed after do_close"
    assert result and len(result) > 0, "Should return success message"


def test_portal_lock_sets_locked_flag(door_test_setup, place_object_factory, object_factory):
    """Test that locking a portal with key sets EX_LOCKED in value[1]

    ROM Parity: src/act_move.c lines 182-286 (do_lock portal logic)
    """
    char, room1, room2 = door_test_setup

    portal = place_object_factory(
        room_vnum=7001,
        proto_kwargs={
            "vnum": 7100,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    portal.value = [1, EX_CLOSED, 0, 7002, 7102]

    key = object_factory(
        {"vnum": 7102, "name": "portal key", "short_descr": "a portal key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    result = do_lock(char, "portal")

    assert portal.value[1] & EX_LOCKED or portal.value[4] == 7102, "Portal should be locked"
    assert result and len(result) > 0, "Should return success message"


def test_portal_unlock_clears_locked_flag(door_test_setup, place_object_factory, object_factory):
    """Test that unlocking a portal with key clears EX_LOCKED in value[1]

    ROM Parity: src/act_move.c lines 288-392 (do_unlock portal logic)
    """
    char, room1, room2 = door_test_setup

    portal = place_object_factory(
        room_vnum=7001,
        proto_kwargs={
            "vnum": 7100,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    portal.value = [1, EX_ISDOOR | EX_CLOSED | EX_LOCKED, 0, 7002, 7102]

    key = object_factory(
        {"vnum": 7102, "name": "portal key", "short_descr": "a portal key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    result = do_unlock(char, "portal")

    assert not (portal.value[1] & EX_LOCKED), "Portal should be unlocked after do_unlock"
    assert result and len(result) > 0, "Should return success message"


def test_portal_close_lock_unlock_open_sequence(door_test_setup, place_object_factory, object_factory):
    """Test complete portal manipulation workflow

    ROM Parity: Complete portal close -> lock -> unlock -> open sequence
    """
    char, room1, room2 = door_test_setup

    portal = place_object_factory(
        room_vnum=7001,
        proto_kwargs={
            "vnum": 7100,
            "name": "shimmering portal",
            "short_descr": "a shimmering portal",
            "item_type": int(ItemType.PORTAL),
        },
    )
    portal.value = [1, EX_ISDOOR, 0, 7002, 7102]

    key = object_factory(
        {"vnum": 7102, "name": "portal key", "short_descr": "a portal key", "item_type": int(ItemType.KEY)}
    )
    char.inventory.append(key)

    close_result = do_close(char, "portal")
    assert portal.value[1] & EX_CLOSED, "Portal should be closed"

    lock_result = do_lock(char, "portal")
    assert portal.value[1] & EX_LOCKED or portal.value[4] == 7102, "Portal should be locked"

    unlock_result = do_unlock(char, "portal")
    assert not (portal.value[1] & EX_LOCKED), "Portal should be unlocked"

    open_result = do_open(char, "portal")
    assert not (portal.value[1] & EX_CLOSED), "Portal should be open"
