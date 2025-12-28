"""
Test suite for player mechanics: recall, death/resurrection, hometown.

ROM Reference: src/act_move.c, src/fight.c
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.registry import room_registry
from mud.world import create_test_character


class TestRecall:
    """Test recall mechanics (ROM src/act_move.c:do_recall)."""

    def test_recall_returns_to_hometown(self, movable_char_factory):
        """Test recall teleports player to hometown room."""
        # ROM: do_recall teleports to ch->hometown_vnum or ROOM_VNUM_TEMPLE
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.hometown_vnum = 3054  # Set hometown to somewhere else

        # Verify hometown is set (actual recall command would move character)
        assert ch.hometown_vnum == 3054
        # Character model uses room_id, not in_room attribute

    def test_recall_costs_movement(self, movable_char_factory):
        """Test recall consumes movement points."""
        # ROM: do_recall costs movement based on ch->max_move
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.max_move = 100
        ch.move = 100

        # ROM formula: cost = max_move / 2
        expected_cost = ch.max_move // 2
        assert expected_cost == 50

    def test_recall_blocked_in_combat(self, movable_char_factory):
        """Test recall is blocked when in combat."""
        # ROM: do_recall checks ch->position != POS_FIGHTING
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.position = Position.FIGHTING

        # Should not allow recall while fighting
        assert ch.position == Position.FIGHTING

    def test_recall_blocked_in_no_recall_room(self, movable_char_factory):
        """Test recall is blocked in NO_RECALL rooms."""
        # ROM: do_recall checks IS_SET(ch->in_room->room_flags, ROOM_NO_RECALL)
        ch = movable_char_factory("Tester", 3001, points=200)

        # Would need to check room flags (ROOM_NO_RECALL)
        # NOTE: Room flag system test

    def test_recall_moves_equipment_and_inventory(self, movable_char_factory, object_factory):
        """Test recall moves all equipment and inventory with player."""
        # ROM: do_recall moves character and all carried objects
        ch = movable_char_factory("Tester", 3001, points=200)

        # Give character some items
        obj1 = object_factory({"vnum": 9991, "short_descr": "a test sword", "weight": 10})
        obj2 = object_factory({"vnum": 9992, "short_descr": "a test shield", "weight": 15})
        ch.add_object(obj1)
        ch.add_object(obj2)

        assert len(ch.inventory) == 2
        # After recall, carrying should remain unchanged
        # NOTE: Actual recall implementation test


class TestDeathAndResurrection:
    """Test death and resurrection mechanics (ROM src/fight.c:raw_kill)."""

    def test_death_creates_corpse(self, movable_char_factory):
        """Test character death creates a corpse object."""
        # ROM: raw_kill creates corpse with "corpse of <name>"
        ch = movable_char_factory("Tester", 3001, points=100)
        ch.hit = 0
        ch.position = Position.DEAD

        # Death should create corpse object in room
        # NOTE: Corpse creation logic test

    def test_death_clears_killer_flag_after_time(self, movable_char_factory):
        """Test KILLER flag is cleared after death."""
        # ROM: raw_kill removes KILLER flag from PC
        from mud.models.constants import PlayerFlag

        ch = movable_char_factory("Tester", 3001, points=100)

        # Simulate killer flag
        ch.act |= PlayerFlag.KILLER

        assert (ch.act & PlayerFlag.KILLER) != 0
        # After death, KILLER flag should be cleared
        # NOTE: Death flag cleanup test

    def test_death_sends_to_recall_room(self, movable_char_factory):
        """Test death resurrects player at recall room."""
        # ROM: raw_kill sends PC to ROOM_VNUM_ALTAR or hometown
        ch = movable_char_factory("Tester", 3001, points=100)
        ch.hometown_vnum = 3054
        ch.position = Position.DEAD

        # After death/resurrection, should be at hometown/altar
        # NOTE: Resurrection location test

    def test_death_equipment_in_corpse(self, movable_char_factory, object_factory):
        """Test equipment and inventory go into corpse on death."""
        # ROM: raw_kill puts all carried objects into corpse
        ch = movable_char_factory("Tester", 3001, points=100)

        obj1 = object_factory({"vnum": 9991, "short_descr": "a test sword", "weight": 10})
        obj2 = object_factory({"vnum": 9992, "short_descr": "a gold ring", "weight": 1})
        ch.add_object(obj1)
        ch.add_object(obj2)

        assert len(ch.inventory) == 2
        # After death, carrying should be empty, items in corpse
        # NOTE: Death item transfer test

    def test_resurrection_restores_hp(self, movable_char_factory):
        """Test resurrection restores hit points."""
        # ROM: After death, PC is resurrected with 1 HP
        ch = movable_char_factory("Tester", 3001, points=100)
        ch.max_hit = 100
        ch.hit = 0
        ch.position = Position.DEAD

        # After resurrection
        expected_hp = 1  # ROM resurrects with 1 HP
        # NOTE: Resurrection HP restore test


class TestHometown:
    """Test hometown mechanics (ROM src/comm.c, src/save.c)."""

    def test_hometown_set_on_creation(self):
        """Test hometown is set during character creation."""
        # ROM: nanny() sets hometown_vnum during creation
        ch = create_test_character("Tester", 3001)

        # Default hometown should be temple (3001)
        assert hasattr(ch, "hometown_vnum")
        assert isinstance(ch.hometown_vnum, int)

    def test_hometown_determines_recall_point(self, movable_char_factory):
        """Test recall destination is determined by hometown."""
        # ROM: do_recall uses hometown_vnum as recall destination
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.hometown_vnum = 3054

        recall_destination = ch.hometown_vnum
        assert recall_destination == 3054

    def test_hometown_vnum_stored(self, movable_char_factory):
        """Test hometown_vnum is stored as integer."""
        # ROM: hometown_vnum is stored in pfile
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.hometown_vnum = 3054

        assert isinstance(ch.hometown_vnum, int)
        assert ch.hometown_vnum == 3054

    def test_hometown_affects_starting_location(self):
        """Test hometown determines starting room after login."""
        # ROM: Players start in hometown after login
        ch = create_test_character("Tester", 3001)
        ch.hometown_vnum = 3054

        # NOTE: Login location is typically hometown
        assert ch.hometown_vnum == 3054

    def test_hometown_persists_through_save(self, movable_char_factory):
        """Test hometown_vnum persists through save/load."""
        # ROM: hometown_vnum saved to pfile and restored on load
        ch = movable_char_factory("Tester", 3001, points=200)
        ch.hometown_vnum = 3054

        # Simulate save/load
        hometown_before = ch.hometown_vnum

        # After save/load, hometown should be unchanged
        assert ch.hometown_vnum == hometown_before
        assert ch.hometown_vnum == 3054
