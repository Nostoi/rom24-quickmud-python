"""OLC_SAVE-002 — mob form/parts/size/material persisted on JSON save.

Mirrors ROM src/olc_save.c:213-219 (save_mobile writes form, parts, size,
material). Without this, a save→reload cycle silently drops physical
descriptors that drive corpse parts, magic targeting, and combat sizing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.models.area import Area
from mud.models.mob import MobIndex
from mud.models.races import race_lookup
from mud.olc.save import _serialize_mobile, save_area_to_json
from mud.registry import mob_registry


@pytest.fixture(autouse=True)
def _clean_mob_registry():
    saved = dict(mob_registry)
    mob_registry.clear()
    try:
        yield
    finally:
        mob_registry.clear()
        mob_registry.update(saved)


def _build_area() -> Area:
    return Area(
        vnum=999,
        name="OLC_SAVE-002 Test Area",
        file_name="olc_save_002_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialize_mobile_emits_form_parts_size_material():
    """Mirrors ROM src/olc_save.c:213-219 — fwrite_flag/fwrite for these fields."""
    area = _build_area()
    mob = MobIndex(
        vnum=9001,
        short_descr="a test mob",
        form="ABV",
        parts="ABCDH",
        size="large",
        material="iron",
        area=area,
    )
    mob_registry[mob.vnum] = mob

    payload = _serialize_mobile(mob)

    assert payload["form"] == "ABV"
    assert payload["parts"] == "ABCDH"
    assert payload["size"] == "large"
    assert payload["material"] == "iron"


def test_round_trip_writes_form_parts_size_material_to_json(tmp_path: Path):
    """JSON file written by save_area_to_json contains the four fields verbatim.

    Asserting JSON contents (not a re-loaded MobIndex) because the loader's
    `merge_race_flags` unions race-default bits into form/parts on read, so
    the reloaded value is a superset, not an equality. JSON-authoritative
    framing locks the canonical write format here.
    """
    area = _build_area()
    original = MobIndex(
        vnum=9002,
        short_descr="round-trip mob",
        form="ABV",
        parts="ABCDH",
        size="huge",
        material="steel",
        area=area,
    )
    mob_registry[original.vnum] = original

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_002_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    written = next(m for m in data["mobiles"] if m["id"] == 9002)
    assert written["form"] == "ABV"
    assert written["parts"] == "ABCDH"
    assert written["size"] == "huge"
    assert written["material"] == "steel"


def test_default_size_serializes_as_medium_string(tmp_path: Path):
    """MobIndex.size default Size.MEDIUM serializes as 'medium' (loader-compatible)."""
    area = _build_area()
    bare = MobIndex(vnum=9003, short_descr="bare mob", area=area)
    mob_registry[bare.vnum] = bare

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_002_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    written = next(m for m in data["mobiles"] if m["id"] == 9003)
    # Defaults must round-trip without crashing the loader, which expects
    # string-form fields per mud/loaders/json_loader.py:456-459.
    assert written["size"] == "medium"
    assert isinstance(written["form"], str)
    assert isinstance(written["parts"], str)
    assert isinstance(written["material"], str)


def test_serialize_mobile_emits_race_name_from_rom_index():
    """Mirrors ROM src/olc_save.c:184 — save_mobile writes race_table name."""
    mob = MobIndex(vnum=9004, short_descr="indexed race mob", race=race_lookup("human"))

    payload = _serialize_mobile(mob)

    assert payload["race"] == "human"
