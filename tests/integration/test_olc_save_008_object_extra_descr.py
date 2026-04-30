"""OLC_SAVE-008 — object extra-description list serialized via structured helper.

Mirrors ROM src/olc_save.c:431-435 (save_object emits each extra_descr
keyword + tilde-terminated description). Without normalization, an
``ExtraDescr`` dataclass instance on the prototype would crash
``json.dump``, and a future loader change adding new fields would
silently drop them.

This closure routes ``_serialize_object``'s ``extra_descriptions``
output through the existing ``_serialize_extra_descr`` helper so both
plain dicts and ``ExtraDescr`` dataclasses produce the same flat
``{"keyword", "description"}`` payload.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area
from mud.models.obj import ObjIndex, obj_index_registry
from mud.models.room import ExtraDescr
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
        name="OLC_SAVE-008 Test Area",
        file_name="olc_save_008_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_round_trip_preserves_dict_extra_descriptions(tmp_path: Path):
    area = _build_area()
    obj = ObjIndex(
        vnum=9001,
        short_descr="dict extras",
        extra_descr=[
            {"keyword": "candlestick", "description": "An old pewter candlestick.\n"},
            {"keyword": "pewter", "description": "A dull grey metal.\n"},
        ],
        area=area,
    )
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    obj_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_008_test.json"
    load_area_from_json(str(saved_path))

    reloaded = obj_registry[9001]
    assert len(reloaded.extra_descr) == 2
    assert reloaded.extra_descr[0]["keyword"] == "candlestick"
    assert reloaded.extra_descr[0]["description"].startswith("An old pewter")
    assert reloaded.extra_descr[1]["keyword"] == "pewter"


def test_object_with_extradescr_dataclass_survives_json_dump(tmp_path: Path):
    """Regression: an ``ExtraDescr`` dataclass on the prototype must not crash json.dump."""
    area = _build_area()
    obj = ObjIndex(
        vnum=9002,
        short_descr="dataclass extras",
        extra_descr=[ExtraDescr(keyword="rune", description="A glowing rune.\n")],
        area=area,
    )
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_008_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)
    written = next(o for o in data["objects"] if o["id"] == 9002)
    assert len(written["extra_descriptions"]) == 1
    assert written["extra_descriptions"][0]["keyword"] == "rune"
    assert written["extra_descriptions"][0]["description"].startswith("A glowing rune")


def test_serialized_extra_descr_uses_canonical_keys(tmp_path: Path):
    """Output payload must be exactly ``{"keyword", "description"}`` (no extra fields)."""
    area = _build_area()
    obj = ObjIndex(
        vnum=9003,
        short_descr="strict shape",
        extra_descr=[{"keyword": "rune", "description": "A rune.\n", "stray": "drop me"}],
        area=area,
    )
    obj_registry[obj.vnum] = obj

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_008_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)
    written = next(o for o in data["objects"] if o["id"] == 9003)
    extras = written["extra_descriptions"]
    assert len(extras) == 1
    assert set(extras[0].keys()) == {"keyword", "description"}
