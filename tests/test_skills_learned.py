from __future__ import annotations

from pathlib import Path

from mud.game_loop import violence_tick
from mud.models.character import Character, character_registry
from mud.skills import SkillRegistry, SkillUseResult
from mud.utils import rng_mm


def load_registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.load(Path("data/skills.json"))
    return reg


def test_learned_percent_gates_success_boundary(monkeypatch) -> None:
    reg = load_registry()
    caster = Character(mana=40)  # Increased to handle two casts (15 + 15 = 30 mana needed)
    target = Character()
    # Learned 75% should succeed when roll == 75, fail when 76
    caster.skills["fireball"] = 75

    # Force roll=75
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 75)
    result = reg.use(caster, "fireball", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert result.payload == 42

    # Cooldown applied; tick twice to reuse and drain wait via violence pulses
    character_registry.append(caster)
    try:
        reg.tick(caster)
        reg.tick(caster)
        while caster.wait > 0:
            violence_tick()
    finally:
        character_registry.remove(caster)

    # Force roll=76 → fail
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 76)
    result2 = reg.use(caster, "fireball", target)
    assert isinstance(result2, SkillUseResult)
    assert result2.success is False
