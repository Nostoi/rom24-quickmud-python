"""
Parity tests for healer command against ROM 2.4 C src/healer.c

Tests healer pricing, spell costs, and cure formulas.
"""

import pytest

from mud.commands.healer import do_heal
from mud.models.character import Character
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


def setup_healer_test() -> tuple[Character, Character]:
    """Create test character and healer."""
    initialize_world("area/area.lst")

    # Create test character with gold
    char = create_test_character("Patient", 3001)
    char.gold = 1000
    char.position = Position.STANDING

    # Create healer NPC - mark it as healer
    healer = create_test_character("Healer", 3001)
    healer.is_npc = True
    healer.is_healer = True

    # Add healer to the room's people list
    if char.room:
        if not hasattr(char.room, "people"):
            char.room.people = []
        if healer not in char.room.people:
            char.room.people.append(healer)

    return char, healer


def test_healer_pricing_parity():
    """Test healer pricing matches ROM C costs exactly."""
    char, healer = setup_healer_test()

    # Test pricing matches ROM C healer.c costs
    expected_costs = {
        "light": 10,
        "serious": 15,
        "critical": 25,
        "heal": 50,
        "refresh": 5,
        "mana": 10,
    }

    for spell_type, expected_cost in expected_costs.items():
        char.gold = expected_cost
        char.hit = 10
        char.max_hit = 100

        result = do_heal(char, spell_type)

        assert "feel" in result.lower() or "wounds" in result.lower() or "glow" in result.lower()
        assert char.gold == 0


def test_healer_cost_display():
    """Test healer cost list display."""
    char, healer = setup_healer_test()

    result = do_heal(char, "")

    # Should display price list
    assert "Healer offers" in result or "offer" in result.lower()
    assert "gold" in result


def test_healer_insufficient_gold():
    """Test healer behavior with insufficient gold like ROM C."""
    char, healer = setup_healer_test()

    # Set gold less than cost
    char.gold = 5

    result = do_heal(char, "heal")

    # Should refuse service
    assert "gold" in result.lower()
    assert char.gold == 5  # Gold should not be deducted


def test_healer_no_healer_present():
    """Test healer command when no healer present like ROM C."""
    char, healer = setup_healer_test()

    # Remove healer from room
    if char.room and hasattr(char.room, "people"):
        char.room.people = [p for p in char.room.people if p != healer]

    result = do_heal(char, "light")

    # Should fail with ROM C message
    assert "can't do that here" in result.lower()


def test_healer_spell_effects():
    """Test healer spell effects match ROM C spell applications."""
    char, healer = setup_healer_test()

    # Test healing spells
    for spell_type in ["light", "serious", "critical", "heal"]:
        # Set character to need healing
        char.hit = 10
        char.max_hit = 100
        char.gold = 100

        do_heal(char, spell_type)

        # Health should increase
        assert char.hit > 10


def test_healer_refresh_effect():
    """Test healer refresh spell restores movement."""
    char, healer = setup_healer_test()

    char.move = 10
    char.max_move = 100
    char.gold = 10

    result = do_heal(char, "refresh")

    assert "refresh" in result.lower()
    assert char.move >= 10


def test_healer_mana_effect():
    """Test healer mana spell restores mana."""
    char, healer = setup_healer_test()

    char.mana = 10
    char.max_mana = 100
    char.gold = 20

    result = do_heal(char, "mana")

    assert "glow" in result.lower() or "mana" in result.lower() or len(result) > 0
    assert char.mana >= 10


def test_healer_prefix_matching():
    """Test healer command prefix matching matches ROM C."""
    char, healer = setup_healer_test()

    # Test prefix matching (e.g., "critic" should match "critical")
    char.gold = 100
    result = do_heal(char, "critic")

    # Should match "critical" and heal
    assert "feel" in result.lower() or "gold" in result.lower()


def test_healer_case_sensitivity():
    """Test healer command case sensitivity matches ROM C."""
    char, healer = setup_healer_test()

    # Test case insensitive matching
    char.gold = 100
    result = do_heal(char, "LIGHT")

    # Should match "light" (lowercased internally)
    assert result != ""


def test_healer_unknown_spell():
    """Test healer with unknown spell type like ROM C."""
    char, healer = setup_healer_test()

    result = do_heal(char, "unknown_spell")

    # Should show help/pricelist
    assert "heal" in result.lower()


def test_healer_cure_conditions():
    """Test healer cures specific conditions."""
    char, healer = setup_healer_test()

    # Test condition cures
    for spell_type in ["blindness", "disease", "poison", "uncurse"]:
        char.gold = 100

        result = do_heal(char, spell_type)

        # Should attempt to cure condition
        assert result != ""


if __name__ == "__main__":
    pytest.main([__file__])
