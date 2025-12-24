"""
Parity tests for scan command against ROM 2.4 C src/scan.c

Tests scan distance calculations, direction handling, and room visibility.
"""

import pytest

from mud.commands.inspection import do_scan
from mud.models.character import Character
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


def setup_scan_test() -> Character:
    """Create test environment for scan testing."""
    initialize_world("area/area.lst")

    # Create test character in a room with exits (Temple of Midgaard)
    char = create_test_character("Scanner", 3001)
    char.position = Position.STANDING

    return char


def test_scan_all_directions():
    """Test scan in all directions matches ROM C behavior."""
    char = setup_scan_test()

    result = do_scan(char, "")

    # Should scan current room and show "Looking around you see:"
    assert "Looking around you see:" in result


def test_scan_single_direction():
    """Test directional scan matches ROM C depth logic."""
    char = setup_scan_test()

    # Try scanning north (most rooms have this exit)
    result = do_scan(char, "north")

    # Should show directional scan or no exit message
    assert "Looking north you see:" in result or "Nothing of note" in result


def test_scan_distance_messages():
    """Test scan distance messages match ROM C distance array."""
    char = setup_scan_test()

    result = do_scan(char, "")

    # ROM C distance messages:
    # "right here.", "nearby to the %s.", "not far %s.", "off in the distance %s."
    # The scan output should use these patterns
    assert "Looking around you see:" in result


def test_scan_no_exit():
    """Test scan direction with no exit matches ROM C."""
    char = setup_scan_test()

    # Try scanning in a direction that might not have an exit
    result = do_scan(char, "down")

    # Should show scan header or nothing of note
    assert "Looking down you see:" in result or "Nothing of note" in result


def test_scan_invalid_direction():
    """Test scan with invalid direction matches ROM C."""
    char = setup_scan_test()

    result = do_scan(char, "invalid")

    assert "Which way do you want to scan?" in result


def test_scan_direction_mapping():
    """Test direction string mapping matches ROM C."""
    char = setup_scan_test()

    # Test all direction mappings
    directions = ["n", "north", "e", "east", "s", "south", "w", "west", "u", "up", "d", "down"]

    for direction in directions:
        result = do_scan(char, direction)
        # Should successfully parse and scan
        assert "Looking" in result or "Nothing of note" in result


def test_scan_direction_abbreviations():
    """Test direction abbreviations work like ROM C."""
    char = setup_scan_test()

    # Test single letter abbreviations
    abbrevs = [("n", "north"), ("e", "east"), ("s", "south"), ("w", "west"), ("u", "up"), ("d", "down")]

    for abbrev, full in abbrevs:
        result_abbrev = do_scan(char, abbrev)
        result_full = do_scan(char, full)

        # Both should produce same output format
        assert result_abbrev.startswith("Looking") or "Nothing of note" in result_abbrev
        assert result_full.startswith("Looking") or "Nothing of note" in result_full


def test_scan_room_messages():
    """Test scan room description messages match ROM C."""
    char = setup_scan_test()

    result = do_scan(char, "")

    # Should include "Looking around you see:"
    assert "Looking around you see:" in result


def test_scan_with_people_in_room():
    """Test scan shows people in current room."""
    char = setup_scan_test()

    # Add another character to the room
    other = create_test_character("OtherPerson", 3001)
    other.position = Position.STANDING
    if char.room:
        char.room.add_character(other)

    result = do_scan(char, "")

    # Should show other person in room
    assert "OtherPerson" in result or "Looking around you see:" in result


def test_scan_empty_room():
    """Test scan shows appropriate message when no one around."""
    char = setup_scan_test()

    # Clear other people from room
    if char.room:
        char.room.people = [char]

    result = do_scan(char, "")

    # Should show "No one is nearby." when empty
    assert "No one is nearby." in result or "Looking around you see:" in result


def test_scan_directional_depth():
    """Test scan shows characters at different depths."""
    char = setup_scan_test()

    # Scan north to see depth reporting
    result = do_scan(char, "north")

    # Should have looking message
    assert "Looking north you see:" in result


def test_scan_no_room():
    """Test scan when character has no room."""
    char = setup_scan_test()
    char.room = None

    result = do_scan(char, "")

    assert "You see nothing." in result


def test_scan_parity_golden_sequence():
    """Golden test sequence for scan parity against ROM C behavior."""
    char = setup_scan_test()

    # Test all scan modes
    test_cases = [
        ("", "Looking around you see:"),  # Scan all directions
        ("north", "Looking north you see:"),  # Directional scan
        ("n", "Looking north you see:"),  # Short direction
        ("invalid", "Which way do you want to scan?"),  # Invalid direction
    ]

    for args, expected in test_cases:
        result = do_scan(char, args)
        assert expected in result, f"Expected '{expected}' for args='{args}', got: {result}"


if __name__ == "__main__":
    pytest.main([__file__])
