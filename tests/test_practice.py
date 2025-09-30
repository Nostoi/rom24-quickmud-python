from pathlib import Path

from mud.commands.advancement import do_practice
from mud.models.character import Character
from mud.skills.registry import load_skills, skill_registry


def setup_function(_):
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def test_practice_uses_class_levels() -> None:
    load_skills(Path("data/skills.json"))

    char = Character(
        practice=1,
        level=10,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        skills={"acid blast": 0},
    )

    msg = do_practice(char, "acid blast")
    assert msg == "You can't practice that."
    assert char.practice == 1
    assert char.skills["acid blast"] == 0

    char.level = 28
    msg = do_practice(char, "acid blast")
    assert msg == "You practice acid blast."
    assert char.practice == 0
    assert char.skills["acid blast"] == 40

    skill = skill_registry.get("acid blast")
    assert skill.slot == 70


def test_practice_accepts_skill_abbreviations() -> None:
    load_skills(Path("data/skills.json"))

    char = Character(
        practice=1,
        level=25,
        ch_class=1,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        skills={"sanctuary": 1},
    )

    msg = do_practice(char, "sanc")
    assert msg == "You practice sanctuary."
    assert char.practice == 0
    assert char.skills["sanctuary"] > 1
