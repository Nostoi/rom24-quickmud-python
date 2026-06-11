"""FIGHT-046 — do_backstab must call check_killer before the WAIT_STATE/roll.

ROM src/fight.c:2951 calls ``check_killer(ch, victim)`` unconditionally after all
guard checks and BEFORE ``WAIT_STATE`` + the skill roll.  Python ``do_backstab``
performed all the guard checks, applied the wait state, rolled, and attacked —
but never called ``check_killer``.

**Why KILLER flag IS the right assertion here (unlike FIGHT-044/045):**
``do_backstab`` requires ``char.fighting is None`` to proceed (returns
"You're facing the wrong end." otherwise).  ``check_killer``'s
``attacker.fighting is resolved_victim`` guard therefore does NOT fire, so the
KILLER flag is actually set — this is a real behavioral gap, not just structural.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_backstab
from mud.models.constants import PlayerFlag, Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_combatants():
    """Clan PC backstabber (not fighting) + PC victim, both in room 3001."""
    attacker = create_test_character("Rogue", 3001)
    victim = create_test_character("Mark", 3001)

    attacker.clan = 1  # is_clan_member gate in check_killer + _kill_safety_message
    attacker.desc = object()  # simulates a connected player
    attacker.skills["backstab"] = 100
    attacker.wait = 0
    attacker.hit = 500
    attacker.max_hit = 500
    # do_backstab requires char.fighting is None (enforced by its own guard)
    attacker.fighting = None

    victim.clan = 1  # _kill_safety_message line 85: victim must also be clan
    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.STANDING)

    return attacker, victim


def test_backstab_flags_attacker_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2951 — check_killer fires before WAIT_STATE.
    # do_backstab requires fighting=None, so check_killer's fighting guard does
    # NOT fire; the KILLER flag is actually set (unlike the bash/trip/kick cases).
    attacker, victim = _make_combatants()
    # do_backstab only checks get_wielded_weapon(char) is None — stub with a truthy sentinel
    monkeypatch.setattr("mud.commands.combat.get_wielded_weapon", lambda _c: "dagger")
    # Stub the actual backstab handler — only check_killer and KILLER flag matter here
    monkeypatch.setattr("mud.commands.combat.skill_handlers.backstab", lambda c, v: "You backstab!")
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # low roll → success

    do_backstab(attacker, "Mark")

    assert attacker.act & int(PlayerFlag.KILLER), (
        "do_backstab: attacker was not flagged PLR_KILLER (FIGHT-046 missing check_killer)"
    )
    assert "*** You are now a KILLER!! ***" in attacker.messages


def test_backstab_failure_still_flags_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # ROM calls check_killer before the roll, so even a failed backstab sets KILLER.
    attacker, victim = _make_combatants()
    monkeypatch.setattr("mud.commands.combat.get_wielded_weapon", lambda _c: "dagger")
    attacker.skills["backstab"] = 10  # low skill → force failure with roll=99
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)  # 99 < 10 → failure

    do_backstab(attacker, "Mark")

    assert attacker.act & int(PlayerFlag.KILLER), (
        "do_backstab failure: attacker was not flagged PLR_KILLER (FIGHT-046 missing check_killer)"
    )
