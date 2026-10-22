"""FIGHT-101 — do_flee carries no wait-gate and applies no WAIT_STATE in ROM.

ROM `do_flee` (src/fight.c:2970-3030) neither checks `ch->wait` nor applies
WAIT_STATE. Player wait is enforced ONE layer up, in the descriptor input
loop (src/comm.c:619-623: a waiting char's typed input stays buffered) —
which Python mirrors in mud/net/connection.py:1039-1047. Direct dispatch
(`do_function` in ROM: mobprogs, damage()'s auto-flee epilogue) bypasses the
interpreter wait entirely, so:

1. ROM damage()'s wimpy auto-flee (FIGHT-100, gated `wait < PULSE_VIOLENCE/2`)
   fires at wait 1..5 — Python's internal "You are still recovering." gate
   wrongly blocked it.
2. ROM do_flee applies NO lag — Python's `_apply_wait_state(ch,
   PULSE_VIOLENCE)` invented 12 pulses of recovery per flee attempt.

Surfaced 2026-07-16 while closing FIGHT-100.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_damage, set_fighting
from mud.commands.combat import do_flee
from mud.models.character import Character
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_ROOM = 3005


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _open_door(char: Character) -> int:
    from mud.models.constants import RoomFlag

    for idx, ex in enumerate(getattr(char.room, "exits", []) or []):
        to_room = getattr(ex, "to_room", None) if ex is not None else None
        if to_room is None:
            continue
        if int(getattr(to_room, "room_flags", 0) or 0) & int(RoomFlag.ROOM_NO_MOB):
            continue
        return idx
    raise AssertionError("test room has no open NPC-fleeable exit")


def _pc(name: str) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = False
    ch.level = 10
    ch.max_hit = 100
    ch.hit = 100
    ch.wait = 0
    ch.move = 100
    ch.max_move = 100
    ch.desc = object()  # connected — isolate from the FIGHT-099 link-dead leg
    return ch


def test_fight101_wimpy_autoflee_fires_at_small_wait(monkeypatch) -> None:
    """mirrors ROM src/fight.c:1007-1012 + 2970-3030 — the PC wimpy auto-flee
    gate is wait < PULSE_VIOLENCE / 2, and do_flee itself never checks wait,
    so a victim with wait 3 still flees."""
    victim = _pc("Winded")
    victim.wimpy = 30
    victim.hit = 35
    victim.wait = 3  # < PULSE_VIOLENCE(12) / 2 — ROM flees

    attacker = create_test_character("Mugger3", _ROOM)
    attacker.is_npc = True
    attacker.level = 10
    set_fighting(attacker, victim)

    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(victim))

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum != _ROOM, (
        "ROM's only wait gate is damage()'s wait < PULSE_VIOLENCE/2 — do_flee "
        f"must not re-check wait (src/fight.c:2970-3030); still in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight101_do_flee_applies_no_wait_state(monkeypatch) -> None:
    """ROM do_flee applies NO WAIT_STATE anywhere in src/fight.c:2970-3030 —
    a successful flee leaves ch->wait untouched."""
    fleer = _pc("Swift")
    opponent = create_test_character("Thug", _ROOM)
    opponent.is_npc = True
    opponent.level = 10
    set_fighting(opponent, fleer)
    fleer.fighting = opponent

    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(fleer))

    do_flee(fleer, "")

    assert fleer.room is not None and fleer.room.vnum != _ROOM, "flee itself must succeed"
    assert int(getattr(fleer, "wait", 0) or 0) == 0, f"ROM do_flee applies no lag; got wait={fleer.wait}"
