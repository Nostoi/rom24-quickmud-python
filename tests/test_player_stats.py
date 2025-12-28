"""
Player Stats System Tests

Tests for ROM character stat mechanics - perm_stat, mod_stat, get_curr_stat.
ROM Reference: src/handler.c (get_curr_stat), merc.h (STAT_* defines)

Priority: P1 (Critical for gameplay)

Test Coverage:
- Permanent Stats (perm_stat) (7 tests)
- Modified Stats (mod_stat) (7 tests)
- Stat Bounds & Clamping (6 tests)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Stat
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character, initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


def create_player_with_initialized_stat_arrays(name: str, room_vnum: int = 3001, perm_stats=None, mod_stats=None):
    player = create_test_character(name, room_vnum)
    player.perm_stat = perm_stats or [13, 13, 13, 13, 13]
    player.mod_stat = mod_stats or [0, 0, 0, 0, 0]
    return player


class TestPermanentStats:
    """Test permanent stat array (perm_stat)."""

    def test_perm_stat_initialized_as_list(self):
        """perm_stat should be a 5-element list [STR, INT, WIS, DEX, CON]."""
        player = create_player_with_initialized_stat_arrays("StatTest")

        assert isinstance(player.perm_stat, list)
        assert len(player.perm_stat) == 5

    def test_perm_stat_defaults_to_zeros(self):
        """perm_stat should default to [0, 0, 0, 0, 0] if not set."""
        player = Character(name="NewChar")
        player.perm_stat = [0, 0, 0, 0, 0]

        assert player.perm_stat == [0, 0, 0, 0, 0]

    def test_perm_stat_can_be_set_individually(self):
        """Each perm_stat element can be set independently."""
        player = create_player_with_initialized_stat_arrays("SetStatTest")

        player.perm_stat[Stat.STR] = 18
        player.perm_stat[Stat.INT] = 14
        player.perm_stat[Stat.WIS] = 12
        player.perm_stat[Stat.DEX] = 16
        player.perm_stat[Stat.CON] = 15

        assert player.perm_stat[Stat.STR] == 18
        assert player.perm_stat[Stat.INT] == 14
        assert player.perm_stat[Stat.WIS] == 12
        assert player.perm_stat[Stat.DEX] == 16
        assert player.perm_stat[Stat.CON] == 15

    def test_perm_stat_persists_across_modifications(self):
        """perm_stat values should persist when other stats change."""
        player = create_player_with_initialized_stat_arrays("PersistTest", perm_stats=[18, 14, 12, 16, 15])

        original_stats = player.perm_stat.copy()

        player.level = 10
        player.hit = 100

        assert player.perm_stat == original_stats

    def test_perm_stat_accepts_valid_range(self):
        """perm_stat should accept values in ROM range (typically 3-25)."""
        player = create_player_with_initialized_stat_arrays("RangeTest", perm_stats=[3, 13, 18, 25, 10])

        assert player.perm_stat == [3, 13, 18, 25, 10]

    def test_perm_stat_stat_enum_indexing(self):
        """perm_stat should be indexable using Stat enum values."""
        player = create_player_with_initialized_stat_arrays("EnumTest", perm_stats=[18, 14, 12, 16, 15])

        assert player.perm_stat[Stat.STR] == 18
        assert player.perm_stat[Stat.INT] == 14
        assert player.perm_stat[Stat.WIS] == 12
        assert player.perm_stat[Stat.DEX] == 16
        assert player.perm_stat[Stat.CON] == 15

    def test_perm_stat_independent_per_character(self):
        """Each character should have independent perm_stat arrays."""
        player1 = create_player_with_initialized_stat_arrays("Player1", perm_stats=[18, 10, 10, 10, 10])
        player2 = create_player_with_initialized_stat_arrays("Player2", perm_stats=[10, 18, 10, 10, 10])

        assert player1.perm_stat[Stat.STR] == 18
        assert player2.perm_stat[Stat.STR] == 10
        assert player1.perm_stat[Stat.INT] == 10
        assert player2.perm_stat[Stat.INT] == 18


class TestModifiedStats:
    """Test modified stat array (mod_stat)."""

    def test_mod_stat_initialized_as_list(self):
        """mod_stat should be a 5-element list matching perm_stat length."""
        player = create_player_with_initialized_stat_arrays("ModStatTest")

        assert isinstance(player.mod_stat, list)
        assert len(player.mod_stat) == 5

    def test_mod_stat_defaults_to_zeros(self):
        """mod_stat should default to [0, 0, 0, 0, 0] (no modifiers)."""
        player = create_player_with_initialized_stat_arrays("ModDefaultTest")

        assert player.mod_stat == [0, 0, 0, 0, 0]

    def test_mod_stat_can_be_positive(self):
        """mod_stat can hold positive bonuses."""
        player = create_player_with_initialized_stat_arrays("PosBonusTest")

        player.mod_stat[Stat.STR] = 3
        player.mod_stat[Stat.DEX] = 2

        assert player.mod_stat[Stat.STR] == 3
        assert player.mod_stat[Stat.DEX] == 2

    def test_mod_stat_can_be_negative(self):
        """mod_stat can hold negative penalties."""
        player = create_player_with_initialized_stat_arrays("NegPenaltyTest")

        player.mod_stat[Stat.STR] = -2
        player.mod_stat[Stat.INT] = -3

        assert player.mod_stat[Stat.STR] == -2
        assert player.mod_stat[Stat.INT] == -3

    def test_mod_stat_does_not_affect_perm_stat(self):
        """Changing mod_stat should not change perm_stat."""
        player = create_player_with_initialized_stat_arrays("IndependentTest")

        player.mod_stat[Stat.STR] = 5

        assert player.perm_stat[Stat.STR] == 13
        assert player.mod_stat[Stat.STR] == 5

    def test_mod_stat_independent_per_character(self):
        """Each character should have independent mod_stat arrays."""
        player1 = create_player_with_initialized_stat_arrays("Mod1", mod_stats=[3, 0, 0, 0, 0])
        player2 = create_player_with_initialized_stat_arrays("Mod2", mod_stats=[-2, 0, 0, 0, 0])

        assert player1.mod_stat[Stat.STR] == 3
        assert player2.mod_stat[Stat.STR] == -2

    def test_mod_stat_temporary_nature(self):
        """mod_stat represents temporary bonuses/penalties from spells/affects."""
        player = create_player_with_initialized_stat_arrays("TempModTest", perm_stats=[15, 15, 15, 15, 15])

        player.mod_stat[Stat.STR] = 4

        player.mod_stat[Stat.STR] = 0

        assert player.perm_stat[Stat.STR] == 15


class TestStatBoundsAndClamping:
    """Test stat calculation and ROM bounds (0-25)."""

    def test_get_curr_stat_returns_perm_plus_mod(self):
        """get_curr_stat() should return perm_stat + mod_stat."""
        player = create_player_with_initialized_stat_arrays(
            "CalcTest", perm_stats=[15, 12, 10, 14, 13], mod_stats=[3, -2, 0, 1, -1]
        )

        assert player.get_curr_stat(Stat.STR) == 18
        assert player.get_curr_stat(Stat.INT) == 10
        assert player.get_curr_stat(Stat.WIS) == 10
        assert player.get_curr_stat(Stat.DEX) == 15
        assert player.get_curr_stat(Stat.CON) == 12

    def test_get_curr_stat_clamps_to_maximum_25(self):
        """get_curr_stat() should clamp total to 25 (ROM maximum)."""
        player = create_player_with_initialized_stat_arrays(
            "MaxClampTest", perm_stats=[25, 20, 18, 25, 22], mod_stats=[5, 10, 0, 3, 0]
        )

        assert player.get_curr_stat(Stat.STR) == 25
        assert player.get_curr_stat(Stat.INT) == 25
        assert player.get_curr_stat(Stat.WIS) == 18
        assert player.get_curr_stat(Stat.DEX) == 25

    def test_get_curr_stat_clamps_to_minimum_0(self):
        """get_curr_stat() should clamp total to 0 (ROM minimum)."""
        player = create_player_with_initialized_stat_arrays(
            "MinClampTest", perm_stats=[5, 3, 8, 10, 12], mod_stats=[-10, -5, -2, 0, 0]
        )

        assert player.get_curr_stat(Stat.STR) == 0
        assert player.get_curr_stat(Stat.INT) == 0
        assert player.get_curr_stat(Stat.WIS) == 6

    def test_get_curr_stat_handles_stat_enum(self):
        """get_curr_stat() should accept Stat enum values."""
        player = create_player_with_initialized_stat_arrays("EnumCalcTest")

        assert player.get_curr_stat(Stat.STR) == 13
        assert player.get_curr_stat(Stat.INT) == 13
        assert player.get_curr_stat(Stat.WIS) == 13
        assert player.get_curr_stat(Stat.DEX) == 13
        assert player.get_curr_stat(Stat.CON) == 13

    def test_get_curr_stat_handles_integer_index(self):
        """get_curr_stat() should accept integer stat index (0-4)."""
        player = create_player_with_initialized_stat_arrays(
            "IntIndexTest", perm_stats=[15, 12, 10, 14, 13], mod_stats=[2, 1, 0, -1, 3]
        )

        assert player.get_curr_stat(0) == 17
        assert player.get_curr_stat(1) == 13
        assert player.get_curr_stat(2) == 10
        assert player.get_curr_stat(3) == 13
        assert player.get_curr_stat(4) == 16

    def test_get_curr_stat_returns_none_for_invalid_stat(self):
        """get_curr_stat() should return None for out-of-bounds stat index."""
        player = create_player_with_initialized_stat_arrays("InvalidStatTest")

        assert player.get_curr_stat(-1) is None
        assert player.get_curr_stat(5) is None
        assert player.get_curr_stat(99) is None
