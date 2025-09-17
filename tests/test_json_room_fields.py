import json

from mud.loaders.json_loader import load_area_from_json
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


def test_json_loader_parses_extended_room_fields(tmp_path):
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_payload = {
        "area": {
            "vnum": 4000,
            "name": "Test Fields",
            "min_vnum": 4000,
            "max_vnum": 4002,
            "builders": "ROM",
            "credits": "ROM",
            "area_flags": 0,
            "security": 9,
        },
        "rooms": [
            {
                "id": 4000,
                "name": "Explicit Values",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "heal_rate": 150,
                "mana_rate": 90,
                "clan": 7,
                "owner": "ROM Council",
                "exits": {},
                "extra_descriptions": [],
            },
            {
                "id": 4001,
                "name": "Defaulted Values",
                "description": "",
                "sector_type": "inside",
                "flags": 0,
                "exits": {},
                "extra_descriptions": [],
            },
        ],
        "mobs": [],
        "objects": [],
        "resets": [],
    }
    path = tmp_path / "extended_area.json"
    path.write_text(json.dumps(area_payload))
    try:
        load_area_from_json(str(path))
        explicit = room_registry[4000]
        assert explicit.heal_rate == 150
        assert explicit.mana_rate == 90
        assert explicit.clan == 7
        assert explicit.owner == "ROM Council"
        defaulted = room_registry[4001]
        assert defaulted.heal_rate == 100
        assert defaulted.mana_rate == 100
        assert defaulted.clan == 0
        assert defaulted.owner == ""
    finally:
        area_registry.clear()
        room_registry.clear()
        mob_registry.clear()
        obj_registry.clear()
