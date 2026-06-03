"""INV-021 — OBJECT-EXTRACT-RECURSIVE.

ROM ``src/handler.c:2052-2086 extract_obj`` recursively extracts
every item in ``obj->contains`` BEFORE removing the outer object
from the global ``object_list``. Otherwise contained items would
remain in the world-scan registry — visible to
``spell_locate_object`` (``src/magic.c:3737``), persisted by save,
counted by area sweeps — even though their carrier/room/parent
container has been freed.

The contract spans three modules:

- ``mud/spawning/obj_spawner.py:spawn_object`` (registers every new
  Object into ``mud.models.obj.object_registry``) — see INV-014.
- ``mud/game_loop.py:_extract_obj`` — the recursive extractor.
- ``mud/models/obj.py:object_registry`` — the canonical list every
  world-scan iterates.

INV-014 already pins "every new Object lands in the registry";
this row pins the dual: "every extract drains the registry, all
the way down".
"""

from __future__ import annotations

import pytest

from mud.game_loop import _extract_obj
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object


def _is_in_registry(obj: Object) -> bool:
    """Identity check — dataclass equality is field-deep on Object."""
    return any(o is obj for o in object_registry)


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(object_registry)
    object_registry.clear()
    yield
    object_registry.clear()
    object_registry.extend(snapshot)


def _make_obj(name: str) -> Object:
    proto = ObjIndex(vnum=8000, short_descr=name)
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = name
    object_registry.append(obj)
    return obj


def test_inv021_extract_obj_removes_container_and_all_contents():
    """ROM src/handler.c:2063-2067 — extract_obj recurses into ->contains."""
    container = _make_obj("sack")
    item_a = _make_obj("apple")
    item_b = _make_obj("biscuit")

    container.contained_items.extend([item_a, item_b])
    item_a.in_obj = container
    item_b.in_obj = container

    assert _is_in_registry(container)
    assert _is_in_registry(item_a)
    assert _is_in_registry(item_b)

    _extract_obj(container)

    assert not _is_in_registry(container), "container must leave the registry"
    assert not _is_in_registry(item_a), (
        "nested item must be recursively extracted from object_registry (ROM src/handler.c:2063-2067)"
    )
    assert not _is_in_registry(item_b), "nested item must be recursively extracted"


def test_inv021_extract_obj_recurses_to_arbitrary_depth():
    """A container inside a container inside a container — all three drain."""
    outer = _make_obj("outer")
    middle = _make_obj("middle")
    inner = _make_obj("inner")
    leaf = _make_obj("leaf")

    outer.contained_items.append(middle)
    middle.in_obj = outer
    middle.contained_items.append(inner)
    inner.in_obj = middle
    inner.contained_items.append(leaf)
    leaf.in_obj = inner

    _extract_obj(outer)

    for o in (outer, middle, inner, leaf):
        assert not _is_in_registry(o), f"{o.short_descr!r} must be recursively extracted (depth-N nesting)"
