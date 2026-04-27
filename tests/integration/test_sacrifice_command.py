"""Integration tests for do_sacrifice() ROM parity (SAC-001 .. SAC-005).

ROM Reference: src/act_obj.c lines 1765-1862 (do_sacrifice).
"""
from __future__ import annotations

import pytest

from mud.commands.obj_manipulation import do_sacrifice
from mud.models.character import Character
from mud.models.constants import ItemType, PlayerFlag, WearFlag
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clear_registries():
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_room() -> Room:
    room = Room(vnum=3001, name="Test Room", description="A test room.")
    room_registry[3001] = room
    return room


@pytest.fixture
def actor(test_room) -> Character:
    char = create_test_character("Tester", room_vnum=3001)
    char.silver = 0
    char.is_npc = False
    return char


def _make_sacrificeable_obj(object_factory, *, vnum: int = 9001, name: str = "sword",
                             short_descr: str = "a rusty sword", level: int = 5,
                             cost: int = 30, item_type: ItemType = ItemType.WEAPON):
    """Create a basic object that can be sacrificed (TAKE flag set)."""
    obj = object_factory({
        "vnum": vnum,
        "name": name,
        "short_descr": short_descr,
        "item_type": int(item_type),
        "value": [0, 0, 0, 0, 0],
        "level": level,
    })
    obj.item_type = int(item_type)
    obj.level = level
    obj.cost = cost
    obj.wear_flags = int(WearFlag.TAKE)  # SAC-003: must use enum, not hardcoded hex
    return obj


# ---------------------------------------------------------------------------
# SAC-001: TO_ROOM broadcast on normal sacrifice
# ---------------------------------------------------------------------------

def test_sacrifice_broadcasts_to_room(test_room, actor, object_factory):
    """SAC-001: observer in the same room sees '$n sacrifices $p to Mota.'

    ROM src/act_obj.c:1856: act("$n sacrifices $p to Mota.", ch, obj, NULL, TO_ROOM)
    """
    obj = _make_sacrificeable_obj(object_factory, short_descr="a rusty sword")
    test_room.contents.append(obj)
    obj.location = test_room

    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    result = do_sacrifice(actor, "sword")

    assert "silver" in result.lower(), f"Actor should receive silver; got: {result!r}"
    combined = " ".join(observer.messages)
    assert "sacrifices" in combined and "mota" in combined.lower(), (
        f"Observer should see sacrifice broadcast; got: {observer.messages!r}"
    )


# ---------------------------------------------------------------------------
# SAC-002: TO_ROOM broadcast on self-sacrifice
# ---------------------------------------------------------------------------

def test_sacrifice_self_broadcasts_to_room(test_room, actor, object_factory):
    """SAC-002: observer sees '$n offers <self> to Mota, who graciously declines.'

    ROM src/act_obj.c:1782-1783: act("$n offers $mself to Mota, who graciously declines.",
                                     ch, NULL, NULL, TO_ROOM)
    """
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    # Empty arg triggers self-sacrifice path
    result = do_sacrifice(actor, "")

    assert "mota appreciates" in result.lower(), f"Actor msg wrong; got: {result!r}"
    combined = " ".join(observer.messages)
    assert "offers" in combined and "mota" in combined.lower() and "declines" in combined.lower(), (
        f"Observer should see self-sacrifice broadcast; got: {observer.messages!r}"
    )


def test_sacrifice_self_by_name_broadcasts_to_room(test_room, actor):
    """SAC-002: using own name as arg also triggers self-sacrifice broadcast."""
    observer = create_test_character("Observer", room_vnum=3001)
    observer.messages = []

    result = do_sacrifice(actor, "Tester")

    assert "mota appreciates" in result.lower()
    combined = " ".join(observer.messages)
    assert "offers" in combined and "declines" in combined.lower(), (
        f"Observer should see self-sacrifice broadcast; got: {observer.messages!r}"
    )


# ---------------------------------------------------------------------------
# SAC-003: NO_SAC flag rejects item
# ---------------------------------------------------------------------------

def test_sacrifice_no_sac_item_rejected(test_room, actor, object_factory):
    """SAC-003: item with WearFlag.NO_SAC is rejected with correct ROM message.

    ROM src/act_obj.c:1806: if (!CAN_WEAR(obj, ITEM_TAKE) || CAN_WEAR(obj, ITEM_NO_SAC))
    WearFlag.NO_SAC = 1 << 15 = 32768 (not 0x4000 = 16384 which was the old wrong value).
    """
    obj = _make_sacrificeable_obj(object_factory, short_descr="a blessed relic")
    # Set NO_SAC flag using the correct enum (1 << 15)
    obj.wear_flags = int(WearFlag.TAKE) | int(WearFlag.NO_SAC)
    test_room.contents.append(obj)
    obj.location = test_room

    result = do_sacrifice(actor, "relic")

    assert "not an acceptable sacrifice" in result.lower(), (
        f"Expected rejection message; got: {result!r}"
    )
    assert actor.silver == 0, "Silver should not be granted for a NO_SAC item"


# ---------------------------------------------------------------------------
# SAC-004: AUTOSPLIT with group members splits silver
# ---------------------------------------------------------------------------

def test_sacrifice_autosplit_with_group(test_room, actor, object_factory, movable_char_factory):
    """SAC-004: PlayerFlag.AUTOSPLIT + 2+ group members causes silver to split.

    ROM src/act_obj.c:1840-1853: IS_SET(ch->act, PLR_AUTOSPLIT) check.
    PLR_AUTOSPLIT = 1 << 7 = 128 (not 0x00002000 which was the old wrong value).
    """
    # Level 10 object: silver = max(1, 10*3) = 30, cost=100 => min(30,100) = 30
    obj = _make_sacrificeable_obj(object_factory, short_descr="a silver dagger",
                                  level=10, cost=100)
    test_room.contents.append(obj)
    obj.location = test_room

    # Enable AUTOSPLIT using the enum (1 << 7 = 128)
    actor.act = int(PlayerFlag.AUTOSPLIT)
    actor.silver = 0

    follower = movable_char_factory(name="Follower", room_vnum=3001)
    follower.silver = 0
    follower.leader = actor
    follower.master = actor
    actor.group_members = [actor, follower]
    follower.group_members = [actor, follower]

    result = do_sacrifice(actor, "dagger")

    assert "silver" in result.lower(), f"Actor should get silver msg; got: {result!r}"
    # After autosplit of 30 silver between 2 members, actor should have 15 (split gives each 15)
    assert actor.silver < 30, (
        f"AUTOSPLIT should have reduced actor silver below 30; got {actor.silver}"
    )
    assert follower.silver > 0, (
        f"Follower should have received split silver; got {follower.silver}"
    )


# ---------------------------------------------------------------------------
# SAC-005: Zero-cost non-corpse gives zero silver
# ---------------------------------------------------------------------------

def test_sacrifice_zero_cost_non_corpse_gives_zero_silver(test_room, actor, object_factory):
    """SAC-005: UMIN(silver, obj->cost) is unconditional — zero cost gives 0 silver.

    ROM src/act_obj.c:1825: silver = UMIN(silver, obj->cost); (no obj_cost > 0 guard).
    Old Python code had 'if obj_cost > 0' guard which wrongly gave level*3 silver.
    """
    # Level 10 gives silver=30 before cap; cost=0 => min(30, 0) = 0
    obj = _make_sacrificeable_obj(object_factory, short_descr="a worthless trinket",
                                  level=10, cost=0)
    test_room.contents.append(obj)
    obj.location = test_room

    result = do_sacrifice(actor, "trinket")

    # ROM gives 0 silver (UMIN caps it), so message says "one silver coin" only if silver==1
    # With cost=0 and silver capped at 0, ROM actually gives max(1, level*3) capped to 0 = 0
    # The TO_CHAR message in ROM is only sent after silver is calculated, and silver=0
    # means ROM says "one silver coin" only when silver==1. silver=0 is an edge case.
    # The key invariant: actor.silver should be 0 (not 30).
    assert actor.silver == 0, (
        f"Zero-cost non-corpse should yield 0 silver (SAC-005); got {actor.silver}"
    )
