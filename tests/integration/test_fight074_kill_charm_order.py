"""FIGHT-074 — do_kill must check charm LAST (after is_safe + kill-steal).

ROM ``do_kill`` (src/fight.c:2794-2807) orders its gates::

    if (is_safe (ch, victim)) return;                       /* 2794 */
    if (victim->fighting != NULL && !is_same_group(...))    /* 2797 */
        { "Kill stealing is not permitted."; return; }
    if (IS_AFFECTED(ch, AFF_CHARM) && ch->master == victim) /* 2803 */
        { act("$N is your beloved master.", ...); return; }

i.e. is_safe → kill-steal → charm. But Python ``do_kill`` routed safety through
``_kill_safety_message`` with the bundled charm gate checked at the TOP of the
helper (before its is_safe body) AND before do_kill's separate kill-steal gate
(combat.py:141). So a charmed PC targeting its master in a safe room — or a
master being kill-stolen — saw "… is your beloved master." where ROM emits the
is_safe / kill-steal line first.

Two assertions pin the ordering: charm must lose to is_safe (safe room) and to
kill-steal (master already fighting an ungrouped third party).
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_kill
from mud.models.constants import AffectFlag, RoomFlag
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _charmed_kill_setup():
    attacker = create_test_character("Thrall", 3001)
    victim = create_test_character("wizard", 3001)
    victim.is_npc = True
    victim.short_descr = "a dark wizard"

    attacker.wait = 0
    attacker.add_affect(AffectFlag.CHARM)
    attacker.master = victim

    return attacker, victim


def test_kill_charmed_master_in_safe_room_shows_safe_line_not_charm() -> None:
    # mirrors ROM src/fight.c:2794 vs 2803 — is_safe is checked BEFORE charm,
    # so a charmed PC targeting its master in a ROOM_SAFE room gets the safe line.
    attacker, victim = _charmed_kill_setup()
    attacker.room.room_flags = int(RoomFlag.ROOM_SAFE)
    result = do_kill(attacker, "wizard")
    assert result == "Not in this room.", result


def test_kill_charmed_master_being_kill_stolen_shows_kill_steal_not_charm() -> None:
    # mirrors ROM src/fight.c:2797 vs 2803 — kill-steal is checked BEFORE charm,
    # so a charmed PC whose master is already fighting an ungrouped third party
    # gets the kill-steal line.
    attacker, victim = _charmed_kill_setup()
    attacker.room.room_flags = 0  # non-safe so is_safe does not pre-empt
    other = create_test_character("Rival", 3001)
    victim.fighting = other
    result = do_kill(attacker, "wizard")
    assert result == "Kill stealing is not permitted.", result


def test_kill_charmed_master_still_shows_beloved_master_when_safe_passes() -> None:
    # mirrors ROM src/fight.c:2803-2807 — when is_safe + kill-steal pass, the
    # charm gate fires with "beloved master" (guard that the message survives
    # moving the gate out of _kill_safety_message).
    attacker, victim = _charmed_kill_setup()
    attacker.room.room_flags = 0
    result = do_kill(attacker, "wizard")
    assert result == "A dark wizard is your beloved master.", result
