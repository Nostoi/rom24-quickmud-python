"""
Test weapon damage calculation logic.
"""

from mud.combat.engine import calculate_weapon_damage
from mud.models.constants import DamageType, Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def setup_damage_test():
    """Create test characters for damage calculation."""
    initialize_world()

    room_vnum = 3001  # limbo

    # Create attacker
    attacker = create_test_character("Attacker", room_vnum)
    attacker.level = 20
    attacker.damroll = 5
    attacker.enhanced_damage_skill = 0  # Start with no enhanced damage
    attacker.skills["hand to hand"] = 100

    # Create victim
    victim = create_test_character("Victim", room_vnum)
    victim.hit = 100
    victim.position = Position.FIGHTING

    return attacker, victim


def test_unarmed_damage_calculation():
    """Test unarmed damage calculation matches ROM formula."""
    attacker, victim = setup_damage_test()

    # Set deterministic RNG to verify calculation
    rng_mm.seed_mm(12345)

    # Calculate unarmed damage
    # Formula: number_range(1 + 4*skill/100, 2*level/3*skill/100) + damroll * min(100,skill)/100
    # With skill=120, level=20, damroll=5:
    # Base: number_range(1+4*120/100, 2*20/3*120/100) = number_range(5, 15)
    # Plus damroll: + 5 * 100/100 = + 5
    # Total range: [5+5, 15+5] = [10, 20]
    dam_type = DamageType.BASH
    damage = calculate_weapon_damage(attacker, victim, dam_type)

    # Should be in expected range including damroll contribution
    assert 10 <= damage <= 20, f"Unarmed damage {damage} not in expected range [10, 20]"


def test_enhanced_damage_skill():
    """Test enhanced damage skill bonus."""
    attacker, victim = setup_damage_test()
    attacker.enhanced_damage_skill = 50  # 50% chance

    # Set deterministic RNG - first call for enhanced damage check, then base damage
    rng_mm.seed_mm(12345)  # This should give us a percent roll that passes the 50% check

    dam_type = DamageType.BASH
    damage = calculate_weapon_damage(attacker, victim, dam_type)

    # With enhanced damage, should be higher than base
    # Base calculation gives us some value, enhanced damage adds 2 * (dam * percent / 300)
    assert damage > 5, f"Enhanced damage {damage} should be higher than minimum"


def test_position_damage_modifiers():
    """Test damage modifiers based on victim position."""
    attacker, victim = setup_damage_test()

    # Test sleeping victim (x2 damage)
    victim.position = Position.SLEEPING
    # Mock is_awake to return False for sleeping
    victim.is_awake = lambda: False

    rng_mm.seed_mm(12345)
    damage_sleeping = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    # Test resting victim (x1.5 damage)
    victim.position = Position.RESTING
    victim.is_awake = lambda: True

    rng_mm.seed_mm(12345)  # Same seed for comparison
    damage_resting = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    # Test fighting victim (normal damage)
    victim.position = Position.FIGHTING

    rng_mm.seed_mm(12345)  # Same seed for comparison
    damage_fighting = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    # Sleeping should be highest, then resting, then fighting
    assert damage_sleeping > damage_resting > damage_fighting, (
        f"Damage progression wrong: sleeping={damage_sleeping}, resting={damage_resting}, fighting={damage_fighting}"
    )


def test_damroll_contribution():
    """Test that damroll contributes to final damage."""
    attacker, victim = setup_damage_test()

    # Test with low damroll
    attacker.damroll = 2
    rng_mm.seed_mm(12345)
    damage_low = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    # Test with high damroll
    attacker.damroll = 10
    rng_mm.seed_mm(12345)
    damage_high = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    # Higher damroll should give higher damage
    assert damage_high > damage_low, f"Higher damroll should increase damage: {damage_high} vs {damage_low}"

    # The difference should be approximately the damroll difference (modified by skill)
    expected_diff = (10 - 2) * 120 // 100  # skill=120
    actual_diff = damage_high - damage_low
    assert abs(actual_diff - expected_diff) <= 1, (
        f"Damroll contribution incorrect: expected ~{expected_diff}, got {actual_diff}"
    )


def test_minimum_damage():
    """Test that damage is always at least 1."""
    attacker, victim = setup_damage_test()

    # Set very low stats to try to get 0 damage
    attacker.level = 1
    attacker.damroll = -10
    attacker.enhanced_damage_skill = 0

    damage = calculate_weapon_damage(attacker, victim, DamageType.BASH)

    assert damage >= 1, f"Damage should be at least 1, got {damage}"
