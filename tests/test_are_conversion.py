import json

import jsonschema

from mud.scripts.convert_are_to_json import convert_area


def test_convert_area_creates_valid_json():
    data = convert_area("area/chapel.are")
    with open("schemas/area.schema.json") as f:
        schema = json.load(f)
    jsonschema.validate(data, schema)
    assert data["rooms"], "converted area should include rooms"
    assert data["mobiles"], "converted area should include mobiles"
    assert data["objects"], "converted area should include objects"
