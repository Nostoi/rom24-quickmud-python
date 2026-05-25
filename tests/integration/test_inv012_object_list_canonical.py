"""INV-012 OBJECT-LIST-CANONICAL enforcement.

ROM ref: src/handler.c:1626 obj_to_char, 1642 obj_from_char,
1904 obj_from_room, 1953 obj_to_room, 1968 obj_to_obj, 1996 obj_from_obj,
2051 extract_obj. ROM keeps a single global linked list (`object_list`)
of every OBJ_DATA instance; create_object appends, extract_obj removes
(recursively for contents).

Python contract (INV-012):

    Every Object returned by `spawn_object` appears in `object_registry`.
    `_extract_obj` removes it (recursively for nested contents).
    Container chains stay coherent with the registry.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-012.
"""

from __future__ import annotations

from mud.models.obj import ObjIndex
from mud.models.object import Object


def test_object_has_rom_named_fields_with_none_defaults():
    """Task 1a — Object exposes the ROM-named container fields."""
    proto = ObjIndex(vnum=93000, short_descr="a test object")
    obj = Object(instance_id=None, prototype=proto)
    # New dataclass fields (Commit 1a):
    assert obj.in_room is None
    assert obj.in_obj is None
    assert obj.carried_by is None


def test_pindexdata_aliases_prototype():
    """Task 1b — pIndexData is a property aliased to prototype."""
    proto = ObjIndex(vnum=93001, short_descr="another object")
    obj = Object(instance_id=None, prototype=proto)
    assert obj.pIndexData is obj.prototype
    assert obj.pIndexData is proto

    # Setter round-trips through prototype.
    new_proto = ObjIndex(vnum=93002, short_descr="replacement")
    obj.pIndexData = new_proto
    assert obj.prototype is new_proto


def test_contains_aliases_contained_items():
    """Task 1c — contains is a property returning contained_items."""
    proto = ObjIndex(vnum=93003, short_descr="a container")
    obj = Object(instance_id=None, prototype=proto)
    assert obj.contains is obj.contained_items
    assert obj.contains == []

    # Mutations through the underlying list are visible via the alias.
    child_proto = ObjIndex(vnum=93004, short_descr="a coin")
    child = Object(instance_id=None, prototype=child_proto)
    obj.contained_items.append(child)
    assert obj.contains == [child]


def test_spawn_appends_to_registry():
    """Task 2 — every spawn_object appends to object_registry."""
    from mud.models.obj import object_registry
    from mud.registry import obj_registry
    from mud.spawning.obj_spawner import spawn_object

    obj_registry[93010] = ObjIndex(vnum=93010, short_descr="a stone", item_type=1)
    inst = None
    try:
        before = len(object_registry)
        inst = spawn_object(93010)
        assert inst is not None
        assert inst in object_registry
        assert len(object_registry) == before + 1
    finally:
        if inst is not None and inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93010, None)


def test_extract_removes_from_registry():
    """Task 2 — _extract_obj drains the registry."""
    from mud.game_loop import _extract_obj
    from mud.models.obj import object_registry
    from mud.registry import obj_registry
    from mud.spawning.obj_spawner import spawn_object

    obj_registry[93011] = ObjIndex(vnum=93011, short_descr="a doomed thing", item_type=1)
    try:
        inst = spawn_object(93011)
        assert inst in object_registry
        _extract_obj(inst)
        assert inst not in object_registry
    finally:
        obj_registry.pop(93011, None)


def test_extract_recursively_removes_nested_contents():
    """Task 2 — _extract_obj on a container also drains its contents
    (ROM extract_obj recursion at src/handler.c:2063-2067)."""
    from mud.game_loop import _extract_obj
    from mud.models.obj import object_registry
    from mud.registry import obj_registry
    from mud.spawning.obj_spawner import spawn_object

    obj_registry[93012] = ObjIndex(vnum=93012, short_descr="a sack", item_type=15)
    obj_registry[93013] = ObjIndex(vnum=93013, short_descr="a coin", item_type=20)
    try:
        sack = spawn_object(93012)
        coin = spawn_object(93013)
        sack.contained_items.append(coin)
        coin.in_obj = sack

        assert sack in object_registry
        assert coin in object_registry

        _extract_obj(sack)

        assert sack not in object_registry
        assert coin not in object_registry, (
            "extract_obj must recurse into contents (src/handler.c:2063-2067)"
        )
    finally:
        obj_registry.pop(93012, None)
        obj_registry.pop(93013, None)


def test_get_obj_world_smoke_finds_spawned_object():
    """Task 2 smoke — locate-object plumbing returns a real spawned
    object. Was previously a no-op because object_registry was empty.
    """
    from mud.models.character import Character
    from mud.models.obj import object_registry
    from mud.registry import obj_registry
    from mud.spawning.obj_spawner import spawn_object
    from mud.world.obj_find import get_obj_world

    obj_registry[93014] = ObjIndex(
        vnum=93014,
        name="findme uniquekeyword",
        short_descr="a uniquely-named widget",
        item_type=1,
    )
    inst = None
    try:
        inst = spawn_object(93014)
        looker = Character(name="Watcher", level=60)
        hit = get_obj_world(looker, "uniquekeyword")
        assert hit is inst, "get_obj_world must find spawned objects via object_registry"
    finally:
        if inst is not None and inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93014, None)


def test_obj_update_smoke_decrements_timer_on_spawned_object():
    """Task 2 smoke — object decay tick iterates object_registry and
    decrements timers on spawned objects. Previously no-op.

    Note: the function is mud.game_loop.obj_update (NOT object_update).
    """
    from mud.game_loop import obj_update
    from mud.models.obj import object_registry
    from mud.registry import obj_registry
    from mud.spawning.obj_spawner import spawn_object

    obj_registry[93015] = ObjIndex(vnum=93015, short_descr="a fading thing", item_type=1)
    inst = None
    try:
        inst = spawn_object(93015)
        inst.timer = 3

        obj_update()

        assert inst.timer == 2, (
            f"obj_update must decrement timers on spawned objects; got {inst.timer}"
        )
    finally:
        if inst is not None and inst in object_registry:
            object_registry.remove(inst)
        obj_registry.pop(93015, None)
