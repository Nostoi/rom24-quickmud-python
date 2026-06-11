"""FIGHT-047 — do_kick must call check_killer unconditionally after both branches.

ROM src/fight.c:3138 calls ``check_killer(ch, victim)`` as the last statement of
``do_kick``, after both the success and failure branches.  Python ``do_kick`` had
no ``check_killer`` call at all.

**KILLER-flag note (same as FIGHT-044/045):**
``do_kick`` requires ``char.fighting`` to be non-None to proceed.  For PC victims,
check_killer's ``attacker.fighting is resolved_victim`` guard fires and the KILLER
flag is never set — same in ROM C.  The parity gap is structural.
The correct assertion is that the call *happens*, not that KILLER is set.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_kick
from mud.models.constants import Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_combatants():
    """Clan PC attacker already fighting a clan PC victim, both in room 3001."""
    attacker = create_test_character("Kicker", 3001)
    victim = create_test_character("Target", 3001)

    attacker.clan = 1  # is_clan_member gate in check_killer
    attacker.desc = object()  # simulates a connected player
    attacker.ch_class = 3  # kick level requirement: class 3 = 8, class 0 (Mage) = 53
    attacker.level = 50  # well above the class-3 minimum of 8
    attacker.skills["kick"] = 100
    attacker.wait = 0
    attacker.hit = 500
    attacker.max_hit = 500
    # do_kick requires char.fighting to be non-None
    attacker.fighting = victim
    attacker.position = int(Position.FIGHTING)

    victim.clan = 1  # _kill_safety_message victim-clan gate
    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.FIGHTING)
    victim.fighting = attacker

    return attacker, victim


def test_kick_success_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:3138 — check_killer called after the success branch
    attacker, victim = _make_combatants()
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # low roll → success

    do_kick(attacker, "")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_kick success: check_killer(char, opponent) was not called (FIGHT-047)"
    )


def test_kick_failure_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:3138 — check_killer called after the failure branch too
    attacker, victim = _make_combatants()
    attacker.skills["kick"] = 10  # low skill → chance ≈ 10
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)  # 99 > 10 → failure

    do_kick(attacker, "")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_kick failure: check_killer(char, opponent) was not called (FIGHT-047)"
    )
