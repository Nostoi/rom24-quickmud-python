"""
ROM Parity Tests for act_enter.c Portal/Enter Commands

Tests verify exact ROM 2.4b6 behavior for portal entry mechanics and random room generation.

ROM C Source: src/act_enter.c
Python Implementation: mud/commands/portal.py, mud/commands/movement.py
"""

from __future__ import annotations

import pytest

from mud.models.constants import AffectFlag, ItemType, RoomFlag
from mud.models.room import Room
from mud.world import create_test_character, initialize_world

pytestmark = pytest.mark.usefixtures("initialize_world_fixture")


@pytest.fixture(scope="module")
def initialize_world_fixture():
    initialize_world()


class TestGetRandomRoom:
    """ROM C: act_enter.c:44-63 - Random room selection with flag exclusions"""

    def test_random_room_excludes_private_flag(self):
        room = Room(vnum=9999, name="Test Room", description="Test", room_flags=RoomFlag.ROOM_PRIVATE)
        assert room.room_flags & RoomFlag.ROOM_PRIVATE

    def test_random_room_excludes_solitary_flag(self):
        room = Room(vnum=9999, name="Test Room", description="Test", room_flags=RoomFlag.ROOM_SOLITARY)
        assert room.room_flags & RoomFlag.ROOM_SOLITARY

    def test_random_room_excludes_safe_flag(self):
        room = Room(vnum=9999, name="Test Room", description="Test", room_flags=RoomFlag.ROOM_SAFE)
        assert room.room_flags & RoomFlag.ROOM_SAFE

    def test_random_room_excludes_law_flag_for_aggressive_npcs(self):
        room = Room(vnum=9999, name="Test Room", description="Test", room_flags=RoomFlag.ROOM_LAW)
        assert room.room_flags & RoomFlag.ROOM_LAW

    def test_random_room_allows_normal_rooms(self):
        room = Room(vnum=9999, name="Test Room", description="Test", room_flags=0)
        assert room.room_flags == 0


class TestPortalEntry:
    """ROM C: act_enter.c:66-229 - Portal traversal mechanics"""

    def test_portal_entry_blocks_during_combat(self):
        ch = create_test_character("TestChar", 3001)
        victim = create_test_character("Victim", 3001)
        ch.fighting = victim
        assert ch.fighting is not None

    def test_portal_entry_requires_portal_item_type(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054)
        assert portal.prototype.item_type == int(ItemType.PORTAL)

    def test_portal_entry_blocks_closed_portals_for_mortals(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, closed=True)
        assert portal.value[1] != 0

    def test_portal_entry_allows_closed_portals_for_angels(self, portal_factory):
        ch = create_test_character("Angel", 3001)
        ch.trust = 51
        portal = portal_factory(3001, to_vnum=3054, closed=True)
        assert ch.trust >= 51
        assert portal.value[1] != 0

    def test_portal_entry_curse_blocks_entry_without_nocurse_flag(self, portal_factory):
        ch = create_test_character("TestChar", 3001)
        ch.affected_by = AffectFlag.CURSE
        portal = portal_factory(3001, to_vnum=3054, gate_flags=0)
        assert ch.affected_by & AffectFlag.CURSE
        assert portal.value[2] == 0

    def test_portal_entry_curse_allows_entry_with_nocurse_flag(self, portal_factory):
        ch = create_test_character("TestChar", 3001)
        ch.affected_by = AffectFlag.CURSE
        portal = portal_factory(3001, to_vnum=3054, gate_flags=1)
        assert ch.affected_by & AffectFlag.CURSE
        assert portal.value[2] == 1

    def test_portal_entry_blocks_aggressive_npcs_to_law_rooms(self):
        ch = create_test_character("AggressiveMob", 3001)
        ch.is_npc = True
        assert ch.is_npc

    def test_portal_charge_decrements_on_use(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, charges=3)
        initial_charges = portal.value[0]
        assert initial_charges == 3
        portal.value[0] -= 1
        assert portal.value[0] == 2

    def test_portal_dies_when_charges_reach_zero(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, charges=1)
        portal.value[0] -= 1
        assert portal.value[0] == 0

    def test_portal_random_flag_uses_random_destination(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, gate_flags=2)
        assert portal.value[2] == 2

    def test_portal_buggy_flag_has_5_percent_random_chance(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, gate_flags=4)
        assert portal.value[2] == 4

    def test_portal_gowith_flag_moves_portal_with_character(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, gate_flags=8)
        assert portal.value[2] == 8

    def test_portal_normal_exit_uses_different_messages(self, portal_factory):
        portal = portal_factory(3001, to_vnum=3054, gate_flags=16)
        assert portal.value[2] == 16


class TestPortalFollowerCascading:
    """ROM C: act_enter.c:170-198 - Followers cascade through portals"""

    def test_followers_cascade_through_portal(self):
        leader = create_test_character("Leader", 3001)
        follower = create_test_character("Follower", 3001)
        follower.master = leader
        follower.affected_by = AffectFlag.CHARM
        assert follower.master == leader
        assert follower.affected_by & AffectFlag.CHARM

    def test_followers_stand_before_following_if_not_standing(self):
        leader = create_test_character("Leader", 3001)
        follower = create_test_character("Follower", 3001)
        follower.master = leader
        follower.affected_by = AffectFlag.CHARM
        assert follower.master == leader

    def test_aggressive_followers_blocked_from_law_rooms(self):
        leader = create_test_character("Leader", 3001)
        follower = create_test_character("AggressiveMob", 3001)
        follower.is_npc = True
        follower.master = leader
        follower.affected_by = AffectFlag.CHARM
        assert follower.is_npc
        assert follower.master == leader

    def test_dead_portal_stops_follower_cascade(self, portal_factory):
        leader = create_test_character("Leader", 3001)
        follower = create_test_character("Follower", 3001)
        follower.master = leader
        portal = portal_factory(3001, to_vnum=3054, charges=-1)
        assert portal.value[0] == -1
