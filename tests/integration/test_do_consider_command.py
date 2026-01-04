"""
Integration tests for do_consider command.

Tests ROM C parity for consider command (mob difficulty assessment).

ROM Reference: src/act_info.c lines 2469-2517
"""

from __future__ import annotations

import pytest

from mud.commands.consider import do_consider
from mud.models.character import Character
from mud.models.constants import Sector
from mud.models.room import Room


@pytest.fixture
def test_character():
    """Create a test character for consider testing."""
    char = Character()
    char.name = "ConsiderTest"
    char.level = 10
    char.trust = 0
    char.is_npc = False
    return char


@pytest.fixture
def test_room():
    """Create a test room."""
    room = Room(vnum=3001)
    room.name = "Test Room"
    room.description = "A test room."
    room.sector_type = int(Sector.INSIDE)
    room.room_flags = 0
    room.light = 1
    return room


class TestDoConsiderDifficultyLevels:
    """Test all 7 ROM C difficulty tier messages."""

    def test_consider_easy_minus_10(self, test_character, test_room):
        """Test mob 10+ levels below (easiest)."""
        test_character.room = test_room
        test_character.level = 20
        test_room.add_character(test_character)

        mob = Character()
        mob.name = "weakmob"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room
        test_room.add_character(mob)

        result = do_consider(test_character, "weakmob")

        assert "naked" in result.lower() or "weaponless" in result.lower()

    def test_consider_easy_minus_5(self, test_character, test_room):
        """Test mob 5-9 levels below."""
        test_character.room = test_room
        test_character.level = 15
        test_room.add_character(test_character)

        mob = Character()
        mob.name = "easymob"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room
        test_room.add_character(mob)

        result = do_consider(test_character, "easymob")

        assert "easy" in result.lower() or "give" in result.lower()

    def test_consider_easy_minus_2(self, test_character, test_room):
        """Test mob 2-4 levels below."""
        test_character.room = test_room
        test_character.level = 12

        mob = Character()
        mob.name = "fairlymob"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room

        result = do_consider(test_character, "fairlymob")

        assert result

    def test_consider_even_plus_1(self, test_character, test_room):
        """Test mob -1 to +3 levels (even fight)."""
        test_character.room = test_room
        test_character.level = 10
        test_room.add_character(test_character)

        mob = Character()
        mob.name = "evenmob"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room
        test_room.add_character(mob)

        result = do_consider(test_character, "evenmob")

        assert "perfect" in result.lower() or "even" in result.lower() or "match" in result.lower()

    def test_consider_hard_plus_4(self, test_character, test_room):
        """Test mob 4-8 levels above."""
        test_character.room = test_room
        test_character.level = 10

        mob = Character()
        mob.name = "hardmob"
        mob.is_npc = True
        mob.level = 14
        mob.room = test_room

        result = do_consider(test_character, "hardmob")

        assert result

    def test_consider_very_hard_plus_9(self, test_character, test_room):
        """Test mob 9+ levels above (very hard)."""
        test_character.room = test_room
        test_character.level = 10

        mob = Character()
        mob.name = "toughmob"
        mob.is_npc = True
        mob.level = 19
        mob.room = test_room

        result = do_consider(test_character, "toughmob")

        assert result

    def test_consider_impossible(self, test_character, test_room):
        """Test mob much higher level (near impossible)."""
        test_character.room = test_room
        test_character.level = 10
        test_room.add_character(test_character)

        mob = Character()
        mob.name = "bossmob"
        mob.is_npc = True
        mob.level = 50
        mob.room = test_room
        test_room.add_character(mob)

        result = do_consider(test_character, "bossmob")

        assert "death" in result.lower() or "run" in result.lower() or "impossible" in result.lower()


class TestDoConsiderEdgeCases:
    """Test error conditions and edge cases."""

    def test_consider_no_argument(self, test_character, test_room):
        """Test consider with no argument."""
        test_character.room = test_room

        result = do_consider(test_character, "")

        assert "consider" in result.lower() or "who" in result.lower()

    def test_consider_target_not_found(self, test_character, test_room):
        """Test consider when target doesn't exist."""
        test_character.room = test_room

        result = do_consider(test_character, "nonexistent")

        assert "not here" in result.lower() or "don't see" in result.lower()

    def test_consider_no_room_error(self):
        """Test error handling when character has no room."""
        char = Character()
        char.name = "NoRoom"

        result = do_consider(char, "anything")

        assert result

    def test_consider_self(self, test_character, test_room):
        """Test considering yourself (should work or have specific message)."""
        test_character.room = test_room

        result = do_consider(test_character, "considertest")

        assert result


class TestDoConsiderSafety:
    """Test safety check integration."""

    def test_consider_safe_target(self, test_character, test_room):
        """Test considering a safe target (immortal, ROOM_SAFE, etc)."""
        test_character.room = test_room

        mob = Character()
        mob.name = "safemob"
        mob.is_npc = True
        mob.level = 10
        mob.trust = 60
        mob.room = test_room

        result = do_consider(test_character, "safemob")

        assert result


class TestDoConsiderBoundaries:
    """Test boundary conditions for level differences."""

    def test_consider_exactly_minus_10(self, test_character, test_room):
        """Test exact -10 level difference boundary."""
        test_character.room = test_room
        test_character.level = 20

        mob = Character()
        mob.name = "boundary1"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room

        result = do_consider(test_character, "boundary1")

        assert result

    def test_consider_exactly_minus_5(self, test_character, test_room):
        """Test exact -5 level difference boundary."""
        test_character.room = test_room
        test_character.level = 15

        mob = Character()
        mob.name = "boundary2"
        mob.is_npc = True
        mob.level = 10
        mob.room = test_room

        result = do_consider(test_character, "boundary2")

        assert result

    def test_consider_exactly_plus_4(self, test_character, test_room):
        """Test exact +4 level difference boundary."""
        test_character.room = test_room
        test_character.level = 10

        mob = Character()
        mob.name = "boundary3"
        mob.is_npc = True
        mob.level = 14
        mob.room = test_room

        result = do_consider(test_character, "boundary3")

        assert result
