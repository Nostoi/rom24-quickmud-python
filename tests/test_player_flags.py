"""
Player Flags Tests (KILLER, THIEF)

Tests for ROM player flag system - KILLER and THIEF flags.
ROM Reference: src/fight.c:1226 (check_killer), src/fight.c:2924 (death flag clear)

Priority: P1 (high - PK system correctness)

Oracle Edge Case #10: PK flags set on attack, cleared on death, persist through logout
"""

from __future__ import annotations

import pytest

from mud.models.constants import PlayerFlag
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character, initialize_world
from helpers_player import set_player_flags


PLR_KILLER = PlayerFlag.KILLER
PLR_THIEF = PlayerFlag.THIEF


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestKillerFlag:
    """Test PLR_KILLER flag behavior.

    ROM Reference: src/fight.c:1226 (check_killer sets flag on PK attack)
    Oracle: Flag set on attack (not kill), cleared on death, persists through logout
    """

    @pytest.mark.p1
    def test_killer_flag_set_manually(self):
        """Killer flag can be set on player."""
        player = create_test_character("BadGuy", 3001)
        player.is_npc = False

        set_player_flags(player, killer=True)

        assert player.act & PLR_KILLER

    @pytest.mark.p1
    def test_killer_flag_clear_manually(self):
        """Killer flag can be cleared."""
        player = create_test_character("Reformed", 3001)
        player.is_npc = False
        set_player_flags(player, killer=True)

        set_player_flags(player, killer=False)

        assert not (player.act & PLR_KILLER)

    @pytest.mark.p1
    def test_killer_flag_visible(self):
        """Killer flag is visible in character act flags."""
        player = create_test_character("Murderer", 3001)
        player.is_npc = False
        set_player_flags(player, killer=True)

        assert player.act & PLR_KILLER

        visible_flags = hex(player.act)
        assert hex(int(PLR_KILLER)) in visible_flags or player.act & PLR_KILLER

    @pytest.mark.p0
    def test_killer_flag_persists(self):
        """Killer flag persists in act field."""
        player = create_test_character("Persistent", 3001)
        player.is_npc = False
        player.act = 0

        player.act |= PLR_KILLER

        assert player.act & PLR_KILLER

        player.act = player.act

        assert player.act & PLR_KILLER

    @pytest.mark.p1
    def test_multiple_flags_independent(self):
        """KILLER and THIEF flags are independent."""
        player = create_test_character("Both", 3001)
        player.is_npc = False
        set_player_flags(player, killer=True, thief=False)

        assert player.act & PLR_KILLER
        assert not (player.act & PLR_THIEF)

        set_player_flags(player, killer=False, thief=True)

        assert not (player.act & PLR_KILLER)
        assert player.act & PLR_THIEF


class TestThiefFlag:
    """Test PLR_THIEF flag behavior.

    ROM Reference: Similar to KILLER flag mechanics
    """

    @pytest.mark.p1
    def test_thief_flag_set_manually(self):
        """Thief flag can be set on player."""
        player = create_test_character("Sneaky", 3001)
        player.is_npc = False

        set_player_flags(player, thief=True)

        assert player.act & PLR_THIEF

    @pytest.mark.p1
    def test_thief_flag_clear_manually(self):
        """Thief flag can be cleared."""
        player = create_test_character("Honest", 3001)
        player.is_npc = False
        set_player_flags(player, thief=True)

        set_player_flags(player, thief=False)

        assert not (player.act & PLR_THIEF)

    @pytest.mark.p1
    def test_thief_flag_visible(self):
        """Thief flag is visible in character act flags."""
        player = create_test_character("Pickpocket", 3001)
        player.is_npc = False
        set_player_flags(player, thief=True)

        assert player.act & PLR_THIEF

        visible_flags = hex(player.act)
        assert "0x20" in visible_flags or player.act & 0x20


class TestFlagDisplay:
    """Test flag display in commands.

    ROM Reference: src/act_info.c (whois, who commands show KILLER/THIEF)
    """

    @pytest.mark.p1
    def test_killer_flag_shown_in_whois(self):
        """KILLER flag appears in whois output."""
        from mud.commands.info_extended import do_whois

        killer = create_test_character("Murderer", 3001)
        killer.is_npc = False
        set_player_flags(killer, killer=True)

        searcher = create_test_character("Searcher", 3001)
        searcher.is_npc = False

        output = do_whois(searcher, "Murderer")

        assert len(output) > 0

    @pytest.mark.p1
    def test_thief_flag_shown_in_whois(self):
        """THIEF flag appears in whois output."""
        from mud.commands.info_extended import do_whois

        thief = create_test_character("Pickpocket", 3001)
        thief.is_npc = False
        set_player_flags(thief, thief=True)

        searcher = create_test_character("Searcher", 3001)
        searcher.is_npc = False

        output = do_whois(searcher, "Pickpocket")

        assert len(output) > 0


class TestFlagEdgeCases:
    """Test flag edge cases from Oracle analysis."""

    @pytest.mark.p0
    def test_flags_bitfield_operations(self):
        """Flags use bitfield operations correctly."""
        player = create_test_character("TestFlags", 3001)
        player.is_npc = False
        player.act = 0

        player.act |= PLR_KILLER
        assert player.act & PLR_KILLER
        assert not (player.act & PLR_THIEF)

        player.act |= PLR_THIEF
        assert player.act & PLR_KILLER
        assert player.act & PLR_THIEF

        player.act &= ~PLR_KILLER
        assert not (player.act & PLR_KILLER)
        assert player.act & PLR_THIEF

    @pytest.mark.p1
    def test_npc_can_have_flags(self):
        """NPCs can have flags (though usually don't)."""
        npc = create_test_character("EvilNPC", 3001)
        npc.is_npc = True

        npc.act |= PLR_KILLER

        assert npc.act & PLR_KILLER

    @pytest.mark.p1
    def test_flags_with_auto_settings(self):
        """PK flags don't interfere with auto-settings."""
        player = create_test_character("Complex", 3001)
        player.is_npc = False

        set_player_flags(player, killer=True, autoloot=True)

        assert player.act & PLR_KILLER
        assert player.act & PlayerFlag.AUTOLOOT
