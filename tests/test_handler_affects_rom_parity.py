"""
ROM Parity Tests: Character Affect Mechanics (ROM handler.c:1266-1492)

Tests affect_to_char, affect_remove, affect_join, and is_affected mechanics
to match ROM 2.4b6 handler.c affect manipulation exactly.

ROM C Reference: src/handler.c:1266-1492
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Stat
from mud.models.obj import Affect


@pytest.fixture
def test_char():
    """Create a test character for affect manipulation."""
    return Character(
        name="TestChar",
        level=10,
        hit=100,
        max_hit=100,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        hitroll=0,
        damroll=0,
        saving_throw=0,
        armor=[100, 100, 100, 100],
        affected_by=0,
        perm_stat=[13, 13, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
    )


# =============================================================================
# affect_to_char Mechanics (ROM handler.c:1266-1279)
# =============================================================================


@pytest.mark.p0
class TestAffectToChar:
    """Test affect_to_char() adds affects to character linked list (ROM handler.c:1266-1279)."""

    def test_affect_to_char_adds_affect_to_spell_effects(self, test_char):
        """ROM handler.c:1272-1275 - affect_to_char() adds affect to ch->affected linked list."""
        from mud.models.character import SpellEffect

        # ROM: paf_new->next = ch->affected; ch->affected = paf_new;
        assert len(test_char.spell_effects) == 0

        effect = SpellEffect(
            name="armor",
            duration=24,
            level=10,
            ac_mod=-20,
        )
        test_char.apply_spell_effect(effect)

        # Verify affect was added
        assert len(test_char.spell_effects) == 1
        assert "armor" in test_char.spell_effects
        assert test_char.spell_effects["armor"].duration == 24
        assert test_char.spell_effects["armor"].level == 10

    def test_affect_to_char_calls_affect_modify(self, test_char):
        """ROM handler.c:1277 - affect_to_char() calls affect_modify(ch, paf_new, TRUE)."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify(ch, paf_new, TRUE) applies AC modifier
        initial_armor = test_char.armor.copy()

        effect = SpellEffect(
            name="armor",
            duration=24,
            level=10,
            ac_mod=-20,
        )
        test_char.apply_spell_effect(effect)

        # Verify affect_modify was applied (armor decreased by 20 on all AC types)
        assert test_char.armor == [
            initial_armor[0] - 20,
            initial_armor[1] - 20,
            initial_armor[2] - 20,
            initial_armor[3] - 20,
        ]

    def test_affect_to_char_applies_hitroll_damroll(self, test_char):
        """ROM handler.c:1277 - affect_modify() applies hitroll and damroll bonuses."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() increments hitroll/damroll by paf->modifier
        assert test_char.hitroll == 0
        assert test_char.damroll == 0

        effect = SpellEffect(
            name="bless",
            duration=10,
            level=10,
            hitroll_mod=2,
            damroll_mod=2,
        )
        test_char.apply_spell_effect(effect)

        # Verify modifiers were applied
        assert test_char.hitroll == 2
        assert test_char.damroll == 2

    def test_affect_to_char_applies_saving_throw(self, test_char):
        """ROM handler.c:1277 - affect_modify() applies saving throw bonuses."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() decrements saving_throw by paf->modifier
        assert test_char.saving_throw == 0

        effect = SpellEffect(
            name="bless",
            duration=10,
            level=10,
            saving_throw_mod=-2,
        )
        test_char.apply_spell_effect(effect)

        # Verify saving throw was modified
        assert test_char.saving_throw == -2

    def test_affect_to_char_applies_affect_flag(self, test_char):
        """ROM handler.c:1277 - affect_modify() sets affect flag bitvectors."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() calls SET_BIT(ch->affected_by, paf->bitvector)
        assert not test_char.has_affect(AffectFlag.SANCTUARY)

        effect = SpellEffect(
            name="sanctuary",
            duration=10,
            level=10,
            affect_flag=AffectFlag.SANCTUARY,
        )
        test_char.apply_spell_effect(effect)

        # Verify affect flag was set
        assert test_char.has_affect(AffectFlag.SANCTUARY)

    def test_affect_to_char_applies_stat_modifiers(self, test_char):
        """ROM handler.c:1277 - affect_modify() applies stat modifiers (APPLY_STR, etc.)."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() increments ch->mod_stat[paf->location] by paf->modifier
        assert test_char.get_curr_stat(Stat.STR) == 13  # base perm_stat

        effect = SpellEffect(
            name="giant_strength",
            duration=10,
            level=10,
            stat_modifiers={Stat.STR: 5},
        )
        test_char.apply_spell_effect(effect)

        # Verify stat modifier was applied
        assert test_char.get_curr_stat(Stat.STR) == 18  # 13 + 5

    def test_affect_to_char_multiple_affects(self, test_char):
        """ROM handler.c:1272-1275 - Multiple affects stack in linked list."""
        from mud.models.character import SpellEffect

        # ROM: Each affect_to_char() adds to the head of ch->affected
        effect1 = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        effect2 = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2)
        effect3 = SpellEffect(name="sanctuary", duration=8, level=10, affect_flag=AffectFlag.SANCTUARY)

        test_char.apply_spell_effect(effect1)
        test_char.apply_spell_effect(effect2)
        test_char.apply_spell_effect(effect3)

        # Verify all affects are tracked
        assert len(test_char.spell_effects) == 3
        assert "armor" in test_char.spell_effects
        assert "bless" in test_char.spell_effects
        assert "sanctuary" in test_char.spell_effects


# =============================================================================
# affect_remove Mechanics (ROM handler.c:1317-1360)
# =============================================================================


@pytest.mark.p0
class TestAffectRemove:
    """Test affect_remove() removes affects from character (ROM handler.c:1317-1360)."""

    def test_affect_remove_from_head_of_list(self, test_char):
        """ROM handler.c:1333-1336 - Remove affect from head of linked list."""
        from mud.models.character import SpellEffect

        # ROM: if (paf == ch->affected) { ch->affected = paf->next; }
        effect = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect)

        assert "armor" in test_char.spell_effects
        initial_armor = test_char.armor.copy()

        test_char.remove_spell_effect("armor")

        # Verify affect was removed
        assert "armor" not in test_char.spell_effects
        # Verify armor was restored (affect_modify called with FALSE)
        assert test_char.armor != initial_armor

    def test_affect_remove_from_middle_of_list(self, test_char):
        """ROM handler.c:1338-1351 - Remove affect from middle of linked list."""
        from mud.models.character import SpellEffect

        # ROM: for (prev = ch->affected; prev != NULL; prev = prev->next)
        effect1 = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        effect2 = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2)
        effect3 = SpellEffect(name="sanctuary", duration=8, level=10, affect_flag=AffectFlag.SANCTUARY)

        test_char.apply_spell_effect(effect1)
        test_char.apply_spell_effect(effect2)
        test_char.apply_spell_effect(effect3)

        # Remove middle affect
        test_char.remove_spell_effect("bless")

        # Verify correct affect was removed
        assert "armor" in test_char.spell_effects
        assert "bless" not in test_char.spell_effects
        assert "sanctuary" in test_char.spell_effects

    def test_affect_remove_calls_affect_modify_false(self, test_char):
        """ROM handler.c:1327 - affect_remove() calls affect_modify(ch, paf, FALSE)."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify(ch, paf, FALSE) reverts AC modifier
        effect = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect)

        modified_armor = test_char.armor.copy()
        test_char.remove_spell_effect("armor")

        # Verify armor was reverted (AC increased by 20)
        assert test_char.armor == [
            modified_armor[0] + 20,
            modified_armor[1] + 20,
            modified_armor[2] + 20,
            modified_armor[3] + 20,
        ]

    def test_affect_remove_reverts_hitroll_damroll(self, test_char):
        """ROM handler.c:1327 - affect_modify(FALSE) reverts hitroll/damroll."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() decrements hitroll/damroll by paf->modifier
        effect = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2, damroll_mod=2)
        test_char.apply_spell_effect(effect)

        assert test_char.hitroll == 2
        assert test_char.damroll == 2

        test_char.remove_spell_effect("bless")

        # Verify modifiers were reverted
        assert test_char.hitroll == 0
        assert test_char.damroll == 0

    def test_affect_remove_reverts_saving_throw(self, test_char):
        """ROM handler.c:1327 - affect_modify(FALSE) reverts saving throw."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() increments saving_throw by paf->modifier (reverting -2)
        effect = SpellEffect(name="bless", duration=10, level=10, saving_throw_mod=-2)
        test_char.apply_spell_effect(effect)

        assert test_char.saving_throw == -2

        test_char.remove_spell_effect("bless")

        # Verify saving throw was reverted
        assert test_char.saving_throw == 0

    def test_affect_remove_clears_affect_flag(self, test_char):
        """ROM handler.c:1327 - affect_modify(FALSE) clears affect flag bitvectors."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() calls REMOVE_BIT(ch->affected_by, paf->bitvector)
        effect = SpellEffect(name="sanctuary", duration=10, level=10, affect_flag=AffectFlag.SANCTUARY)
        test_char.apply_spell_effect(effect)

        assert test_char.has_affect(AffectFlag.SANCTUARY)

        test_char.remove_spell_effect("sanctuary")

        # Verify affect flag was cleared
        assert not test_char.has_affect(AffectFlag.SANCTUARY)

    def test_affect_remove_reverts_stat_modifiers(self, test_char):
        """ROM handler.c:1327 - affect_modify(FALSE) reverts stat modifiers."""
        from mud.models.character import SpellEffect

        # ROM: affect_modify() decrements ch->mod_stat[paf->location] by paf->modifier
        effect = SpellEffect(name="giant_strength", duration=10, level=10, stat_modifiers={Stat.STR: 5})
        test_char.apply_spell_effect(effect)

        assert test_char.get_curr_stat(Stat.STR) == 18  # 13 + 5

        test_char.remove_spell_effect("giant_strength")

        # Verify stat modifier was reverted
        assert test_char.get_curr_stat(Stat.STR) == 13  # back to base

    def test_affect_remove_calls_affect_check(self, test_char):
        """ROM handler.c:1358 - affect_remove() calls affect_check(ch, where, vector)."""
        from mud.models.character import SpellEffect

        # ROM: affect_check() verifies no other affects use the same bitvector
        # Apply two sanctuary affects (hypothetical - normally would join)
        effect1 = SpellEffect(name="sanctuary", duration=10, level=10, affect_flag=AffectFlag.SANCTUARY)
        effect2 = SpellEffect(name="protection_good", duration=10, level=10, affect_flag=AffectFlag.PROTECT_GOOD)

        test_char.apply_spell_effect(effect1)
        test_char.apply_spell_effect(effect2)

        assert test_char.has_affect(AffectFlag.SANCTUARY)
        assert test_char.has_affect(AffectFlag.PROTECT_GOOD)

        # Remove sanctuary - affect_check should clear SANCTUARY bit
        test_char.remove_spell_effect("sanctuary")

        assert not test_char.has_affect(AffectFlag.SANCTUARY)
        assert test_char.has_affect(AffectFlag.PROTECT_GOOD)


# =============================================================================
# affect_join Mechanics (ROM handler.c:1463-1484)
# =============================================================================


@pytest.mark.p0
class TestAffectJoin:
    """Test affect_join() stacks same-type affects (ROM handler.c:1463-1484)."""

    def test_affect_join_averages_level(self, test_char):
        """ROM handler.c:1472 - affect_join() averages level: (old + new) / 2."""
        from mud.models.character import SpellEffect

        # ROM: paf->level = (paf->level += paf_old->level) / 2;
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        effect2 = SpellEffect(name="armor", duration=10, level=20, ac_mod=-20)
        test_char.apply_spell_effect(effect2)  # This will join with existing

        # Verify level was averaged: (10 + 20) / 2 = 15
        assert test_char.spell_effects["armor"].level == 15

    def test_affect_join_sums_duration(self, test_char):
        """ROM handler.c:1473 - affect_join() sums duration."""
        from mud.models.character import SpellEffect

        # ROM: paf->duration += paf_old->duration;
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        effect2 = SpellEffect(name="armor", duration=15, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect2)

        # Verify duration was summed: 10 + 15 = 25
        assert test_char.spell_effects["armor"].duration == 25

    def test_affect_join_sums_modifier(self, test_char):
        """ROM handler.c:1474 - affect_join() sums modifier."""
        from mud.models.character import SpellEffect

        # ROM: paf->modifier += paf_old->modifier;
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        initial_armor = test_char.armor.copy()

        effect2 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-10)
        test_char.apply_spell_effect(effect2)

        # Verify AC modifier was summed: -20 + -10 = -30
        assert test_char.spell_effects["armor"].ac_mod == -30
        # Verify armor reflects combined modifier
        assert test_char.armor == [
            initial_armor[0] - 10,
            initial_armor[1] - 10,
            initial_armor[2] - 10,
            initial_armor[3] - 10,
        ]

    def test_affect_join_removes_old_affect(self, test_char):
        """ROM handler.c:1475 - affect_join() calls affect_remove(ch, paf_old)."""
        from mud.models.character import SpellEffect

        # ROM: affect_remove(ch, paf_old) before affect_to_char(ch, paf)
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        effect2 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect2)

        # Verify only one "armor" affect exists (old was removed, new was added)
        assert len([k for k in test_char.spell_effects.keys() if k == "armor"]) == 1

    def test_affect_join_calls_affect_to_char(self, test_char):
        """ROM handler.c:1480 - affect_join() calls affect_to_char(ch, paf)."""
        from mud.models.character import SpellEffect

        # ROM: affect_to_char(ch, paf) after removing old affect
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        effect2 = SpellEffect(name="armor", duration=15, level=20, ac_mod=-10)
        test_char.apply_spell_effect(effect2)

        # Verify new combined affect was applied
        assert "armor" in test_char.spell_effects
        assert test_char.spell_effects["armor"].duration == 25  # joined duration
        assert test_char.spell_effects["armor"].level == 15  # averaged level

    def test_affect_join_different_types_do_not_join(self, test_char):
        """ROM handler.c:1470 - affect_join() only joins same paf->type."""
        from mud.models.character import SpellEffect

        # ROM: if (paf_old->type == paf->type) { ... }
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        effect2 = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2)

        test_char.apply_spell_effect(effect1)
        test_char.apply_spell_effect(effect2)

        # Verify both affects exist separately
        assert "armor" in test_char.spell_effects
        assert "bless" in test_char.spell_effects
        assert len(test_char.spell_effects) == 2


# =============================================================================
# is_affected Mechanics (ROM handler.c:1447-1458)
# =============================================================================


@pytest.mark.p0
class TestIsAffected:
    """Test is_affected() checks for spell/skill affects (ROM handler.c:1447-1458)."""

    def test_is_affected_returns_true_when_affect_present(self, test_char):
        """ROM handler.c:1450-1455 - is_affected() returns TRUE when paf->type matches."""
        from mud.models.character import SpellEffect

        # ROM: for (paf = ch->affected; paf != NULL; paf = paf->next)
        effect = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect)

        # Verify is_affected returns true
        assert test_char.has_spell_effect("armor") is True

    def test_is_affected_returns_false_when_affect_absent(self, test_char):
        """ROM handler.c:1456 - is_affected() returns FALSE when no match."""
        # ROM: return FALSE;
        assert test_char.has_spell_effect("armor") is False

    def test_is_affected_checks_all_affects(self, test_char):
        """ROM handler.c:1450-1455 - is_affected() scans entire linked list."""
        from mud.models.character import SpellEffect

        # ROM: for (paf = ch->affected; paf != NULL; paf = paf->next)
        effect1 = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        effect2 = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2)
        effect3 = SpellEffect(name="sanctuary", duration=8, level=10, affect_flag=AffectFlag.SANCTUARY)

        test_char.apply_spell_effect(effect1)
        test_char.apply_spell_effect(effect2)
        test_char.apply_spell_effect(effect3)

        # Verify all affects are detected
        assert test_char.has_spell_effect("armor") is True
        assert test_char.has_spell_effect("bless") is True
        assert test_char.has_spell_effect("sanctuary") is True
        assert test_char.has_spell_effect("nonexistent") is False


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.p0
class TestAffectIntegration:
    """Integration tests for affect mechanics working together."""

    def test_full_affect_lifecycle(self, test_char):
        """Test complete lifecycle: add -> modify -> join -> remove."""
        from mud.models.character import SpellEffect

        # Add initial affect
        effect1 = SpellEffect(name="armor", duration=10, level=10, ac_mod=-20)
        test_char.apply_spell_effect(effect1)

        assert test_char.has_spell_effect("armor") is True
        assert test_char.armor[0] == 80  # 100 - 20

        # Join with another armor affect
        effect2 = SpellEffect(name="armor", duration=15, level=20, ac_mod=-10)
        test_char.apply_spell_effect(effect2)

        assert test_char.spell_effects["armor"].duration == 25  # 10 + 15
        assert test_char.spell_effects["armor"].level == 15  # (10 + 20) / 2
        assert test_char.armor[0] == 70  # 100 - 30 (joined AC mod)

        # Remove affect
        test_char.remove_spell_effect("armor")

        assert test_char.has_spell_effect("armor") is False
        assert test_char.armor[0] == 100  # restored

    def test_multiple_affect_types_interact_correctly(self, test_char):
        """Test multiple different affects can coexist and be managed independently."""
        from mud.models.character import SpellEffect

        # Add multiple different affects
        armor_effect = SpellEffect(name="armor", duration=24, level=10, ac_mod=-20)
        bless_effect = SpellEffect(name="bless", duration=10, level=10, hitroll_mod=2, damroll_mod=2)
        sanc_effect = SpellEffect(name="sanctuary", duration=8, level=10, affect_flag=AffectFlag.SANCTUARY)

        test_char.apply_spell_effect(armor_effect)
        test_char.apply_spell_effect(bless_effect)
        test_char.apply_spell_effect(sanc_effect)

        # Verify all affects are active
        assert len(test_char.spell_effects) == 3
        assert test_char.armor[0] == 80  # armor applied
        assert test_char.hitroll == 2  # bless applied
        assert test_char.damroll == 2  # bless applied
        assert test_char.has_affect(AffectFlag.SANCTUARY)  # sanctuary applied

        # Remove one affect
        test_char.remove_spell_effect("bless")

        # Verify other affects remain
        assert len(test_char.spell_effects) == 2
        assert test_char.armor[0] == 80  # armor still applied
        assert test_char.hitroll == 0  # bless removed
        assert test_char.damroll == 0  # bless removed
        assert test_char.has_affect(AffectFlag.SANCTUARY)  # sanctuary still applied

    def test_stat_modifier_stacking(self, test_char):
        """Test stat modifiers from multiple affects stack correctly."""
        from mud.models.character import SpellEffect

        # ROM: Multiple stat modifiers should stack additively
        effect1 = SpellEffect(name="giant_strength", duration=10, level=10, stat_modifiers={Stat.STR: 5})
        effect2 = SpellEffect(name="stone_skin", duration=10, level=10, stat_modifiers={Stat.STR: 3})

        test_char.apply_spell_effect(effect1)
        assert test_char.get_curr_stat(Stat.STR) == 18  # 13 + 5

        test_char.apply_spell_effect(effect2)
        assert test_char.get_curr_stat(Stat.STR) == 21  # 13 + 5 + 3

        test_char.remove_spell_effect("giant_strength")
        assert test_char.get_curr_stat(Stat.STR) == 16  # 13 + 3

        test_char.remove_spell_effect("stone_skin")
        assert test_char.get_curr_stat(Stat.STR) == 13  # base
