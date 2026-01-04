"""
Integration tests for player configuration commands.

ROM Reference: src/act_info.c lines 972-1035
Commands: do_noloot, do_nofollow, do_nosummon

This test suite verifies ROM C behavioral parity for player configuration commands.
These commands toggle player flags that control:
- Whether corpse can be looted (PLR_CANLOOT)
- Whether character accepts followers (PLR_NOFOLLOW)
- Whether character can be summoned (PLR_NOSUMMON for players, IMM_SUMMON for NPCs)
"""

from __future__ import annotations

import pytest

from mud.commands.player_config import do_noloot, do_nofollow, do_nosummon
from mud.models.character import Character
from mud.models.constants import PlayerFlag
from mud.models.room import Room


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_room():
    """Create a test room for player config tests."""
    room = Room(
        vnum=3001,
        name="Test Room",
        description="A room for testing player config commands.",
        sector_type=0,
    )
    room.people = []
    yield room
    room.people.clear()


@pytest.fixture
def test_char(test_room):
    """Create a test player character with no flags set."""
    char = Character(
        name="TestChar",
        level=5,
        room=test_room,
        is_npc=False,
    )
    char.act = 0  # Initialize all flags to 0
    char.master = None
    char.leader = None
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def test_npc(test_room):
    """Create a test NPC for NPC rejection tests."""
    npc = Character(
        name="TestNPC",
        level=5,
        room=test_room,
        is_npc=True,
    )
    npc.act = PlayerFlag.IS_NPC  # NPCs have IS_NPC flag set
    npc.imm_flags = 0  # Initialize immunity flags
    test_room.people.append(npc)
    yield npc
    if npc in test_room.people:
        test_room.people.remove(npc)


# ============================================================================
# do_noloot() TESTS (ROM C lines 972-987)
# ============================================================================


def test_noloot_npc_returns_empty(test_npc):
    """
    NPCs cannot use noloot command.

    ROM C Reference: src/act_info.c lines 974-975
    - if (IS_NPC(ch)) return;
    """
    output = do_noloot(test_npc, "")
    assert output == "", "NPCs should not be able to toggle loot permission"


def test_noloot_toggle_on(test_char):
    """
    Noloot command toggles from safe (no PLR_CANLOOT) to lootable (PLR_CANLOOT set).

    ROM C Reference: src/act_info.c lines 977-986
    - Checks if PLR_CANLOOT is set
    - If not set: sets PLR_CANLOOT and sends "may now be looted" message
    """
    # Initially safe from looting (PLR_CANLOOT not set)
    assert not (test_char.act & PlayerFlag.CANLOOT), "Should start with no CANLOOT flag"

    # Enable looting
    output = do_noloot(test_char, "")

    # Verify flag set and message
    assert "may now be looted" in output.lower(), f"Expected looting enabled message, got: {output}"
    assert test_char.act & PlayerFlag.CANLOOT, "PLR_CANLOOT flag should be set"


def test_noloot_toggle_off(test_char):
    """
    Noloot command toggles from lootable (PLR_CANLOOT set) to safe (no PLR_CANLOOT).

    ROM C Reference: src/act_info.c lines 977-986
    - Checks if PLR_CANLOOT is set
    - If set: removes PLR_CANLOOT and sends "safe from thieves" message
    """
    # Start with looting enabled (PLR_CANLOOT set)
    test_char.act = PlayerFlag.CANLOOT
    assert test_char.act & PlayerFlag.CANLOOT, "Should start with CANLOOT flag"

    # Disable looting
    output = do_noloot(test_char, "")

    # Verify flag cleared and message
    assert "safe from thieves" in output.lower(), f"Expected looting disabled message, got: {output}"
    assert not (test_char.act & PlayerFlag.CANLOOT), "PLR_CANLOOT flag should be cleared"


# ============================================================================
# do_nofollow() TESTS (ROM C lines 989-1005)
# ============================================================================


def test_nofollow_npc_returns_empty(test_npc):
    """
    NPCs cannot use nofollow command.

    ROM C Reference: src/act_info.c lines 991-992
    - if (IS_NPC(ch)) return;
    """
    output = do_nofollow(test_npc, "")
    assert output == "", "NPCs should not be able to toggle follower permission"


def test_nofollow_toggle_on(test_char):
    """
    Nofollow command toggles from accepting followers to rejecting them.

    ROM C Reference: src/act_info.c lines 994-1004
    - If PLR_NOFOLLOW not set: sets PLR_NOFOLLOW, calls die_follower(), sends message
    """
    # Initially accepts followers (PLR_NOFOLLOW not set)
    assert not (test_char.act & PlayerFlag.NOFOLLOW), "Should start with no NOFOLLOW flag"

    # Enable nofollow
    output = do_nofollow(test_char, "")

    # Verify flag set and message
    assert "no longer accept followers" in output.lower(), f"Expected nofollow enabled message, got: {output}"
    assert test_char.act & PlayerFlag.NOFOLLOW, "PLR_NOFOLLOW flag should be set"


def test_nofollow_toggle_off(test_char):
    """
    Nofollow command toggles from rejecting followers to accepting them.

    ROM C Reference: src/act_info.c lines 994-1004
    - If PLR_NOFOLLOW set: removes PLR_NOFOLLOW and sends message
    """
    # Start with nofollow enabled (PLR_NOFOLLOW set)
    test_char.act = PlayerFlag.NOFOLLOW
    assert test_char.act & PlayerFlag.NOFOLLOW, "Should start with NOFOLLOW flag"

    # Disable nofollow
    output = do_nofollow(test_char, "")

    # Verify flag cleared and message
    assert "now accept followers" in output.lower(), f"Expected nofollow disabled message, got: {output}"
    assert not (test_char.act & PlayerFlag.NOFOLLOW), "PLR_NOFOLLOW flag should be cleared"


# ============================================================================
# do_nosummon() TESTS (ROM C lines 1007-1035)
# ============================================================================


def test_nosummon_player_toggle_on(test_char):
    """
    Nosummon command toggles player from summonable to immune.

    ROM C Reference: src/act_info.c lines 1022-1034
    - Players use PLR_NOSUMMON flag in ch->act
    - If not set: sets PLR_NOSUMMON and sends "immune to summoning" message
    """
    # Initially summonable (PLR_NOSUMMON not set)
    assert not (test_char.act & PlayerFlag.NOSUMMON), "Should start with no NOSUMMON flag"

    # Enable nosummon
    output = do_nosummon(test_char, "")

    # Verify flag set and message
    assert "immune to summoning" in output.lower(), f"Expected nosummon enabled message, got: {output}"
    assert test_char.act & PlayerFlag.NOSUMMON, "PLR_NOSUMMON flag should be set"


def test_nosummon_player_toggle_off(test_char):
    """
    Nosummon command toggles player from immune to summonable.

    ROM C Reference: src/act_info.c lines 1022-1034
    - Players use PLR_NOSUMMON flag in ch->act
    - If set: removes PLR_NOSUMMON and sends "no longer immune" message
    """
    # Start with nosummon enabled (PLR_NOSUMMON set)
    test_char.act = PlayerFlag.NOSUMMON
    assert test_char.act & PlayerFlag.NOSUMMON, "Should start with NOSUMMON flag"

    # Disable nosummon
    output = do_nosummon(test_char, "")

    # Verify flag cleared and message
    assert "no longer immune to summon" in output.lower(), f"Expected nosummon disabled message, got: {output}"
    assert not (test_char.act & PlayerFlag.NOSUMMON), "PLR_NOSUMMON flag should be cleared"


def test_nosummon_npc_toggle(test_npc):
    """
    NPCs use IMM_SUMMON immunity flag instead of PLR_NOSUMMON act flag.

    ROM C Reference: src/act_info.c lines 1009-1021
    - NPCs use IMM_SUMMON flag in ch->imm_flags
    - Toggle works same as players but uses different flag field
    """
    IMM_SUMMON = 0x00000010  # bit 4

    # Initially summonable (IMM_SUMMON not set)
    assert not (test_npc.imm_flags & IMM_SUMMON), "NPC should start without IMM_SUMMON flag"

    # Enable nosummon (should use imm_flags)
    output = do_nosummon(test_npc, "")

    # Verify imm_flags set (not act flags)
    assert "immune to summoning" in output.lower(), f"Expected nosummon enabled message, got: {output}"
    assert test_npc.imm_flags & IMM_SUMMON, "IMM_SUMMON flag should be set in imm_flags"

    # Toggle off
    output = do_nosummon(test_npc, "")
    assert "no longer immune to summon" in output.lower(), f"Expected nosummon disabled message, got: {output}"
    assert not (test_npc.imm_flags & IMM_SUMMON), "IMM_SUMMON flag should be cleared"


# ============================================================================
# SUMMARY
# ============================================================================
# Total Tests: 9
# - do_noloot: 3 tests (NPC rejection, toggle on, toggle off)
# - do_nofollow: 3 tests (NPC rejection, toggle on, toggle off)
# - do_nosummon: 3 tests (player toggle on, player toggle off, NPC uses imm_flags)
#
# All tests verify ROM C behavioral parity from src/act_info.c lines 972-1035
# ============================================================================
