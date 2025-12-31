"""
ROM Parity Tests: Save Formulas and Immunity (ROM magic.c:215-254, handler.c:213-320)

Tests saves_spell, saves_dispel, and check_immune to match ROM 2.4b6
save formula calculations exactly.

ROM C References:
- src/magic.c:215-239 - saves_spell()
- src/magic.c:243-254 - saves_dispel()
- src/handler.c:213-320 - check_immune()
"""

from __future__ import annotations

import pytest
from mud.affects.saves import check_dispel, saves_dispel, saves_spell
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, DamageType, DefenseBit
from mud.utils import rng_mm


class TestSavesSpell:
    """Test saves_spell() formula matches ROM magic.c:215-239."""

    def test_saves_spell_base_formula(self, movable_char_factory, monkeypatch):
        """ROM magic.c:219 - save = 50 + (victim->level - level) * 5 - victim->saving_throw * 2."""
        # Character: level 10, saving_throw -5
        # Spell level: 15
        # Expected: 50 + (10 - 15) * 5 - (-5) * 2 = 50 - 25 + 10 = 35
        char = movable_char_factory("Test", 3001)
        char.level = 10
        char.saving_throw = -5
        char.ch_class = 3  # Warrior (no fMana reduction)

        # Set RNG to return deterministic values
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 34)
        result = saves_spell(15, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 35)
        result = saves_spell(15, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_berserk_bonus(self, movable_char_factory, monkeypatch):
        """ROM magic.c:220-221 - berserk adds victim->level / 2 (C integer division)."""
        char = movable_char_factory("Berserker", 3001)
        char.level = 15
        char.saving_throw = 0
        char.ch_class = 3  # Warrior (no fMana reduction)

        # Base save: 50 + (15 - 10) * 5 - 0 * 2 = 75
        # With berserk: 75 + 15/2 = 75 + 7 = 82 (C integer division)
        char.apply_spell_effect(SpellEffect(name="berserk", affect_flag=AffectFlag.BERSERK, duration=10, level=1))

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 81)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 82)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_immune_auto_success(self, movable_char_factory, monkeypatch):
        """ROM magic.c:225-226 - IS_IMMUNE returns TRUE (auto success)."""
        char = movable_char_factory("Immune", 3001)
        char.level = 10
        char.saving_throw = 0
        char.imm_flags = DefenseBit.FIRE  # Immune to fire

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)
        result = saves_spell(50, char, int(DamageType.FIRE))
        assert result is True

    def test_saves_spell_resistant_bonus(self, movable_char_factory, monkeypatch):
        """ROM magic.c:227-229 - IS_RESISTANT adds +2 to save."""
        char = movable_char_factory("Resistant", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 3  # Warrior (no fMana reduction)
        char.res_flags = DefenseBit.FIRE  # Resistant to fire

        # Base save: 50 + (10 - 10) * 5 - 0 * 2 = 50
        # Resistant: 50 + 2 = 52
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 51)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 52)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_vulnerable_penalty(self, movable_char_factory, monkeypatch):
        """ROM magic.c:230-232 - IS_VULNERABLE subtracts 2 from save."""
        char = movable_char_factory("Vulnerable", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 3  # Warrior (no fMana reduction)
        char.vuln_flags = DefenseBit.FIRE  # Vulnerable to fire

        # Base save: 50 + (10 - 10) * 5 - 0 * 2 = 50
        # Vulnerable: 50 - 2 = 48
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 47)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 48)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_fmana_class_reduction(self, movable_char_factory, monkeypatch):
        """ROM magic.c:235-236 - mana-using classes get save = 9 * save / 10 (C division)."""
        # Mage (class 0) uses mana
        char = movable_char_factory("Mage", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 0  # Mage
        char.is_npc = False

        # Base save: 50 + (10 - 10) * 5 - 0 * 2 = 50
        # fMana: 9 * 50 / 10 = 45 (C integer division)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 44)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 45)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_non_fmana_class_no_reduction(self, movable_char_factory, monkeypatch):
        """ROM magic.c:235-236 - non-mana classes don't get reduction."""
        # Warrior (class 3) doesn't use mana
        char = movable_char_factory("Warrior", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 3  # Warrior
        char.is_npc = False

        # Base save: 50 + (10 - 10) * 5 - 0 * 2 = 50
        # No reduction (warrior doesn't use mana)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 49)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_clamped_to_5_95(self, movable_char_factory, monkeypatch):
        """ROM magic.c:237 - save = URANGE(5, save, 95)."""
        char = movable_char_factory("Extreme", 3001)
        char.saving_throw = 0

        # Very low save (clamped to 5)
        char.level = 1
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 4)
        result = saves_spell(100, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)
        result = saves_spell(100, char, int(DamageType.FIRE))
        assert result is False

        # Very high save (clamped to 95)
        char.level = 100
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 94)
        result = saves_spell(1, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 95)
        result = saves_spell(1, char, int(DamageType.FIRE))
        assert result is False

    def test_saves_spell_npc_no_fmana_reduction(self, movable_char_factory, monkeypatch):
        """ROM magic.c:235 - NPCs don't get fMana reduction (IS_NPC check)."""
        # Use movable_char_factory and set is_npc to True
        char = movable_char_factory("Mob", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 0  # Mage class, but NPC
        char.is_npc = True

        # Base save: 50 + (10 - 10) * 5 - 0 * 2 = 50
        # No reduction (NPC doesn't get fMana bonus)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 49)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False


class TestCheckImmune:
    """Test check_immune() matches ROM handler.c:213-320."""

    def test_check_immune_weapon_global_immune(self, movable_char_factory):
        """ROM handler.c:217-224 - DAM_BASH/PIERCE/SLASH check IMM_WEAPON first."""
        char = movable_char_factory("WeaponImmune", 3001)
        char.imm_flags = DefenseBit.WEAPON  # Global weapon immunity

        from mud.affects.saves import _check_immune

        # All weapon types should return IS_IMMUNE (1)
        assert _check_immune(char, int(DamageType.BASH)) == 1
        assert _check_immune(char, int(DamageType.PIERCE)) == 1
        assert _check_immune(char, int(DamageType.SLASH)) == 1

    def test_check_immune_weapon_global_resistant(self, movable_char_factory):
        """ROM handler.c:225-227 - RES_WEAPON gives IS_RESISTANT default."""
        char = movable_char_factory("WeaponResist", 3001)
        char.res_flags = DefenseBit.WEAPON

        from mud.affects.saves import _check_immune

        # Weapon types should return IS_RESISTANT (2) by default
        assert _check_immune(char, int(DamageType.BASH)) == 2
        assert _check_immune(char, int(DamageType.PIERCE)) == 2
        assert _check_immune(char, int(DamageType.SLASH)) == 2

    def test_check_immune_weapon_global_vulnerable(self, movable_char_factory):
        """ROM handler.c:228-230 - VULN_WEAPON gives IS_VULNERABLE default."""
        char = movable_char_factory("WeaponVuln", 3001)
        char.vuln_flags = DefenseBit.WEAPON

        from mud.affects.saves import _check_immune

        # Weapon types should return IS_VULNERABLE (3) by default
        assert _check_immune(char, int(DamageType.BASH)) == 3
        assert _check_immune(char, int(DamageType.PIERCE)) == 3
        assert _check_immune(char, int(DamageType.SLASH)) == 3

    def test_check_immune_magic_global_immune(self, movable_char_factory):
        """ROM handler.c:234-242 - Magic damage types check IMM_MAGIC first."""
        char = movable_char_factory("MagicImmune", 3001)
        char.imm_flags = DefenseBit.MAGIC

        from mud.affects.saves import _check_immune

        # Magic types should return IS_IMMUNE (1) by default
        assert _check_immune(char, int(DamageType.FIRE)) == 1
        assert _check_immune(char, int(DamageType.COLD)) == 1
        assert _check_immune(char, int(DamageType.LIGHTNING)) == 1

    def test_check_immune_specific_overrides_global(self, movable_char_factory):
        """ROM handler.c:302-314 - Specific IMM_FIRE overrides RES_MAGIC."""
        char = movable_char_factory("Mixed", 3001)
        char.res_flags = DefenseBit.MAGIC  # Resistant to magic (default IS_RESISTANT)
        char.imm_flags = DefenseBit.FIRE  # But immune to fire specifically

        from mud.affects.saves import _check_immune

        # Fire should be IS_IMMUNE (1) due to specific flag
        assert _check_immune(char, int(DamageType.FIRE)) == 1

        # Other magic should be IS_RESISTANT (2) from global
        assert _check_immune(char, int(DamageType.COLD)) == 2
        assert _check_immune(char, int(DamageType.LIGHTNING)) == 2

    def test_check_immune_vuln_downgrades_immunity(self, movable_char_factory):
        """ROM handler.c:306-314 - VULN downgrades immunity levels."""
        char = movable_char_factory("Conflict", 3001)

        from mud.affects.saves import _check_immune

        # Case 1: IMM + VULN = RESISTANT
        char.imm_flags = DefenseBit.FIRE
        char.vuln_flags = DefenseBit.FIRE
        char.res_flags = 0
        assert _check_immune(char, int(DamageType.FIRE)) == 2  # IS_RESISTANT

        # Case 2: RES + VULN = NORMAL
        char.imm_flags = 0
        char.res_flags = DefenseBit.FIRE
        char.vuln_flags = DefenseBit.FIRE
        assert _check_immune(char, int(DamageType.FIRE)) == 0  # IS_NORMAL

        # Case 3: VULN alone = VULNERABLE
        char.imm_flags = 0
        char.res_flags = 0
        char.vuln_flags = DefenseBit.FIRE
        assert _check_immune(char, int(DamageType.FIRE)) == 3  # IS_VULNERABLE

    def test_check_immune_all_damage_types_mapped(self, movable_char_factory):
        """ROM handler.c:247-299 - All damage types have bit mappings."""
        char = movable_char_factory("AllTypes", 3001)

        from mud.affects.saves import _check_immune

        # Set immunity to all damage types
        char.imm_flags = (
            DefenseBit.BASH
            | DefenseBit.PIERCE
            | DefenseBit.SLASH
            | DefenseBit.FIRE
            | DefenseBit.COLD
            | DefenseBit.LIGHTNING
            | DefenseBit.ACID
            | DefenseBit.POISON
            | DefenseBit.NEGATIVE
            | DefenseBit.HOLY
            | DefenseBit.ENERGY
            | DefenseBit.MENTAL
            | DefenseBit.DISEASE
            | DefenseBit.DROWNING
            | DefenseBit.LIGHT
            | DefenseBit.CHARM
            | DefenseBit.SOUND
        )

        # All should return IS_IMMUNE (1)
        damage_types = [
            DamageType.BASH,
            DamageType.PIERCE,
            DamageType.SLASH,
            DamageType.FIRE,
            DamageType.COLD,
            DamageType.LIGHTNING,
            DamageType.ACID,
            DamageType.POISON,
            DamageType.NEGATIVE,
            DamageType.HOLY,
            DamageType.ENERGY,
            DamageType.MENTAL,
            DamageType.DISEASE,
            DamageType.DROWNING,
            DamageType.LIGHT,
            DamageType.CHARM,
            DamageType.SOUND,
        ]

        for dt in damage_types:
            assert _check_immune(char, int(dt)) == 1, f"{dt.name} should be immune"

    def test_check_immune_none_returns_minus_one(self, movable_char_factory):
        """ROM handler.c:214-215 - DAM_NONE returns -1."""
        char = movable_char_factory("Test", 3001)

        from mud.affects.saves import _check_immune

        assert _check_immune(char, int(DamageType.NONE)) == -1


class TestSavesDispel:
    """Test saves_dispel() matches ROM magic.c:243-254."""

    def test_saves_dispel_base_formula(self, monkeypatch):
        """ROM magic.c:251-253 - save = 50 + (spell_level - dis_level) * 5, clamped 5-95."""
        # spell_level=15, dis_level=10, duration=5
        # Expected: 50 + (15 - 10) * 5 = 75
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 74)
        result = saves_dispel(10, 15, 5)
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 75)
        result = saves_dispel(10, 15, 5)
        assert result is False

    def test_saves_dispel_permanent_effect_bonus(self, monkeypatch):
        """ROM magic.c:247-249 - duration=-1 adds +5 to spell_level."""
        # spell_level=10, dis_level=10, duration=-1 (permanent)
        # Expected: 50 + ((10 + 5) - 10) * 5 = 50 + 25 = 75
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 74)
        result = saves_dispel(10, 10, -1)
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 75)
        result = saves_dispel(10, 10, -1)
        assert result is False

    def test_saves_dispel_clamped_to_5_95(self, monkeypatch):
        """ROM magic.c:252 - save = URANGE(5, save, 95)."""
        # Very low save (clamped to 5)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 4)
        result = saves_dispel(100, 1, 1)
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)
        result = saves_dispel(100, 1, 1)
        assert result is False

        # Very high save (clamped to 95)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 94)
        result = saves_dispel(1, 100, 1)
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 95)
        result = saves_dispel(1, 100, 1)
        assert result is False


class TestCheckDispel:
    """Test check_dispel() matches ROM magic.c:258-282."""

    def test_check_dispel_removes_on_failed_save(self, movable_char_factory, monkeypatch):
        """ROM magic.c:268-276 - Failed save removes affect and shows message."""
        char = movable_char_factory("Victim", 3001)
        char.apply_spell_effect(
            SpellEffect(name="bless", duration=10, level=5, wear_off_message="You feel less righteous.")
        )

        # Force failed save: dispel_level=20, spell_level=5, duration=10
        # Save = 50 + (5 - 20) * 5 = -25, clamped to 5
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)
        result = check_dispel(20, char, "bless")
        assert result is True
        assert "bless" not in char.spell_effects

    def test_check_dispel_reduces_level_on_successful_save(self, movable_char_factory, monkeypatch):
        """ROM magic.c:278-279 - Successful save reduces affect level by 1."""
        char = movable_char_factory("Victim", 3001)
        char.apply_spell_effect(SpellEffect(name="bless", duration=10, level=10))

        # Force successful save
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 4)
        result = check_dispel(5, char, "bless")
        assert result is False
        assert "bless" in char.spell_effects
        assert char.spell_effects["bless"].level == 9  # Reduced by 1

    def test_check_dispel_returns_false_if_not_affected(self, movable_char_factory):
        """ROM magic.c:262 - Returns false if not affected."""
        char = movable_char_factory("Clean", 3001)

        result = check_dispel(20, char, "bless")
        assert result is False

    def test_check_dispel_permanent_effect_harder_to_remove(self, movable_char_factory, monkeypatch):
        """ROM magic.c:247-249 - Permanent effects (duration=-1) get +5 level bonus."""
        char = movable_char_factory("Permanent", 3001)
        char.apply_spell_effect(SpellEffect(name="sanctuary", duration=-1, level=10))

        # Permanent: effective level = 10 + 5 = 15
        # Save = 50 + (15 - 10) * 5 = 75
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 74)
        result = check_dispel(10, char, "sanctuary")
        assert result is False
        assert "sanctuary" in char.spell_effects


class TestSavesIntegration:
    """Integration tests combining saves_spell, check_immune, and damage reduction."""

    def test_immune_character_never_takes_damage(self, movable_char_factory, monkeypatch):
        """ROM magic.c:225-226 - Immune characters always save."""
        char = movable_char_factory("ImmuneFire", 3001)
        char.level = 1
        char.saving_throw = 100  # Terrible saves
        char.imm_flags = DefenseBit.FIRE

        # Even with terrible saves and high spell level, should succeed
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)
        result = saves_spell(100, char, int(DamageType.FIRE))
        assert result is True

    def test_vulnerable_resistant_cancel_out(self, movable_char_factory, monkeypatch):
        """ROM handler.c:306-314 - VULN and RES cancel to NORMAL."""
        char = movable_char_factory("Mixed", 3001)
        char.level = 10
        char.saving_throw = 0
        char.ch_class = 3  # Warrior (no fMana reduction)
        char.res_flags = DefenseBit.FIRE
        char.vuln_flags = DefenseBit.FIRE

        # Base save: 50 + (10 - 10) * 5 = 50
        # RES would add +2, but VULN cancels to NORMAL (+0)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 49)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is True

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)
        result = saves_spell(10, char, int(DamageType.FIRE))
        assert result is False

    def test_mage_class_gets_better_saves(self, movable_char_factory, monkeypatch):
        """ROM magic.c:235-236 - Mage class gets 10% save bonus."""
        mage = movable_char_factory("Mage", 3001)
        mage.level = 10
        mage.saving_throw = 0
        mage.ch_class = 0  # Mage
        mage.is_npc = False

        warrior = movable_char_factory("Warrior", 3002)
        warrior.level = 10
        warrior.saving_throw = 0
        warrior.ch_class = 3  # Warrior
        warrior.is_npc = False

        # Base save: 50 + (10 - 10) * 5 = 50
        # Mage: 9 * 50 / 10 = 45
        # Warrior: 50

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 45)
        assert saves_spell(10, mage, int(DamageType.FIRE)) is False  # Mage needs < 45
        assert saves_spell(10, warrior, int(DamageType.FIRE)) is True  # Warrior needs < 50

    def test_level_difference_matters(self, movable_char_factory, monkeypatch):
        """ROM magic.c:219 - (victim->level - level) * 5 is significant."""
        char = movable_char_factory("LevelTest", 3001)
        char.saving_throw = 0
        char.ch_class = 3  # Warrior (no fMana reduction)

        # Level 20 vs level 10 spell
        char.level = 20
        # Save = 50 + (20 - 10) * 5 = 100, clamped to 95
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 94)
        assert saves_spell(10, char, int(DamageType.FIRE)) is True

        # Level 10 vs level 20 spell
        char.level = 10
        # Save = 50 + (10 - 20) * 5 = 0, clamped to 5
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)
        assert saves_spell(20, char, int(DamageType.FIRE)) is False

    def test_saving_throw_stat_matters(self, movable_char_factory, monkeypatch):
        """ROM magic.c:219 - saving_throw * 2 is subtracted from save."""
        char = movable_char_factory("SaveTest", 3001)
        char.level = 10
        char.ch_class = 3  # Warrior (no fMana reduction)

        # Good saves: -10
        char.saving_throw = -10
        # Save = 50 + (10 - 10) * 5 - (-10) * 2 = 50 + 20 = 70
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 69)
        assert saves_spell(10, char, int(DamageType.FIRE)) is True

        # Bad saves: +10
        char.saving_throw = 10
        # Save = 50 + (10 - 10) * 5 - 10 * 2 = 50 - 20 = 30
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 30)
        assert saves_spell(10, char, int(DamageType.FIRE)) is False
