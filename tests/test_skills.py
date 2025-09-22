from pathlib import Path
from random import Random

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag
import mud.skills.handlers as skill_handlers
from mud.skills import SkillRegistry
from mud.utils import rng_mm


def load_registry() -> SkillRegistry:
    reg = SkillRegistry(rng=Random(0))
    reg.load(Path("data/skills.json"))
    return reg


def test_casting_uses_min_mana_and_beats() -> None:
    reg = load_registry()
    caster = Character(mana=35)
    target = Character()
    skill = reg.get("fireball")

    assert skill.min_mana == 15
    assert skill.beats == 12
    assert skill.slot == 26

    result = reg.use(caster, "fireball", target)
    assert result == 42
    assert caster.mana == 20  # 35 - min_mana 15
    assert caster.wait == 12
    assert caster.cooldowns["fireball"] == 0  # Fireball has no cooldown in skills.json

    # Simulate wait recovery before a second cast
    caster.wait = 0
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


def test_skill_use_advances_learned_percent(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.rating[0] = 4

    caster = Character(
        mana=20,
        ch_class=0,
        level=10,
        is_npc=False,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 50},
    )
    target = Character()

    percent_rolls = iter([30, 1])
    range_rolls = iter([10])

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert result == 42
    assert caster.skills["fireball"] == 51
    assert caster.exp == 8
    assert any("become better" in msg for msg in caster.messages)


def test_skill_failure_grants_learning_xp(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.rating[0] = 4

    caster = Character(
        mana=20,
        ch_class=0,
        level=10,
        is_npc=False,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 50},
    )
    target = Character()

    percent_rolls = iter([100, 10])
    range_rolls = iter([10, 2])

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert result is False
    assert caster.skills["fireball"] == 52
    assert caster.exp == 8
    assert any("learn from your mistakes" in msg for msg in caster.messages)


def test_skill_use_sets_wait_state_and_blocks_until_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reg = load_registry()
    skill = reg.get("acid blast")
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "dice", lambda level, size: 60)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    caster = Character(mana=40, is_npc=False, skills={"acid blast": 100})
    caster.level = 30
    target = Character()

    result = reg.use(caster, "acid blast", target)
    assert result == 60
    assert caster.wait == skill.lag
    assert caster.mana == 20
    assert caster.cooldowns.get("acid blast", 0) == skill.cooldown

    with pytest.raises(ValueError) as excinfo:
        reg.use(caster, "acid blast", target)
    assert "recover" in str(excinfo.value)
    assert caster.messages[-1] == "You are still recovering."
    assert caster.mana == 20


def test_skill_wait_adjusts_for_haste_and_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("acid blast")
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    haste_caster = Character(
        mana=20,
        is_npc=False,
        affected_by=int(AffectFlag.HASTE),
        skills={"acid blast": 100},
    )
    haste_target = Character()
    reg.use(haste_caster, "acid blast", haste_target)
    assert haste_caster.wait == max(1, skill.lag // 2)

    slow_caster = Character(
        mana=20,
        is_npc=False,
        affected_by=int(AffectFlag.SLOW),
        skills={"acid blast": 100},
    )
    slow_target = Character()
    reg.use(slow_caster, "acid blast", slow_target)
    assert slow_caster.wait == skill.lag * 2
