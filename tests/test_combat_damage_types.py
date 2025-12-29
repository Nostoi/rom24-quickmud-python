"""Test damage type resistance/vulnerability system.

Tests ROM C fight.c:804-816 damage modifier logic via check_immune().
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_damage
from mud.models.character import Character
from mud.models.constants import DamageType, Position, DefenseBit


@pytest.fixture
def attacker(movable_char_factory) -> Character:
    """Create a test attacker."""
    char = movable_char_factory("Attacker", 3001, points=100)
    char.level = 10
    char.hit = 100
    char.max_hit = 100
    return char


@pytest.fixture
def victim(movable_char_factory) -> Character:
    """Create a test victim with no resistances."""
    char = movable_char_factory("Victim", 3001, points=100)
    char.level = 10
    char.hit = 100
    char.max_hit = 100
    # No resistances by default
    char.imm_flags = 0
    char.res_flags = 0
    char.vuln_flags = 0
    return char


def test_normal_damage_no_resistance(attacker, victim):
    """Test damage with no resistance/vulnerability (baseline)."""
    # Apply 30 damage with no resistance
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # Victim should take exactly 30 damage
    assert victim.hit == 70  # 100 - 30 = 70


def test_resistance_reduces_damage_by_one_third(attacker, victim):
    """Test RES_FIRE reduces fire damage by 33% (ROM fight.c:811)."""
    # Give victim fire resistance
    victim.res_flags = DefenseBit.FIRE

    # Apply 30 fire damage
    # ROM: dam -= dam / 3 (C integer division)
    # 30 - (30 / 3) = 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # Victim should take 20 damage (30 - 10)
    assert victim.hit == 80  # 100 - 20 = 80


def test_vulnerability_increases_damage_by_one_half(attacker, victim):
    """Test VULN_FIRE increases fire damage by 50% (ROM fight.c:814)."""
    # Give victim fire vulnerability
    victim.vuln_flags = DefenseBit.FIRE

    # Apply 30 fire damage
    # ROM: dam += dam / 2 (C integer division)
    # 30 + (30 / 2) = 30 + 15 = 45 damage
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # Victim should take 45 damage (30 + 15)
    assert victim.hit == 55  # 100 - 45 = 55


def test_immunity_prevents_all_damage(attacker, victim):
    """Test IMM_FIRE prevents all fire damage (ROM fight.c:807-808)."""
    # Give victim fire immunity
    victim.imm_flags = DefenseBit.FIRE

    # Apply 30 fire damage
    # ROM: immune = TRUE; dam = 0
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # Victim should take NO damage
    assert victim.hit == 100  # 100 - 0 = 100


def test_weapon_resistance_affects_physical_damage(attacker, victim):
    """Test RES_WEAPON applies to bash/pierce/slash (ROM handler.c:224-231)."""
    # Give victim weapon resistance (applies to all physical damage types)
    victim.res_flags = DefenseBit.WEAPON

    # Apply 30 bash damage
    # ROM: dam -= dam / 3 (C integer division)
    # 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.BASH, show=False)

    # Victim should take 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_magic_resistance_affects_magical_damage(attacker, victim):
    """Test RES_MAGIC applies to magical damage types (ROM handler.c:234-241)."""
    # Give victim magic resistance (applies to all magical damage types)
    victim.res_flags = DefenseBit.MAGIC

    # Apply 30 lightning damage (magical type)
    # ROM: dam -= dam / 3 (C integer division)
    # 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.LIGHTNING, show=False)

    # Victim should take 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_specific_resistance_overrides_weapon_global(attacker, victim):
    """Test specific RES_FIRE overrides global RES_WEAPON (ROM handler.c:244-320)."""
    # Give victim weapon resistance AND fire resistance
    victim.res_flags = DefenseBit.WEAPON | DefenseBit.FIRE

    # Apply 30 fire damage
    # ROM: specific bit (RES_FIRE) should be checked, not global (RES_WEAPON)
    # 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # Victim should take 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_c_integer_division_semantics(attacker, victim):
    """Test damage reduction uses C integer division semantics."""
    # Give victim cold resistance
    victim.res_flags = DefenseBit.COLD

    # Apply 35 cold damage
    # ROM: dam -= dam / 3 (C integer division)
    # 35 / 3 = 11 (C integer division, truncates)
    # 35 - 11 = 24 damage
    apply_damage(attacker, victim, 35, DamageType.COLD, show=False)

    # Victim should take 24 damage (35 - 11)
    assert victim.hit == 76  # 100 - 24 = 76


def test_vulnerability_c_integer_division(attacker, victim):
    """Test vulnerability increase uses C integer division semantics."""
    # Give victim acid vulnerability
    victim.vuln_flags = DefenseBit.ACID

    # Apply 35 acid damage
    # ROM: dam += dam / 2 (C integer division)
    # 35 / 2 = 17 (C integer division, truncates)
    # 35 + 17 = 52 damage
    apply_damage(attacker, victim, 35, DamageType.ACID, show=False)

    # Victim should take 52 damage (35 + 17)
    assert victim.hit == 48  # 100 - 52 = 48


def test_resistance_on_slash_damage(attacker, victim):
    """Test resistance applies to slash damage."""
    # Give victim slash resistance
    victim.res_flags = DefenseBit.SLASH

    # Apply 30 slash damage
    # 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.SLASH, show=False)

    # Victim should take 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_resistance_on_pierce_damage(attacker, victim):
    """Test resistance applies to pierce damage."""
    # Give victim pierce resistance
    victim.res_flags = DefenseBit.PIERCE

    # Apply 30 pierce damage
    # 30 - 10 = 20 damage
    apply_damage(attacker, victim, 30, DamageType.PIERCE, show=False)

    # Victim should take 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_multiple_resistances_specific_type_wins(attacker, victim):
    """Test specific type resistance takes precedence over global."""
    # Give victim both weapon resistance (global) and fire resistance (specific)
    victim.res_flags = DefenseBit.WEAPON | DefenseBit.FIRE

    # Apply 30 bash damage (physical, should use weapon resistance)
    apply_damage(attacker, victim, 30, DamageType.BASH, show=False)
    assert victim.hit == 80  # 100 - 20 = 80

    # Reset hit points
    victim.hit = 100

    # Apply 30 fire damage (should use fire resistance, not weapon)
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)
    assert victim.hit == 80  # 100 - 20 = 80


def test_immunity_overrides_vulnerability(attacker, victim):
    """Test immunity takes precedence over vulnerability (ROM handler.c:308-309)."""
    # Give victim both fire immunity AND fire vulnerability (edge case)
    victim.imm_flags = DefenseBit.FIRE
    victim.vuln_flags = DefenseBit.FIRE

    # Apply 30 fire damage
    # ROM: immunity check happens first, reduces to resistance
    # But should still block damage effectively
    apply_damage(attacker, victim, 30, DamageType.FIRE, show=False)

    # With immunity, should take reduced damage (immunity + vuln = resistance per ROM)
    # ROM handler.c:308-309: if immune == IS_IMMUNE: immune = IS_RESISTANT
    # So 30 - 10 = 20 damage
    assert victim.hit == 80  # 100 - 20 = 80


def test_no_damage_type_specified_no_modifiers(attacker, victim):
    """Test damage without dam_type specified bypasses resistance checks."""
    # Give victim fire resistance
    victim.res_flags = DefenseBit.FIRE

    # Apply 30 damage with NO damage type specified (use DAM_NONE)
    apply_damage(attacker, victim, 30, DamageType.NONE, show=False)

    # Should take full damage (no resistance check for DAM_NONE)
    assert victim.hit == 70  # 100 - 30 = 70


def test_position_change_on_damage(attacker, victim):
    """Test victim position changes when damaged (ROM fight.c:832)."""
    victim.position = Position.STANDING

    # Apply enough damage to change position
    # ROM: position updated via update_pos() after damage
    apply_damage(attacker, victim, 90, DamageType.BASH, show=False)

    # Victim should be fighting
    assert victim.position == Position.FIGHTING
    assert victim.hit == 10  # 100 - 90 = 10
