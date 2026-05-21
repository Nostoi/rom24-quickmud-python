import json
import logging
from pathlib import Path

from mud.loaders.json_loader import load_area_from_json
from mud.models.character import character_registry
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.scripts.convert_are_to_json import convert_area
from mud.spawning.reset_handler import reset_area


def test_midgaard_counts_match_original_are():
    data = convert_area("area/midgaard.are")
    loaded = json.loads(json.dumps(data))
    assert len(loaded["rooms"]) == len(room_registry)
    assert len(loaded["mobiles"]) == len(mob_registry)
    assert len(loaded["objects"]) == len(obj_registry)


def test_hitower_checked_in_json_matches_original_are_counts():
    converted = convert_area("area/hitower.are")
    with open("data/areas/hitower.json", encoding="utf-8") as handle:
        checked_in = json.load(handle)

    assert len(checked_in["rooms"]) == len(converted["rooms"])
    assert len(checked_in["mobiles"]) == len(converted["mobiles"])
    assert len(checked_in["objects"]) == len(converted["objects"])
    assert len(checked_in["resets"]) == len(converted["resets"])


def test_checked_in_area_json_counts_match_original_are_files():
    mismatches = []

    for are_path in sorted(Path("area").glob("*.are")):
        json_path = Path("data/areas") / f"{are_path.stem}.json"
        if not json_path.exists():
            continue

        converted = convert_area(str(are_path))
        with open(json_path, encoding="utf-8") as handle:
            checked_in = json.load(handle)

        converted_counts = (
            len(converted.get("rooms", [])),
            len(converted.get("mobiles", [])),
            len(converted.get("objects", [])),
            len(converted.get("resets", [])),
        )
        checked_in_counts = (
            len(checked_in.get("rooms", [])),
            len(checked_in.get("mobiles", [])),
            len(checked_in.get("objects", [])),
            len(checked_in.get("resets", [])),
        )

        if checked_in_counts != converted_counts:
            mismatches.append((are_path.name, checked_in_counts, converted_counts))

    assert mismatches == []


def test_hitower_reset_no_longer_logs_missing_1301_1320_chain(caplog):
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    with caplog.at_level(logging.WARNING):
        area = load_area_from_json("data/areas/hitower.json")
        reset_area(area)

    messages = [record.getMessage() for record in caplog.records]
    assert "Invalid O reset 1301 -> 1320" not in messages
    assert "Invalid P reset 20 -> 1301 (missing prototype)" not in messages
