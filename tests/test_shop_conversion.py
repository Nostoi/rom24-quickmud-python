import json
from pathlib import Path

from mud.scripts.convert_shops_to_json import convert_shops


def test_convert_shops_produces_grocer():
    shops = convert_shops("area/area.lst")
    grocer = next(s for s in shops if s["keeper"] == 3002)
    assert "food" in grocer["buy_types"]
    assert grocer["profit_buy"] == 150
    assert grocer["open_hour"] == 0
    assert grocer["close_hour"] == 23


def test_shops_json_matches_legacy_counts():
    shops = convert_shops("area/area.lst")
    json_shops = json.loads(Path("data/shops.json").read_text())
    assert len(json_shops) == len(shops)
    assert {s["keeper"] for s in json_shops} == {s["keeper"] for s in shops}
