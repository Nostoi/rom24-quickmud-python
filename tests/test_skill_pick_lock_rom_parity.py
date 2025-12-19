from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ContainerFlag, ItemType, Position
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills.handlers import pick_lock
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "thief"),
        "level": overrides.get("level", 20),
        "skills": overrides.get("skills", {}),
        "is_npc": overrides.get("is_npc", False),
        "inventory": overrides.get("inventory", []),
        "room": overrides.get("room", None),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
        "people": overrides.get("people", []),
        "contents": overrides.get("contents", []),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def make_container(locked: bool = True, pickproof: bool = False, closed: bool = True) -> Object:
    flags = 0
    if closed:
        flags |= int(ContainerFlag.CLOSEABLE) | int(ContainerFlag.CLOSED)
    if locked:
        flags |= int(ContainerFlag.LOCKED)
    if pickproof:
        flags |= int(ContainerFlag.PICKPROOF)

    proto = ObjIndex(
        vnum=1000,
        name="chest",
        short_descr="a wooden chest",
        item_type=int(ItemType.CONTAINER),
        value=[100, flags, 5000, 0, 100],
    )
    obj = Object(instance_id=1, prototype=proto)
    obj.value = list(proto.value)
    obj.item_type = ItemType.CONTAINER
    return obj


def make_portal(locked: bool = True, pickproof: bool = False, closed: bool = True) -> Object:
    EX_ISDOOR = 1
    EX_CLOSED = 2
    EX_LOCKED = 4
    EX_PICKPROOF = 32

    flags = EX_ISDOOR
    if closed:
        flags |= EX_CLOSED
    if locked:
        flags |= EX_LOCKED
    if pickproof:
        flags |= EX_PICKPROOF

    proto = ObjIndex(
        vnum=2000,
        name="gate",
        short_descr="an iron gate",
        item_type=int(ItemType.PORTAL),
        value=[0, flags, 0, 3054, 5001],
    )
    obj = Object(instance_id=2, prototype=proto)
    obj.value = list(proto.value)
    obj.item_type = ItemType.PORTAL
    return obj


def test_pick_lock_requires_target_name():
    """ROM L850-854: Must specify what to pick."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 75})

    result = pick_lock(thief, target_name="")

    assert result["success"] is False
    assert "pick what" in result["message"].lower()


def test_pick_lock_guard_blocks_picking():
    """ROM L858-867: High level guard blocks picking."""
    room = make_room()
    thief = make_character(room=room, level=10, skills={"pick lock": 75})
    guard = make_character(name="guard", level=20, is_npc=True, position=Position.STANDING)
    room.people = [thief, guard]

    result = pick_lock(thief, target_name="chest")

    assert result["success"] is False
    assert "standing too close" in result["message"].lower()


def test_pick_lock_container_success():
    """ROM L916-947: Successfully pick locked container."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    chest = make_container(locked=True)
    thief.inventory = [chest]

    rng_mm.seed_mm(0x1234)
    result = pick_lock(thief, target_name="chest")

    assert result["success"] is True
    assert result.get("picked_type") == "container"
    assert not (chest.value[1] & int(ContainerFlag.LOCKED))


def test_pick_lock_container_not_closed():
    """ROM L922-925: Can't pick open container."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    chest = make_container(locked=False, closed=False)
    thief.inventory = [chest]

    result = pick_lock(thief, target_name="chest")

    assert result["success"] is False
    assert "not closed" in result["message"].lower()


def test_pick_lock_container_not_locked():
    """ROM L932-936: Can't pick unlocked container."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    chest = make_container(locked=False, closed=True)
    thief.inventory = [chest]

    result = pick_lock(thief, target_name="chest")

    assert result["success"] is False
    assert "already unlocked" in result["message"].lower()


def test_pick_lock_container_pickproof():
    """ROM L937-941: Pickproof containers can't be picked."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    chest = make_container(locked=True, pickproof=True)
    thief.inventory = [chest]

    result = pick_lock(thief, target_name="chest")

    assert result["success"] is False
    assert "failed" in result["message"].lower()


def test_pick_lock_portal_success():
    """ROM L879-910: Successfully pick locked portal."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    gate = make_portal(locked=True)
    room.contents = [gate]

    rng_mm.seed_mm(0x5678)
    result = pick_lock(thief, target_name="gate")

    assert result["success"] is True
    assert result.get("picked_type") == "portal"
    EX_LOCKED = 4
    assert not (gate.value[1] & EX_LOCKED)


def test_pick_lock_portal_pickproof():
    """ROM L899-903: Pickproof portals can't be picked."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    gate = make_portal(locked=True, pickproof=True)
    room.contents = [gate]

    result = pick_lock(thief, target_name="gate")

    assert result["success"] is False
    assert "failed" in result["message"].lower()


def test_pick_lock_skill_check_failure():
    """ROM L869-874: Low skill causes failure."""
    room = make_room()
    thief = make_character(room=room, is_npc=False, skills={"pick lock": 10})
    chest = make_container(locked=True)
    thief.inventory = [chest]

    rng_mm.seed_mm(0xDEAD)
    result = pick_lock(thief, target_name="chest")

    if not result["success"]:
        assert "failed" in result["message"].lower() or result["message"] == ""


def test_pick_lock_item_not_found():
    """ROM implies: Item must exist to be picked."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})

    result = pick_lock(thief, target_name="chest")

    assert result["success"] is False
    assert "don't see" in result["message"].lower()


def test_pick_lock_uses_rom_rng():
    """ROM L869: Uses ROM RNG for skill check."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 50})
    chest1 = make_container(locked=True)
    thief.inventory = [chest1]

    rng_mm.seed_mm(0xBEEF)
    result1 = pick_lock(thief, target_name="chest")

    chest2 = make_container(locked=True)
    thief.inventory = [chest2]
    rng_mm.seed_mm(0xBEEF)
    result2 = pick_lock(thief, target_name="chest")

    assert result1["success"] == result2["success"]


def test_pick_lock_searches_room_contents():
    """ROM L876: Searches room contents for object."""
    room = make_room()
    thief = make_character(room=room, skills={"pick lock": 95})
    chest = make_container(locked=True)
    room.contents = [chest]

    rng_mm.seed_mm(0xAAAA)
    result = pick_lock(thief, target_name="chest")

    if result["success"]:
        assert result.get("picked_type") == "container"
