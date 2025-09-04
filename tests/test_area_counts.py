import json

from mud.scripts.convert_are_to_json import convert_area
from mud.registry import room_registry, mob_registry, obj_registry


def test_midgaard_counts_match_original_are():
    data = convert_area("area/midgaard.are")
    loaded = json.loads(json.dumps(data))
    assert len(loaded["rooms"]) == len(room_registry)
    assert len(loaded["mobiles"]) == len(mob_registry)
    assert len(loaded["objects"]) == len(obj_registry)
