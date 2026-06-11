"""FIGHT-044 — do_bash must call check_killer unconditionally after both branches.

ROM src/fight.c:2486 calls ``check_killer(ch, victim)`` as the last statement of
``do_bash``, after both the success and failure branches.  Python ``do_bash`` had
no ``check_killer`` call at all.

**Why the KILLER flag itself is not the right assertion here:**
``damage()`` (even for 0 damage) calls ``set_fighting(ch, victim)`` inside
``apply_damage``.  By the time ``check_killer`` runs at the end of ``do_bash``,
``attacker.fighting is victim`` is already True — so check_killer's
``attacker.fighting is resolved_victim`` guard fires and it early-returns without
setting the flag (same behaviour in ROM C).  The parity gap is *structural*:
ROM calls check_killer unconditionally; Python must too.  The correct assertion
is that the call *happens*, not that KILLER is set.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_bash
from mud.models.constants import Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_combatants():
    """PC attacker + PC victim, both in room 3001."""
    attacker = create_test_character("Basher", 3001)
    victim = create_test_character("Target", 3001)

    attacker.clan = 1  # is_clan_member gate in check_killer
    attacker.desc = object()  # simulates a connected player
    attacker.skills["bash"] = 100
    attacker.wait = 0
    attacker.hit = 500
    attacker.max_hit = 500

    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.STANDING)

    return attacker, victim


def test_bash_success_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2486 — check_killer called unconditionally after success.
    # KILLER flag itself won't be set because apply_damage starts the fight first
    # (attacker.fighting is victim → check_killer early-returns); we assert the call
    # *happened* to verify structural parity.
    attacker, victim = _make_combatants()
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # low roll → success

    do_bash(attacker, "Target")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_bash success: check_killer(char, victim) was not called (FIGHT-044)"
    )


def test_bash_failure_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2486 — check_killer called unconditionally after failure.
    attacker, victim = _make_combatants()
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)  # high roll → failure

    do_bash(attacker, "Target")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_bash failure: check_killer(char, victim) was not called (FIGHT-044)"
    )
