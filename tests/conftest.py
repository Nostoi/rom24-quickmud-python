import pytest
from helpers import ensure_can_move as _ensure_can_move_helper


@pytest.fixture
def ensure_can_move():
    """Callable fixture to provision movement points on a character-like entity.

    Usage: ensure_can_move(char[, points])
    """
    return _ensure_can_move_helper


@pytest.fixture
def movable_char_factory():
    """Factory fixture that creates a test character with movement set.

    Example:
        ch = movable_char_factory('Tester', 3001, points=200)
    """
    from mud.world import create_test_character

    def _factory(name: str, room_vnum: int, *, points: int = 100):
        ch = create_test_character(name, room_vnum)
        _ensure_can_move_helper(ch, points)
        return ch

    return _factory


@pytest.fixture
def movable_mob_factory():
    """Factory fixture that spawns a mob and ensures it can move.

    Example:
        mob = movable_mob_factory(3000, 3001, points=150)
    """
    from mud.registry import room_registry
    from mud.spawning.mob_spawner import spawn_mob

    def _factory(vnum: int, room_vnum: int, *, points: int = 100):
        mob = spawn_mob(vnum)
        room = room_registry[room_vnum]
        room.add_mob(mob)
        _ensure_can_move_helper(mob, points)
        return mob

    return _factory


@pytest.fixture
def place_object_factory():
    """Factory that places an object in a room.

    Usage:
        obj = place_object_factory(room_vnum=3001, vnum=3031)
        obj = place_object_factory(room_vnum=3001, proto_kwargs={"vnum": 9999, "short_descr": "a stone"})
    """
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.registry import room_registry
    from mud.spawning.obj_spawner import spawn_object

    def _factory(*, room_vnum: int, vnum: int | None = None, proto_kwargs: dict | None = None):
        room = room_registry[room_vnum]
        if vnum is not None:
            obj = spawn_object(vnum)
            assert obj is not None
        else:
            proto_kwargs = proto_kwargs or {}
            proto = ObjIndex(**proto_kwargs)
            obj = Object(instance_id=None, prototype=proto)
        room.add_object(obj)
        return obj

    return _factory


@pytest.fixture
def object_factory():
    """Factory that returns an object instance without placing it in a room.

    Usage:
        obj = object_factory({"vnum": 9999, "short_descr": "a stone"})
    """
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    def _factory(proto_kwargs: dict):
        proto = ObjIndex(**proto_kwargs)
        return Object(instance_id=None, prototype=proto)

    return _factory


@pytest.fixture
def inventory_object_factory():
    """Factory that spawns a ROM object by vnum for inventory use.

    Wraps spawn_object(vnum) for clarity in tests.
    """
    from mud.spawning.obj_spawner import spawn_object

    def _factory(vnum: int):
        obj = spawn_object(vnum)
        assert obj is not None
        return obj

    return _factory


@pytest.fixture
def portal_factory(place_object_factory):
    """Convenience to create a portal object in a room.

    Example:
        portal_factory(3001, to_vnum=3054, closed=True)
    """
    from mud.models.constants import EX_CLOSED, ItemType

    def _factory(
        room_vnum: int,
        *,
        to_vnum: int,
        closed: bool = False,
        gate_flags: int = 0,
        charges: int = 1,
    ):
        flags = EX_CLOSED if closed else 0
        obj = place_object_factory(
            room_vnum=room_vnum,
            proto_kwargs={
                "vnum": 9998,
                "name": "shimmering portal",
                "short_descr": "a shimmering portal",
                "item_type": int(ItemType.PORTAL),
            },
        )
        # ROM portal values: [charges, exit_flags, portal_flags, to_vnum, placeholder]
        values = [charges, flags, gate_flags, to_vnum, 0]
        obj.prototype.value = values.copy()
        if hasattr(obj, "value"):
            obj.value = values.copy()
        return obj

    return _factory
