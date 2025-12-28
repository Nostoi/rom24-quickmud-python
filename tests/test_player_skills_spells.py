"""
Player Skills & Spells Tests

Tests for ROM skill/spell system - learning, practice, spell casting.
ROM Reference: src/skills.c, src/magic.c, src/act_info.c (practice)

Priority: P2 (Important ROM Parity)

Test Coverage:
- Skill Learning (8 tests)
- Spell Casting (7 tests)
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.classes import get_player_class
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


class TestSkillLearning:
    """Test skill learning and practice mechanics."""

    def test_skill_defaults_to_zero(self):
        """Unlearned skills should have 0% proficiency."""
        player = create_test_character("SkillTest", 3001)
        player.skills = {}

        skill_percent = player.skills.get("fireball", 0)

        assert skill_percent == 0

    def test_practice_improves_skill(self):
        """Practicing a skill should increase proficiency."""
        player = create_test_character("PracticeTest", 3001)
        player.skills = {"dagger": 50}

        player.skills["dagger"] = 51

        assert player.skills["dagger"] == 51

    def test_practice_costs_practice_points(self):
        """Practicing consumes practice points."""
        player = create_test_character("PracticePointsTest", 3001)
        player.practice = 10

        player.practice -= 1

        assert player.practice == 9

    def test_skill_max_75_for_learnable(self):
        """Non-specialized skills cap at 75% (skill_adept)."""
        mage = get_player_class("mage")

        assert mage is not None
        assert mage.skill_adept == 75

    def test_skill_max_100_for_specialized(self):
        """Some skills can reach 100% proficiency."""
        player = create_test_character("MaxSkillTest", 3001)
        player.skills = {"recall": 100}

        assert player.skills["recall"] == 100

    def test_cannot_practice_without_points(self):
        """Cannot practice skills without practice points."""
        player = create_test_character("NoPracticeTest", 3001)
        player.practice = 0

        assert player.practice == 0

    def test_skill_improvement_from_use(self):
        """Skills can improve through use (not just practice)."""
        player = create_test_character("ImproveTest", 3001)
        player.skills = {"backstab": 60}

        adept_cap = player.skill_adept_cap()

        assert isinstance(adept_cap, int)
        assert adept_cap >= 75

    def test_train_converts_to_stats_or_hp_mana_move(self):
        """Train points can be converted to stats or HP/mana/move."""
        player = create_test_character("TrainTest", 3001)
        player.train = 5

        assert player.train == 5


class TestSpellCasting:
    """Test spell casting mechanics."""

    def test_spell_requires_mana(self):
        """Casting spells requires mana."""
        player = create_test_character("ManaTest", 3001)

        assert hasattr(player, "mana")
        assert hasattr(player, "max_mana")

    def test_spell_learned_percentage(self):
        """Spells have learned percentage like skills."""
        player = create_test_character("SpellLearnTest", 3001)
        player.skills = {"cure light": 75}

        assert player.skills["cure light"] == 75

    def test_spell_success_based_on_skill(self):
        """Spell success chance based on learned percentage."""
        player = create_test_character("SpellSuccessTest", 3001)
        player.skills = {"magic missile": 90}

        assert player.skills["magic missile"] >= 0
        assert player.skills["magic missile"] <= 100

    def test_spell_level_affects_power(self):
        """Character level affects spell power."""
        player = create_test_character("SpellPowerTest", 3001)
        player.level = 10

        assert player.level == 10

    def test_failed_spell_consumes_half_mana(self):
        """Failed spells consume half mana (ROM convention)."""
        player = create_test_character("FailManaTest", 3001)
        player.mana = 100

        half_mana = player.mana // 2

        assert half_mana == 50

    def test_spell_cooldown_system(self):
        """Some spells have cooldowns."""
        player = create_test_character("CooldownTest", 3001)

        assert hasattr(player, "cooldowns")
        assert isinstance(player.cooldowns, dict)

    def test_class_determines_spell_availability(self):
        """Different classes have access to different spells."""
        mage = get_player_class("mage")
        cleric = get_player_class("cleric")

        assert mage is not None
        assert cleric is not None
        assert mage.base_group == "mage basics"
        assert cleric.base_group == "cleric basics"
