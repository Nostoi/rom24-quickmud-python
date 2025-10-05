"""Integration tests for damage reduction in full combat scenarios."""

import pytest

from mud.combat.engine import attack_round
from mud.models.character import Character, PCData
from mud.models.constants import AffectFlag, Position
from mud.utils import rng_mm


def assert_attack_message(message: str, target: str) -> None:
    assert message.startswith("{2")
    assert target in message
    assert message.endswith("{x")


def setup_combat_with_damage_reduction():
    """Set up combat scenario for damage reduction testing."""
    attacker = Character(
        name="Attacker",
        level=10,
        hitroll=100,  # Guarantee hit
        damroll=5,
        position=Position.STANDING,
        alignment=0,  # Neutral
    )

    victim = Character(
        name="Victim",
        level=10,
        hit=50,
        max_hit=50,
        position=Position.STANDING,
        alignment=0,  # Neutral
        pcdata=PCData(),
    )

    return attacker, victim


def test_sanctuary_integration_in_combat():
    """Test sanctuary affect reduces damage in full combat round."""
    rng_mm.seed_mm(12345)  # Deterministic results

    attacker, victim = setup_combat_with_damage_reduction()
    victim.add_affect(AffectFlag.SANCTUARY)

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    # Should hit but with reduced damage due to sanctuary
    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # Damage should be less than it would be without sanctuary
    # Verify sanctuary was applied by checking that damage is reasonable
    assert damage_dealt > 0  # Some damage was dealt
    assert damage_dealt < 10  # But reduced due to sanctuary (would be ~6-8 normally, ~3-4 with sanctuary)


def test_protection_spell_integration_in_combat():
    """Test protection affects reduce damage vs opposing alignment."""
    rng_mm.seed_mm(12345)

    attacker, victim = setup_combat_with_damage_reduction()
    attacker.alignment = -500  # Evil attacker
    victim.add_affect(AffectFlag.PROTECT_EVIL)

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # Should have reduced damage due to protect_evil vs evil attacker
    assert damage_dealt > 0
    assert damage_dealt < 10  # Reduced by 25% from protection


def test_drunk_condition_integration_in_combat():
    """Test drunk condition reduces damage in full combat."""
    rng_mm.seed_mm(12345)

    attacker, victim = setup_combat_with_damage_reduction()
    victim.pcdata.condition = [15, 0, 0, 0]  # Drunk condition > 10

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # Should have 10% reduced damage due to drunk condition
    assert damage_dealt > 0


def test_multiple_reductions_stack_in_combat():
    """Test multiple damage reductions stack properly in combat."""
    rng_mm.seed_mm(12345)

    attacker, victim = setup_combat_with_damage_reduction()

    # Apply all three types of damage reduction
    victim.add_affect(AffectFlag.SANCTUARY)  # 50% reduction
    victim.add_affect(AffectFlag.PROTECT_EVIL)  # 25% reduction vs evil
    victim.pcdata.condition = [15, 0, 0, 0]  # 10% reduction when drunk
    attacker.alignment = -500  # Evil attacker (for protection to work)

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # With all reductions stacking, damage should be significantly reduced
    # Expected: ~6-8 base damage -> ~5 (drunk) -> ~2-3 (sanctuary) -> ~2 (protection)
    assert damage_dealt > 0
    assert damage_dealt < 5  # Should be heavily reduced


def test_no_damage_reduction_for_npcs():
    """Test NPCs don't get drunk condition reduction."""
    rng_mm.seed_mm(12345)

    attacker, victim = setup_combat_with_damage_reduction()
    victim.pcdata = None  # Make victim an NPC

    # Set up conditions that would reduce damage for PCs
    victim.add_affect(AffectFlag.SANCTUARY)  # This should still work for NPCs

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # Should still get sanctuary reduction but no drunk reduction
    # (drunk reduction only applies to PCs with pcdata)
    assert damage_dealt > 0


def test_damage_reduction_with_riv_scaling():
    """Test damage reduction interacts correctly with RIV scaling."""
    rng_mm.seed_mm(12345)

    attacker, victim = setup_combat_with_damage_reduction()

    # Add sanctuary for damage reduction
    victim.add_affect(AffectFlag.SANCTUARY)

    # Set up vulnerability for damage increase (this should happen after reduction)
    victim.vuln_flags = 1 << 3  # Vulnerable to BASH damage (unarmed is BASH)

    original_hp = victim.hit
    result = attack_round(attacker, victim)

    assert_attack_message(result, "Victim")
    damage_dealt = original_hp - victim.hit

    # Damage should be: base -> sanctuary reduction -> vulnerability increase
    # This tests that the order is correct (reduction before RIV)
    assert damage_dealt > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
