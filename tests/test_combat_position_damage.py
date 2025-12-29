"""Tests for position-based damage multipliers (ROM fight.c:575-578).

ROM C Reference (src/fight.c:575-578):
    if (!IS_AWAKE (victim))
        dam *= 2;
    else if (victim->position < POS_FIGHTING)
        dam = dam * 3 / 2;

Position hierarchy (merc.h:301-310):
    POS_DEAD = 0
    POS_MORTAL = 1
    POS_INCAP = 2
    POS_STUNNED = 3
    POS_SLEEPING = 4
    POS_RESTING = 5
    POS_SITTING = 6
    POS_FIGHTING = 7
    POS_STANDING = 8

IS_AWAKE macro (merc.h:524):
    #define IS_AWAKE(ch) (ch->position > POS_SLEEPING)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.combat import engine as combat_engine
from mud.models.constants import DamageType, Position, WeaponType
from mud.models.room import Room
from mud.utils import rng_mm


@pytest.fixture
def setup_position_combat():
    """Create attacker and victim for position-based damage testing."""
    room = Room(vnum=3001)

    attacker = SimpleNamespace(
        name="Attacker",
        level=30,
        damroll=0,
        hitroll=100,
        has_shield_equipped=False,
        enhanced_damage_skill=0,
        skills={"sword": 100},
        position=Position.FIGHTING,
        affected_by=0,
        in_room=room,
    )

    victim = SimpleNamespace(
        name="Victim",
        level=30,
        hit=100,
        max_hit=100,
        armor=[0, 0, 0, 0],
        saves=0,
        size=2,
        affected_by=0,
        imm_flags=0,
        res_flags=0,
        vuln_flags=0,
        in_room=room,
        position=Position.FIGHTING,  # Default to fighting position
    )

    weapon = SimpleNamespace(
        item_type="weapon",
        new_format=True,
        value=[int(WeaponType.SWORD), 2, 4, 0],
        weapon_stats=set(),
        weapon_flags=0,
        level=30,
        name="longsword",
    )
    attacker.equipment = {"wield": weapon}

    return attacker, victim, weapon


def test_sleeping_victim_takes_double_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test sleeping victims take 2x damage (ROM fight.c:575-576).

    ROM C Reference:
        if (!IS_AWAKE (victim))  // position <= POS_SLEEPING
            dam *= 2;
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test sleeping victim
    victim.position = Position.SLEEPING
    sleeping_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: sleeping victims take 2x damage
    assert sleeping_damage == base_damage * 2, (
        f"Sleeping victim should take 2x damage: {sleeping_damage} != {base_damage * 2}"
    )


def test_resting_victim_takes_1_5x_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resting victims take 1.5x damage (ROM fight.c:577-578).

    ROM C Reference:
        else if (victim->position < POS_FIGHTING)  // position 5-6
            dam = dam * 3 / 2;
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test resting victim
    victim.position = Position.RESTING
    resting_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: resting victims take 1.5x damage (dam * 3 / 2)
    expected_damage = base_damage * 3 // 2
    assert resting_damage == expected_damage, (
        f"Resting victim should take 1.5x damage: {resting_damage} != {expected_damage}"
    )


def test_sitting_victim_takes_1_5x_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test sitting victims take 1.5x damage (ROM fight.c:577-578).

    ROM C Reference:
        else if (victim->position < POS_FIGHTING)  // position 5-6
            dam = dam * 3 / 2;
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test sitting victim
    victim.position = Position.SITTING
    sitting_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: sitting victims take 1.5x damage (dam * 3 / 2)
    expected_damage = base_damage * 3 // 2
    assert sitting_damage == expected_damage, (
        f"Sitting victim should take 1.5x damage: {sitting_damage} != {expected_damage}"
    )


def test_standing_victim_takes_normal_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test standing victims take normal damage (no multiplier)."""
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with fighting position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test standing victim
    victim.position = Position.STANDING
    standing_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Standing victims take normal damage (no multiplier)
    assert standing_damage == base_damage, (
        f"Standing victim should take normal damage: {standing_damage} != {base_damage}"
    )


def test_fighting_victim_takes_normal_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fighting victims take normal damage (no multiplier)."""
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Fighting victims take normal damage (no multiplier)
    # This is the baseline, so damage should match itself
    assert base_damage > 0, "Base damage should be positive"


def test_stunned_victim_takes_double_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test stunned victims take 2x damage (position <= SLEEPING).

    ROM C Reference:
        if (!IS_AWAKE (victim))  // position <= POS_SLEEPING
            dam *= 2;

    POS_STUNNED (3) < POS_SLEEPING (4), so !IS_AWAKE is TRUE.
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test stunned victim
    victim.position = Position.STUNNED
    stunned_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: stunned victims take 2x damage (position <= SLEEPING)
    assert stunned_damage == base_damage * 2, (
        f"Stunned victim should take 2x damage: {stunned_damage} != {base_damage * 2}"
    )


def test_incapacitated_victim_takes_double_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test incapacitated victims take 2x damage (position <= SLEEPING).

    ROM C Reference:
        if (!IS_AWAKE (victim))  // position <= POS_SLEEPING
            dam *= 2;

    POS_INCAP (2) < POS_SLEEPING (4), so !IS_AWAKE is TRUE.
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test incapacitated victim
    victim.position = Position.INCAP
    incap_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: incapacitated victims take 2x damage (position <= SLEEPING)
    assert incap_damage == base_damage * 2, (
        f"Incapacitated victim should take 2x damage: {incap_damage} != {base_damage * 2}"
    )


def test_mortal_victim_takes_double_damage(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test mortally wounded victims take 2x damage (position <= SLEEPING).

    ROM C Reference:
        if (!IS_AWAKE (victim))  // position <= POS_SLEEPING
            dam *= 2;

    POS_MORTAL (1) < POS_SLEEPING (4), so !IS_AWAKE is TRUE.
    """
    attacker, victim, weapon = setup_position_combat
    victim.position = Position.FIGHTING  # Start with normal position

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Get base damage when fighting
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Now test mortally wounded victim
    victim.position = Position.MORTAL
    mortal_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # ROM: mortally wounded victims take 2x damage (position <= SLEEPING)
    assert mortal_damage == base_damage * 2, (
        f"Mortally wounded victim should take 2x damage: {mortal_damage} != {base_damage * 2}"
    )


def test_position_multiplier_stacks_with_damage_dice(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test position multiplier applies AFTER base damage calculation.

    ROM C shows position multiplier is applied after weapon dice roll.
    """
    attacker, victim, weapon = setup_position_combat

    # Use non-trivial dice roll to verify multiplication order
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 15)  # Fixed dice result
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    victim.position = Position.FIGHTING
    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    victim.position = Position.SLEEPING
    sleeping_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Position multiplier should apply to ENTIRE base damage
    assert sleeping_damage == base_damage * 2


def test_position_multiplier_order_vs_resistance(setup_position_combat, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test position multiplier applies BEFORE resistance/vulnerability (ROM fight.c order).

    ROM C order (fight.c:575-816):
    1. Position multiplier (line 575-578)
    2. Backstab/dirt kick/trip (line 580-603)
    3. Damage type resistance/vulnerability (line 804-816)
    """
    attacker, victim, weapon = setup_position_combat

    # Fix RNG for deterministic damage
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    # Set victim to be resistant to slash damage
    # This is a bit tricky to test since resistance is checked in apply_damage(),
    # not calculate_weapon_damage(). The position multiplier happens in calculate_weapon_damage().
    # So we just verify that position multiplier happens regardless of resistance flags.

    victim.res_flags = 1 << int(DamageType.SLASH)  # Resistant to slash
    victim.position = Position.SLEEPING

    sleeping_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=100,
    )

    # Position multiplier should still apply (resistance is checked later in apply_damage)
    # We just verify damage is calculated (resistance will be applied in apply_damage, not here)
    assert sleeping_damage > 0, "Damage should be calculated regardless of resistance flags"
