import json
from io import StringIO

from mud.models import AreaJson, RoomJson
from mud.models.json_io import load_dataclass, dump_dataclass


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
