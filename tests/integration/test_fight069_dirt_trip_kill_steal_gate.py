"""FIGHT-069 — do_dirt / do_trip must gate on the kill-steal check.

ROM ``do_dirt`` (src/fight.c:2537-2542) and ``do_trip`` (src/fight.c:2678-2683)
both reject an attack on an NPC that someone *outside the attacker's group* is
already fighting::

    if (IS_NPC(victim) && victim->fighting != NULL
            && !is_same_group(ch, victim->fighting))
    {
        send_to_char("Kill stealing is not permitted.\n\r", ch);
        return;
    }

``do_kill`` ports this as a check *separate* from ``_kill_safety_message``
(combat.py:141).  But Python ``do_dirt`` / ``do_trip`` called only
``_kill_safety_message`` — which is do_kill's is_safe-messages + beloved-master
composite and does **not** include the kill-steal gate — so they let a player
dirt-kick or trip a mob another (ungrouped) character was fighting, stealing the
kill.  This test sets up exactly that NPC-victim-already-fighting case in a
non-safe room and asserts the ROM rejection.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_dirt, do_trip
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _setup_kill_steal_target(attacker_skill: str):
    attacker = create_test_character("Stealer", 3001)
    victim = create_test_character("Mark", 3001)
    other = create_test_character("Rival", 3001)

    attacker.skills[attacker_skill] = 100
    attacker.wait = 0

    # Victim is an NPC already fighting a third party who is NOT in the
    # attacker's group — the ROM kill-steal condition (IS_NPC + fighting + !group).
    victim.is_npc = True
    victim.fighting = other

    # Non-safe room so is_safe() does not pre-empt the kill-steal gate.
    room = attacker.room
    room.room_flags = 0

    return attacker, victim


def test_dirt_kick_respects_kill_steal_gate() -> None:
    # mirrors ROM src/fight.c:2537-2542 — do_dirt kill-steal rejection.
    attacker, victim = _setup_kill_steal_target("dirt kicking")
    result = do_dirt(attacker, "Mark")
    assert result == "Kill stealing is not permitted.", (
        "do_dirt let a player kick dirt at a mob another group is fighting (FIGHT-069)"
    )


def test_trip_respects_kill_steal_gate() -> None:
    # mirrors ROM src/fight.c:2678-2683 — do_trip kill-steal rejection.
    attacker, victim = _setup_kill_steal_target("trip")
    result = do_trip(attacker, "Mark")
    assert result == "Kill stealing is not permitted.", (
        "do_trip let a player trip a mob another group is fighting (FIGHT-069)"
    )
