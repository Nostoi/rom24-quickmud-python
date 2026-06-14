"""FIGHT-071 — do_dirt / do_trip charm-friend message + gate ORDER must match ROM.

``do_dirt`` and ``do_trip`` route their charmed-attacker-attacking-master check
through ``_kill_safety_message`` (do_kill's is_safe composite), which emits
do_kill's line — ``act("$N is your beloved master.", …)`` — at the TOP, *before*
the is_safe body. But ROM checks charm **last**, with per-command strings:

* do_dirt (src/fight.c:2544-2548): ``act("But $N is such a good friend!", …)`` —
  AFTER is_safe (2534) and kill-steal (2537).
* do_trip (src/fight.c:2705-2709): ``act("$N is your beloved master.", …)`` —
  AFTER is_safe (2675), kill-steal (2678), flying (2685), position (2691) and
  victim==ch (2697).

Two divergences therefore exist: do_dirt emits the WRONG STRING ("beloved
master" instead of "such a good friend"), and BOTH check charm in the WRONG
ORDER (a flying master should hear the flying line, not the charm line).
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_dirt, do_trip
from mud.models.constants import AffectFlag
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _charmed_attacker(skill: str, victim_flying: bool = False):
    attacker = create_test_character("Thrall", 3001)
    victim = create_test_character("wizard", 3001)
    victim.is_npc = True
    victim.short_descr = "a dark wizard"

    attacker.skills[skill] = 100
    attacker.wait = 0
    attacker.add_affect(AffectFlag.CHARM)
    attacker.master = victim

    if victim_flying:
        victim.add_affect(AffectFlag.FLYING)

    # Non-safe room so is_safe() does not pre-empt the charm gate.
    attacker.room.room_flags = 0

    return attacker, victim


def test_dirt_kick_charmed_master_uses_good_friend_message() -> None:
    # mirrors ROM src/fight.c:2544-2548 — do_dirt charm gate emits the
    # per-command "such a good friend" line, NOT do_kill's "beloved master".
    attacker, victim = _charmed_attacker("dirt kicking")
    result = do_dirt(attacker, "wizard")
    assert result == "But a dark wizard is such a good friend!", result


def test_trip_charmed_flying_master_hears_flying_line_not_charm() -> None:
    # mirrors ROM src/fight.c:2685-2689 vs 2705-2709 — flying is checked BEFORE
    # charm, so a charmed attacker tripping a flying master gets the flying line.
    attacker, victim = _charmed_attacker("trip", victim_flying=True)
    result = do_trip(attacker, "wizard")
    assert result == "Their feet aren't on the ground.", result


def test_trip_charmed_master_uses_beloved_master_message() -> None:
    # mirrors ROM src/fight.c:2705-2709 — do_trip charm gate (after is_safe,
    # kill-steal, flying, position and victim==ch) emits "beloved master".
    attacker, victim = _charmed_attacker("trip")
    result = do_trip(attacker, "wizard")
    assert result == "A dark wizard is your beloved master.", result
