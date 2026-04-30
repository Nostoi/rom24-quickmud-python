"""OLC_ACT-013 — `_get_area_for_vnum` iterates areas in load order.

Mirrors ROM `src/olc_act.c:588-599` (`get_vnum_area`), which walks the
`area_first` linked list. Python's `area_registry` is a dict, but
CPython preserves insertion order (since 3.7), so iterating
`area_registry.values()` yields areas in load order — equivalent to
the ROM linked-list traversal.

These tests lock that equivalence so a future switch to a non-ordered
container (or a sort step in the loader) would surface as a regression.
"""

from __future__ import annotations

import pytest

from mud.commands.build import _get_area_for_vnum
from mud.models.area import Area
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _clean_area_registry():
    saved = dict(area_registry)
    area_registry.clear()
    try:
        yield
    finally:
        area_registry.clear()
        area_registry.update(saved)


def _make_area(vnum: int, name: str, min_vnum: int, max_vnum: int) -> Area:
    area = Area()
    area.vnum = vnum
    area.name = name
    area.min_vnum = min_vnum
    area.max_vnum = max_vnum
    return area


def test_get_area_for_vnum_returns_match():
    a = _make_area(1, "Alpha", 100, 199)
    b = _make_area(2, "Beta", 200, 299)
    area_registry[a.vnum] = a
    area_registry[b.vnum] = b

    assert _get_area_for_vnum(150) is a
    assert _get_area_for_vnum(250) is b
    assert _get_area_for_vnum(999) is None


def test_get_area_for_vnum_returns_first_match_in_load_order():
    """ROM `get_vnum_area` returns the first area in `area_first` order whose
    range contains the vnum. With overlapping ranges (which can occur in
    builder data), Python must return the earlier-inserted area to match
    ROM linked-list order."""
    first = _make_area(10, "FirstLoaded", 100, 200)
    second = _make_area(20, "SecondLoaded", 150, 250)  # overlaps 150-200

    area_registry[first.vnum] = first
    area_registry[second.vnum] = second

    # Vnum 175 is in both; ROM walks area_first → first match wins.
    assert _get_area_for_vnum(175) is first


def test_area_registry_iterates_in_insertion_order():
    """Locks the dict-insertion-order guarantee that makes `_get_area_for_vnum`
    equivalent to ROM's `area_first` chain walk."""
    vnums = [50, 10, 30, 20, 40]
    for v in vnums:
        area_registry[v] = _make_area(v, f"Area{v}", v * 100, v * 100 + 99)

    assert list(area_registry.keys()) == vnums
