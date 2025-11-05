from pathlib import Path
from random import Random

from mud.models.character import Character
from mud.skills import SkillRegistry


ROM_NEWLINE = "\n\r"


SPELL_NULL_MESSAGE = f"That's not a spell!{ROM_NEWLINE}"


def load_registry() -> SkillRegistry:
    registry = SkillRegistry(rng=Random(0))
    registry.load(Path("data/skills.json"))
    return registry


def test_weapon_skill_use_reports_not_spell() -> None:
    registry = load_registry()
    skill = registry.get("axe")
    skill.cooldown = 4
    skill.lag = 6
    caster = Character(mana=10, is_npc=False, skills={"axe": 100})
    caster.messages = []

    result = registry.use(caster, "axe")

    assert result.success is False
    assert result.message == SPELL_NULL_MESSAGE
    assert result.cooldown == 0
    assert result.lag == 0
    assert result.payload is None
    assert caster.mana == 10
    assert caster.cooldowns["axe"] == 0
    assert caster.messages[-1] == SPELL_NULL_MESSAGE
    assert caster.wait == 0
