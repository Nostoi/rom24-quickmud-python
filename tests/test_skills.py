from pathlib import Path
from random import Random

import pytest

from mud.models.character import Character
from mud.skills import SkillRegistry


def load_registry() -> SkillRegistry:
    reg = SkillRegistry(rng=Random(0))
    reg.load(Path("data/skills.json"))
    return reg


def test_cast_fireball_success() -> None:
    reg = load_registry()
    caster = Character(mana=20)
    target = Character()

    result = reg.use(caster, "fireball", target)
    assert result == 42
    assert caster.mana == 5  # 20 - 15 mana cost = 5
    assert caster.cooldowns["fireball"] == 0  # Fireball has no cooldown in skills.json

    # Since there's no cooldown, we can cast again immediately if we have mana
    # Give enough mana for another cast (15 mana needed)
    caster.mana = 15
    reg.use(caster, "fireball", target)
    assert caster.mana == 0


def test_cast_fireball_failure() -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.failure_rate = 1.0

    called: list[bool] = []

    def dummy(caster, target):  # pragma: no cover - test helper
        called.append(True)
        return 99

    reg.handlers["fireball"] = dummy

    caster = Character(mana=20)
    target = Character()
    result = reg.use(caster, "fireball", target)
    assert result is False
    assert caster.mana == 5  # 20 - 15 mana cost = 5 (mana consumed even on failure)
    assert called == []
