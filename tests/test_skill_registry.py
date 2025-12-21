from pathlib import Path

from mud.skills import load_skills, skill_registry


def test_load_skills_registers_handlers():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    skills_path = Path(__file__).resolve().parent.parent / "data" / "skills.json"
    load_skills(skills_path)
    assert "fireball" in skill_registry.skills
    assert "fireball" in skill_registry.handlers
    assert callable(skill_registry.handlers["fireball"])

    from mud.skills import handlers as skill_handlers

    assert skill_registry.handlers["fireball"] is skill_handlers.fireball
