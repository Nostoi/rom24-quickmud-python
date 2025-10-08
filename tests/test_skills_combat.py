from __future__ import annotations

from collections.abc import Callable

import pytest

from mud.combat import engine as combat_engine
from mud.models import Character
from mud.models.constants import Position
from mud.skills import handlers as skill_handlers


def _patch_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    called: dict[str, bool] = {"shield": False, "parry": False, "dodge": False}

    def _make_recorder(name: str) -> Callable[[Character, Character], bool]:
        def _recorder(attacker: Character, victim: Character) -> bool:
            called[name] = True
            return False

        return _recorder

    monkeypatch.setattr(combat_engine, "check_shield_block", _make_recorder("shield"))
    monkeypatch.setattr(combat_engine, "check_parry", _make_recorder("parry"))
    monkeypatch.setattr(combat_engine, "check_dodge", _make_recorder("dodge"))

    return called


def _make_combatant(name: str, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.max_hit = 200
    char.hit = 200
    char.position = Position.FIGHTING
    char.messages = []
    return char


def test_kick_bypasses_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> None:
    defenses_called = _patch_weapon_defenses(monkeypatch)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    kicker = _make_combatant("Warrior")
    kicker.skills["kick"] = 75

    victim = _make_combatant("Target", level=25)
    victim.is_npc = True

    result = skill_handlers.kick(kicker, target=victim, success=True, roll=0)

    assert isinstance(result, str)
    assert defenses_called == {"shield": False, "parry": False, "dodge": False}
    assert victim.hit < victim.max_hit


def test_bash_bypasses_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> None:
    defenses_called = _patch_weapon_defenses(monkeypatch)
    monkeypatch.setattr("mud.config.get_pulse_violence", lambda: 1)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    basher = _make_combatant("Knight")
    basher.skills["bash"] = 65

    victim = _make_combatant("Ogre", level=28)
    victim.is_npc = True

    result = skill_handlers.bash(basher, victim, success=True, chance=100)

    assert isinstance(result, str)
    assert defenses_called == {"shield": False, "parry": False, "dodge": False}
    assert victim.position == Position.RESTING
