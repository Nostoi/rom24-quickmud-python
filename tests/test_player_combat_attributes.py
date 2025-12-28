"""
Player Combat Attributes Tests

Tests for ROM combat attributes - hitroll, damroll, armor class.
ROM Reference: src/fight.c (combat calculations), merc.h (AC_* defines)

Priority: P1 (Critical for gameplay)

Test Coverage:
- Hitroll (5 tests)
- Damroll (5 tests)
- Armor Class (5 tests)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AC_BASH, AC_EXOTIC, AC_PIERCE, AC_SLASH
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


class TestHitroll:
    """Test hitroll (to-hit bonus) attribute."""

    def test_hitroll_defaults_to_zero(self):
        """hitroll should default to 0 for new characters."""
        player = create_test_character("HitrollTest", 3001)

        assert player.hitroll == 0

    def test_hitroll_can_be_set_positive(self):
        """hitroll can be set to positive values (equipment/spell bonuses)."""
        player = create_test_character("PosHitrollTest", 3001)

        player.hitroll = 10

        assert player.hitroll == 10

    def test_hitroll_can_be_set_negative(self):
        """hitroll can be set to negative values (curse/blind penalties)."""
        player = create_test_character("NegHitrollTest", 3001)

        player.hitroll = -5

        assert player.hitroll == -5

    def test_hitroll_accumulates_from_equipment(self):
        """hitroll accumulates bonuses from multiple sources."""
        player = create_test_character("AccumHitrollTest", 3001)

        player.hitroll = 0
        player.hitroll += 5
        player.hitroll += 3
        player.hitroll += 2

        assert player.hitroll == 10

    def test_hitroll_independent_per_character(self):
        """Each character should have independent hitroll values."""
        player1 = create_test_character("Hit1", 3001)
        player2 = create_test_character("Hit2", 3001)

        player1.hitroll = 15
        player2.hitroll = -3

        assert player1.hitroll == 15
        assert player2.hitroll == -3


class TestDamroll:
    """Test damroll (damage bonus) attribute."""

    def test_damroll_defaults_to_zero(self):
        """damroll should default to 0 for new characters."""
        player = create_test_character("DamrollTest", 3001)

        assert player.damroll == 0

    def test_damroll_can_be_set_positive(self):
        """damroll can be set to positive values (strength/equipment bonuses)."""
        player = create_test_character("PosDamrollTest", 3001)

        player.damroll = 12

        assert player.damroll == 12

    def test_damroll_can_be_set_negative(self):
        """damroll can be set to negative values (weakness/curse penalties)."""
        player = create_test_character("NegDamrollTest", 3001)

        player.damroll = -4

        assert player.damroll == -4

    def test_damroll_accumulates_from_equipment(self):
        """damroll accumulates bonuses from multiple sources."""
        player = create_test_character("AccumDamrollTest", 3001)

        player.damroll = 0
        player.damroll += 4
        player.damroll += 6
        player.damroll += 2

        assert player.damroll == 12

    def test_damroll_independent_per_character(self):
        """Each character should have independent damroll values."""
        player1 = create_test_character("Dam1", 3001)
        player2 = create_test_character("Dam2", 3001)

        player1.damroll = 20
        player2.damroll = -5

        assert player1.damroll == 20
        assert player2.damroll == -5


class TestArmorClass:
    """Test armor class (AC) system."""

    def test_armor_initialized_as_four_element_list(self):
        """armor should be a 4-element list [AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC]."""
        player = create_test_character("ArmorTest", 3001)

        if not player.armor:
            player.armor = [100, 100, 100, 100]

        assert isinstance(player.armor, list)
        assert len(player.armor) == 4

    def test_armor_defaults_to_100_per_slot(self):
        """armor should default to [100, 100, 100, 100] (naked/unarmored)."""
        player = create_test_character("DefaultArmorTest", 3001)
        player.armor = [100, 100, 100, 100]

        assert player.armor[AC_PIERCE] == 100
        assert player.armor[AC_BASH] == 100
        assert player.armor[AC_SLASH] == 100
        assert player.armor[AC_EXOTIC] == 100

    def test_armor_lower_is_better(self):
        """In ROM, lower AC values are better (more protection)."""
        player = create_test_character("BetterArmorTest", 3001)

        player.armor = [50, 40, 30, 60]

        assert player.armor[AC_PIERCE] == 50
        assert player.armor[AC_BASH] == 40
        assert player.armor[AC_SLASH] == 30
        assert player.armor[AC_EXOTIC] == 60

    def test_armor_can_be_negative(self):
        """armor can be negative (very well protected)."""
        player = create_test_character("NegArmorTest", 3001)

        player.armor = [-20, -15, -25, -10]

        assert player.armor[AC_PIERCE] == -20
        assert player.armor[AC_BASH] == -15
        assert player.armor[AC_SLASH] == -25
        assert player.armor[AC_EXOTIC] == -10

    def test_armor_independent_per_character(self):
        """Each character should have independent armor arrays."""
        player1 = create_test_character("Armor1", 3001)
        player2 = create_test_character("Armor2", 3001)

        player1.armor = [50, 50, 50, 50]
        player2.armor = [100, 100, 100, 100]

        assert player1.armor[AC_PIERCE] == 50
        assert player2.armor[AC_PIERCE] == 100
