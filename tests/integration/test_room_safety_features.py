"""Integration tests for ROM C handler.c char_to_room/char_from_room safety features.

Tests:
1. Temple fallback safety (handler.c:1545-1554) - char_to_room(NULL) protection
2. Furniture clearing (handler.c:1532) - ch->on = NULL when leaving room

Created: January 2, 2026
"""

from __future__ import annotations

import logging

import pytest

from mud.models.constants import ROOM_VNUM_TEMPLE
from mud.models.room import Room, room_registry
from mud.world import create_test_character


# Import char_to_room directly from the module
import mud.models.room as room_module


@pytest.fixture(autouse=True)
def _clear_registries():
    """Clear room registry before each test."""
    room_registry.clear()
    yield
    room_registry.clear()


@pytest.fixture
def temple_room():
    """Create the temple room (vnum 3001)."""
    room = Room(vnum=ROOM_VNUM_TEMPLE, name="The Temple Of Mota", description="The temple.")
    room_registry[ROOM_VNUM_TEMPLE] = room
    return room


@pytest.fixture
def test_room():
    """Create a test room."""
    room = Room(vnum=1000, name="Test Room", description="A test room")
    room_registry[1000] = room
    return room


@pytest.fixture
def character(test_room):
    """Create a test character."""
    char = create_test_character("TestChar", room_vnum=1000)
    char.is_npc = False
    test_room.add_character(char)
    return char


# =============================================================================
# Temple Fallback Safety Tests (ROM C handler.c:1545-1554)
# =============================================================================


def test_char_to_room_with_none_falls_back_to_temple(character, temple_room, caplog):
    """
    ROM C handler.c:1545-1554 - char_to_room(NULL) logs error and places char in temple.

    ROM C behavior:
        if (pRoomIndex == NULL)
        {
            bug ("Char_to_room: NULL.", 0);
            if ((room = get_room_index (ROOM_VNUM_TEMPLE)) != NULL)
                char_to_room (ch, room);
            return;
        }
    """
    # Character starts in test room
    assert character.room.vnum == 1000

    # Try to move character to NULL room
    with caplog.at_level(logging.ERROR):
        room_module.char_to_room(character, None)

    # Verify error was logged
    assert any("char_to_room: NULL room" in record.message for record in caplog.records)

    # Verify character was placed in temple instead
    assert character.room is not None
    assert character.room.vnum == ROOM_VNUM_TEMPLE
    assert character in temple_room.people


def test_char_to_room_with_none_does_nothing_if_temple_missing(character, caplog):
    """
    ROM C handler.c:1551 - If temple room doesn't exist, char_to_room(NULL) just returns.

    This is a safety edge case - if temple lookup fails, don't crash.
    """
    # Don't create temple room (room_registry is empty except test room)
    initial_room = character.room

    # Try to move character to NULL room (temple doesn't exist)
    with caplog.at_level(logging.ERROR):
        room_module.char_to_room(character, None)

    # Verify error was logged
    assert any("char_to_room: NULL room" in record.message for record in caplog.records)

    # Verify character stayed in original room (no crash)
    assert character.room is initial_room


def test_char_to_room_with_valid_room_works_normally(character, test_room):
    """char_to_room() with valid room should work normally (no fallback triggered)."""
    # Create a second room
    room2 = Room(vnum=2000, name="Room 2", description="Second room")
    room_registry[2000] = room2

    # Character starts in test_room
    assert character.room is test_room
    assert character in test_room.people

    # Move to room2 using char_to_room
    test_room.remove_character(character)
    room_module.char_to_room(character, room2)

    # Verify successful move
    assert character.room is room2
    assert character in room2.people
    assert character not in test_room.people


# =============================================================================
# Furniture Clearing Tests (ROM C handler.c:1532)
# =============================================================================


def test_remove_character_clears_furniture_reference(character, test_room):
    """
    ROM C handler.c:1532 - char_from_room() clears ch->on (furniture reference).

    ROM C behavior:
        ch->on = NULL;

    Prevents: Character sitting on furniture in wrong room after movement.
    """
    # Simulate character sitting on furniture (set to non-None value)
    character.on = "furniture"  # Just needs to be non-None for test

    # Verify furniture reference is set
    assert character.on is not None

    # Character leaves room
    test_room.remove_character(character)

    # Verify furniture reference was cleared
    assert character.on is None


def test_remove_character_handles_missing_on_attribute(character, test_room):
    """
    Furniture clearing should handle characters without 'on' attribute gracefully.

    This is defensive programming - not all characters may have furniture state.
    """
    # Character has no 'on' attribute
    if hasattr(character, "on"):
        delattr(character, "on")

    # Should not raise AttributeError
    test_room.remove_character(character)

    # Verify character was still removed successfully
    assert character not in test_room.people


def test_furniture_cleared_before_room_change(test_room):
    """
    Furniture should be cleared BEFORE character moves to new room.

    Scenario: Character sits on chair in Room A, walks to Room B.
    Expected: ch->on cleared when leaving Room A (not when entering Room B).
    """
    # Create two rooms
    room_a = test_room
    room_b = Room(vnum=2000, name="Room B", description="Second room")
    room_registry[2000] = room_b

    # Create character in room A
    char = create_test_character("Sitter", room_vnum=1000)
    char.on = "chair"  # Mock furniture reference

    # Character moves from A to B
    room_a.remove_character(char)  # Furniture should be cleared HERE

    # Verify furniture cleared when leaving room A
    assert char.on is None

    # Now add to room B
    room_b.add_character(char)

    # Furniture should still be None
    assert char.on is None


def test_multiple_characters_on_different_furniture(test_room):
    """
    Multiple characters sitting on different furniture should each clear independently.

    Ensures no shared state bugs.
    """
    # Create two characters with different furniture
    char1 = create_test_character("Char1", room_vnum=1000)
    char2 = create_test_character("Char2", room_vnum=1000)

    char1.on = "chair1"
    char2.on = "chair2"

    # Char1 leaves room
    test_room.remove_character(char1)

    # Verify char1 furniture cleared
    assert char1.on is None

    # Verify char2 furniture unaffected (still in room)
    assert char2.on == "chair2"

    # Char2 leaves room
    test_room.remove_character(char2)

    # Verify char2 furniture now cleared
    assert char2.on is None


# =============================================================================
# Combined Safety Tests
# =============================================================================


def test_temple_fallback_clears_furniture(temple_room, caplog):
    """
    When char_to_room(NULL) triggers temple fallback, furniture should still be cleared.

    Tests interaction between two safety features.
    """
    # Create character with furniture reference
    char = create_test_character("Sitter", room_vnum=ROOM_VNUM_TEMPLE)
    char.on = "furniture"

    # Character leaves temple (furniture cleared)
    temple_room.remove_character(char)
    assert char.on is None

    # Try to place character in NULL room (temple fallback)
    with caplog.at_level(logging.ERROR):
        room_module.char_to_room(char, None)

    # Verify character placed back in temple
    assert char.room is temple_room

    # Verify furniture is still cleared
    assert char.on is None
