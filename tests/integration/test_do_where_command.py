"""
Integration tests for do_where command.

Tests ROM C parity for where command (player location search).

ROM Reference: src/act_info.c lines 2407-2467
"""

from __future__ import annotations

import pytest

from mud.commands.info import do_where
from mud.models.character import Character
from mud.models.constants import AffectFlag, RoomFlag, Sector
from mud.models.room import Room
from mud.net.session import Session, SESSIONS
from mud.world.world_state import character_registry


@pytest.fixture
def setup_area_rooms():
    """Create a simple area with multiple rooms for where testing."""
    from mud.models.area import Area

    area1 = Area(vnum=1)
    area1.name = "Midgaard"

    area2 = Area(vnum=2)
    area2.name = "Other Area"

    rooms = []

    temple = Room(vnum=3001)
    temple.name = "Midgaard Temple"
    temple.description = "You are in the temple."
    temple.sector_type = int(Sector.INSIDE)
    temple.room_flags = 0
    temple.light = 1
    temple.area = area1
    rooms.append(temple)

    square = Room(vnum=3002)
    square.name = "Temple Square"
    square.description = "A busy square."
    square.sector_type = int(Sector.CITY)
    square.room_flags = 0
    square.light = 1
    square.area = area1
    rooms.append(square)

    private = Room(vnum=3003)
    private.name = "Private Room"
    private.description = "A private room."
    private.sector_type = int(Sector.INSIDE)
    private.room_flags = int(RoomFlag.ROOM_PRIVATE)
    private.light = 1
    private.area = area1
    rooms.append(private)

    other_area_room = Room(vnum=4001)
    other_area_room.name = "Other Area"
    other_area_room.description = "Different area."
    other_area_room.sector_type = int(Sector.FIELD)
    other_area_room.room_flags = 0
    other_area_room.light = 1
    other_area_room.area = area2
    rooms.append(other_area_room)

    return {"temple": temple, "square": square, "private": private, "other_area": other_area_room, "all": rooms}


@pytest.fixture
def clear_sessions():
    """Clear SESSIONS before and after test."""
    SESSIONS.clear()
    yield
    SESSIONS.clear()


@pytest.fixture
def test_character():
    """Create a test character for where testing."""
    char = Character()
    char.name = "WhereTest"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    return char


@pytest.fixture
def immortal_character():
    """Create an immortal character for testing private room visibility."""
    char = Character()
    char.name = "TestImmortal"
    char.level = 60
    char.trust = 60
    char.is_npc = False
    return char


class TestDoWhereMode1:
    """Test mode 1: where (no argument) - list all players in area."""

    def test_where_lists_players_in_same_area(self, clear_sessions, test_character, setup_area_rooms):
        """Test where lists all visible players in same area."""
        test_character.room = setup_area_rooms["temple"]

        # Create session for test_character
        sess1 = Session(name="WhereTest", character=test_character, reader=None, connection=None)
        SESSIONS["WhereTest"] = sess1

        player2 = Character()
        player2.name = "OtherPlayer"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["square"]

        # Create session for player2
        sess2 = Session(name="OtherPlayer", character=player2, reader=None, connection=None)
        SESSIONS["OtherPlayer"] = sess2

        result = do_where(test_character, "")

        assert "OtherPlayer" in result
        assert "Temple Square" in result

    def test_where_excludes_players_in_other_area(self, test_character, setup_area_rooms):
        """Test where does not show players in different areas."""
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "FarPlayer"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["other_area"]
        character_registry.append(player2)

        result = do_where(test_character, "")

        assert "FarPlayer" not in result

        character_registry.remove(player2)

    def test_where_excludes_private_rooms_for_mortals(self, test_character, setup_area_rooms):
        """Test mortals cannot see players in private rooms."""
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "PrivatePlayer"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["private"]
        character_registry.append(player2)

        result = do_where(test_character, "")

        assert "PrivatePlayer" not in result

        character_registry.remove(player2)

    def test_where_shows_private_rooms_for_immortals(self, clear_sessions, immortal_character, setup_area_rooms):
        """Test immortals can see players in private rooms."""
        immortal_character.room = setup_area_rooms["temple"]

        sess1 = Session(name="TestImmortal", character=immortal_character, reader=None, connection=None)
        SESSIONS["TestImmortal"] = sess1

        player2 = Character()
        player2.name = "PrivatePlayer"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["private"]

        sess2 = Session(name="PrivatePlayer", character=player2, reader=None, connection=None)
        SESSIONS["PrivatePlayer"] = sess2

        result = do_where(immortal_character, "")

        assert "PrivatePlayer" in result
        assert "Private Room" in result

    def test_where_excludes_invisible_players(self, test_character, setup_area_rooms):
        """Test where does not show invisible players to mortals."""
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "InvisPlayer"
        player2.is_npc = False
        player2.level = 1
        player2.affected_by = int(AffectFlag.INVISIBLE)
        player2.room = setup_area_rooms["square"]
        character_registry.append(player2)

        result = do_where(test_character, "")

        assert "InvisPlayer" not in result

        character_registry.remove(player2)

    def test_where_shows_self(self, clear_sessions, test_character, setup_area_rooms):
        """Test where always shows the character themselves."""
        test_character.room = setup_area_rooms["temple"]

        sess = Session(name="WhereTest", character=test_character, reader=None, connection=None)
        SESSIONS["WhereTest"] = sess

        result = do_where(test_character, "")

        assert "WhereTest" in result
        assert "Midgaard Temple" in result


class TestDoWhereMode2:
    """Test mode 2: where <target> - search for specific character/mob."""

    def test_where_target_finds_player_in_area(self, test_character, setup_area_rooms):
        """Test where <target> finds specific player in area."""
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "Hassan"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["square"]
        character_registry.append(player2)

        result = do_where(test_character, "hassan")

        assert "Hassan" in result
        assert "Temple Square" in result

        character_registry.remove(player2)

    def test_where_target_finds_mob_in_area(self, test_character, setup_area_rooms):
        """Test where <target> finds specific mob in area."""
        test_character.room = setup_area_rooms["temple"]

        mob = Character()
        mob.name = "cityguard"
        mob.is_npc = True
        mob.level = 10
        mob.room = setup_area_rooms["square"]
        character_registry.append(mob)

        result = do_where(test_character, "cityguard")

        assert "cityguard" in result or "guard" in result.lower()
        assert "Temple Square" in result

        character_registry.remove(mob)

    def test_where_target_not_found(self, test_character, setup_area_rooms):
        """Test where <target> when target does not exist."""
        test_character.room = setup_area_rooms["temple"]

        result = do_where(test_character, "nonexistent")

        assert "didn't find" in result.lower() or "not found" in result.lower()

    def test_where_target_respects_visibility(self, test_character, setup_area_rooms):
        """Test where <target> respects can_see checks."""
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "InvisPlayer"
        player2.is_npc = False
        player2.level = 1
        player2.affected_by = int(AffectFlag.INVISIBLE)
        player2.room = setup_area_rooms["square"]
        character_registry.append(player2)

        result = do_where(test_character, "invisplayer")

        assert "InvisPlayer" not in result

        character_registry.remove(player2)

    def test_where_target_searches_only_same_area_not_world(self, test_character, setup_area_rooms):
        """Test where <target> only searches same area (ROM C line 2447).

        NOTE: This test documents that ROM C Mode 2 does NOT search the entire world.
        ROM C line 2447: && victim->in_room->area == ch->in_room->area

        Mode 1 (no args) searches same area.
        Mode 2 (with args) also searches same area, NOT entire world.
        """
        test_character.room = setup_area_rooms["temple"]

        player2 = Character()
        player2.name = "FarPlayer"
        player2.is_npc = False
        player2.level = 1
        player2.room = setup_area_rooms["other_area"]
        character_registry.append(player2)

        result = do_where(test_character, "farplayer")

        # Should NOT find player in different area (correct ROM C behavior)
        assert "FarPlayer" not in result
        assert "didn't find" in result.lower()

        character_registry.remove(player2)


class TestDoWhereEdgeCases:
    """Test edge cases and error conditions."""

    def test_where_no_room_error(self):
        """Test error handling when character has no room."""
        char = Character()
        char.name = "NoRoom"

        result = do_where(char, "")

        assert result
        assert "nowhere" in result.lower() or "error" in result.lower()

    def test_where_no_players_in_area(self, clear_sessions, test_character, setup_area_rooms):
        """Test where when only character is self."""
        test_character.room = setup_area_rooms["temple"]

        sess = Session(name="WhereTest", character=test_character, reader=None, connection=None)
        SESSIONS["WhereTest"] = sess

        result = do_where(test_character, "")

        assert "WhereTest" in result
