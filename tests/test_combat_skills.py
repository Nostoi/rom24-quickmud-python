from collections import deque

import pytest

from mud.combat.engine import attack_round, multi_hit
from mud.models import Character, Skill
from mud.models.constants import Position, Sex
from mud.skills.registry import skill_registry
from mud.utils import rng_mm


def _setup_skill(monkeypatch: pytest.MonkeyPatch, name: str) -> Skill:
    skill = Skill(name=name, type="skill", function=name.replace(" ", "_"), rating={3: 1})
    monkeypatch.setitem(skill_registry.skills, name, skill)
    return skill


def _make_pc(name: str) -> Character:
    char = Character(name=name, level=30, ch_class=3, is_npc=False)
    char.perm_stat = [25, 25, 25, 25, 25]
    char.mod_stat = [0, 0, 0, 0, 0]
    char.sex = Sex.MALE
    char.hitroll = 50
    char.damroll = 5
    return char


def test_second_attack_trains_on_success(monkeypatch: pytest.MonkeyPatch):
    _setup_skill(monkeypatch, "second attack")
    monkeypatch.setattr("mud.advancement.gain_exp", lambda *args, **kwargs: None)

    attacker = _make_pc("Warrior")
    attacker.skills["second attack"] = 50
    attacker.second_attack_skill = 100
    attacker.third_attack_skill = 0
    attacker.messages.clear()

    victim = _make_pc("Target")
    victim.position = Position.FIGHTING
    victim.messages.clear()

    attack_results = []

    def fake_attack_round(att, vic, dt=None):
        att.fighting = vic
        vic.fighting = att
        vic.position = Position.FIGHTING
        attack_results.append(dt)
        return f"swing-{len(attack_results)}"

    monkeypatch.setattr("mud.combat.engine.attack_round", fake_attack_round)

    percent_values = deque([1, 1])

    def fake_number_percent():
        if not percent_values:
            return 1
        return percent_values.popleft()

    monkeypatch.setattr(rng_mm, "number_percent", fake_number_percent)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1 if (a, b) == (1, 1000) else a)

    results = multi_hit(attacker, victim)

    assert len(results) == 2
    assert attacker.skills["second attack"] == 51
    assert any("second attack" in msg for msg in attacker.messages)


def test_enhanced_damage_checks_improve(monkeypatch: pytest.MonkeyPatch):
    _setup_skill(monkeypatch, "enhanced damage")
    monkeypatch.setattr("mud.advancement.gain_exp", lambda *args, **kwargs: None)

    attacker = _make_pc("Fighter")
    attacker.skills["enhanced damage"] = 60
    attacker.enhanced_damage_skill = 80
    attacker.messages.clear()

    victim = _make_pc("Dummy")
    victim.max_hit = 120
    victim.hit = 120
    victim.armor = [0, 0, 0, 0]

    percent_values = deque([10, 1])

    def fake_number_percent():
        if not percent_values:
            return 1
        return percent_values.popleft()

    def fake_number_range(a, b):
        if (a, b) == (1, 1000):
            return 1
        return b

    monkeypatch.setattr(rng_mm, "number_percent", fake_number_percent)
    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    attack_round(attacker, victim)

    assert attacker.skills["enhanced damage"] == 61
    assert any("enhanced damage" in msg for msg in attacker.messages)
