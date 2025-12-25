import json
from pathlib import Path


def test_skills_json_contains_fireball():
    skills = json.loads(Path("data/skills.json").read_text())
    assert len(skills) == 134  # All ROM 2.4 skills converted
    skill_names = [s["name"] for s in skills]
    assert "fireball" in skill_names
    fireball = next(s for s in skills if s["name"] == "fireball")
    assert fireball["type"] == "spell"
    assert fireball["function"] == "fireball"
