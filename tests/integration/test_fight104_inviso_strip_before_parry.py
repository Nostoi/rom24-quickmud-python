"""FIGHT-104: an invisible attacker fades into existence even when the blow is
parried / dodged / shield-blocked.

ROM `damage()` strips the attacker's invisibility (`src/fight.c:763-769`,
`"$n fades into existence."`) BEFORE the parry/dodge/shield_block checks
(`src/fight.c:790-800`). So an invisible attacker whose swing is defended still
reveals themselves. Python's `apply_damage` previously placed the inviso strip
AFTER the parry/dodge early-returns, so a parried/dodged attacker stayed
invisible — a divergence hidden behind the (incorrect) FIGHT-092 comment
claiming parry/dodge resolve in `one_hit` before `damage()`.
"""

from __future__ import annotations

import pytest

import mud.combat.engine as engine
from mud.combat.engine import TYPE_HIT, apply_damage
from mud.models.character import Character
from mud.models.constants import AffectFlag, DamageType, Position
from mud.models.room import Room


def _pair() -> tuple[Character, Character]:
    room = Room(vnum=3001)
    attacker = Character(name="Attacker", level=10)
    victim = Character(name="Victim", level=10)
    attacker.room = room
    victim.room = room
    room.people = [attacker, victim]
    attacker.position = Position.FIGHTING
    victim.position = Position.FIGHTING
    attacker.affected_by = int(AffectFlag.INVISIBLE)
    return attacker, victim


def test_invisible_attacker_fades_when_parried(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = _pair()
    assert attacker.has_affect(AffectFlag.INVISIBLE)

    monkeypatch.setattr(engine, "check_parry", lambda a, v: True)
    monkeypatch.setattr(engine, "check_dodge", lambda a, v: False)
    monkeypatch.setattr(engine, "check_shield_block", lambda a, v: False)

    apply_damage(attacker, victim, 20, int(DamageType.BASH), dt=TYPE_HIT)

    # ROM strips invis before the parry early-return.
    assert not attacker.has_affect(AffectFlag.INVISIBLE)


def test_invisible_attacker_fades_when_dodged(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = _pair()

    monkeypatch.setattr(engine, "check_parry", lambda a, v: False)
    monkeypatch.setattr(engine, "check_dodge", lambda a, v: True)
    monkeypatch.setattr(engine, "check_shield_block", lambda a, v: False)

    apply_damage(attacker, victim, 20, int(DamageType.BASH), dt=TYPE_HIT)

    assert not attacker.has_affect(AffectFlag.INVISIBLE)
