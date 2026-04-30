"""OLC_SAVE-004 — mob shop bindings persisted on JSON save.

Mirrors ROM src/olc_save.c:578-606 (save_specials/SHOPS) plus
src/olc_save.c:786-824 (save_shops). Without persistence, a save→reload
cycle silently erases every shop binding (keeper, buy_type[5],
profit_buy/sell, open_hour/close_hour).

JSON-authoritative framing: emit a top-level ``shops`` list per area; the
loader reads it back into ``shop_registry`` keyed by keeper vnum.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.loaders.shop_loader import Shop
from mud.models.area import Area
from mud.models.mob import MobIndex
from mud.olc.save import save_area_to_json
from mud.registry import area_registry, mob_registry, shop_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_mobs = dict(mob_registry)
    saved_shops = dict(shop_registry)
    saved_areas = dict(area_registry)
    mob_registry.clear()
    shop_registry.clear()
    area_registry.clear()
    try:
        yield
    finally:
        mob_registry.clear()
        shop_registry.clear()
        area_registry.clear()
        mob_registry.update(saved_mobs)
        shop_registry.update(saved_shops)
        area_registry.update(saved_areas)


def _build_area() -> Area:
    return Area(
        vnum=999,
        name="OLC_SAVE-004 Test Area",
        file_name="olc_save_004_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialized_area_emits_shops_section(tmp_path: Path):
    area = _build_area()
    keeper = MobIndex(vnum=9001, short_descr="shopkeeper", area=area)
    keeper.pShop = Shop(
        keeper=9001,
        buy_types=[1, 2, 3, 0, 0],
        profit_buy=120,
        profit_sell=80,
        open_hour=8,
        close_hour=18,
    )
    mob_registry[keeper.vnum] = keeper

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_004_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert "shops" in data
    assert len(data["shops"]) == 1
    shop_data = data["shops"][0]
    assert shop_data["keeper"] == 9001
    assert shop_data["buy_types"] == [1, 2, 3, 0, 0]
    assert shop_data["profit_buy"] == 120
    assert shop_data["profit_sell"] == 80
    assert shop_data["open_hour"] == 8
    assert shop_data["close_hour"] == 18


def test_round_trip_restores_shop_registry(tmp_path: Path):
    area = _build_area()
    keeper = MobIndex(vnum=9002, short_descr="shopkeeper2", area=area)
    keeper.pShop = Shop(
        keeper=9002,
        buy_types=[5, 6, 7, 8, 9],
        profit_buy=110,
        profit_sell=90,
        open_hour=6,
        close_hour=22,
    )
    mob_registry[keeper.vnum] = keeper

    assert save_area_to_json(area, output_dir=tmp_path) is True

    # Wipe registries; reload from saved JSON.
    shop_registry.clear()
    mob_registry.clear()
    area_registry.clear()

    saved_path = tmp_path / "olc_save_004_test.json"
    load_area_from_json(str(saved_path))

    assert 9002 in shop_registry
    reloaded = shop_registry[9002]
    assert reloaded.keeper == 9002
    assert list(reloaded.buy_types) == [5, 6, 7, 8, 9]
    assert reloaded.profit_buy == 110
    assert reloaded.profit_sell == 90
    assert reloaded.open_hour == 6
    assert reloaded.close_hour == 22


def test_mob_without_shop_emits_no_shop_entry(tmp_path: Path):
    area = _build_area()
    mob = MobIndex(vnum=9003, short_descr="not a shopkeeper", area=area)
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_004_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert data.get("shops", []) == []
