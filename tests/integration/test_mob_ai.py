"""
Integration tests for mob AI behaviors (mobile_update and aggressive_update).

Tests verify that mobs behave according to ROM 2.4b6 AI patterns:
- Sentinel mobs stay in place
- Non-sentinel mobs wander
- Scavenger mobs pick up items
- Aggressive mobs attack players
- Wimpy mobs flee at low HP
- Out-of-area mobs are extracted by the home-roll path

ROM Reference: src/update.c (mobile_update, aggr_update)
"""

from __future__ import annotations

import pytest

from mud.ai import aggressive_update, mobile_update
from mud.models.area import Area
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
from mud.models.room import Exit, Room
from mud.registry import area_registry, room_registry
from mud.utils import rng_mm
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
    """Get the Temple of Mota (room 3001) for testing.

    Restores the shared room's occupant list afterwards so characters spawned by
    one test (e.g. an aggressive mob's victim) do not leak into the next test in
    the class — the same snapshot/restore discipline the isolated fixtures use for
    character_registry. Without this, FIGHT-019's THAC0 model (which kills less
    often than the retired percent model) leaves victims alive in room 3001 across
    tests, and a later aggressive-mob test attacks the leftover instead of its own
    target.
    """
    room = room_registry.get(3001)
    people_snapshot = list(room.people) if room is not None else []
    try:
        yield room
    finally:
        if room is not None:
            room.people[:] = people_snapshot


@pytest.fixture
def adjacent_room():
    """Get room north of Temple (room 3004) for testing."""
    return room_registry.get(3004)


@pytest.fixture
def valhalla_room():
    """Get a room in Valhalla (area 1200) for cross-area tests."""
    return room_registry.get(1200)


@pytest.fixture
def isolated_mobile_room():
    """Provide an isolated room and registry slice for deterministic mob AI tests."""
    snapshot = list(character_registry)
    character_registry.clear()

    room = Room(
        vnum=999001,
        name="Isolated Mob AI Room",
        description="A deterministic room for mob AI parity tests.",
        room_flags=0,
        sector_type=0,
    )
    room_registry[room.vnum] = room

    try:
        yield room
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(room.vnum, None)


@pytest.fixture
def isolated_wander_rooms():
    """Provide deterministic room/area topology for ROM wander-gate tests."""
    snapshot = list(character_registry)
    character_registry.clear()

    room_snapshot = {}
    area_snapshot = {}
    area_ids = (999101, 999102)
    room_ids = (999111, 999112, 999113, 999114)

    for area_id in area_ids:
        area_snapshot[area_id] = area_registry.get(area_id)
    for room_id in room_ids:
        room_snapshot[room_id] = room_registry.get(room_id)

    area_one = Area(vnum=area_ids[0], name="Mob AI Area One", min_vnum=room_ids[0], max_vnum=room_ids[2])
    area_two = Area(vnum=area_ids[1], name="Mob AI Area Two", min_vnum=room_ids[3], max_vnum=room_ids[3])
    area_registry[area_one.vnum] = area_one
    area_registry[area_two.vnum] = area_two

    stay_area_start = Room(vnum=room_ids[0], name="Stay Area Start", area=area_one)
    indoor_start = Room(vnum=room_ids[1], name="Indoor Start", area=area_one, room_flags=int(RoomFlag.ROOM_INDOORS))
    outdoor_start = Room(vnum=room_ids[2], name="Outdoor Start", area=area_one)
    cross_area_target = Room(vnum=room_ids[3], name="Cross Area Target", area=area_two)

    stay_area_start.exits[int(Direction.NORTH)] = Exit(to_room=cross_area_target)
    indoor_start.exits[int(Direction.NORTH)] = Exit(to_room=outdoor_start)
    outdoor_start.exits[int(Direction.NORTH)] = Exit(to_room=indoor_start)

    room_registry[stay_area_start.vnum] = stay_area_start
    room_registry[indoor_start.vnum] = indoor_start
    room_registry[outdoor_start.vnum] = outdoor_start
    room_registry[cross_area_target.vnum] = cross_area_target

    try:
        yield {
            "stay_area_start": stay_area_start,
            "indoor_start": indoor_start,
            "outdoor_start": outdoor_start,
            "cross_area_target": cross_area_target,
        }
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        for room_id, prior in room_snapshot.items():
            if prior is None:
                room_registry.pop(room_id, None)
            else:
                room_registry[room_id] = prior
        for area_id, prior in area_snapshot.items():
            if prior is None:
                area_registry.pop(area_id, None)
            else:
                area_registry[area_id] = prior


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

    def test_scavenger_picks_up_items(self, isolated_mobile_room):
        """ROM parity: src/update.c:621 - Scavenger mobs pick up valuable items."""
        scavenger = create_test_mob(
            isolated_mobile_room.vnum,
            name="scavenger rat",
            act=int(ActFlag.SCAVENGER),
        )

        obj = create_test_object(
            9100,
            isolated_mobile_room.vnum,
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
        assert obj not in isolated_mobile_room.contents

    def test_scavenger_prefers_valuable_items(self, isolated_mobile_room):
        """ROM parity: src/update.c:633 - Scavengers pick most valuable item.

        Loop bound generous enough that the 1/64-per-tick action roll fires
        many times. RNG seeding is handled by the integration conftest
        autouse fixture for determinism.
        """
        scavenger = create_test_mob(
            isolated_mobile_room.vnum,
            name="scavenger goblin",
            act=int(ActFlag.SCAVENGER),
        )

        create_test_object(
            9101,
            isolated_mobile_room.vnum,
            name="rusty dagger",
            cost=10,
            wear_flags=int(WearFlag.TAKE),
        )

        expensive_obj = create_test_object(
            9102,
            isolated_mobile_room.vnum,
            name="diamond ring",
            cost=1000,
            wear_flags=int(WearFlag.TAKE),
        )

        for _ in range(5000):
            mobile_update()
            if expensive_obj in scavenger.inventory:
                break

        assert expensive_obj in scavenger.inventory


class TestHomeReturn:
    """Test ROM out-of-zone mobs are extracted during char_update."""

    def test_mob_out_of_area_is_extracted_on_home_roll(self, test_room, valhalla_room):
        """ROM parity: src/update.c:688-693 - Out-of-zone mobs are extracted on a low roll."""
        from mud.game_loop import char_update

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

        original = rng_mm.number_percent
        rng_mm.number_percent = lambda: 1
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        assert mob.room is None
        assert mob not in character_registry


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

        create_test_player("TestHighLevel", 3001, level=20)

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

    def test_stay_area_mob_wont_leave_area(self, isolated_wander_rooms, monkeypatch):
        """ROM parity: src/update.c:503 - Mobs with STAY_AREA won't leave their area."""
        import mud.ai as ai_module

        monkeypatch.setattr(ai_module.rng_mm, "number_bits", lambda bits: 0)
        monkeypatch.setattr(ai_module.rng_mm, "number_door", lambda: int(Direction.NORTH))

        stay_area = create_test_mob(
            isolated_wander_rooms["stay_area_start"].vnum,
            name="area guardian",
            act=int(ActFlag.STAY_AREA),
        )

        original_room = isolated_wander_rooms["stay_area_start"]

        mobile_update()

        assert stay_area.room is original_room
        assert stay_area.room.area is original_room.area


class TestMobileWanderUsesNumberBits5:
    """ROM ``mobile_update`` wander draws the door with a SINGLE ``number_bits(5)``
    and aborts the wander when the result is ``> 5`` (src/update.c:498:
    ``(door = number_bits(5)) <= 5``). It must NOT use ``number_door()`` — that is
    the ``do_flee``/``do_mpflee`` primitive (src/db.c:3541, a `while (... > 5)`
    loop that re-rolls until it lands on a valid 0-5 door and so ALWAYS yields a
    direction). Borrowing ``number_door`` here makes mobs wander ~5x too often
    (every gated tick instead of 6/32 of them) and desyncs the shared MM RNG
    stream (a loop of variable draws vs one fixed draw).
    """

    def test_wander_aborts_when_number_bits5_exceeds_five(self, isolated_wander_rooms, monkeypatch):
        """mirrors ROM src/update.c:498 — a door roll > 5 aborts the wander; the
        mob stays put for this tick rather than re-rolling into a valid door."""
        import mud.ai as ai_module

        # Gate (number_bits(3)) passes; the door roll (number_bits(5)) returns 10,
        # which is > 5 and must abort the wander. number_door is patched to a valid
        # door so the OLD (buggy) number_door()-based code would deterministically
        # move the mob — making this a clean RED before the fix.
        monkeypatch.setattr(ai_module.rng_mm, "number_bits", lambda bits: 0 if bits != 5 else 10)
        monkeypatch.setattr(ai_module.rng_mm, "number_door", lambda: int(Direction.NORTH))

        start = isolated_wander_rooms["outdoor_start"]
        wanderer = create_test_mob(start.vnum, name="roaming peddler", act=0)
        assert wanderer.room is start
        # sanity: the room really does have a NORTH exit the mob could take
        assert start.exits[int(Direction.NORTH)] is not None

        mobile_update()

        assert wanderer.room is start, (
            "ROM src/update.c:498 aborts the wander when number_bits(5) > 5; the mob "
            "must stay put. A moved mob means the wander used number_door() (the flee "
            "primitive), which re-rolls until valid and never aborts."
        )

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

    def test_outdoors_mob_wont_enter_indoors(self, isolated_wander_rooms, monkeypatch):
        """ROM parity: src/update.c:698 - ACT_OUTDOORS mobs avoid ROOM_INDOORS."""
        import mud.ai as ai_module

        monkeypatch.setattr(ai_module.rng_mm, "number_bits", lambda bits: 0)
        monkeypatch.setattr(ai_module.rng_mm, "number_door", lambda: int(Direction.NORTH))

        outdoor_mob = create_test_mob(
            isolated_wander_rooms["outdoor_start"].vnum,
            name="sunlight creature",
            act=int(ActFlag.OUTDOORS),
        )

        original_outdoor = isolated_wander_rooms["outdoor_start"]

        mobile_update()

        assert outdoor_mob.room is original_outdoor
        assert not (int(getattr(outdoor_mob.room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS))

    def test_indoors_mob_wont_go_outdoors(self, isolated_wander_rooms, monkeypatch):
        """ROM parity: src/update.c:700 - ACT_INDOORS mobs require ROOM_INDOORS."""
        import mud.ai as ai_module

        monkeypatch.setattr(ai_module.rng_mm, "number_bits", lambda bits: 0)
        monkeypatch.setattr(ai_module.rng_mm, "number_door", lambda: int(Direction.NORTH))

        indoor_mob = create_test_mob(
            isolated_wander_rooms["indoor_start"].vnum,
            name="cave dweller",
            act=int(ActFlag.INDOORS),
        )

        indoor_mob_room_flags = int(getattr(isolated_wander_rooms["indoor_start"], "room_flags", 0))
        assert indoor_mob_room_flags & int(RoomFlag.ROOM_INDOORS)

        mobile_update()

        assert int(getattr(indoor_mob.room, "room_flags", 0)) & int(RoomFlag.ROOM_INDOORS)


class TestMobileUpdateIterationOrder:
    """GL-042: mobile_update must walk characters newest-first (INV-045).

    ROM src/update.c:416 walks char_list, which src/db.c:2256-2257
    (create_mobile) head-inserts — the most-recently-created mob is visited
    first, so it consumes the shared Mitchell-Moore RNG stream first.
    """

    def test_shop_wealth_rolls_drawn_newest_mob_first(self, test_room):
        """mirrors ROM src/update.c:433-440 — the shopkeeper wealth
        replenishment rolls number_range(1,20) for gold then silver per
        shopkeeper, in char_list (newest-first) visit order."""
        saved = list(character_registry)
        character_registry.clear()
        try:
            # SENTINEL so the wander block never draws number_bits and the
            # only RNG consumed per mob is the gold+silver roll pair.
            old_mob = create_test_mob(3001, name="old shopkeeper", act=int(ActFlag.SENTINEL))
            new_mob = create_test_mob(3001, name="new shopkeeper", act=int(ActFlag.SENTINEL))
            for mob in (old_mob, new_mob):
                mob.pShop = object()
                mob.wealth = 5_000_000
                mob.gold = 0
                mob.silver = 0

            # seed 12345 -> number_range(1,20) draws [1, 19, 13, 12]:
            # first-visited mob gets gold +1 / silver +1900, second-visited
            # gets gold +13 / silver +1200 (wealth*roll//5_000_000 and
            # wealth*roll//50_000 with wealth=5_000_000).
            rng_mm.seed_mm(12345)
            mobile_update()

            assert (new_mob.gold, new_mob.silver) == (1, 1900), (
                "newest mob must be visited first (ROM char_list is head-inserted); "
                f"got new=({new_mob.gold},{new_mob.silver}) old=({old_mob.gold},{old_mob.silver})"
            )
            assert (old_mob.gold, old_mob.silver) == (13, 1200)
        finally:
            character_registry.clear()
            character_registry.extend(saved)


class TestAggressiveUpdateIterationOrder:
    """GL-043: aggressive_update must walk PC watchers newest-first (INV-045).

    ROM src/update.c:1087-1092 walks char_list for the PC watcher ``wch``;
    char_list is head-inserted (src/db.c:2256-2257 create_mobile,
    src/nanny.c:757-758 PC login), so the most-recently-added character is
    visited first and its room's aggressors draw the number_bits(1)
    aggression coin (src/update.c:1107) first.
    """

    def test_aggression_coin_drawn_for_newest_watcher_first(self, monkeypatch):
        """mirrors ROM src/update.c:1087-1107 — the FIRST aggression coin
        belongs to the NEWEST watcher's aggressor; scripting coins [1, 0]
        must make the newest player's mob attack and the older one's skip."""
        import mud.ai.aggressive as aggressive_module

        saved = list(character_registry)
        character_registry.clear()
        room_old = Room(vnum=999201, name="Old Watcher Room")
        room_new = Room(vnum=999202, name="New Watcher Room")
        room_registry[room_old.vnum] = room_old
        room_registry[room_new.vnum] = room_new
        try:
            old_player = create_test_player("OldWatcher", room_old.vnum, level=10)
            new_player = create_test_player("NewWatcher", room_new.vnum, level=10)
            old_mob = create_test_mob(room_old.vnum, name="old orc", act=int(ActFlag.AGGRESSIVE))
            new_mob = create_test_mob(room_new.vnum, name="new orc", act=int(ActFlag.AGGRESSIVE))
            assert old_mob is not None and old_player is not None

            # Coin script: the first (watcher, mob) aggression check attacks,
            # every later draw (second watcher's check, check_assist coins)
            # skips. Which mob lands the scripted 1 reveals the walk order.
            coins = [1, 0]
            monkeypatch.setattr(
                aggressive_module.rng_mm,
                "number_bits",
                lambda width: coins.pop(0) if coins else 0,
            )
            attacks: list[tuple[Character, Character]] = []
            monkeypatch.setattr(
                aggressive_module,
                "multi_hit",
                lambda attacker, victim: attacks.append((attacker, victim)),
            )

            aggressive_update()

            assert attacks, "the scripted coin must trigger exactly one attack"
            attacker, victim = attacks[0]
            assert attacker is new_mob and victim is new_player, (
                "newest watcher must be visited first (ROM char_list is head-inserted); "
                f"first attack was {attacker.name} -> {victim.name}"
            )
            assert len(attacks) == 1
        finally:
            character_registry.clear()
            character_registry.extend(saved)
            room_registry.pop(room_old.vnum, None)
            room_registry.pop(room_new.vnum, None)


class TestAggressiveUpdateDoesNotAssist:
    """ROM ``aggr_update`` (src/update.c:1077-1141) ends each aggression with a
    bare ``multi_hit(ch, victim, TYPE_UNDEFINED)`` (line 1136) — it NEVER calls
    ``check_assist``. Auto-assist is exclusively ``violence_update``'s job
    (src/fight.c:90, run on the next PULSE_VIOLENCE). So an aggressive mob that
    aggros a player must NOT pull its room-mates into the fight during the
    aggression pulse itself; assists land one violence-tick later.

    The Python port previously fired ``check_assist`` inline at the end of
    ``aggressive_update`` (mis-citing fight.c:90, which is the *violence_update*
    site), drawing extra assist coins from the shared MM RNG stream and starting
    assists a full tick early — a parity divergence.
    """

    def test_aggression_pulse_does_not_invoke_check_assist(self, monkeypatch):
        """mirrors ROM src/update.c:1136 — aggr_update calls only multi_hit;
        check_assist belongs to violence_update (src/fight.c:90), not here."""
        import mud.ai.aggressive as aggressive_module
        import mud.combat.assist as assist_module

        saved = list(character_registry)
        character_registry.clear()
        room = Room(vnum=999210, name="Aggro-no-assist Room")
        room_registry[room.vnum] = room
        try:
            player = create_test_player("Victim", room.vnum, level=10)
            mob = create_test_mob(room.vnum, name="lone orc", act=int(ActFlag.AGGRESSIVE))
            assert player is not None and mob is not None

            # Force the aggression coin (number_bits(1)) to pass and the victim
            # reservoir (number_range) to pick the first eligible PC.
            monkeypatch.setattr(aggressive_module.rng_mm, "number_bits", lambda width: 1)
            monkeypatch.setattr(aggressive_module.rng_mm, "number_range", lambda lo, hi: 0)

            attacks: list[tuple[Character, Character]] = []
            monkeypatch.setattr(
                aggressive_module,
                "multi_hit",
                lambda attacker, victim: attacks.append((attacker, victim)),
            )

            # Spy on check_assist — aggressive_update imports it function-locally
            # (`from mud.combat.assist import check_assist`), so patching the
            # module attribute is seen at call time.
            assist_calls: list[tuple[Character, Character]] = []
            monkeypatch.setattr(
                assist_module,
                "check_assist",
                lambda ch, victim: assist_calls.append((ch, victim)),
            )

            aggressive_update()

            # Aggression must actually have fired, else the assertion below is vacuous.
            assert attacks == [(mob, player)], "the aggressive mob should have aggro'd the player"
            assert assist_calls == [], (
                "aggr_update (src/update.c:1136) must NOT call check_assist — auto-assist "
                "is violence_update's job (src/fight.c:90), one tick later. The inline "
                "check_assist starts assists early and consumes extra RNG coins."
            )
        finally:
            character_registry.clear()
            character_registry.extend(saved)
            room_registry.pop(room.vnum, None)
