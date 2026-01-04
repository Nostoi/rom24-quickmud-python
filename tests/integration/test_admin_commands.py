"""
Integration tests for admin/immortal commands.

Tests complete workflows for administrative commands (goto, transfer, force, wiznet, etc.).
These tests verify that admin tools work correctly end-to-end.

ROM Reference: src/act_wiz.c
"""

from __future__ import annotations

import pytest
from mud.commands.dispatcher import process_command
from mud.commands.imm_commands import do_goto, do_transfer
from mud.commands.admin_commands import (
    cmd_spawn,
    cmd_wizlock,
    cmd_newlock,
    cmd_ban,
    cmd_allow,
    cmd_permban,
)
from mud.models.character import Character, character_registry
from mud.models.room import Room
from mud.models.mob import MobIndex
from mud.models.constants import LEVEL_HERO, LEVEL_IMMORTAL
from mud.net.session import Session, SESSIONS
from mud.registry import room_registry, mob_registry
from mud.security import bans
from mud.world.world_state import (
    is_wizlock_enabled,
    is_newlock_enabled,
    reset_lockdowns,
)


@pytest.fixture(autouse=True)
def cleanup_test_state():
    """Clean up test state before and after each test."""
    # Clear bans and lockdowns before test
    bans.clear_all_bans()
    reset_lockdowns()

    # Clean up any test characters
    test_names = ["TestImmortal", "TestPlayer", "TestVictim"]
    for name in test_names:
        if name in SESSIONS:
            SESSIONS.pop(name)

    yield

    # Clean up after test
    bans.clear_all_bans()
    reset_lockdowns()
    for name in test_names:
        if name in SESSIONS:
            SESSIONS.pop(name)


@pytest.fixture
def immortal_char():
    """Create an immortal character with admin privileges."""
    char = Character()
    char.name = "TestImmortal"
    char.level = LEVEL_IMMORTAL
    char.trust = LEVEL_IMMORTAL
    char.is_npc = False
    char.is_admin = True
    char.messages = []
    return char


@pytest.fixture
def player_char():
    """Create a regular player character."""
    char = Character()
    char.name = "TestPlayer"
    char.level = 10
    char.trust = 0
    char.is_npc = False
    char.is_admin = False
    char.messages = []
    return char


@pytest.fixture
def test_room_pair():
    """Create two test rooms for teleportation tests."""
    room1 = Room(
        vnum=9001,
        name="Test Room 1",
        description="The first test room.",
        room_flags=0,
        sector_type=0,
    )
    room1.people = []
    room1.contents = []
    room_registry[9001] = room1

    room2 = Room(
        vnum=9002,
        name="Test Room 2",
        description="The second test room.",
        room_flags=0,
        sector_type=0,
    )
    room2.people = []
    room2.contents = []
    room_registry[9002] = room2

    yield (room1, room2)

    room_registry.pop(9001, None)
    room_registry.pop(9002, None)


@pytest.fixture
def test_mob_proto():
    """Create a test mob prototype for spawn tests."""
    mob = MobIndex(
        vnum=9003,
        short_descr="a test guard",
        long_descr="A test guard is standing here, looking alert.",
        level=5,
    )
    mob_registry[9003] = mob
    yield mob
    mob_registry.pop(9003, None)


# ============================================================================
# Test: Goto Command (Immortal Teleportation)
# ============================================================================


def test_goto_teleports_immortal_to_room(immortal_char, test_room_pair):
    """
    Test: Immortal can teleport to a valid room using goto command

    ROM Parity: Mirrors ROM src/act_wiz.c:do_goto

    Steps:
    1. Immortal starts in room 9001
    2. Execute goto command to room 9002
    3. Verify immortal is now in room 9002
    """
    room1, room2 = test_room_pair
    room1.add_character(immortal_char)

    result = do_goto(immortal_char, "9002")

    assert immortal_char.room == room2
    assert immortal_char in room2.people
    assert immortal_char not in room1.people


def test_goto_rejects_invalid_room(immortal_char, test_room_pair):
    """
    Test: Goto command rejects invalid room vnums

    Steps:
    1. Immortal tries to goto non-existent room 99999
    2. Verify error message returned
    3. Verify immortal stayed in original room
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    result = do_goto(immortal_char, "99999")

    assert "no such location" in result.lower()
    assert immortal_char.room == room1


def test_goto_requires_numeric_vnum(immortal_char, test_room_pair):
    """
    Test: Goto command requires numeric room vnum

    Steps:
    1. Immortal tries to goto "invalid_room"
    2. Verify error message returned
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    result = do_goto(immortal_char, "invalid_room")

    assert "no such location" in result.lower()


# ============================================================================
# Test: Spawn Command (Create Mobs as Admin)
# ============================================================================


def test_spawn_creates_mob_in_room(immortal_char, test_room_pair, test_mob_proto):
    """
    Test: Immortal can spawn a mob in their current room

    ROM Parity: Mirrors ROM src/act_wiz.c:do_mload

    Steps:
    1. Immortal in room 9001
    2. Execute spawn command for mob vnum 9003
    3. Verify mob created in room
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    result = cmd_spawn(immortal_char, "9003")

    assert "Spawned" in result
    assert any(char.is_npc for char in room1.people)


def test_spawn_rejects_invalid_vnum(immortal_char, test_room_pair):
    """
    Test: Spawn command rejects invalid mob vnums

    Steps:
    1. Immortal tries to spawn non-existent mob 99999
    2. Verify error message returned
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    result = cmd_spawn(immortal_char, "99999")

    assert "not found" in result.lower()


def test_spawn_requires_numeric_vnum(immortal_char, test_room_pair):
    """
    Test: Spawn command requires numeric mob vnum

    Steps:
    1. Immortal tries to spawn "invalid_mob"
    2. Verify error message returned
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    result = cmd_spawn(immortal_char, "invalid_mob")

    assert "Invalid vnum" in result


# ============================================================================
# Test: Wizlock Command (Game Lockdown)
# ============================================================================


def test_wizlock_toggles_game_lockdown(immortal_char):
    """
    Test: Wizlock command toggles game lockdown state

    ROM Parity: Mirrors ROM src/act_wiz.c:do_wizlock

    Steps:
    1. Execute wizlock command (enable)
    2. Verify wizlock is enabled
    3. Execute wizlock command again (disable)
    4. Verify wizlock is disabled
    """
    # Enable wizlock
    result = cmd_wizlock(immortal_char, "")
    assert "wizlocked" in result.lower()
    assert is_wizlock_enabled()

    # Disable wizlock
    result = cmd_wizlock(immortal_char, "")
    assert "un-wizlocked" in result.lower()
    assert not is_wizlock_enabled()


def test_newlock_toggles_new_character_lockdown(immortal_char):
    """
    Test: Newlock command toggles new character creation lockdown

    ROM Parity: Mirrors ROM src/act_wiz.c:do_newlock

    Steps:
    1. Execute newlock command (enable)
    2. Verify newlock is enabled
    3. Execute newlock command again (disable)
    4. Verify newlock is disabled
    """
    # Enable newlock
    result = cmd_newlock(immortal_char, "")
    assert "locked out" in result.lower()
    assert is_newlock_enabled()

    # Disable newlock
    result = cmd_newlock(immortal_char, "")
    assert "removed" in result.lower()
    assert not is_newlock_enabled()


# ============================================================================
# Test: Ban Management Commands
# ============================================================================


def test_ban_command_creates_site_ban(immortal_char):
    """
    Test: Ban command creates a site ban entry

    ROM Parity: Mirrors ROM src/act_wiz.c:do_ban

    Steps:
    1. Execute ban command for site "example.com all"
    2. Verify ban entry created
    3. Verify ban list shows the entry
    """
    result = cmd_ban(immortal_char, "example.com all")
    assert "banned" in result.lower()

    # Verify ban was created
    listing = cmd_ban(immortal_char, "")
    assert "example.com" in listing


def test_ban_command_requires_valid_type(immortal_char):
    """
    Test: Ban command requires valid ban type (all, newbies, permit)

    Steps:
    1. Try to ban with invalid type "invalid"
    2. Verify error message returned
    """
    result = cmd_ban(immortal_char, "example.com invalid")
    assert "acceptable ban types" in result.lower()


def test_allow_command_removes_site_ban(immortal_char):
    """
    Test: Allow command removes a site ban

    ROM Parity: Mirrors ROM src/act_wiz.c:do_allow

    Steps:
    1. Create a ban for "example.com"
    2. Execute allow command to remove it
    3. Verify ban is removed from list
    """
    cmd_ban(immortal_char, "example.com all")

    result = cmd_allow(immortal_char, "example.com")
    assert "lifted" in result.lower()

    # Verify ban was removed
    listing = cmd_ban(immortal_char, "")
    assert "example.com" not in listing or "No sites banned" in listing


def test_permban_creates_permanent_ban(immortal_char):
    """
    Test: Permban creates a permanent ban requiring high trust to remove

    ROM Parity: Mirrors ROM src/act_wiz.c:do_permban

    Steps:
    1. Execute permban command
    2. Verify permanent ban created
    3. Verify ban shows as permanent in listing
    """
    result = cmd_permban(immortal_char, "blocked.com all")
    assert "banned" in result.lower()

    listing = cmd_ban(immortal_char, "")
    assert "blocked.com" in listing
    assert "perm" in listing.lower()


# ============================================================================
# Test: Trust Level and Permission Checks
# ============================================================================


def test_low_trust_cannot_use_admin_commands(player_char, test_room_pair):
    """
    Test: Regular players cannot use admin commands

    Steps:
    1. Regular player tries to use goto command via dispatcher
    2. Verify command is blocked by dispatcher
    """
    room1, _ = test_room_pair
    room1.add_character(player_char)

    result = process_command(player_char, "@goto 9002")

    assert "huh?" in result.lower() or player_char.room == room1


def test_immortal_can_use_all_admin_commands(immortal_char, test_room_pair):
    """
    Test: Immortals can use all admin commands

    Steps:
    1. Verify immortal can use goto
    2. Verify immortal can use wizlock
    3. Verify immortal can use ban
    """
    room1, _ = test_room_pair
    room1.add_character(immortal_char)

    goto_result = do_goto(immortal_char, "9002")
    assert immortal_char.room.vnum == 9002

    wizlock_result = cmd_wizlock(immortal_char, "")
    assert "wizlocked" in wizlock_result.lower()

    ban_result = cmd_ban(immortal_char, "test.com all")
    assert "banned" in ban_result.lower()


# ============================================================================
# Test: Admin Command Error Handling
# ============================================================================


def test_spawn_without_room_returns_error(immortal_char, test_mob_proto):
    """
    Test: Spawn command requires immortal to be in a room

    Steps:
    1. Immortal not in any room
    2. Try to spawn mob
    3. Verify error message
    """
    # Don't add immortal to any room
    result = cmd_spawn(immortal_char, "9003")
    assert "nowhere" in result.lower() or "not in" in result.lower()


def test_ban_listing_shows_empty_when_no_bans(immortal_char):
    """
    Test: Ban listing shows appropriate message when no bans exist

    Steps:
    1. Execute ban command with no arguments (list bans)
    2. Verify "no sites banned" message
    """
    result = cmd_ban(immortal_char, "")
    assert "no sites banned" in result.lower()


def test_allow_on_nonexistent_ban_returns_error(immortal_char):
    """
    Test: Allow command returns error when trying to remove non-existent ban

    Steps:
    1. Try to allow a site that isn't banned
    2. Verify error message
    """
    result = cmd_allow(immortal_char, "notbanned.com")
    assert "not banned" in result.lower()
