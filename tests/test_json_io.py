import json
from io import StringIO

from mud.models import AreaJson, RoomJson
from mud.models.json_io import dump_dataclass, load_dataclass


def test_room_roundtrip_defaults():
    data = {
        "id": 1,
        "name": "A room",
        "description": "desc",
        "sector_type": "inside",
        "area": 0,
    }
    fp = StringIO(json.dumps(data))
    room = load_dataclass(RoomJson, fp)
    assert room.flags == []
    assert room.exits == {}
    out = StringIO()
    dump_dataclass(room, out)
    out.seek(0)
    dumped = json.load(out)
    assert dumped["flags"] == []
    assert dumped["exits"] == {}


def test_nested_area_roundtrip():
    area_data = {
        "name": "Test",
        "vnum_range": {"min": 0, "max": 10},
        "rooms": [
            {
                "id": 1,
                "name": "r1",
                "description": "d1",
                "sector_type": "inside",
                "area": 0,
            }
        ],
    }
    fp = StringIO(json.dumps(area_data))
    area = load_dataclass(AreaJson, fp)
    assert area.rooms[0].flags == []
    out = StringIO()
    dump_dataclass(area, out)
    out.seek(0)
    dumped = json.load(out)
    assert dumped["rooms"][0]["flags"] == []


def test_room_method_roundtrip_defaults():
    data = {
        "id": 1,
        "name": "A room",
        "description": "desc",
        "sector_type": "inside",
        "area": 0,
    }
    room = RoomJson.from_dict(data)
    assert room.flags == []
    dumped = room.to_dict()
    assert dumped["flags"] == []
    assert dumped["exits"] == {}


def test_area_method_roundtrip():
    area_data = {
        "name": "Test",
        "vnum_range": {"min": 0, "max": 10},
        "rooms": [
            {
                "id": 1,
                "name": "r1",
                "description": "d1",
                "sector_type": "inside",
                "area": 0,
            }
        ],
    }
    area = AreaJson.from_dict(area_data)
    assert area.rooms[0].flags == []
    dumped = area.to_dict()
    assert dumped["rooms"][0]["flags"] == []
