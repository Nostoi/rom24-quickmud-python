import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import AffectFlag, ItemType, OBJ_VNUM_PORTAL, RoomFlag
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry, room_registry
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int, name: str, description: str = "") -> Room:
    return Room(vnum=vnum, name=name, description=description)


@pytest.fixture
def portal_prototype() -> ObjIndex:
    existing = obj_registry.get(OBJ_VNUM_PORTAL)
    prototype = ObjIndex(vnum=OBJ_VNUM_PORTAL, short_descr="a shimmering portal")
    obj_registry[OBJ_VNUM_PORTAL] = prototype
    yield prototype
    if existing is None:
        obj_registry.pop(OBJ_VNUM_PORTAL, None)
    else:
        obj_registry[OBJ_VNUM_PORTAL] = existing


def _register_room(room: Room) -> None:
    room_registry[room.vnum] = room


def _restore_room(vnum: int, previous: Room | None) -> None:
    if previous is None:
        room_registry.pop(vnum, None)
    else:
        room_registry[vnum] = previous


def test_gate_moves_caster_and_pet_with_room_checks() -> None:
    origin = _make_room(1000, "Circle of Warding")
    destination = _make_room(1001, "Hall of Mirrors", "Polished stone reflects endless images.")

    caster = Character(name="Sorcerer", level=45, is_npc=False)
    pet = Character(name="Wolf", level=30, is_npc=True)
    pet.master = caster
    caster.pet = pet

    target = Character(name="Ally", level=40, is_npc=False)
    observer = Character(name="Witness", level=20, is_npc=False)

    origin.add_character(caster)
    origin.add_character(pet)
    origin.add_character(observer)
    destination.add_character(target)

    caster.messages.clear()
    pet.messages.clear()
    observer.messages.clear()
    target.messages.clear()

    result = skill_handlers.gate(caster, target)

    assert result is True
    assert caster.room is destination
    assert pet.room is destination

    assert caster.messages[0] == "You step through a gate and vanish."
    assert "Hall of Mirrors" in caster.messages[1]
    assert "Polished stone reflects endless images." in caster.messages[1]

    # Pet first sees the caster's departure broadcast, then its own gate message
    assert pet.messages[0] == "Sorcerer steps through a gate and vanishes."
    assert pet.messages[1] == "You step through a gate and vanish."
    assert "Hall of Mirrors" in pet.messages[2]
    assert "Polished stone reflects endless images." in pet.messages[2]

    assert observer.messages[-2:] == [
        "Sorcerer steps through a gate and vanishes.",
        "Wolf steps through a gate and vanishes.",
    ]
    assert target.messages[-2:] == [
        "Sorcerer has arrived through a gate.",
        "Wolf has arrived through a gate.",
    ]


def test_gate_rejects_safe_room_or_clan_mismatch() -> None:
    origin = _make_room(2000, "Arcane Junction")
    safe_destination = _make_room(2001, "Sanctum", "A serene, warded chamber.")
    safe_destination.room_flags = int(RoomFlag.ROOM_SAFE)

    caster = Character(name="Invoker", level=35, clan=1, is_npc=False)
    target = Character(name="Rival", level=33, clan=2, is_npc=False)

    origin.add_character(caster)
    safe_destination.add_character(target)

    caster.messages.clear()

    result = skill_handlers.gate(caster, target)

    assert result is False
    assert caster.room is origin
    assert caster.messages[-1] == "You failed."


def test_portal_conjures_warp_stone_gateway(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3000, "Arcane Nexus")
    destination = _make_room(3001, "Crystal Spire")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Invoker", level=45, is_npc=False)
        target = Character(name="Scout", level=35, is_npc=False)
        observer = Character(name="Watcher", level=20, is_npc=False)

        origin.add_character(caster)
        origin.add_character(observer)
        destination.add_character(target)

        stone_proto = ObjIndex(vnum=4000, short_descr="a glittering warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()
        observer.messages.clear()

        portal_obj = skill_handlers.portal(caster, target)

        assert isinstance(portal_obj, Object)
        assert portal_obj in origin.contents
        assert portal_obj.location is origin
        assert portal_obj.value[3] == destination.vnum
        assert portal_obj.timer == 2 + c_div(caster.level, 25)
        assert caster.equipment.get("hold") is None
        assert warp_stone not in caster.inventory

        assert caster.messages[:3] == [
            "You draw upon the power of a glittering warp stone.",
            "It flares brightly and vanishes!",
            "a shimmering portal rises up before you.",
        ]
        assert observer.messages[-1] == "a shimmering portal rises up from the ground."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_portal_blocks_blind_caster_without_sight(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3150, "Shadowed Nexus")
    destination = _make_room(3151, "Hidden Landing")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Invoker", level=45, is_npc=False)
        target = Character(name="Scout", level=35, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        caster.add_affect(AffectFlag.BLIND)

        stone_proto = ObjIndex(vnum=4005, short_descr="a radiant warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()

        portal_obj = skill_handlers.portal(caster, target)

        assert portal_obj is None
        assert caster.equipment.get("hold") is warp_stone
        assert warp_stone not in caster.inventory
        assert caster.messages[-1] == "You failed."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_portal_blocks_forbidden_destinations(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3100, "Sanctuary Threshold")
    destination = _make_room(3101, "Wardstone Vault")
    destination.room_flags = int(RoomFlag.ROOM_SAFE)
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Invoker", level=40, is_npc=False)
        target = Character(name="Guardian", level=30, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        stone_proto = ObjIndex(vnum=4001, short_descr="a warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()

        result = skill_handlers.portal(caster, target)

        assert result is None
        assert caster.messages[-1] == "You failed."
        assert caster.equipment.get("hold") is warp_stone
        assert warp_stone in caster.inventory or warp_stone is caster.equipment.get("hold")
        assert origin.contents == []
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_portal_requires_warp_stone(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3110, "Portal Verge")
    destination = _make_room(3111, "Arcane Reach")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Invoker", level=45, is_npc=False)
        target = Character(name="Scout", level=35, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        caster.messages.clear()

        result = skill_handlers.portal(caster, target)

        assert result is None
        assert caster.messages[-1] == "You lack the proper component for this spell."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_nexus_creates_bidirectional_portals(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3200, "Crystal Atrium")
    destination = _make_room(3201, "Moonlit Terrace")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Archmage", level=50, is_npc=False)
        target = Character(name="Sentinel", level=40, is_npc=False)
        observer = Character(name="Witness", level=30, is_npc=False)

        origin.add_character(caster)
        origin.add_character(observer)
        destination.add_character(target)

        stone_proto = ObjIndex(vnum=4002, short_descr="a radiant warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()
        observer.messages.clear()
        target.messages.clear()

        portals = skill_handlers.nexus(caster, target)

        assert isinstance(portals, list) and len(portals) == 2
        outgoing, returning = portals
        assert outgoing.location is origin
        assert returning.location is destination
        assert outgoing.value[3] == destination.vnum
        assert returning.value[3] == origin.vnum
        assert outgoing.timer == 1 + c_div(caster.level, 10)
        assert returning.timer == 1 + c_div(caster.level, 10)
        assert caster.equipment.get("hold") is None

        assert caster.messages[:3] == [
            "You draw upon the power of a radiant warp stone.",
            "It flares brightly and vanishes!",
            "a shimmering portal rises up before you.",
        ]
        assert observer.messages[-1] == "a shimmering portal rises up from the ground."
        assert target.messages[-1] == "a shimmering portal rises up from the ground."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_nexus_requires_warp_stone(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3230, "Astral Gate")
    destination = _make_room(3231, "Echoing Hollow")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Archmage", level=50, is_npc=False)
        target = Character(name="Sentinel", level=40, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        caster.messages.clear()

        portals = skill_handlers.nexus(caster, target)

        assert portals == []
        assert caster.messages[-1] == "You lack the proper component for this spell."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_nexus_allows_private_origin_rooms(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3240, "Hidden Study")
    origin.room_flags = int(RoomFlag.ROOM_PRIVATE | RoomFlag.ROOM_SOLITARY)
    destination = _make_room(3241, "Moonlit Landing")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Archmage", level=50, is_npc=False)
        target = Character(name="Scout", level=40, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        stone_proto = ObjIndex(
            vnum=4004,
            short_descr="a radiant warp stone",
            item_type=int(ItemType.WARP_STONE),
        )
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        portals = skill_handlers.nexus(caster, target)

        assert isinstance(portals, list) and len(portals) == 2
        outgoing, returning = portals
        assert outgoing.location is origin
        assert returning.location is destination
        assert outgoing.value[3] == destination.vnum
        assert returning.value[3] == origin.vnum
        assert outgoing.timer == 1 + c_div(caster.level, 10)
        assert returning.timer == 1 + c_div(caster.level, 10)
        assert caster.equipment.get("hold") is None
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_nexus_blocks_blind_caster_without_sight(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3270, "Arcane Hall")
    destination = _make_room(3271, "Lightless Terrace")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Archmage", level=50, is_npc=False)
        target = Character(name="Scout", level=40, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        caster.add_affect(AffectFlag.BLIND)

        stone_proto = ObjIndex(vnum=4006, short_descr="a radiant warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()

        portals = skill_handlers.nexus(caster, target)

        assert portals == []
        assert caster.equipment.get("hold") is warp_stone
        assert warp_stone not in caster.inventory
        assert caster.messages[-1] == "You failed."
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)


def test_nexus_fails_when_origin_forbids_recall(portal_prototype: ObjIndex) -> None:
    origin = _make_room(3300, "Sanctified Hall")
    origin.room_flags = int(RoomFlag.ROOM_SAFE)
    destination = _make_room(3301, "Gateway Plaza")
    previous_origin = room_registry.get(origin.vnum)
    previous_destination = room_registry.get(destination.vnum)
    try:
        _register_room(origin)
        _register_room(destination)

        caster = Character(name="Archmage", level=45, is_npc=False)
        target = Character(name="Scout", level=30, is_npc=False)

        origin.add_character(caster)
        destination.add_character(target)

        stone_proto = ObjIndex(vnum=4003, short_descr="a warp stone", item_type=int(ItemType.WARP_STONE))
        warp_stone = Object(instance_id=None, prototype=stone_proto, item_type=ItemType.WARP_STONE)
        caster.add_object(warp_stone)
        caster.equip_object(warp_stone, "hold")

        caster.messages.clear()

        portals = skill_handlers.nexus(caster, target)

        assert portals == []
        assert caster.messages[-1] == "You failed."
        assert caster.equipment.get("hold") is warp_stone
        assert origin.contents == []
    finally:
        _restore_room(origin.vnum, previous_origin)
        _restore_room(destination.vnum, previous_destination)
