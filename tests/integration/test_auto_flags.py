"""Integration tests for auto-flag commands (act_info.c:744-970).

Tests ROM C parity for all auto-flag toggle commands:
- do_autoassist, do_autoexit, do_autogold, do_autoloot, do_autosac, do_autosplit
- do_autoall, do_brief, do_compact, do_combine

ROM Reference: src/act_info.c lines 744-970
"""

from __future__ import annotations

import pytest

from mud.commands.auto_settings import (
    do_autoall,
    do_autoassist,
    do_autoexit,
    do_autogold,
    do_autoloot,
    do_autosac,
    do_autosplit,
    do_brief,
    do_compact,
    do_combine,
)
from mud.models.character import Character
from mud.models.constants import CommFlag, PlayerFlag


@pytest.fixture
def test_char(test_room):
    """Create test character for auto-flag testing."""
    char = Character(
        name="TestChar",
        level=5,
        room=test_room,
        is_npc=False,
        hit=100,
        max_hit=100,
    )
    # Initialize flags (all OFF initially)
    char.act = 0
    char.comm = 0
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def test_npc(test_room):
    """Create test NPC for NPC rejection tests."""
    npc = Character(
        name="TestMob",
        level=5,
        room=test_room,
        is_npc=True,
        hit=100,
        max_hit=100,
    )
    npc.act = 0
    npc.comm = 0
    test_room.people.append(npc)
    yield npc
    if npc in test_room.people:
        test_room.people.remove(npc)


# =============================================================================
# do_autoassist Tests (ROM C lines 744-759)
# =============================================================================


class TestAutoAssist:
    """Test do_autoassist command ROM C parity."""

    def test_autoassist_npc_returns_empty(self, test_npc):
        """NPCs can't use autoassist (ROM C line 746-747)."""
        output = do_autoassist(test_npc, "")
        assert output == ""

    def test_autoassist_toggle_on(self, test_char):
        """Autoassist toggles from OFF to ON (ROM C line 755-757)."""
        assert not (test_char.act & PlayerFlag.AUTOASSIST)
        output = do_autoassist(test_char, "")
        assert "assist" in output.lower()
        assert "needed" in output.lower()
        assert test_char.act & PlayerFlag.AUTOASSIST

    def test_autoassist_toggle_off(self, test_char):
        """Autoassist toggles from ON to OFF (ROM C line 749-752)."""
        test_char.act |= PlayerFlag.AUTOASSIST
        output = do_autoassist(test_char, "")
        assert "removed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOASSIST)

    def test_autoassist_ignores_arguments(self, test_char):
        """Autoassist ignores all arguments (ROM C behavior)."""
        output = do_autoassist(test_char, "random arguments")
        assert "assist" in output.lower()
        assert test_char.act & PlayerFlag.AUTOASSIST


# =============================================================================
# do_autoexit Tests (ROM C lines 761-776)
# =============================================================================


class TestAutoExit:
    """Test do_autoexit command ROM C parity."""

    def test_autoexit_npc_returns_empty(self, test_npc):
        """NPCs can't use autoexit (ROM C line 763-764)."""
        output = do_autoexit(test_npc, "")
        assert output == ""

    def test_autoexit_toggle_on(self, test_char):
        """Autoexit toggles from OFF to ON (ROM C line 771-774)."""
        assert not (test_char.act & PlayerFlag.AUTOEXIT)
        output = do_autoexit(test_char, "")
        assert "exits will now be displayed" in output.lower()
        assert test_char.act & PlayerFlag.AUTOEXIT

    def test_autoexit_toggle_off(self, test_char):
        """Autoexit toggles from ON to OFF (ROM C line 766-769)."""
        test_char.act |= PlayerFlag.AUTOEXIT
        output = do_autoexit(test_char, "")
        assert "exits will no longer be displayed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOEXIT)


# =============================================================================
# do_autogold Tests (ROM C lines 778-793)
# =============================================================================


class TestAutoGold:
    """Test do_autogold command ROM C parity."""

    def test_autogold_npc_returns_empty(self, test_npc):
        """NPCs can't use autogold (ROM C line 780-781)."""
        output = do_autogold(test_npc, "")
        assert output == ""

    def test_autogold_toggle_on(self, test_char):
        """Autogold toggles from OFF to ON (ROM C line 788-791)."""
        assert not (test_char.act & PlayerFlag.AUTOGOLD)
        output = do_autogold(test_char, "")
        assert "automatic gold looting set" in output.lower()
        assert test_char.act & PlayerFlag.AUTOGOLD

    def test_autogold_toggle_off(self, test_char):
        """Autogold toggles from ON to OFF (ROM C line 783-786)."""
        test_char.act |= PlayerFlag.AUTOGOLD
        output = do_autogold(test_char, "")
        assert "autogold removed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOGOLD)


# =============================================================================
# do_autoloot Tests (ROM C lines 795-810)
# =============================================================================


class TestAutoLoot:
    """Test do_autoloot command ROM C parity."""

    def test_autoloot_npc_returns_empty(self, test_npc):
        """NPCs can't use autoloot (ROM C line 797-798)."""
        output = do_autoloot(test_npc, "")
        assert output == ""

    def test_autoloot_toggle_on(self, test_char):
        """Autoloot toggles from OFF to ON (ROM C line 805-808)."""
        assert not (test_char.act & PlayerFlag.AUTOLOOT)
        output = do_autoloot(test_char, "")
        assert "automatic corpse looting set" in output.lower()
        assert test_char.act & PlayerFlag.AUTOLOOT

    def test_autoloot_toggle_off(self, test_char):
        """Autoloot toggles from ON to OFF (ROM C line 800-803)."""
        test_char.act |= PlayerFlag.AUTOLOOT
        output = do_autoloot(test_char, "")
        assert "autolooting removed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOLOOT)


# =============================================================================
# do_autosac Tests (ROM C lines 812-827)
# =============================================================================


class TestAutoSac:
    """Test do_autosac command ROM C parity."""

    def test_autosac_npc_returns_empty(self, test_npc):
        """NPCs can't use autosac (ROM C line 814-815)."""
        output = do_autosac(test_npc, "")
        assert output == ""

    def test_autosac_toggle_on(self, test_char):
        """Autosac toggles from OFF to ON (ROM C line 822-825)."""
        assert not (test_char.act & PlayerFlag.AUTOSAC)
        output = do_autosac(test_char, "")
        assert "automatic corpse sacrificing set" in output.lower()
        assert test_char.act & PlayerFlag.AUTOSAC

    def test_autosac_toggle_off(self, test_char):
        """Autosac toggles from ON to OFF (ROM C line 817-820)."""
        test_char.act |= PlayerFlag.AUTOSAC
        output = do_autosac(test_char, "")
        assert "autosacrificing removed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOSAC)


# =============================================================================
# do_autosplit Tests (ROM C lines 829-844)
# =============================================================================


class TestAutoSplit:
    """Test do_autosplit command ROM C parity."""

    def test_autosplit_npc_returns_empty(self, test_npc):
        """NPCs can't use autosplit (ROM C line 831-832)."""
        output = do_autosplit(test_npc, "")
        assert output == ""

    def test_autosplit_toggle_on(self, test_char):
        """Autosplit toggles from OFF to ON (ROM C line 839-842)."""
        assert not (test_char.act & PlayerFlag.AUTOSPLIT)
        output = do_autosplit(test_char, "")
        assert "automatic gold splitting set" in output.lower()
        assert test_char.act & PlayerFlag.AUTOSPLIT

    def test_autosplit_toggle_off(self, test_char):
        """Autosplit toggles from ON to OFF (ROM C line 834-837)."""
        test_char.act |= PlayerFlag.AUTOSPLIT
        output = do_autosplit(test_char, "")
        assert "autosplitting removed" in output.lower()
        assert not (test_char.act & PlayerFlag.AUTOSPLIT)


# =============================================================================
# do_autoall Tests (ROM C lines 846-875)
# =============================================================================


class TestAutoAll:
    """Test do_autoall command ROM C parity."""

    def test_autoall_npc_returns_empty(self, test_npc):
        """NPCs can't use autoall (ROM C line 848-849)."""
        output = do_autoall(test_npc, "on")
        assert output == ""

    def test_autoall_on_sets_all_flags(self, test_char):
        """Autoall on sets all 6 auto-flags (ROM C line 851-860)."""
        assert test_char.act == 0
        output = do_autoall(test_char, "on")
        assert "all autos turned on" in output.lower()
        # Verify all 6 flags are set
        assert test_char.act & PlayerFlag.AUTOASSIST
        assert test_char.act & PlayerFlag.AUTOEXIT
        assert test_char.act & PlayerFlag.AUTOGOLD
        assert test_char.act & PlayerFlag.AUTOLOOT
        assert test_char.act & PlayerFlag.AUTOSAC
        assert test_char.act & PlayerFlag.AUTOSPLIT

    def test_autoall_off_clears_all_flags(self, test_char):
        """Autoall off clears all 6 auto-flags (ROM C line 862-871)."""
        # Set all flags first
        test_char.act = (
            PlayerFlag.AUTOASSIST
            | PlayerFlag.AUTOEXIT
            | PlayerFlag.AUTOGOLD
            | PlayerFlag.AUTOLOOT
            | PlayerFlag.AUTOSAC
            | PlayerFlag.AUTOSPLIT
        )
        output = do_autoall(test_char, "off")
        assert "all autos turned off" in output.lower()
        # Verify all 6 flags are cleared
        assert not (test_char.act & PlayerFlag.AUTOASSIST)
        assert not (test_char.act & PlayerFlag.AUTOEXIT)
        assert not (test_char.act & PlayerFlag.AUTOGOLD)
        assert not (test_char.act & PlayerFlag.AUTOLOOT)
        assert not (test_char.act & PlayerFlag.AUTOSAC)
        assert not (test_char.act & PlayerFlag.AUTOSPLIT)

    def test_autoall_invalid_argument_shows_usage(self, test_char):
        """Autoall with invalid argument shows usage (ROM C line 873-874)."""
        output = do_autoall(test_char, "invalid")
        assert "usage" in output.lower()
        assert "autoall" in output.lower()

    def test_autoall_case_insensitive(self, test_char):
        """Autoall accepts ON/OFF in any case."""
        # Test uppercase
        output = do_autoall(test_char, "ON")
        assert "all autos turned on" in output.lower()
        # Test mixed case
        output = do_autoall(test_char, "OfF")
        assert "all autos turned off" in output.lower()


# =============================================================================
# do_brief Tests (ROM C lines 877-889)
# =============================================================================


class TestBrief:
    """Test do_brief command ROM C parity."""

    def test_brief_toggle_on(self, test_char):
        """Brief toggles from OFF to ON (ROM C line 884-887)."""
        assert not (test_char.comm & CommFlag.BRIEF)
        output = do_brief(test_char, "")
        assert "short descriptions activated" in output.lower()
        assert test_char.comm & CommFlag.BRIEF

    def test_brief_toggle_off(self, test_char):
        """Brief toggles from ON to OFF (ROM C line 879-882)."""
        test_char.comm |= CommFlag.BRIEF
        output = do_brief(test_char, "")
        assert "full descriptions activated" in output.lower()
        assert not (test_char.comm & CommFlag.BRIEF)

    def test_brief_npc_can_toggle(self, test_npc):
        """NPCs CAN toggle brief (no NPC check in ROM C)."""
        output = do_brief(test_npc, "")
        assert "short descriptions activated" in output.lower()
        assert test_npc.comm & CommFlag.BRIEF


# =============================================================================
# do_compact Tests (ROM C lines 891-903)
# =============================================================================


class TestCompact:
    """Test do_compact command ROM C parity."""

    def test_compact_toggle_on(self, test_char):
        """Compact toggles from OFF to ON (ROM C line 898-901)."""
        assert not (test_char.comm & CommFlag.COMPACT)
        output = do_compact(test_char, "")
        assert "compact mode set" in output.lower()
        assert test_char.comm & CommFlag.COMPACT

    def test_compact_toggle_off(self, test_char):
        """Compact toggles from ON to OFF (ROM C line 893-896)."""
        test_char.comm |= CommFlag.COMPACT
        output = do_compact(test_char, "")
        assert "compact mode removed" in output.lower()
        assert not (test_char.comm & CommFlag.COMPACT)

    def test_compact_npc_can_toggle(self, test_npc):
        """NPCs CAN toggle compact (no NPC check in ROM C)."""
        output = do_compact(test_npc, "")
        assert "compact mode set" in output.lower()
        assert test_npc.comm & CommFlag.COMPACT


# =============================================================================
# do_combine Tests (ROM C lines 958-970)
# =============================================================================


class TestCombine:
    """Test do_combine command ROM C parity."""

    def test_combine_toggle_on(self, test_char):
        """Combine toggles from OFF to ON (ROM C line 965-968)."""
        assert not (test_char.comm & CommFlag.COMBINE)
        output = do_combine(test_char, "")
        # QuickMUD has more descriptive message than ROM C
        assert "combined" in output.lower() or "items will now be combined" in output.lower()
        assert test_char.comm & CommFlag.COMBINE

    def test_combine_toggle_off(self, test_char):
        """Combine toggles from ON to OFF (ROM C line 960-963)."""
        test_char.comm |= CommFlag.COMBINE
        output = do_combine(test_char, "")
        # QuickMUD has more descriptive message than ROM C
        assert "long inventory" in output.lower() or "no longer be combined" in output.lower()
        assert not (test_char.comm & CommFlag.COMBINE)

    def test_combine_npc_can_toggle(self, test_npc):
        """NPCs CAN toggle combine (no NPC check in ROM C)."""
        output = do_combine(test_npc, "")
        assert "combined" in output.lower() or "items will now be combined" in output.lower()
        assert test_npc.comm & CommFlag.COMBINE


# =============================================================================
# Flag Persistence Tests
# =============================================================================


class TestFlagPersistence:
    """Test that flag changes persist across multiple toggles."""

    def test_autoassist_multiple_toggles(self, test_char):
        """Autoassist state persists through multiple toggles."""
        # OFF -> ON
        do_autoassist(test_char, "")
        assert test_char.act & PlayerFlag.AUTOASSIST
        # ON -> OFF
        do_autoassist(test_char, "")
        assert not (test_char.act & PlayerFlag.AUTOASSIST)
        # OFF -> ON
        do_autoassist(test_char, "")
        assert test_char.act & PlayerFlag.AUTOASSIST

    def test_brief_multiple_toggles(self, test_char):
        """Brief state persists through multiple toggles."""
        # OFF -> ON
        do_brief(test_char, "")
        assert test_char.comm & CommFlag.BRIEF
        # ON -> OFF
        do_brief(test_char, "")
        assert not (test_char.comm & CommFlag.BRIEF)
        # OFF -> ON
        do_brief(test_char, "")
        assert test_char.comm & CommFlag.BRIEF

    def test_autoall_partial_flags(self, test_char):
        """Autoall off clears flags even if only some were set."""
        # Set only 3 of 6 flags
        test_char.act = PlayerFlag.AUTOASSIST | PlayerFlag.AUTOGOLD | PlayerFlag.AUTOSPLIT
        output = do_autoall(test_char, "off")
        assert "all autos turned off" in output.lower()
        # Verify all 6 flags are cleared
        assert not (test_char.act & PlayerFlag.AUTOASSIST)
        assert not (test_char.act & PlayerFlag.AUTOEXIT)
        assert not (test_char.act & PlayerFlag.AUTOGOLD)
        assert not (test_char.act & PlayerFlag.AUTOLOOT)
        assert not (test_char.act & PlayerFlag.AUTOSAC)
        assert not (test_char.act & PlayerFlag.AUTOSPLIT)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_autoall_empty_argument_shows_usage(self, test_char):
        """Autoall with empty argument shows usage."""
        output = do_autoall(test_char, "")
        assert "usage" in output.lower()

    def test_autoall_whitespace_argument_shows_usage(self, test_char):
        """Autoall with whitespace-only argument shows usage."""
        output = do_autoall(test_char, "   ")
        assert "usage" in output.lower()

    def test_flags_independent(self, test_char):
        """Auto-flags operate independently."""
        # Set autoassist
        do_autoassist(test_char, "")
        assert test_char.act & PlayerFlag.AUTOASSIST
        # Set autoexit (autoassist should remain set)
        do_autoexit(test_char, "")
        assert test_char.act & PlayerFlag.AUTOASSIST
        assert test_char.act & PlayerFlag.AUTOEXIT
        # Clear autoexit (autoassist should remain set)
        do_autoexit(test_char, "")
        assert test_char.act & PlayerFlag.AUTOASSIST
        assert not (test_char.act & PlayerFlag.AUTOEXIT)

    def test_comm_flags_independent(self, test_char):
        """Comm flags operate independently."""
        # Set brief
        do_brief(test_char, "")
        assert test_char.comm & CommFlag.BRIEF
        # Set compact (brief should remain set)
        do_compact(test_char, "")
        assert test_char.comm & CommFlag.BRIEF
        assert test_char.comm & CommFlag.COMPACT
        # Clear compact (brief should remain set)
        do_compact(test_char, "")
        assert test_char.comm & CommFlag.BRIEF
        assert not (test_char.comm & CommFlag.COMPACT)
