"""OLC_SAVE-006 — object `level` persisted on JSON save.

Mirrors ROM src/olc_save.c:378 (save_object writes the object level).
Without this, a save→reload cycle silently resets every object level
to 0/default — breaking level-gated drops, identify-output, etc.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area
from mud.models.obj import ObjIndex, obj_index_registry
from mud.olc.save import save_area_to_json
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
        name="OLC_SAVE-006 Test Area",
        file_name="olc_save_006_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialize_object_emits_level():
    area = _build_area()
    obj = ObjIndex(vnum=9001, short_descr="leveled item", level=42, area=area)
    obj_registry[obj.vnum] = obj

    from mud.olc.save import _serialize_object

    payload = _serialize_object(obj)
    assert payload["level"] == 42


def test_round_trip_preserves_object_level(tmp_path: Path):
    area = _build_area()
    obj = ObjIndex(vnum=9002, short_descr="rt-leveled", level=37, area=area)
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    obj_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_006_test.json"
    load_area_from_json(str(saved_path))

    assert obj_registry[9002].level == 37


def test_default_object_level_zero_round_trip(tmp_path: Path):
    area = _build_area()
    obj = ObjIndex(vnum=9003, short_descr="default-level", area=area)
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    obj_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_006_test.json"
    load_area_from_json(str(saved_path))

    assert obj_registry[9003].level == 0
