import json
from pathlib import Path

import pytest

from mud.loaders import load_area_file
from mud.loaders.json_loader import load_area_from_json
from mud.models.constants import RoomFlag
from mud.registry import area_registry, room_registry
from mud.scripts.convert_are_to_json import convert_area, clear_registries


def test_duplicate_area_vnum_raises_value_error(tmp_path):
    area_registry.clear()
    src = Path("area") / "midgaard.are"
    lines = src.read_text(encoding="latin-1").splitlines()
    lines[1] = "dup.are~"
    dup = tmp_path / "dup.are"
    dup.write_text("\n".join(lines), encoding="latin-1")
    load_area_file(str(src))
    with pytest.raises(ValueError):
        load_area_file(str(dup))
    area_registry.clear()


def test_areadata_parsing(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "test.are~\n"
        "Test Area~\n"
        "Credits~\n"
        "0 0\n"
        "#AREADATA\n"
        "Builders Alice~\n"
        "Security 9\n"
        "Flags 3\n"
        "#$\n"
    )
    path = tmp_path / "test.are"
    path.write_text(content, encoding="latin-1")
    area = load_area_file(str(path))
    assert area.builders == "Alice"
    assert area.security == 9
    assert area.area_flags == 3
    area_registry.clear()


def test_optional_room_fields_roundtrip(tmp_path):
    clear_registries()
    data = convert_area("area/midgaard.are")

    temple_room = next(room for room in data["rooms"] if room["id"] == 3054)
    assert temple_room["heal_rate"] == 110
    assert temple_room["mana_rate"] == 110

    out_file = tmp_path / "midgaard.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    load_area_from_json(str(out_file))

    loaded_room = room_registry[3054]
    assert loaded_room.heal_rate == 110
    assert loaded_room.mana_rate == 110

    area_registry.clear()
    room_registry.clear()


def test_convert_area_preserves_clan_and_owner(tmp_path):
    content = (
        "#AREA\n"
        "tmp.are~\n"
        "Tmp Area~\n"
        "Builder~\n"
        "0 0\n"
        "#ROOMS\n"
        "#100\n"
        "Clan Room~\n"
        "A clan-owned room.\n"
        "~\n"
        "0 0 0\n"
        "H 150 M 90\n"
        "C test_clan~\n"
        "O test_owner~\n"
        "S\n"
        "#0\n"
        "#$\n"
    )
    area_path = tmp_path / "tmp.are"
    area_path.write_text(content, encoding="latin-1")

    clear_registries()
    data = convert_area(str(area_path))
    room_data = data["rooms"][0]

    assert room_data["heal_rate"] == 150
    assert room_data["mana_rate"] == 90
    assert room_data["clan"] == "test_clan"
    assert room_data["owner"] == "test_owner"

    json_path = tmp_path / "tmp.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    load_area_from_json(str(json_path))

    loaded_room = room_registry[100]
    assert loaded_room.heal_rate == 150
    assert loaded_room.mana_rate == 90
    assert loaded_room.clan == "test_clan"
    assert loaded_room.owner == "test_owner"

    area_registry.clear()
    room_registry.clear()


def test_json_loader_applies_defaults_and_law_flag(tmp_path):
    clear_registries()
    data = convert_area("area/midgaard.are")
    json_path = tmp_path / "midgaard.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    area_registry.clear()
    room_registry.clear()
    load_area_from_json(str(json_path))

    room = room_registry[3001]
    assert room.heal_rate == 100
    assert room.mana_rate == 100
    assert room.clan == 0
    assert room.owner == ""
    assert room.room_flags & RoomFlag.ROOM_LAW

    area_registry.clear()
    room_registry.clear()
