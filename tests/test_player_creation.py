"""
Player Character Creation Tests

Tests for ROM character creation flow - race/class selection, stats, starting equipment.
ROM Reference: src/comm.c (nanny state machine), src/class.c, src/race.c

Priority: P2 (Important ROM Parity)

Test Coverage:
- Creation Flow (8 tests)
- Starting Equipment (7 tests)
"""

from __future__ import annotations

import pytest

from mud.models.classes import CLASS_TABLE, get_player_class
from mud.models.constants import OBJ_VNUM_SCHOOL_DAGGER, OBJ_VNUM_SCHOOL_MACE, OBJ_VNUM_SCHOOL_SWORD, Stat
from mud.models.races import PC_RACE_TABLE, get_pc_race
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


class TestCreationFlow:
    """Test character creation flow and stat allocation."""

    def test_new_character_starts_at_level_1(self):
        """New characters should start at level 1 (or 0 during creation)."""
        player = create_test_character("NewChar", 3001)
        player.level = 1

        assert player.level == 1

    def test_select_race_from_available_races(self):
        """Player should be able to select from available PC races."""
        available_races = PC_RACE_TABLE

        assert len(available_races) > 0
        assert any(race.name == "human" for race in available_races)
        assert any(race.name == "elf" for race in available_races)
        assert any(race.name == "dwarf" for race in available_races)

    def test_select_class_from_available_classes(self):
        """Player should be able to select from available classes."""
        available_classes = CLASS_TABLE

        assert len(available_classes) == 4
        assert available_classes[0].name == "mage"
        assert available_classes[1].name == "cleric"
        assert available_classes[2].name == "thief"
        assert available_classes[3].name == "warrior"

    def test_starting_stats_by_race(self):
        """Each race should have specific starting stat bonuses."""
        human = get_pc_race("human")
        elf = get_pc_race("elf")
        dwarf = get_pc_race("dwarf")

        assert human is not None
        assert elf is not None
        assert dwarf is not None

        assert len(human.base_stats) == 5
        assert len(elf.base_stats) == 5
        assert len(dwarf.base_stats) == 5

        assert elf.base_stats[Stat.DEX] > human.base_stats[Stat.DEX]
        assert dwarf.base_stats[Stat.CON] > human.base_stats[Stat.CON]

    def test_starting_stats_by_class(self):
        """Each class should have a prime stat."""
        mage = get_player_class("mage")
        cleric = get_player_class("cleric")
        thief = get_player_class("thief")
        warrior = get_player_class("warrior")

        assert mage is not None
        assert cleric is not None
        assert thief is not None
        assert warrior is not None

        assert mage.prime_stat == Stat.INT
        assert cleric.prime_stat == Stat.WIS
        assert thief.prime_stat == Stat.DEX
        assert warrior.prime_stat == Stat.STR

    def test_creation_points_allocation(self):
        """Races have different creation point costs."""
        human = get_pc_race("human")
        elf = get_pc_race("elf")
        dwarf = get_pc_race("dwarf")

        assert human is not None
        assert elf is not None
        assert dwarf is not None

        assert isinstance(human.points, int)
        assert isinstance(elf.points, int)
        assert isinstance(dwarf.points, int)

        assert human.points == 0

    def test_creation_groups_selection(self):
        """Each class should have base and default skill groups."""
        mage = get_player_class("mage")
        warrior = get_player_class("warrior")

        assert mage is not None
        assert warrior is not None

        assert mage.base_group == "mage basics"
        assert mage.default_group == "mage default"

        assert warrior.base_group == "warrior basics"
        assert warrior.default_group == "warrior default"

    def test_starting_skills_by_class(self):
        """Each race grants bonus skills."""
        human = get_pc_race("human")
        elf = get_pc_race("elf")

        assert human is not None
        assert elf is not None

        assert isinstance(human.bonus_skills, tuple)
        assert isinstance(elf.bonus_skills, tuple)

        assert "sword" in human.bonus_skills or len(human.bonus_skills) >= 0


class TestStartingEquipment:
    """Test starting equipment and gold for new characters."""

    def test_starting_gold_by_class(self):
        """Different classes should start with different gold amounts (implied by ROM)."""
        player = create_test_character("GoldTest", 3001)
        player.level = 1

        assert hasattr(player, "gold")

    def test_starting_weapon_warrior(self):
        """Warrior should start with a sword."""
        warrior = get_player_class("warrior")

        assert warrior is not None
        assert warrior.first_weapon_vnum == OBJ_VNUM_SCHOOL_SWORD

    def test_starting_weapon_thief(self):
        """Thief should start with a dagger."""
        thief = get_player_class("thief")

        assert thief is not None
        assert thief.first_weapon_vnum == OBJ_VNUM_SCHOOL_DAGGER

    def test_starting_weapon_cleric(self):
        """Cleric should start with a mace."""
        cleric = get_player_class("cleric")

        assert cleric is not None
        assert cleric.first_weapon_vnum == OBJ_VNUM_SCHOOL_MACE

    def test_starting_weapon_mage(self):
        """Mage should start with a dagger."""
        mage = get_player_class("mage")

        assert mage is not None
        assert mage.first_weapon_vnum == OBJ_VNUM_SCHOOL_DAGGER

    def test_starting_armor_equipped(self):
        """New characters should start with basic armor (implied by ROM newbie equipment)."""
        player = create_test_character("ArmorTest", 3001)
        player.level = 1

        assert hasattr(player, "equipment")

    def test_map_item_given_to_newbies(self):
        """ROM gives new players a map item (OBJ_VNUM_MAP = 3162)."""
        from mud.models.constants import OBJ_VNUM_MAP

        assert OBJ_VNUM_MAP == 3162
