"""FIGHT-045 — do_trip must call check_killer unconditionally (after both branches).

ROM src/fight.c:2753 calls ``check_killer(ch, victim)`` as the last statement of
``do_trip``, after both the success and failure branches.  Python ``do_trip``
called ``check_killer`` only inside the success branch — the failure branch had
no call at all.

**KILLER-flag note (same as FIGHT-044):**
``apply_damage()`` sets ``attacker.fighting = victim`` before ``check_killer``
runs, so the ``attacker.fighting is resolved_victim`` guard fires and the KILLER
flag is never actually set — same in ROM C.  The parity gap is structural.
The correct assertion is that the call *happens*, not that KILLER is set.

The success-path call existed pre-fix; the load-bearing new case is the
failure path.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_trip
from mud.models.constants import Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_combatants():
    """PC attacker + PC victim, both in room 3001."""
    attacker = create_test_character("Tripper", 3001)
    victim = create_test_character("Target", 3001)

    attacker.clan = 1  # is_clan_member gate in check_killer + _kill_safety_message
    attacker.desc = object()  # simulates a connected player
    attacker.skills["trip"] = 100
    attacker.wait = 0
    attacker.hit = 500
    attacker.max_hit = 500

    victim.clan = 1  # _kill_safety_message line 85: victim must also be clan
    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.STANDING)

    return attacker, victim


def test_trip_success_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2753 — check_killer called after the success branch.
    attacker, victim = _make_combatants()
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # low roll → success

    do_trip(attacker, "Target")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_trip success: check_killer(char, victim) was not called (FIGHT-045)"
    )


def test_trip_failure_calls_check_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2753 — check_killer called after the failure branch too.
    # This is the new case (pre-fix, failure path had no check_killer call).
    # Use skill_level=10 so chance≈10, then roll=99 → 99 < 10 is False → failure branch.
    attacker, victim = _make_combatants()
    attacker.skills["trip"] = 10  # low skill → chance ≈ 10
    called: list[tuple[object, object]] = []
    monkeypatch.setattr("mud.commands.combat.check_killer", lambda a, v: called.append((a, v)))
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)  # 99 < 10 → False → failure

    do_trip(attacker, "Target")

    assert any(a is attacker and v is victim for a, v in called), (
        "do_trip failure: check_killer(char, victim) was not called (FIGHT-045)"
    )
