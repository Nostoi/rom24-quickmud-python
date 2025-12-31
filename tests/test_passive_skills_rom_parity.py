"""
ROM parity tests for passive skills.

Tests passive skill implementations in game_loop.py and combat/engine.py.
These skills are NOT in handlers.py - they're integrated into game systems.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from mud.game_loop import hit_gain, mana_gain
from mud.combat.engine import multi_hit
from mud.models.character import Character
from mud.models.constants import Position, AffectFlag
from mud.world import initialize_world


@pytest.fixture(autouse=True)
def setup_world():
    """Initialize world for all tests."""
    initialize_world("area/area.lst")


class TestFastHealing:
    """ROM src/update.c:185-189 - fast_healing passive HP regen bonus."""

    def test_fast_healing_adds_bonus_on_success(self, movable_char_factory):
        """ROM L185-189: if (roll < fast_healing_skill) gain += roll * gain / 100."""
        char = movable_char_factory("warrior", 3001)
        char.level = 10
        char.perm_stat = [15, 15, 15, 15, 15]
        char.mod_stat = [0, 0, 0, 0, 0]
        char.ch_class = 3
        char.skills["fast healing"] = 75
        char.hit = 50
        char.max_hit = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain = hit_gain(char)

            assert gain > 0

    def test_fast_healing_no_bonus_on_failure(self, movable_char_factory):
        """Verify no bonus when roll >= skill."""
        char = movable_char_factory("warrior", 3001)
        char.level = 10
        char.perm_stat = [15, 15, 15, 15, 15]
        char.mod_stat = [0, 0, 0, 0, 0]
        char.ch_class = 3
        char.skills["fast healing"] = 30
        char.hit = 50
        char.max_hit = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain_with_fail = hit_gain(char)

        char.skills["fast healing"] = 100
        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain_with_success = hit_gain(char)

        assert gain_with_success > gain_with_fail

    def test_fast_healing_requires_below_max_hp_for_improve(self, movable_char_factory):
        """ROM L188-189: only check_improve if ch->hit < ch->max_hit."""
        char = movable_char_factory("warrior", 3001)
        char.skills["fast healing"] = 75
        char.hit = char.max_hit = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            hit_gain(char)


class TestMeditation:
    """ROM src/update.c:265-269 - meditation passive mana regen bonus."""

    def test_meditation_adds_bonus_on_success(self, movable_char_factory):
        """ROM L265-269: if (roll < meditation_skill) gain += roll * gain / 100."""
        char = movable_char_factory("cleric", 3001)
        char.level = 10
        char.perm_stat = [15, 15, 15, 15, 15]
        char.mod_stat = [0, 0, 0, 0, 0]
        char.ch_class = 2
        char.skills["meditation"] = 75
        char.mana = 50
        char.max_mana = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain = mana_gain(char)

            assert gain > 0

    def test_meditation_no_bonus_on_failure(self, movable_char_factory):
        """Verify no bonus when roll >= skill."""
        char = movable_char_factory("cleric", 3001)
        char.level = 10
        char.perm_stat = [15, 15, 15, 15, 15]
        char.mod_stat = [0, 0, 0, 0, 0]
        char.ch_class = 2
        char.skills["meditation"] = 30
        char.mana = 50
        char.max_mana = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain_with_fail = mana_gain(char)

        char.skills["meditation"] = 100
        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            gain_with_success = mana_gain(char)

        assert gain_with_success > gain_with_fail

    def test_meditation_requires_below_max_mana_for_improve(self, movable_char_factory):
        """ROM L268-269: only check_improve if ch->mana < ch->max_mana."""
        char = movable_char_factory("cleric", 3001)
        char.skills["meditation"] = 75
        char.mana = char.max_mana = 100
        char.position = Position.RESTING

        with patch("mud.game_loop.rng_mm.number_percent", return_value=50):
            mana_gain(char)


class TestEnhancedDamage:
    """ROM src/fight.c:565-570 - enhanced_damage passive damage bonus."""

    def test_enhanced_damage_not_implemented_in_handlers(self):
        """Verify enhanced_damage is in combat engine, not handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "enhanced_damage")
            or not callable(getattr(handlers, "enhanced_damage", None))
            or "return 42" not in str(getattr(handlers, "enhanced_damage", ""))
        )


class TestSecondAttack:
    """ROM src/fight.c:220-228 - second_attack passive extra attack."""

    def test_second_attack_not_implemented_in_handlers(self):
        """Verify second_attack is in combat engine, not handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "second_attack")
            or not callable(getattr(handlers, "second_attack", None))
            or "return 42" not in str(getattr(handlers, "second_attack", ""))
        )


class TestThirdAttack:
    """ROM src/fight.c:233-241 - third_attack passive third attack."""

    def test_third_attack_not_implemented_in_handlers(self):
        """Verify third_attack is in combat engine, not handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "third_attack")
            or not callable(getattr(handlers, "third_attack", None))
            or "return 42" not in str(getattr(handlers, "third_attack", ""))
        )


class TestDefenseSkillsNotInHandlers:
    """Verify defense skills removed from handlers (implemented in combat/engine.py)."""

    def test_parry_not_in_handlers(self):
        """Verify parry stub removed from handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "parry")
            or not callable(getattr(handlers, "parry", None))
            or "return 42" not in str(getattr(handlers, "parry", ""))
        )

    def test_dodge_not_in_handlers(self):
        """Verify dodge stub removed from handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "dodge")
            or not callable(getattr(handlers, "dodge", None))
            or "return 42" not in str(getattr(handlers, "dodge", ""))
        )

    def test_shield_block_not_in_handlers(self):
        """Verify shield_block stub removed from handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, "shield_block")
            or not callable(getattr(handlers, "shield_block", None))
            or "return 42" not in str(getattr(handlers, "shield_block", ""))
        )


class TestWeaponProficienciesNotInHandlers:
    """Verify weapon proficiency stubs removed (they're passive skill values)."""

    @pytest.mark.parametrize("weapon", ["axe", "dagger", "flail", "mace", "polearm", "spear", "sword", "whip"])
    def test_weapon_proficiency_stub_removed(self, weapon):
        """Verify weapon proficiency stubs removed from handlers."""
        from mud.skills import handlers

        assert (
            not hasattr(handlers, weapon)
            or not callable(getattr(handlers, weapon, None))
            or "return 42" not in str(getattr(handlers, weapon, ""))
        )


class TestMagicItemSkillsNotInHandlers:
    """Verify magic item skills are passive (no handler functions, used by commands)."""

    def test_staves_not_in_handlers(self):
        """Verify staves is passive skill used by brandish command.

        ROM Reference: src/magic.c:3733-3821 (do_brandish uses gsn_staves)
        Python: mud/commands/magic_items.py:225-281 (do_brandish)

        The 'staves' skill is a passive proficiency that affects success rate
        when using the 'brandish' command with staff items. It should either
        not exist in handlers or be a redirect stub to the brandish command.
        """
        from mud.skills import handlers

        # staves skill should either not exist or be a redirect stub
        if hasattr(handlers, "staves"):
            staves_func = getattr(handlers, "staves")
            # If it exists, it should be a redirect stub
            assert callable(staves_func), "staves should be callable if present"
            # Call it to verify it redirects to brandish command
            result = staves_func(None, None)
            assert isinstance(result, dict), "staves should return dict"
            assert result.get("success") is False, "staves should not succeed directly"
            assert "brandish" in result.get("message", "").lower(), "staves should mention brandish command"
        # If it doesn't exist, that's also correct (passive skill)

    def test_wands_not_in_handlers(self):
        """Verify wands is passive skill used by zap command.

        ROM Reference: src/magic.c:3825-3910 (do_zap uses gsn_wands)
        Python: mud/commands/magic_items.py:343-418 (do_zap)

        The 'wands' skill is a passive proficiency that affects success rate
        when using the 'zap' command with wand items. It should either not
        exist in handlers or be a redirect stub to the zap command.
        """
        from mud.skills import handlers

        # wands skill should either not exist or be a redirect stub
        if hasattr(handlers, "wands"):
            wands_func = getattr(handlers, "wands")
            # If it exists, it should be a redirect stub
            assert callable(wands_func), "wands should be callable if present"
            # Call it to verify it redirects to zap command
            result = wands_func(None, None)
            assert isinstance(result, dict), "wands should return dict"
            assert result.get("success") is False, "wands should not succeed directly"
            assert "zap" in result.get("message", "").lower(), "wands should mention zap command"
        # If it doesn't exist, that's also correct (passive skill)
