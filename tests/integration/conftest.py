"""
Integration test framework for player workflows.

These tests simulate complete player scenarios to ensure end-to-end
functionality beyond unit testing of individual components.
"""
from __future__ import annotations

import pytest
from mud.models.character import Character
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def test_room():
    """Create a basic test room"""
    room = Room(
        vnum=1000,
        name="Test Room",
        description="A room for testing player interactions.",
        room_flags=0,
        sector_type=0
    )
    room.people = []  # Initialize people list
    room.contents = []  # Initialize contents list
    room_registry[1000] = room
    yield room
    room_registry.pop(1000, None)


@pytest.fixture  
def test_player(test_room):
    """Create a test player character"""
    char = Character(
        name="TestPlayer",
        level=5,
        room=test_room,
        gold=1000,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def test_mob(test_room):
    """Create a test mob in the room"""
    mob = Character(
        name="test mob",
        short_descr="a test mob",
        long_descr="A test mob is standing here.",
        level=3,
        room=test_room,
        is_npc=True,
        hit=50,
        max_hit=50,
    )
    test_room.people.append(mob)
    
    yield mob
    
    if mob in test_room.people:
        test_room.people.remove(mob)


def create_shopkeeper(room: Room, name: str = "shopkeeper") -> Character:
    """Helper to create a shopkeeper mob"""
    mob = Character(
        name=name,
        short_descr=f"a {name}",
        long_descr=f"A {name} is standing here.",
        level=10,
        room=room,
        is_npc=True,
    )
    room.people.append(mob)
    return mob
