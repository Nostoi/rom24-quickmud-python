import json
from pathlib import Path


def test_skills_json_contains_fireball():
    skills = json.loads(Path("data/skills.json").read_text())
    assert len(skills) == 1
    skill = skills[0]
    assert skill["name"] == "fireball"
    assert skill["type"] == "spell"
    assert skill["function"] == "fireball"
