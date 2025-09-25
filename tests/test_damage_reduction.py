"""Tests for damage reduction mechanics in combat engine.

These tests verify ROM parity for damage reduction from sanctuary,
protect_good/evil affects, and drunk condition.
"""

import pytest

from mud.combat.engine import apply_damage_reduction, is_evil, is_good, is_neutral
from mud.models.character import Character, PCData
from mud.models.constants import AffectFlag
from mud.utils import rng_mm


@pytest.fixture
def attacker():
    """Create a test attacker character."""
    char = Character(name="Attacker", level=10, alignment=0)
    return char


@pytest.fixture
def victim():
    """Create a test victim character."""
    char = Character(name="Victim", level=10, alignment=0)
    char.pcdata = PCData()
    return char


def test_drunk_condition_damage_reduction(attacker, victim):
    """Test drunk condition reduces damage by 10% for PC victims."""
    rng_mm.seed_mm(12345)  # For deterministic tests

    # Set victim as drunk (condition[0] = COND_DRUNK > 10)
    victim.pcdata.condition = [15, 0, 0, 0]  # drunk condition = 15

    # Test damage reduction
    original_damage = 10
    reduced_damage = apply_damage_reduction(attacker, victim, original_damage)

    # ROM: 9 * dam / 10 with C integer division
    expected = 9 * 10 // 10  # = 9
    assert reduced_damage == expected

    # Test no reduction when not drunk enough
    victim.pcdata.condition[0] = 5  # not drunk enough
    no_reduction = apply_damage_reduction(attacker, victim, original_damage)
    assert no_reduction == original_damage

    # Test no reduction for damage <= 1
    victim.pcdata.condition[0] = 15  # drunk again
    low_damage = apply_damage_reduction(attacker, victim, 1)
    assert low_damage == 1


def test_drunk_condition_npc_immunity(attacker, victim):
    """Test NPCs are not affected by drunk condition."""
    # Make victim an NPC by removing pcdata
    victim.pcdata = None

    original_damage = 10
    reduced_damage = apply_damage_reduction(attacker, victim, original_damage)

    # Should be no reduction for NPCs
    assert reduced_damage == original_damage


def test_sanctuary_damage_reduction(attacker, victim):
    """Test sanctuary affect halves damage."""
    rng_mm.seed_mm(12345)

    # Add sanctuary affect
    victim.add_affect(AffectFlag.SANCTUARY)

    # Test damage reduction
    original_damage = 10
    reduced_damage = apply_damage_reduction(attacker, victim, original_damage)

    # ROM: dam / 2 with C integer division
    expected = 10 // 2  # = 5
    assert reduced_damage == expected

    # Test no reduction without sanctuary
    victim.remove_affect(AffectFlag.SANCTUARY)
    no_reduction = apply_damage_reduction(attacker, victim, original_damage)
    assert no_reduction == original_damage

    # Test no reduction for damage <= 1
    victim.add_affect(AffectFlag.SANCTUARY)
    low_damage = apply_damage_reduction(attacker, victim, 1)
    assert low_damage == 1


def test_protection_spells_damage_reduction(attacker, victim):
    """Test protect_good/evil affects reduce damage vs opposing alignment."""
    rng_mm.seed_mm(12345)

    # Test protect_evil vs evil attacker
    attacker.alignment = -500  # Evil attacker
    victim.add_affect(AffectFlag.PROTECT_EVIL)

    original_damage = 12
    reduced_damage = apply_damage_reduction(attacker, victim, original_damage)

    # ROM: dam -= dam/4 with C integer division
    expected = 12 - (12 // 4)  # 12 - 3 = 9
    assert reduced_damage == expected

    # Test protect_good vs good attacker
    attacker.alignment = 500  # Good attacker
    victim.remove_affect(AffectFlag.PROTECT_EVIL)
    victim.add_affect(AffectFlag.PROTECT_GOOD)

    reduced_damage = apply_damage_reduction(attacker, victim, original_damage)
    expected = 12 - (12 // 4)  # 12 - 3 = 9
    assert reduced_damage == expected

    # Test no reduction when alignments don't match
    attacker.alignment = 0  # Neutral attacker
    no_reduction = apply_damage_reduction(attacker, victim, original_damage)
    assert no_reduction == original_damage

    # Test no reduction without protection spell
    attacker.alignment = 500  # Good attacker again
    victim.remove_affect(AffectFlag.PROTECT_GOOD)
    no_reduction = apply_damage_reduction(attacker, victim, original_damage)
    assert no_reduction == original_damage


def test_combined_damage_reductions(attacker, victim):
    """Test multiple damage reductions stack properly."""
    rng_mm.seed_mm(12345)

    # Set up all reductions
    victim.pcdata.condition = [15, 0, 0, 0]  # Drunk
    victim.add_affect(AffectFlag.SANCTUARY)
    victim.add_affect(AffectFlag.PROTECT_EVIL)
    attacker.alignment = -500  # Evil attacker

    original_damage = 20
    final_damage = apply_damage_reduction(attacker, victim, original_damage)

    # Apply reductions in order following C code:
    # 1. Drunk: 20 * 9/10 = 18
    # 2. Sanctuary: 18 / 2 = 9
    # 3. Protection: 9 - 9/4 = 9 - 2 = 7
    expected_drunk = 20 * 9 // 10  # = 18
    expected_sanctuary = expected_drunk // 2  # = 9
    expected_final = expected_sanctuary - (expected_sanctuary // 4)  # = 9 - 2 = 7

    assert final_damage == expected_final


def test_alignment_classification_functions():
    """Test ROM alignment classification functions."""
    # Test good alignment (>= 350)
    good_char = Character(alignment=350)
    very_good_char = Character(alignment=1000)
    assert is_good(good_char)
    assert is_good(very_good_char)
    assert not is_evil(good_char)
    assert not is_neutral(good_char)

    # Test evil alignment (<= -350)
    evil_char = Character(alignment=-350)
    very_evil_char = Character(alignment=-1000)
    assert is_evil(evil_char)
    assert is_evil(very_evil_char)
    assert not is_good(evil_char)
    assert not is_neutral(evil_char)

    # Test neutral alignment (-349 to 349)
    neutral_char = Character(alignment=0)
    slightly_good_char = Character(alignment=349)
    slightly_evil_char = Character(alignment=-349)

    assert is_neutral(neutral_char)
    assert is_neutral(slightly_good_char)
    assert is_neutral(slightly_evil_char)
    assert not is_good(neutral_char)
    assert not is_evil(neutral_char)


def test_damage_reduction_edge_cases():
    """Test edge cases and boundary conditions."""
    attacker = Character(alignment=0)
    victim = Character(alignment=0)
    victim.pcdata = PCData()

    # Test damage = 1 (no reductions should apply)
    victim.add_affect(AffectFlag.SANCTUARY)
    victim.pcdata.condition = [15, 0, 0, 0]
    damage = apply_damage_reduction(attacker, victim, 1)
    assert damage == 1

    # Test damage = 0 (should pass through unchanged)
    damage = apply_damage_reduction(attacker, victim, 0)
    assert damage == 0

    # Test negative damage (should pass through unchanged)
    damage = apply_damage_reduction(attacker, victim, -5)
    assert damage == -5

    # Test missing pcdata condition array
    victim.pcdata.condition = []
    damage = apply_damage_reduction(attacker, victim, 10)
    # Should not crash and should still apply sanctuary
    assert damage == 5  # Only sanctuary reduction
