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
