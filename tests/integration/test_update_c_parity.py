"""Integration tests for update.c parity gaps GL-009, GL-011, GL-012, GL-013, GL-014, GL-015, GL-018.

Mirrors ROM 2.4b6 src/update.c behaviour verified against the C source.
"""
from __future__ import annotations

import pytest

from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_mob(room: Room, *, zone=None, home_zone=None) -> Character:
    mob = Character(
        name="a mob",
        short_descr="a mob",
        level=5,
        room=room,
        is_npc=True,
        hit=50,
        max_hit=50,
        position=int(Position.STANDING),
    )
    mob.zone = zone
    room.people.append(mob)
    character_registry.append(mob)
    return mob


def _make_player(room: Room) -> Character:
    ch = Character(
        name="TestPlayer",
        level=5,
        room=room,
        hit=100,
        max_hit=100,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        is_npc=False,
        position=int(Position.STANDING),
    )
    room.people.append(ch)
    character_registry.append(ch)
    return ch


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    for vnum in list(room_registry.keys()):
        if vnum >= 9000:
            room_registry.pop(vnum, None)
    # Remove any test characters added
    for ch in list(character_registry):
        if getattr(ch, "name", "") in ("a mob", "TestPlayer"):
            character_registry.remove(ch)


# ---------------------------------------------------------------------------
# GL-009: NPC wanders home — ROM src/update.c:688-696
# ---------------------------------------------------------------------------

class TestNpcWandersHome:
    def test_out_of_zone_npc_extracted_on_5pct_roll(self):
        """NPC out of its home zone is extracted (despawned) when RNG < 5."""
        from mud.game_loop import char_update

        zone_a = object()
        zone_b = object()

        room = _make_room(9001)
        room.area = zone_b  # NPC is in zone_b

        mob = _make_mob(room, zone=zone_a)  # mob belongs to zone_a
        mob.fighting = None
        mob.desc = None

        # Force RNG to always return 0 (< 5) so the 5% check fires
        rng_mm.seed_mm(0)
        # Find a seed that makes number_percent() < 5
        # Instead, monkeypatch
        import mud.game_loop as gl
        original = rng_mm.number_percent

        call_count = 0
        def _always_low():
            nonlocal call_count
            call_count += 1
            return 1  # always < 5

        rng_mm.number_percent = _always_low
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        # Mob should have been extracted — no longer in room or registry
        assert mob not in room.people, "mob should be removed from room after wanders-home"

    def test_in_zone_npc_not_extracted(self):
        """NPC in its home zone is never extracted by wanders-home logic."""
        from mud.game_loop import char_update

        zone_a = object()
        room = _make_room(9002)
        room.area = zone_a

        mob = _make_mob(room, zone=zone_a)  # same zone — no extraction

        import mud.game_loop as gl
        original = rng_mm.number_percent
        rng_mm.number_percent = lambda: 1  # always < 5 if check ran
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        assert mob in room.people, "in-zone mob must NOT be extracted"

    def test_fighting_npc_not_extracted(self):
        """NPC in combat is never extracted regardless of zone."""
        from mud.game_loop import char_update

        zone_a = object()
        zone_b = object()
        room = _make_room(9003)
        room.area = zone_b

        mob = _make_mob(room, zone=zone_a)
        mob.fighting = object()  # in combat

        original = rng_mm.number_percent
        rng_mm.number_percent = lambda: 1
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        assert mob in room.people, "fighting mob must NOT be extracted"

    def test_charmed_npc_not_extracted(self):
        """Charmed NPC is not extracted by wanders-home."""
        from mud.game_loop import char_update

        zone_a = object()
        zone_b = object()
        room = _make_room(9004)
        room.area = zone_b

        mob = _make_mob(room, zone=zone_a)
        mob.fighting = None
        mob.desc = None
        mob.affected_by = int(AffectFlag.CHARM)

        original = rng_mm.number_percent
        rng_mm.number_percent = lambda: 1
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        assert mob in room.people, "charmed mob must NOT be extracted"

    def test_rng_at_5_not_extracted(self):
        """5% check: number_percent() >= 5 means no extraction (boundary)."""
        from mud.game_loop import char_update

        zone_a = object()
        zone_b = object()
        room = _make_room(9005)
        room.area = zone_b

        mob = _make_mob(room, zone=zone_a)
        mob.fighting = None
        mob.desc = None

        original = rng_mm.number_percent
        rng_mm.number_percent = lambda: 5  # boundary — >= 5 → no extraction
        try:
            char_update()
        finally:
            rng_mm.number_percent = original

        assert mob in room.people, "mob with roll==5 must NOT be extracted"


# ---------------------------------------------------------------------------
# GL-012: Poison tick — ROM src/update.c:848-862
# ---------------------------------------------------------------------------

class TestPoisonTick:
    def test_poison_tick_deals_damage(self):
        """Poisoned character takes (level // 10 + 1) damage per char_update tick."""
        from mud.game_loop import char_update

        room = _make_room(9010)
        ch = _make_player(room)
        ch.hit = 80
        ch.max_hit = 100
        ch.position = int(Position.STANDING)
        ch.affected_by = int(AffectFlag.POISON)

        af = AffectData(
            type="poison",
            level=10,
            duration=5,
            location="none",
            modifier=0,
            bitvector=int(AffectFlag.POISON),
        )
        ch.affected = [af]
        # Ensure desc is set so the idle timer doesn't fire
        ch.desc = object()

        before = ch.hit
        char_update()
        # damage = level // 10 + 1 = 10 // 10 + 1 = 2
        expected_damage = af.level // 10 + 1
        assert ch.hit <= before - expected_damage, (
            f"Poison tick should deal {expected_damage} damage; hit went {before} -> {ch.hit}"
        )

    def test_poison_tick_sends_shiver_message(self, capsys):
        """Poisoned character receives the 'You shiver and suffer' message."""
        from mud.game_loop import char_update, _send_to_char

        room = _make_room(9011)
        ch = _make_player(room)
        ch.position = int(Position.STANDING)
        ch.affected_by = int(AffectFlag.POISON)
        ch.messages = []

        af = AffectData(
            type="poison",
            level=5,
            duration=3,
            location="none",
            modifier=0,
            bitvector=int(AffectFlag.POISON),
        )
        ch.affected = [af]
        ch.desc = object()

        char_update()
        assert any("shiver" in m.lower() for m in ch.messages), (
            "Poisoned character should receive shiver message"
        )


# ---------------------------------------------------------------------------
# GL-013/GL-014: Incap/Mortal tick damage — ROM src/update.c:864-871
# ---------------------------------------------------------------------------

class TestIncapMortalTick:
    def test_incap_50pct_chance_deals_1_damage(self):
        """INCAP position: 50% RNG chance of 1 HP damage per tick."""
        from mud.game_loop import char_update

        room = _make_room(9020)
        ch = _make_player(room)
        ch.hit = 50
        ch.max_hit = 100
        ch.position = int(Position.INCAP)
        ch.desc = object()

        # Force RNG to roll 0 (deals damage) by seeding
        hits = 0
        trials = 20
        for _ in range(trials):
            ch.hit = 50
            rng_mm.seed_mm(0)  # seed that makes number_range(0,1)==0
            import mud.game_loop as gl
            original_range = rng_mm.number_range
            rng_mm.number_range = lambda lo, hi: 0  # always deal damage
            try:
                char_update()
            finally:
                rng_mm.number_range = original_range
            if ch.hit < 50:
                hits += 1
            break  # one trial is enough with forced roll

        assert ch.hit < 50, "INCAP with forced roll=0 should deal 1 HP damage"

    def test_mortal_always_deals_1_damage(self):
        """MORTAL position always takes 1 HP damage per tick."""
        from mud.game_loop import char_update

        room = _make_room(9021)
        ch = _make_player(room)
        ch.hit = 50
        ch.max_hit = 100
        ch.position = int(Position.MORTAL)
        ch.desc = object()

        before = ch.hit
        char_update()
        assert ch.hit < before, "MORTAL position should always take 1 HP damage per tick"


# ---------------------------------------------------------------------------
# GL-018: Pit-corpse decay message suppression — ROM src/update.c:1017-1018
# ---------------------------------------------------------------------------

class TestPitDecaySuppression:
    def test_decay_message_suppressed_inside_untakeable_pit(self):
        """Objects inside an untakeable pit (vnum 3010) suppress their decay message."""
        from mud.game_loop import _broadcast_decay
        from mud.models.constants import WearFlag
        from mud.models.obj import ObjIndex
        from mud.models.object import Object

        room = _make_room(9030)
        room.people = [_make_player(room)]

        # Create pit container (vnum 3010, not takeable — WearFlag.TAKE not set)
        pit_proto = ObjIndex(vnum=3010, name="the pit", short_descr="a large pit",
                             wear_flags=0)
        pit = Object(instance_id=3010, prototype=pit_proto)
        pit.in_room = room
        pit.wear_flags = 0  # not takeable

        # Create item inside pit
        proto = ObjIndex(vnum=100, name="a coin", short_descr="a gold coin",
                         wear_flags=int(WearFlag.TAKE))
        item = Object(instance_id=100, prototype=proto)
        item.in_room = room
        item.in_obj = pit

        import mud.game_loop as gl
        original = gl._message_room
        captured = []
        gl._message_room = lambda r, msg, **kw: captured.append(msg)
        try:
            _broadcast_decay(item, "$p crumbles into dust.")
        finally:
            gl._message_room = original

        assert len(captured) == 0, (
            "Decay message should be suppressed when item is inside an untakeable pit"
        )

    def test_decay_message_shown_inside_takeable_container(self):
        """Objects inside a takeable container DO show their decay message."""
        from mud.game_loop import _broadcast_decay
        from mud.models.constants import WearFlag
        from mud.models.obj import ObjIndex
        from mud.models.object import Object

        room = _make_room(9031)
        room.people = [_make_player(room)]

        # Takeable container (not vnum 3010)
        bag_proto = ObjIndex(vnum=200, name="a bag", short_descr="a bag",
                             wear_flags=int(WearFlag.TAKE))
        bag = Object(instance_id=200, prototype=bag_proto)
        bag.in_room = room
        bag.wear_flags = int(WearFlag.TAKE)

        proto = ObjIndex(vnum=101, name="a coin", short_descr="a gold coin",
                         wear_flags=int(WearFlag.TAKE))
        item = Object(instance_id=101, prototype=proto)
        item.in_room = room
        item.in_obj = bag

        import mud.game_loop as gl
        captured = []
        original = gl._message_room
        gl._message_room = lambda r, msg, **kw: captured.append(msg)
        try:
            _broadcast_decay(item, "$p crumbles into dust.")
        finally:
            gl._message_room = original

        assert len(captured) == 1, (
            "Decay message should be sent when item is inside a takeable container"
        )
