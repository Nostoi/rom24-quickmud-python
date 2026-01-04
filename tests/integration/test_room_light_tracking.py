"""Integration test for room light tracking when characters with lit light sources enter/leave.

Tests ROM C handler.c:1504-1507, 1571-1573 compliance.
"""

from __future__ import annotations

import pytest

from mud.models.constants import ItemType, WearLocation
from mud.models.room import Room
from mud.world import create_test_character


@pytest.fixture
def room():
    """Create a test room."""
    return Room(vnum=1000, name="Test Room", description="A test room", light=0)


@pytest.fixture
def character():
    """Create a test character."""
    char = create_test_character("TestChar", room_vnum=1000)
    char.is_npc = False
    char.equipment = {}
    return char


@pytest.fixture
def lit_torch(object_factory):
    """Create a lit torch object (ITEM_LIGHT with value[2] > 0)."""
    return object_factory(
        {
            "vnum": 100,
            "name": "a torch",
            "short_descr": "a burning torch",
            "description": "A torch burns brightly here.",
            "item_type": int(ItemType.LIGHT),
            "value": [0, 0, 100, 0, 0],  # value[2] = 100 (light duration > 0 = lit)
        }
    )


@pytest.fixture
def unlit_torch(object_factory):
    """Create an unlit torch object (ITEM_LIGHT with value[2] = 0)."""
    return object_factory(
        {
            "vnum": 101,
            "name": "a torch",
            "short_descr": "a burnt-out torch",
            "description": "A burnt-out torch lies here.",
            "item_type": int(ItemType.LIGHT),
            "value": [0, 0, 0, 0, 0],  # value[2] = 0 (no light duration = unlit)
        }
    )


@pytest.fixture
def non_light_item(object_factory):
    """Create a non-light item (e.g., a sword)."""
    return object_factory(
        {
            "vnum": 102,
            "name": "a sword",
            "short_descr": "a sharp sword",
            "description": "A sharp sword lies here.",
            "item_type": int(ItemType.WEAPON),
            "value": [0, 0, 0, 0, 0],
        }
    )


def test_room_light_increments_when_character_with_lit_torch_enters(room, character, lit_torch):
    """ROM C handler.c:1571-1573 - Room light increments when character enters with lit light source."""
    # Equip lit torch in LIGHT slot
    character.equipment[str(int(WearLocation.LIGHT))] = lit_torch

    # Verify room starts dark
    assert room.light == 0

    # Character enters room
    room.add_character(character)

    # Verify room light increased
    assert room.light == 1


def test_room_light_decrements_when_character_with_lit_torch_leaves(room, character, lit_torch):
    """ROM C handler.c:1504-1507 - Room light decrements when character leaves with lit light source."""
    # Equip lit torch in LIGHT slot
    character.equipment[str(int(WearLocation.LIGHT))] = lit_torch

    # Character enters room (light should increase to 1)
    room.add_character(character)
    assert room.light == 1

    # Character leaves room
    room.remove_character(character)

    # Verify room light decreased back to 0
    assert room.light == 0


def test_room_light_not_affected_by_unlit_torch(room, character, unlit_torch):
    """Room light should NOT change when character has unlit torch (value[2] = 0)."""
    # Equip unlit torch in LIGHT slot
    character.equipment[str(int(WearLocation.LIGHT))] = unlit_torch

    # Character enters room
    room.add_character(character)

    # Verify room light unchanged (unlit torch has no effect)
    assert room.light == 0

    # Character leaves room
    room.remove_character(character)

    # Verify room light still unchanged
    assert room.light == 0


def test_room_light_not_affected_by_non_light_item(room, character, non_light_item):
    """Room light should NOT change when character has non-light item equipped."""
    # Equip sword in LIGHT slot (wrong item type)
    character.equipment[str(int(WearLocation.LIGHT))] = non_light_item

    # Character enters room
    room.add_character(character)

    # Verify room light unchanged
    assert room.light == 0

    # Character leaves room
    room.remove_character(character)

    # Verify room light still unchanged
    assert room.light == 0


def test_room_light_not_affected_by_character_without_equipment(room, character):
    """Room light should NOT change when character has no equipment."""
    # Character enters room with empty equipment dict
    room.add_character(character)

    # Verify room light unchanged
    assert room.light == 0

    # Character leaves room
    room.remove_character(character)

    # Verify room light still unchanged
    assert room.light == 0


def test_room_light_tracks_multiple_characters_with_lit_torches(room, lit_torch):
    """Room light should increment for each character with a lit torch."""
    # Create three characters with lit torches
    char1 = create_test_character("Char1", room_vnum=1000)
    char1.is_npc = False
    char1.equipment = {str(int(WearLocation.LIGHT)): lit_torch}

    char2 = create_test_character("Char2", room_vnum=1000)
    char2.is_npc = False
    char2.equipment = {str(int(WearLocation.LIGHT)): lit_torch}

    char3 = create_test_character("Char3", room_vnum=1000)
    char3.is_npc = False
    char3.equipment = {str(int(WearLocation.LIGHT)): lit_torch}

    # All enter room
    room.add_character(char1)
    assert room.light == 1

    room.add_character(char2)
    assert room.light == 2

    room.add_character(char3)
    assert room.light == 3

    # All leave room
    room.remove_character(char1)
    assert room.light == 2

    room.remove_character(char2)
    assert room.light == 1

    room.remove_character(char3)
    assert room.light == 0


def test_room_light_never_goes_negative(room, character):
    """ROM C handler.c:1507 - Room light should never go below 0."""
    # Verify room starts dark
    assert room.light == 0

    # Character with no light source leaves (should not go negative)
    character.equipment = {}
    room.remove_character(character)

    # Verify room light stayed at 0 (not negative)
    assert room.light == 0


def test_room_light_correct_when_character_re_enters(room, character, lit_torch):
    """Test light tracking when same character enters/leaves multiple times."""
    character.equipment[str(int(WearLocation.LIGHT))] = lit_torch

    # First entry
    room.add_character(character)
    assert room.light == 1

    # First exit
    room.remove_character(character)
    assert room.light == 0

    # Second entry
    room.add_character(character)
    assert room.light == 1

    # Second exit
    room.remove_character(character)
    assert room.light == 0


def test_room_light_with_mixed_characters(room, lit_torch, unlit_torch):
    """Test light tracking with mix of lit/unlit/no light characters."""
    # Character 1: lit torch
    char1 = create_test_character("Char1", room_vnum=1000)
    char1.is_npc = False
    char1.equipment = {str(int(WearLocation.LIGHT)): lit_torch}

    # Character 2: unlit torch
    char2 = create_test_character("Char2", room_vnum=1000)
    char2.is_npc = False
    char2.equipment = {str(int(WearLocation.LIGHT)): unlit_torch}

    # Character 3: no equipment
    char3 = create_test_character("Char3", room_vnum=1000)
    char3.is_npc = False
    char3.equipment = {}

    # All enter room (only char1 should affect light)
    room.add_character(char1)
    assert room.light == 1

    room.add_character(char2)
    assert room.light == 1  # Unchanged (unlit torch)

    room.add_character(char3)
    assert room.light == 1  # Unchanged (no equipment)

    # All leave room
    room.remove_character(char3)
    assert room.light == 1  # Unchanged (no equipment)

    room.remove_character(char2)
    assert room.light == 1  # Unchanged (unlit torch)

    room.remove_character(char1)
    assert room.light == 0  # Decreased (lit torch removed)
