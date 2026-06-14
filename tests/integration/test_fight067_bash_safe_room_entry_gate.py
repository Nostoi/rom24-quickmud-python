"""FIGHT-067 — do_bash must gate on is_safe() at command entry.

ROM ``do_bash`` (src/fight.c:2405-2419) checks ``is_safe(ch, victim)`` *before*
computing chance, applying WAIT_STATE, or running the knockdown — the entire
skill is short-circuited when the target is protected (safe room, shopkeeper,
pet, …).  Python ``do_bash`` omitted this entry gate: it relied solely on
``apply_damage`` re-checking ``is_safe`` (FIGHT-002), which suppresses only the
HP damage.  The lag, the victim daze, the knockdown to RESTING, and the
"sends you sprawling" broadcast still fired — a real griefing divergence: in a
ROOM_SAFE room a player could still lag and floor another character.

This test sets up a ROOM_SAFE room (``is_safe`` returns True regardless of
NPC/PC, src/fight.c:1034) and forces the bash *success* roll, then asserts the
skill never engaged: no attacker lag, no victim daze, no knockdown.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_bash
from mud.models.constants import Position, RoomFlag
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_bash_in_safe_room_does_not_engage_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:2405 — is_safe gates the whole skill at entry.
    attacker = create_test_character("Basher", 3001)
    victim = create_test_character("Target", 3001)

    attacker.skills["bash"] = 100
    attacker.wait = 0
    attacker.hit = 500
    attacker.max_hit = 500

    victim.hit = 500
    victim.max_hit = 500
    victim.position = int(Position.STANDING)
    victim.daze = 0

    # ROOM_SAFE → is_safe(attacker, victim) returns True (src/fight.c:1034).
    room = attacker.room
    room.room_flags = int(getattr(room, "room_flags", 0) or 0) | int(RoomFlag.ROOM_SAFE)

    # Force the bash "success" roll so the knockdown path would run if not gated.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    do_bash(attacker, "Target")

    assert int(getattr(attacker, "wait", 0) or 0) == 0, "do_bash applied WAIT_STATE in a safe room (FIGHT-067)"
    assert int(getattr(victim, "daze", 0) or 0) == 0, "do_bash dazed the victim in a safe room (FIGHT-067)"
    assert int(getattr(victim, "position", Position.STANDING)) != int(Position.RESTING), (
        "do_bash knocked the victim to RESTING in a safe room (FIGHT-067)"
    )
