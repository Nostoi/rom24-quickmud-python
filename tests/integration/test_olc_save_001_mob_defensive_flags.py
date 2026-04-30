"""OLC_SAVE-001 — mob off/imm/res/vuln flags persisted on JSON save.

Mirrors ROM src/olc_save.c:205-208 (save_mobile writes Off/Imm/Res/Vuln
flag fields). Without this, a save→reload cycle silently drops mob
defensive/offensive flag sets, reverting prototypes to a degraded state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import _load_mobs_from_json
from mud.models.area import Area
from mud.models.mob import MobIndex
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


def _build_area(min_vnum: int = 9000, max_vnum: int = 9009) -> Area:
    area = Area(
        vnum=999,
        name="OLC_SAVE-001 Test Area",
        file_name="olc_save_001_test.are",
        min_vnum=min_vnum,
        max_vnum=max_vnum,
    )
    return area


def test_serialize_mobile_emits_offensive_immune_resist_vuln():
    """Mirrors ROM src/olc_save.c:205-208 — fwrite_flag for Off/Imm/Res/Vuln."""
    area = _build_area()
    mob = MobIndex(
        vnum=9001,
        short_descr="a test mob",
        offensive="EFNU",
        immune="ABC",
        resist="DE",
        vuln="W",
        area=area,
    )
    mob_registry[mob.vnum] = mob

    payload = _serialize_mobile(mob)

    assert payload["offensive"] == "EFNU"
    assert payload["immune"] == "ABC"
    assert payload["resist"] == "DE"
    assert payload["vuln"] == "W"


def test_round_trip_preserves_defensive_flags(tmp_path: Path):
    """Round-trip: build proto → save JSON → load JSON → assert equality."""
    area = _build_area()
    original = MobIndex(
        vnum=9002,
        short_descr="round-trip mob",
        offensive="EFNU",
        immune="ABC",
        resist="DE",
        vuln="W",
        area=area,
    )
    mob_registry[original.vnum] = original

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_001_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    mob_registry.clear()
    _load_mobs_from_json(data["mobiles"], area)

    reloaded = mob_registry[9002]
    assert reloaded.offensive == "EFNU"
    assert reloaded.immune == "ABC"
    assert reloaded.resist == "DE"
    assert reloaded.vuln == "W"


def test_empty_defensive_flags_round_trip_safely(tmp_path: Path):
    """Empty/zero flag strings must survive round-trip without becoming None."""
    area = _build_area()
    bare = MobIndex(
        vnum=9003,
        short_descr="bare mob",
        offensive="",
        immune="0",
        resist="",
        vuln="0",
        area=area,
    )
    mob_registry[bare.vnum] = bare

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_001_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    mob_registry.clear()
    _load_mobs_from_json(data["mobiles"], area)

    reloaded = mob_registry[9003]
    assert reloaded.offensive in ("", "0")
    assert reloaded.immune in ("", "0")
    assert reloaded.resist in ("", "0")
    assert reloaded.vuln in ("", "0")
