"""
Integration tests for invisibility in combat commands.

Tests verify that combat targeting respects AFF_INVISIBLE and AFF_DETECT_INVIS.
"""

from __future__ import annotations

import pytest
from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class TestCombatInvisibility:
    """Test combat commands respect invisibility."""

    def test_cannot_kill_invisible_mob(self):
        """
        Test: Cannot target invisible mobs with KILL command.

        ROM Parity: Mirrors ROM src/fight.c - can_see() check before combat

        Given: Invisible mob in room
        When: Player tries to kill mob
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            attacker = create_test_character("Attacker", 1000)
            attacker.level = 10

            invisible_mob = Character(name="Orc", level=5, room=test_room)
            invisible_mob.is_npc = True
            invisible_mob.short_descr = "an orc"
            invisible_mob.long_descr = "An orc is here."
            invisible_mob.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_mob)
            character_registry.append(invisible_mob)

            result = process_command(attacker, "kill orc")
            assert "aren't here" in result.lower(), f"Should not see invisible mob: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_can_kill_invisible_with_detect_invis(self):
        """
        Test: Can target invisible mobs with DETECT_INVIS.

        ROM Parity: Mirrors ROM src/fight.c - can_see() with AFF_DETECT_INVIS

        Given: Invisible mob + attacker with detect_invis
        When: Player tries to kill mob
        Then: Combat begins successfully
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            attacker = create_test_character("Attacker", 1000)
            attacker.level = 10
            attacker.add_affect(AffectFlag.DETECT_INVIS)

            invisible_mob = Character(name="Orc", level=5, room=test_room)
            invisible_mob.is_npc = True
            invisible_mob.short_descr = "an orc"
            invisible_mob.long_descr = "An orc is here."
            invisible_mob.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_mob)
            character_registry.append(invisible_mob)

            result = process_command(attacker, "kill orc")
            assert "aren't here" not in result.lower(), f"Should see with detect_invis: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_cannot_backstab_invisible_victim(self):
        """
        Test: Cannot backstab invisible victims.

        ROM Parity: Mirrors ROM src/fight.c - backstab visibility check

        Given: Invisible victim in room
        When: Thief tries to backstab
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            thief = create_test_character("Thief", 1000)
            thief.level = 10
            thief.skills = {"backstab": 75}

            invisible_victim = Character(name="Victim", level=5, room=test_room)
            invisible_victim.is_npc = True
            invisible_victim.short_descr = "a victim"
            invisible_victim.long_descr = "A victim is here."
            invisible_victim.hit = 100
            invisible_victim.max_hit = 100
            invisible_victim.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_victim)
            character_registry.append(invisible_victim)

            result = process_command(thief, "backstab victim")
            assert "aren't here" in result.lower(), f"Should not see invisible victim: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_cannot_rescue_invisible_ally(self):
        """
        Test: Cannot rescue invisible allies.

        ROM Parity: Mirrors ROM src/fight.c - rescue visibility check

        Given: Invisible ally in room
        When: Player tries to rescue ally
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            rescuer = create_test_character("Rescuer", 1000)
            rescuer.level = 10

            invisible_ally = create_test_character("Ally", 1000)
            invisible_ally.level = 5
            invisible_ally.add_affect(AffectFlag.INVISIBLE)

            result = process_command(rescuer, "rescue ally")
            assert "aren't here" in result.lower(), f"Should not see invisible ally: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_can_rescue_invisible_with_detect_invis(self):
        """
        Test: Can rescue invisible allies with DETECT_INVIS.

        ROM Parity: Mirrors ROM src/fight.c - rescue with AFF_DETECT_INVIS

        Given: Invisible ally + rescuer with detect_invis
        When: Player tries to rescue ally
        Then: Rescue command processes (may fail for other reasons like "not fighting")
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            rescuer = create_test_character("Rescuer", 1000)
            rescuer.level = 10
            rescuer.add_affect(AffectFlag.DETECT_INVIS)

            invisible_ally = create_test_character("Ally", 1000)
            invisible_ally.level = 5
            invisible_ally.add_affect(AffectFlag.INVISIBLE)

            result = process_command(rescuer, "rescue ally")
            assert "aren't here" not in result.lower(), f"Should see with detect_invis: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()
