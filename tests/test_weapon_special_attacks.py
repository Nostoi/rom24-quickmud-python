"""Tests for weapon special attacks following ROM C src/fight.c logic."""

from unittest.mock import Mock, patch

import pytest

from mud.combat.engine import attack_round, process_weapon_special_attacks
from mud.models.character import Character
from mud.models.constants import (
    WEAPON_FLAMING,
    WEAPON_FROST,
    WEAPON_POISON,
    WEAPON_SHOCKING,
    WEAPON_VAMPIRIC,
    DamageType,
)


@pytest.fixture
def attacker():
    """Create test attacker character."""
    char = Character(name="TestAttacker", level=20, hit=100, max_hit=100, alignment=0, fighting=None)
    return char


@pytest.fixture
def victim():
    """Create test victim character."""
    char = Character(name="TestVictim", level=15, hit=80, max_hit=80, alignment=0)
    return char


@pytest.fixture
def mock_weapon():
    """Create mock weapon for testing."""
    weapon = Mock()
    weapon.name = "test weapon"
    weapon.level = 10
    weapon.weapon_flags = 0  # No flags by default
    return weapon


def test_no_weapon_special_attacks_without_weapon(attacker, victim):
    """Test that no special attacks trigger without a weapon."""
    # No wielded_weapon attribute
    messages = process_weapon_special_attacks(attacker, victim)
    assert messages == []


def test_no_weapon_special_attacks_when_not_fighting(attacker, victim, mock_weapon):
    """Test ROM condition: attacker must be fighting victim."""
    attacker.wielded_weapon = mock_weapon
    attacker.fighting = None  # Not fighting

    messages = process_weapon_special_attacks(attacker, victim)
    assert messages == []


@patch("mud.combat.engine.saves_spell")
def test_weapon_poison_save_succeeds(mock_saves_spell, attacker, victim, mock_weapon):
    """Test WEAPON_POISON when victim saves successfully."""
    mock_saves_spell.return_value = True  # Save succeeds

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    mock_weapon.weapon_flags = WEAPON_POISON

    messages = process_weapon_special_attacks(attacker, victim)

    # Should call saves_spell with level//2
    mock_saves_spell.assert_called_once_with(5, victim, DamageType.POISON)
    assert messages == []  # No poison message if save succeeds


@patch("mud.combat.engine.saves_spell")
def test_weapon_poison_save_fails(mock_saves_spell, attacker, victim, mock_weapon):
    """Test WEAPON_POISON when victim fails save."""
    mock_saves_spell.return_value = False  # Save fails

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    mock_weapon.weapon_flags = WEAPON_POISON

    messages = process_weapon_special_attacks(attacker, victim)

    mock_saves_spell.assert_called_once_with(5, victim, DamageType.POISON)
    assert "You feel poison coursing through your veins." in messages


@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_weapon_vampiric_life_drain(mock_apply_damage, mock_number_range, attacker, victim, mock_weapon):
    """Test WEAPON_VAMPIRIC life drain and healing."""
    mock_number_range.return_value = 4  # damage = number_range(1, level//5 + 1)

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    attacker.hit = 50  # Start with reduced HP to test healing
    attacker.max_hit = 100
    attacker.alignment = 100  # Positive alignment to test evil shift
    mock_weapon.weapon_flags = WEAPON_VAMPIRIC
    mock_weapon.level = 20  # level//5 + 1 = 5, so range(1,5)

    messages = process_weapon_special_attacks(attacker, victim)

    # Should call number_range(1, 20//5 + 1) = (1, 5)
    mock_number_range.assert_called_once_with(1, 5)

    # Should apply negative damage to victim
    mock_apply_damage.assert_called_once_with(attacker, victim, 4, DamageType.NEGATIVE, show=False)

    # Should heal attacker by half damage
    assert attacker.hit == 52  # 50 + 4//2

    # Should shift alignment toward evil
    assert attacker.alignment == 99  # 100 - 1

    # Should include vampiric message
    assert "You feel test weapon drawing your life away." in messages


@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_weapon_vampiric_healing_cap(mock_apply_damage, mock_number_range, attacker, victim, mock_weapon):
    """Test WEAPON_VAMPIRIC doesn't heal above max HP."""
    mock_number_range.return_value = 10

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    attacker.hit = 98  # Close to max
    attacker.max_hit = 100
    mock_weapon.weapon_flags = WEAPON_VAMPIRIC

    process_weapon_special_attacks(attacker, victim)

    # Should cap at max_hit
    assert attacker.hit == 100  # Capped at max_hit


@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_weapon_flaming_fire_damage(mock_apply_damage, mock_number_range, attacker, victim, mock_weapon):
    """Test WEAPON_FLAMING fire damage."""
    mock_number_range.return_value = 3  # damage = number_range(1, level//4 + 1)

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    mock_weapon.weapon_flags = WEAPON_FLAMING
    mock_weapon.level = 12  # level//4 + 1 = 4, so range(1,4)

    messages = process_weapon_special_attacks(attacker, victim)

    # Should call number_range(1, 12//4 + 1) = (1, 4)
    mock_number_range.assert_called_once_with(1, 4)

    # Should apply fire damage
    mock_apply_damage.assert_called_once_with(attacker, victim, 3, DamageType.FIRE, show=False)

    # Should include fire message
    assert "test weapon sears your flesh." in messages


@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_weapon_frost_cold_damage(mock_apply_damage, mock_number_range, attacker, victim, mock_weapon):
    """Test WEAPON_FROST cold damage."""
    mock_number_range.return_value = 5  # damage = number_range(1, level//6 + 2)

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    mock_weapon.weapon_flags = WEAPON_FROST
    mock_weapon.level = 18  # level//6 + 2 = 5, so range(1,5)

    messages = process_weapon_special_attacks(attacker, victim)

    # Should call number_range(1, 18//6 + 2) = (1, 5)
    mock_number_range.assert_called_once_with(1, 5)

    # Should apply cold damage
    mock_apply_damage.assert_called_once_with(attacker, victim, 5, DamageType.COLD, show=False)

    # Should include cold message
    assert "The cold touch surrounds you with ice." in messages


@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_weapon_shocking_lightning_damage(mock_apply_damage, mock_number_range, attacker, victim, mock_weapon):
    """Test WEAPON_SHOCKING lightning damage."""
    mock_number_range.return_value = 6  # damage = number_range(1, level//5 + 2)

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    mock_weapon.weapon_flags = WEAPON_SHOCKING
    mock_weapon.level = 20  # level//5 + 2 = 6, so range(1,6)

    messages = process_weapon_special_attacks(attacker, victim)

    # Should call number_range(1, 20//5 + 2) = (1, 6)
    mock_number_range.assert_called_once_with(1, 6)

    # Should apply lightning damage
    mock_apply_damage.assert_called_once_with(attacker, victim, 6, DamageType.LIGHTNING, show=False)

    # Should include lightning message
    assert "You are shocked by the weapon." in messages


@patch("mud.combat.engine.saves_spell")
@patch("mud.combat.engine.rng_mm.number_range")
@patch("mud.combat.engine.apply_damage")
def test_multiple_weapon_flags(mock_apply_damage, mock_number_range, mock_saves_spell, attacker, victim, mock_weapon):
    """Test weapon with multiple special flags."""
    mock_saves_spell.return_value = False  # Poison save fails
    mock_number_range.side_effect = [4, 3]  # vampiric=4, flaming=3

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim
    attacker.hit = 90
    attacker.max_hit = 100
    mock_weapon.weapon_flags = WEAPON_VAMPIRIC | WEAPON_POISON | WEAPON_FLAMING
    mock_weapon.level = 20

    messages = process_weapon_special_attacks(attacker, victim)

    # Should trigger all three effects
    assert "You feel poison coursing through your veins." in messages
    assert "You feel test weapon drawing your life away." in messages
    assert "test weapon sears your flesh." in messages

    # Should call apply_damage twice (vampiric + flaming)
    assert mock_apply_damage.call_count == 2

    # Should heal from vampiric
    assert attacker.hit == 92  # 90 + 4//2


def test_weapon_flags_via_extra_flags(attacker, victim, mock_weapon):
    """Test that weapon flags work via extra_flags attribute."""
    # Remove weapon_flags, use extra_flags instead
    delattr(mock_weapon, "weapon_flags")
    mock_weapon.extra_flags = WEAPON_POISON

    attacker.wielded_weapon = mock_weapon
    attacker.fighting = victim

    with patch("mud.combat.engine.saves_spell", return_value=False):
        messages = process_weapon_special_attacks(attacker, victim)

    assert "You feel poison coursing through your veins." in messages


@patch("mud.combat.engine.process_weapon_special_attacks")
def test_attack_round_integrates_weapon_specials(mock_weapon_specials, attacker, victim):
    """Test that attack_round calls weapon special attacks and combines messages."""
    # Mock successful hit and weapon special messages
    mock_weapon_specials.return_value = ["You are shocked!", "Fire burns!"]

    # Set up for successful hit
    attacker.hitroll = 50  # High hitroll for guaranteed hit
    victim.armor = [0, 0, 0, 0]  # No armor for easy hit

    result = attack_round(attacker, victim)

    # Should call weapon special attacks
    mock_weapon_specials.assert_called_once_with(attacker, victim)

    # Should combine messages (main message + weapon specials)
    assert "You are shocked!" in result
    assert "Fire burns!" in result
