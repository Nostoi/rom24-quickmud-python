from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import (
    LEVEL_IMMORTAL,
    OBJ_VNUM_DISC,
    OBJ_VNUM_PORTAL,
    ActFlag,
    AffectFlag,
    DamageType,
    ExtraFlag,
    ItemType,
    PlayerFlag,
    Position,
    RoomFlag,
    WearLocation,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry, room_registry
from mud.skills.handlers import floating_disc, gate, nexus, portal, summon
from mud.utils import rng_mm
from mud.world.movement import move_character_through_portal


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
        "room_flags": overrides.get("room_flags", 0),
        "light": overrides.get("light", 0),
        "sector_type": overrides.get("sector_type", 0),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "player"),
        "level": overrides.get("level", 30),
        "trust": overrides.get("trust", 0),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", int(Position.STANDING)),
        "is_npc": overrides.get("is_npc", False),
        "act": overrides.get("act", 0),
        "affected_by": overrides.get("affected_by", 0),
        "saving_throw": overrides.get("saving_throw", 0),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)

    room = getattr(char, "room", None)
    if isinstance(room, Room) and char not in room.people:
        room.add_character(char)

    return char


def _install_object_prototypes() -> None:
    obj_registry[OBJ_VNUM_PORTAL] = ObjIndex(
        vnum=OBJ_VNUM_PORTAL,
        name="portal",
        short_descr="a shimmering portal",
        description="a shimmering portal",
        item_type=int(ItemType.PORTAL),
        value=[0, 0, 0, 0, 0],
        weight=0,
        cost=0,
        level=0,
    )

    obj_registry[OBJ_VNUM_DISC] = ObjIndex(
        vnum=OBJ_VNUM_DISC,
        name="floating disc",
        short_descr="a floating black disc",
        description="a floating black disc",
        item_type=int(ItemType.CONTAINER),
        value=[0, 0, 0, 0, 100],
        weight=0,
        cost=0,
        level=0,
    )


def _make_warp_stone(*, vnum: int = 9999) -> Object:
    proto = ObjIndex(
        vnum=vnum,
        name="warp stone",
        short_descr="a warp stone",
        description="a warp stone",
        item_type=int(ItemType.WARP_STONE),
        value=[0, 0, 0, 0, 0],
        weight=0,
        cost=0,
        level=0,
    )
    stone = Object(instance_id=None, prototype=proto)
    stone.item_type = int(ItemType.WARP_STONE)
    return stone


def _make_floating_item(*, extra_flags: int = 0, vnum: int = 9997) -> Object:
    proto = ObjIndex(
        vnum=vnum,
        name="floating thing",
        short_descr="a floating thing",
        description="a floating thing",
        item_type=int(ItemType.CONTAINER),
        extra_flags=extra_flags,
        value=[0, 0, 0, 0, 0],
        weight=0,
        cost=0,
        level=0,
    )
    obj = Object(instance_id=None, prototype=proto)
    obj.extra_flags = extra_flags
    return obj


@pytest.fixture(autouse=True)
def _seed_and_sandbox_registries():
    rng_mm.seed_mm(42)

    saved_rooms = dict(room_registry)
    saved_objs = dict(obj_registry)
    room_registry.clear()
    obj_registry.clear()
    _install_object_prototypes()

    try:
        yield
    finally:
        room_registry.clear()
        room_registry.update(saved_rooms)
        obj_registry.clear()
        obj_registry.update(saved_objs)


def test_gate_moves_caster_to_target_room_and_sets_was_in_room():
    start = make_room(vnum=1001, name="Start")
    dest = make_room(vnum=1002, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", room=start)
    target = make_character(name="Target", room=dest)

    target.messages.clear()
    caster.messages.clear()

    result = gate(caster, target)

    assert result is True
    assert caster.room is dest
    assert caster.was_in_room is start
    assert any("step through a gate" in msg.lower() for msg in caster.messages)
    assert any("arrived through a gate" in msg.lower() for msg in target.messages)


def test_gate_moves_pet_along_if_pet_in_same_room():
    start = make_room(vnum=1011, name="Start")
    dest = make_room(vnum=1012, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", room=start)
    target = make_character(name="Target", room=dest)
    pet = make_character(name="Pet", is_npc=True, room=start)
    caster.pet = pet

    result = gate(caster, target)

    assert result is True
    assert caster.room is dest
    assert pet.room is dest
    assert pet.was_in_room is start


def test_gate_blocked_by_room_no_recall_on_target_room():
    start = make_room(vnum=1021, name="Start")
    dest = make_room(vnum=1022, name="Destination", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", room=start)
    target = make_character(name="Target", room=dest)

    caster.messages.clear()

    result = gate(caster, target)

    assert result is False
    assert caster.room is start
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_gate_blocked_by_room_no_recall_on_caster_room():
    start = make_room(vnum=1031, name="Start", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    dest = make_room(vnum=1032, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", room=start)
    target = make_character(name="Target", room=dest)

    caster.messages.clear()

    result = gate(caster, target)

    assert result is False
    assert caster.room is start
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_portal_requires_warp_stone_for_mortals():
    start = make_room(vnum=2001, name="Start")
    dest = make_room(vnum=2002, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    caster.messages.clear()

    created = portal(caster, target)

    assert created is None
    assert start.contents == []
    assert any("lack the proper component" in msg.lower() for msg in caster.messages)


def test_portal_creates_portal_object_and_consumes_warp_stone():
    start = make_room(vnum=2011, name="Start")
    dest = make_room(vnum=2012, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    caster.messages.clear()

    created = portal(caster, target)

    assert isinstance(created, Object)
    assert created in start.contents
    assert int(created.value[3]) == dest.vnum
    assert caster.equipment.get("hold") is None
    assert all("warp stone" not in getattr(obj, "name", "") for obj in caster.equipment.values())
    assert any("rises up" in msg.lower() for msg in caster.messages)


def test_portal_blocked_by_room_no_recall_on_target_room_and_does_not_consume_component():
    start = make_room(vnum=2021, name="Start")
    dest = make_room(vnum=2022, name="Destination", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    caster.messages.clear()

    created = portal(caster, target)

    assert created is None
    assert caster.equipment.get("hold") is stone
    assert start.contents == []
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_portal_blocked_by_room_no_recall_on_caster_room_and_does_not_consume_component():
    start = make_room(vnum=2031, name="Start", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    dest = make_room(vnum=2032, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    caster.messages.clear()

    created = portal(caster, target)

    assert created is None
    assert caster.equipment.get("hold") is stone
    assert start.contents == []
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_portal_allows_room_movement_via_enter_portal_logic():
    start = make_room(vnum=2041, name="Start")
    dest = make_room(vnum=2042, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    portal_obj = portal(caster, target)
    assert portal_obj is not None
    assert caster.room is start

    out = move_character_through_portal(caster, portal_obj)

    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert caster.room is dest


def test_nexus_requires_warp_stone_for_mortals():
    start = make_room(vnum=3001, name="Start")
    dest = make_room(vnum=3002, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    caster.messages.clear()

    created = nexus(caster, target)

    assert created == []
    assert any("lack the proper component" in msg.lower() for msg in caster.messages)


def test_nexus_creates_two_portals_and_consumes_warp_stone():
    start = make_room(vnum=3011, name="Start")
    dest = make_room(vnum=3012, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    created = nexus(caster, target)

    assert len(created) == 2
    assert caster.equipment.get("hold") is None

    out_portal = next(obj for obj in start.contents if isinstance(obj, Object))
    return_portal = next(obj for obj in dest.contents if isinstance(obj, Object))

    assert int(out_portal.value[3]) == dest.vnum
    assert int(return_portal.value[3]) == start.vnum


def test_nexus_blocked_by_room_no_recall_on_target_room_and_does_not_consume_component():
    start = make_room(vnum=3021, name="Start")
    dest = make_room(vnum=3022, name="Destination", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    caster.messages.clear()

    created = nexus(caster, target)

    assert created == []
    assert caster.equipment.get("hold") is stone
    assert start.contents == []
    assert dest.contents == []
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_nexus_allows_two_way_room_travel_through_created_portals():
    start = make_room(vnum=3031, name="Start")
    dest = make_room(vnum=3032, name="Destination")
    room_registry[start.vnum] = start
    room_registry[dest.vnum] = dest

    caster = make_character(name="Caster", level=30, trust=0, room=start)
    target = make_character(name="Target", room=dest)

    stone = _make_warp_stone()
    caster.add_object(stone)
    caster.equip_object(stone, "hold")

    created = nexus(caster, target)
    assert len(created) == 2

    out_portal = next(obj for obj in start.contents if isinstance(obj, Object))
    return_portal = next(obj for obj in dest.contents if isinstance(obj, Object))

    out = move_character_through_portal(caster, out_portal)
    assert caster.room is dest
    assert "somewhere else" in out.lower()

    back = move_character_through_portal(caster, return_portal)
    assert caster.room is start
    assert "somewhere else" in back.lower()


def test_summon_success_moves_target_to_caster_room_and_sends_message():
    caster_room = make_room(vnum=4001, name="Caster Room")
    target_room = make_room(vnum=4002, name="Target Room")
    room_registry[caster_room.vnum] = caster_room
    room_registry[target_room.vnum] = target_room

    caster = make_character(name="Caster", level=50, room=caster_room)
    victim = make_character(name="Victim", is_npc=True, level=10, saving_throw=0, room=target_room)

    caster.messages.clear()
    victim.messages.clear()

    result = summon(caster, victim)

    assert result is True
    assert victim.room is caster_room
    assert any("has summoned you" in msg.lower() for msg in victim.messages)


def test_summon_blocked_by_room_no_recall_on_target_room():
    caster_room = make_room(vnum=4011, name="Caster Room")
    target_room = make_room(vnum=4012, name="Target Room", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    room_registry[caster_room.vnum] = caster_room
    room_registry[target_room.vnum] = target_room

    caster = make_character(name="Caster", level=50, room=caster_room)
    victim = make_character(name="Victim", is_npc=True, level=10, room=target_room)

    result = summon(caster, victim)

    assert result is False
    assert victim.room is target_room


def test_summon_save_mechanics_blocks_summon_when_target_succeeds_save():
    caster_room = make_room(vnum=4021, name="Caster Room")
    target_room = make_room(vnum=4022, name="Target Room")
    room_registry[caster_room.vnum] = caster_room
    room_registry[target_room.vnum] = target_room

    caster = make_character(name="Caster", level=50, room=caster_room)
    # With seed_mm(42), first number_percent() is 23. Force save >= 24 via strong (negative) saving throw.
    victim = make_character(
        name="Victim",
        is_npc=True,
        level=10,
        saving_throw=-100,
        room=target_room,
    )

    caster.messages.clear()

    result = summon(caster, victim)

    assert result is False
    assert victim.room is target_room
    assert any("you failed" in msg.lower() for msg in caster.messages)


def test_summon_blocked_by_nosummon_player_flag():
    caster_room = make_room(vnum=4031, name="Caster Room")
    target_room = make_room(vnum=4032, name="Target Room")
    room_registry[caster_room.vnum] = caster_room
    room_registry[target_room.vnum] = target_room

    caster = make_character(name="Caster", level=50, room=caster_room)
    victim = make_character(
        name="Victim",
        is_npc=False,
        level=10,
        act=int(PlayerFlag.NOSUMMON),
        room=target_room,
    )

    result = summon(caster, victim)

    assert result is False
    assert victim.room is target_room


def test_floating_disc_creates_disc_and_equips_float_slot():
    room = make_room(vnum=5001, name="Room")
    room_registry[room.vnum] = room

    caster = make_character(name="Caster", level=25, room=room)
    caster.messages.clear()

    disc = floating_disc(caster)

    assert isinstance(disc, Object)
    assert caster.equipment.get("float") is disc
    assert disc.wear_loc == int(WearLocation.FLOAT)
    assert disc.value[0] == 25 * 10
    assert disc.value[3] == 25 * 5
    assert any("create a floating disc" in msg.lower() for msg in caster.messages)


def test_floating_disc_replaces_existing_float_item_puts_old_in_inventory():
    room = make_room(vnum=5011, name="Room")
    room_registry[room.vnum] = room

    caster = make_character(name="Caster", level=25, room=room)

    old_float = _make_floating_item(extra_flags=0)
    caster.add_object(old_float)
    caster.equip_object(old_float, "float")

    disc = floating_disc(caster)

    assert disc is not False
    assert caster.equipment.get("float") is disc
    assert old_float in caster.inventory


def test_floating_disc_blocked_when_existing_float_item_is_noremove():
    room = make_room(vnum=5021, name="Room")
    room_registry[room.vnum] = room

    caster = make_character(name="Caster", level=25, room=room)

    old_float = _make_floating_item(extra_flags=int(ExtraFlag.NOREMOVE))
    caster.add_object(old_float)
    caster.equip_object(old_float, "float")

    caster.messages.clear()

    result = floating_disc(caster)

    assert result is False
    assert caster.equipment.get("float") is old_float
    assert any("can't remove" in msg.lower() for msg in caster.messages)


def test_floating_disc_replaces_both_float_and_floating_alias_slots():
    room = make_room(vnum=5031, name="Room")
    room_registry[room.vnum] = room

    caster = make_character(name="Caster", level=25, room=room)

    old_float = _make_floating_item(extra_flags=0, vnum=9991)
    old_floating = _make_floating_item(extra_flags=0, vnum=9992)
    caster.equipment["float"] = old_float
    caster.equipment["floating"] = old_floating

    disc = floating_disc(caster)

    assert disc is not False
    assert caster.equipment.get("float") is disc
    assert "floating" not in caster.equipment
    assert old_float in caster.inventory
