"""OLC_SAVE-007 — object affect chain persisted with structured fields.

Mirrors ROM src/olc_save.c:399-429 (save_object affect emission). ROM
emits two distinct affect rows:

- ``A`` (TO_OBJECT applies): ``location`` + ``modifier``.
- ``F`` (TO_AFFECTS/IMMUNE/RESIST/VULN): ``where`` + ``location`` +
  ``modifier`` + ``bitvector``.

Python's prototype affect-list is heterogeneous — `mud/loaders/obj_loader.py`
populates ``obj.affects`` with either 2-field dicts (A-line) or 4-field
dicts including ``where``/``bitvector`` (F-line). The previous JSON
serialization did `list(...affects, [])` raw pass-through, which works
for plain dicts but silently drops fields if anything stores ``Affect``
dataclass instances in the prototype list (and breaks ``json.dump``
outright on dataclass values).

This closure formalizes the shape: emit a normalized affect dict via a
new ``_serialize_affect`` helper that accepts either a dict or an
``Affect`` instance, fills missing keys with ROM defaults, and survives
``json.dump`` either way. The loader continues to accept raw dicts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area
from mud.models.obj import Affect, ObjIndex, obj_index_registry
from mud.olc.save import _serialize_affect, save_area_to_json
from mud.registry import area_registry, obj_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_obj = dict(obj_registry)
    saved_obj_index = dict(obj_index_registry)
    saved_area = dict(area_registry)
    obj_registry.clear()
    obj_index_registry.clear()
    area_registry.clear()
    try:
        yield
    finally:
        obj_registry.clear()
        obj_index_registry.clear()
        area_registry.clear()
        obj_registry.update(saved_obj)
        obj_index_registry.update(saved_obj_index)
        area_registry.update(saved_area)


def _build_area() -> Area:
    return Area(
        vnum=999,
        name="OLC_SAVE-007 Test Area",
        file_name="olc_save_007_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialize_affect_normalizes_a_line_dict():
    """A-line dicts (location + modifier) survive with empty where/bitvector."""
    payload = _serialize_affect({"location": 18, "modifier": 1})
    assert payload["location"] == 18
    assert payload["modifier"] == 1
    # Defaults: TO_OBJECT framing, no bitvector
    assert payload.get("bitvector", 0) == 0


def test_serialize_affect_preserves_f_line_dict():
    """F-line dicts (where + bitvector) survive with all fields."""
    payload = _serialize_affect(
        {"where": "OBJECT", "location": 0, "modifier": 0, "bitvector": 4}
    )
    assert payload["where"] == "OBJECT"
    assert payload["bitvector"] == 4


def test_serialize_affect_handles_affect_dataclass():
    """An ``Affect`` instance must emit all seven fields, json-safe."""
    aff = Affect(where=1, type=-1, level=20, duration=-1, location=18, modifier=2, bitvector=0)
    payload = _serialize_affect(aff)
    # Must round-trip through json.dumps without error.
    json.dumps(payload)
    assert payload["level"] == 20
    assert payload["location"] == 18
    assert payload["modifier"] == 2


def test_round_trip_preserves_object_affects(tmp_path: Path):
    area = _build_area()
    obj = ObjIndex(
        vnum=9001,
        short_descr="affected item",
        affects=[
            {"location": 18, "modifier": 1},
            {"where": "OBJECT", "location": 0, "modifier": 0, "bitvector": 4},
        ],
        area=area,
    )
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    obj_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_007_test.json"
    load_area_from_json(str(saved_path))

    reloaded = obj_registry[9001]
    assert len(reloaded.affects) == 2
    a, f = reloaded.affects
    assert a["location"] == 18
    assert a["modifier"] == 1
    assert f["where"] == "OBJECT"
    assert f["bitvector"] == 4


def test_object_with_affect_dataclass_survives_json_dump(tmp_path: Path):
    """Regression: an Affect dataclass on the prototype must not crash json.dump."""
    area = _build_area()
    obj = ObjIndex(
        vnum=9002,
        short_descr="dataclass affects",
        affects=[
            Affect(where=1, type=-1, level=15, duration=-1, location=18, modifier=2, bitvector=0)
        ],
        area=area,
    )
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_007_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)
    written = next(o for o in data["objects"] if o["id"] == 9002)
    assert len(written["affects"]) == 1
    assert written["affects"][0]["location"] == 18
    assert written["affects"][0]["modifier"] == 2
