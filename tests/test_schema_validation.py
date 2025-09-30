import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip(
    "jsonschema",
    reason="Install optional 'jsonschema' dependency to validate schema files",
)

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_DIR.glob("*.schema.json")))
def test_schema_is_valid(schema_path):
    with schema_path.open() as f:
        schema = json.load(f)
    jsonschema.validators.validator_for(schema).check_schema(schema)
