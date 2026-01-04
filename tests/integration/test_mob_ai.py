"""
Integration tests for mob AI behaviors (mobile_update and aggressive_update).

Tests verify that mobs behave according to ROM 2.4b6 AI patterns:
- Sentinel mobs stay in place
- Non-sentinel mobs wander
- Scavenger mobs pick up items
- Aggressive mobs attack players
- Wimpy mobs flee at low HP
- Mobs return home when out of area

ROM Reference: src/update.c (mobile_update, aggr_update)
"""

from __future__ import annotations

import pytest

from mud.ai import mobile_update, aggressive_update
from mud.models.character import Character, character_registry
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    Direction,
    ItemType,
    Position,
    RoomFlag,
    WearFlag,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.registry import room_registry, area_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world for mob AI tests."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()


@pytest.fixture
def test_room():
    """Get the Temple of Mota (room 3001) for testing."""
    return room_registry.get(3001)


@pytest.fixture
def adjacent_room():
    """Get room north of Temple (room 3004) for testing."""
    return room_registry.get(3004)


@pytest.fixture
def valhalla_room():
    """Get a room in Valhalla (area 1200) for cross-area tests."""
    return room_registry.get(1200)


def create_test_mob(room_vnum: int, **kwargs) -> Character:
    """Create a test mob with specified properties."""
    room = room_registry.get(room_vnum)

    mob = Character(
        name=kwargs.get("name", "testmob"),
        short_descr=kwargs.get("short_descr", "a test mob"),
        is_npc=True,
        level=kwargs.get("level", 10),
        position=kwargs.get("position", Position.STANDING),
        default_pos=kwargs.get("default_pos", Position.STANDING),
        act=kwargs.get("act", 0),
        affected_by=kwargs.get("affected_by", 0),
        room=room,
        inventory=[],
        carry_number=0,
        carry_weight=0,
        # Movement points required for wandering
        move=kwargs.get("move", 1000),
        max_move=kwargs.get("max_move", 1000),
    )

    mob.home_room_vnum = kwargs.get("home_room_vnum", room_vnum)
    mob.home_area = kwargs.get("home_area", getattr(room, "area", None))
    mob.zone = kwargs.get("zone", getattr(room, "area", None))

    if room:
        room.people.append(mob)

    # Add to character_registry so mobile_update() processes it
    character_registry.append(mob)

    return mob


def create_test_player(name: str, room_vnum: int, level: int = 10) -> Character:
    """Create a test player character."""
    room = room_registry.get(room_vnum)

    player = Character(
        name=name,
        short_descr=name,
        is_npc=False,
        level=level,
        position=Position.STANDING,
        default_pos=Position.STANDING,
        inventory=[],
        room=room,
    )

    if room:
        room.add_character(player)

    character_registry.append(player)

    return player


def create_test_object(vnum: int, room_vnum: int, **kwargs) -> Object:
    """Create a test object in a room."""
    proto = ObjIndex(
        vnum=vnum,
        name=kwargs.get("name", f"testobj{vnum}"),
        short_descr=kwargs.get("short_descr", f"a test object {vnum}"),
        item_type=kwargs.get("item_type", ItemType.TRASH),
        wear_flags=kwargs.get("wear_flags", int(WearFlag.TAKE)),
        cost=kwargs.get("cost", 100),
    )

    obj = Object(instance_id=None, prototype=proto)

    obj.cost = int(proto.cost)
    obj.wear_flags = int(proto.wear_flags)

    room = room_registry.get(room_vnum)
    if room:
        room.add_object(obj)

    return obj


class TestSentinelBehavior:
    """Test ACT_SENTINEL flag prevents wandering."""

    def test_sentinel_mob_stays_in_place(self, test_room):
        """ROM parity: src/update.c:677 - Sentinel mobs don't wander."""
        sentinel = create_test_mob(
            3001,
            name="sentinel guard",
            act=int(ActFlag.SENTINEL),
        )

        original_room = sentinel.room

        for _ in range(50):
            mobile_update()

        assert sentinel.room is original_room

    def test_non_sentinel_mob_can_wander(self, test_room):
        """ROM parity: src/update.c:680 - Non-sentinel mobs wander randomly.

        Wandering probability per tick:
        - 1/8 chance to attempt wander (number_bits(3) == 0)
        - 6/32 chance to pick valid direction 0-5 (number_bits(5))
        - 2/6 chance to pick existing exit in room 3001 (south or up)
        Combined: ~1.56% per tick, need ~600 ticks for 99% confidence
        """
        wanderer = create_test_mob(
            3001,
            name="wandering merchant",
            act=0,
        )

        original_room = wanderer.room

        moved = False
        for _ in range(600):  # Increased from 100 for 99% confidence
            mobile_update()
            if wanderer.room != original_room:
                moved = True
                break

        assert moved


class TestScavengerBehavior:
    """Test ACT_SCAVENGER flag causes mobs to pick up items."""

    def test_scavenger_picks_up_items(self, test_room):
        """ROM parity: src/update.c:621 - Scavenger mobs pick up valuable items."""
        scavenger = create_test_mob(
            3001,
            name="scavenger rat",
            act=int(ActFlag.SCAVENGER),
        )

        obj = create_test_object(
            9100,
            3001,
            name="gold coin",
            short_descr="a shiny gold coin",
            cost=500,
            wear_flags=int(WearFlag.TAKE),
        )

        for _ in range(2000):
            mobile_update()
            if obj in scavenger.inventory:
                break

        assert obj in scavenger.inventory
        assert obj not in test_room.contents

    def test_scavenger_prefers_valuable_items(self, test_room):
        """ROM parity: src/update.c:633 - Scavengers pick most valuable item."""
        scavenger = create_test_mob(
            3001,
            name="scavenger goblin",
            act=int(ActFlag.SCAVENGER),
        )

        cheap_obj = create_test_object(
            9101,
            3001,
            name="rusty dagger",
            cost=10,
            wear_flags=int(WearFlag.TAKE),
        )

        expensive_obj = create_test_object(
            9102,
            3001,
            name="diamond ring",
            cost=1000,
            wear_flags=int(WearFlag.TAKE),
        )

        for _ in range(2000):
            mobile_update()
            if expensive_obj in scavenger.inventory:
                break

        assert expensive_obj in scavenger.inventory


class TestHomeReturn:
    """Test mobs return home when out of their area."""

    def test_mob_returns_home_when_out_of_area(self, test_room, valhalla_room):
        """ROM parity: src/update.c:688-693 - Mobs return to home area when displaced."""
        home_vnum = 3001
        away_vnum = 1200

        mob = create_test_mob(
            away_vnum,
            name="displaced wolf",
            level=10,
            home_room_vnum=home_vnum,
            home_area=test_room.area,
            zone=test_room.area,
        )

        assert mob.room == valhalla_room
        assert mob.zone != mob.room.area

        for i in range(2000):
            mobile_update()
            if mob.room == test_room:
                break

        assert mob.room == test_room, "Mob failed to return home after 2000 iterations"


class TestAggressiveBehavior:
    """Test ACT_AGGRESSIVE flag causes mobs to attack players."""

    def test_aggressive_mob_attacks_player(self, test_room):
        """ROM parity: src/update.c:729 - Aggressive mobs attack on sight."""
        aggressive = create_test_mob(
            3001,
            name="aggressive orc",
            act=int(ActFlag.AGGRESSIVE),
            level=10,
        )

        player = create_test_player("TestVictim", 3001, level=10)

        # aggressive_update has 50% RNG check, need multiple iterations
        attacked = False
        for _ in range(20):
            aggressive_update()
            if aggressive.fighting is not None or player.fighting is not None:
                attacked = True
                break

        assert attacked

    def test_aggressive_mob_respects_safe_rooms(self, test_room):
        """ROM parity: src/update.c:738 - Aggressive mobs don't attack in safe rooms."""
        test_room.room_flags = int(RoomFlag.ROOM_SAFE)

        aggressive = create_test_mob(
            3001,
            name="aggressive troll",
            act=int(ActFlag.AGGRESSIVE),
            level=10,
        )

        player = create_test_player("TestSafe", 3001, level=10)

        for _ in range(10):
            aggressive_update()

        assert aggressive.fighting is None
        assert player.fighting is None

        test_room.room_flags = 0

    def test_aggressive_mob_respects_level_difference(self, test_room):
        """ROM parity: src/update.c:757 - Aggressive mobs won't attack much higher level players."""
        aggressive = create_test_mob(
            3001,
            name="weak goblin",
            act=int(ActFlag.AGGRESSIVE),
            level=5,
        )

        player = create_test_player("TestHighLevel", 3001, level=20)

        for _ in range(10):
            aggressive_update()

        assert aggressive.fighting is None


class TestWimpyBehavior:
    """Test ACT_WIMPY flag prevents attacking awake players."""

    def test_wimpy_mob_avoids_awake_players(self, test_room):
        """ROM parity: src/update.c:759 - Wimpy mobs don't attack awake players."""
        wimpy = create_test_mob(
            3001,
            name="wimpy kobold",
            act=int(ActFlag.AGGRESSIVE) | int(ActFlag.WIMPY),
            level=10,
        )

        player = create_test_player("TestAwake", 3001, level=10)
        player.position = Position.STANDING

        for _ in range(10):
            aggressive_update()

        assert wimpy.fighting is None
        assert player.fighting is None


class TestCharmedMobBehavior:
    """Test charmed mobs don't wander or return home."""

    def test_charmed_mob_stays_with_master(self, test_room):
        """ROM parity: src/update.c:571 - Charmed mobs don't return home."""
        charmed = create_test_mob(
            3001,
            name="charmed wolf",
            affected_by=int(AffectFlag.CHARM),
        )

        original_room = charmed.room

        for _ in range(50):
            mobile_update()

        assert charmed.room is original_room


class TestStayAreaBehavior:
    """Test ACT_STAY_AREA flag prevents cross-area movement."""

    def test_stay_area_mob_wont_leave_area(self, test_room, valhalla_room):
        """ROM parity: src/update.c:503 - Mobs with STAY_AREA won't leave their area."""
        from mud.models.room import Exit

        if not test_room or not test_room.area:
            pytest.skip("Test room has no area")
        if not valhalla_room or not valhalla_room.area:
            pytest.skip("Valhalla room has no area")
        if test_room.area == valhalla_room.area:
            pytest.skip("Need rooms in different areas for this test")

        # Create exit to another area (so mob CAN wander, but STAY_AREA prevents it)
        north_exit = Exit(to_room=valhalla_room, key=0, exit_info=0, keyword="", description="")
        test_room.exits[int(Direction.NORTH)] = north_exit

        stay_area = create_test_mob(
            3001,
            name="area guardian",
            act=int(ActFlag.STAY_AREA),
        )

        original_area = test_room.area

        # ROM: number_bits(3) != 0 check means ~12.5% chance to wander per tick
        # So 100 ticks should be enough to attempt wander multiple times
        for _ in range(100):
            mobile_update()
            if stay_area.room and stay_area.room.area != original_area:
                pytest.fail("STAY_AREA mob left its area")

        assert stay_area.room and stay_area.room.area == original_area


class TestMobAssistBehavior:
    """Test mob assist mechanics (ASSIST_VNUM, ASSIST_ALL, etc)."""

    def test_assist_vnum_same_mob_helps_in_combat(self, test_room):
        """ROM parity: src/fight.c:149 - Mobs with ASSIST_VNUM help same vnum.

        Note: ROM has 50% probability per assist check (number_bits(1) == 0)
        so we loop multiple times to ensure assist happens.
        """
        from mud.combat import check_assist
        from mud.models.constants import OffFlag

        attacker = create_test_mob(
            3001,
            name="city guard",
            level=15,
            act=0,
        )
        attacker.vnum = 3001
        attacker.off_flags = int(OffFlag.ASSIST_VNUM)

        helper = create_test_mob(
            3001,
            name="city guard",
            level=15,
            act=0,
        )
        helper.vnum = 3001
        helper.off_flags = int(OffFlag.ASSIST_VNUM)

        player = create_test_player("Attacker", 3001, level=10)

        attacker.fighting = player
        player.fighting = attacker

        assisted = False
        for _ in range(20):
            check_assist(attacker, player)
            if helper.fighting == player:
                assisted = True
                break

        assert assisted, "ASSIST_VNUM mob should help same vnum in combat (50% probability, 20 attempts)"

    def test_assist_all_any_mob_helps(self, test_room):
        """ROM parity: src/fight.c:141 - Mobs with ASSIST_ALL help any mob.

        Note: ROM has 50% probability per assist check (number_bits(1) == 0)
        so we loop multiple times to ensure assist happens.
        """
        from mud.combat import check_assist
        from mud.models.constants import OffFlag

        goblin = create_test_mob(
            3001,
            name="goblin warrior",
            level=12,
            act=0,
        )
        goblin.vnum = 3002

        orc = create_test_mob(
            3001,
            name="orc grunt",
            level=14,
            act=0,
        )
        orc.vnum = 3003
        orc.off_flags = int(OffFlag.ASSIST_ALL)

        player = create_test_player("Victim", 3001, level=10)

        goblin.fighting = player
        player.fighting = goblin

        assisted = False
        for _ in range(20):
            orc.fighting = None  # Reset between attempts (check_assist skips if already fighting)
            check_assist(goblin, player)
            if orc.fighting == player:
                assisted = True
                break

        assert assisted, "ASSIST_ALL mob should help any mob in combat (50% probability, 20 attempts)"


class TestIndoorOutdoorRestrictions:
    """Test ACT_INDOORS and ACT_OUTDOORS movement restrictions."""

    def test_outdoors_mob_wont_enter_indoors(self, test_room):
        """ROM parity: src/update.c:698 - ACT_OUTDOORS mobs avoid ROOM_INDOORS."""
        outdoor_room = room_registry.get(3054)
        if not outdoor_room or int(getattr(outdoor_room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS):
            pytest.skip("Need outdoor room for this test")

        outdoor_mob = create_test_mob(
            3054,
            name="sunlight creature",
            act=int(ActFlag.OUTDOORS),
        )

        original_outdoor = outdoor_mob.room

        for _ in range(300):
            mobile_update()
            if outdoor_mob.room and int(getattr(outdoor_mob.room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS):
                pytest.fail("ACT_OUTDOORS mob entered ROOM_INDOORS")

        assert outdoor_mob.room is not None

    def test_indoors_mob_wont_go_outdoors(self, test_room):
        """ROM parity: src/update.c:700 - ACT_INDOORS mobs require ROOM_INDOORS."""
        if not int(getattr(test_room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS):
            pytest.skip("Need indoor room for this test")

        indoor_mob = create_test_mob(
            3001,
            name="cave dweller",
            act=int(ActFlag.INDOORS),
        )

        indoor_mob_room_flags = int(getattr(indoor_mob.room, "room_flags", 0))
        assert indoor_mob_room_flags & int(RoomFlag.ROOM_INDOORS)

        for _ in range(300):
            mobile_update()
            if indoor_mob.room and not (int(getattr(indoor_mob.room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS)):
                pytest.fail("ACT_INDOORS mob left ROOM_INDOORS")

        assert int(getattr(indoor_mob.room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS)
