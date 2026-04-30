"""OLC_SAVE-005 — mob spec_fun bindings persisted on JSON save.

Mirrors ROM src/olc_save.c:578-606 (save_specials writes the per-area
#SPECIALS section as ``M <vnum> <spec_fun>`` rows). Without this, a
save→reload cycle silently erases every spec_fun binding.

JSON-authoritative framing: emit a top-level ``specials`` list per area;
the loader (``apply_specials_from_json``, already present) re-attaches
each ``MobIndex.spec_fun``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area
from mud.models.mob import MobIndex
from mud.olc.save import save_area_to_json
from mud.registry import area_registry, mob_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_mobs = dict(mob_registry)
    saved_areas = dict(area_registry)
    mob_registry.clear()
    area_registry.clear()
    try:
        yield
    finally:
        mob_registry.clear()
        area_registry.clear()
        mob_registry.update(saved_mobs)
        area_registry.update(saved_areas)


def _build_area() -> Area:
    return Area(
        vnum=999,
        name="OLC_SAVE-005 Test Area",
        file_name="olc_save_005_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialized_area_emits_specials_section(tmp_path: Path):
    area = _build_area()
    mob = MobIndex(vnum=9001, short_descr="dragon", area=area)
    mob.spec_fun = "spec_breath_fire"
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_005_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert "specials" in data
    assert data["specials"] == [{"mob_vnum": 9001, "spec": "spec_breath_fire"}]


def test_round_trip_restores_spec_fun(tmp_path: Path):
    area = _build_area()
    mob = MobIndex(vnum=9002, short_descr="cleric", area=area)
    mob.spec_fun = "spec_cast_cleric"
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    mob_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_005_test.json"
    load_area_from_json(str(saved_path))

    assert mob_registry[9002].spec_fun == "spec_cast_cleric"


def test_mob_without_spec_fun_emits_no_entry(tmp_path: Path):
    area = _build_area()
    mob = MobIndex(vnum=9003, short_descr="plain mob", area=area)
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_005_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert data.get("specials", []) == []
