from pathlib import Path

from mud.skills import load_skills, skill_registry


def test_load_skills_registers_handlers():
    skill_registry.clear()
    skills_path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    load_skills(skills_path)
    assert "fireball" in skill_registry
    assert skill_registry["fireball"](None, None) == 42
