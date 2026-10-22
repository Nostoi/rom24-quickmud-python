"""FIGHT-102 — combat commands carry no in-function wait-gates in ROM.

ROM enforces player wait at exactly ONE layer: the descriptor input loop
(src/comm.c:619-623 — typed input stays buffered while ch->wait > 0), which
Python mirrors in mud/net/connection.py. No ROM combat command reads
ch->wait at entry (the only wait READS in src/fight.c are multi_hit's
decrement :193, mob_hit's dispatch guard :305, damage()'s epilogue
:986/:996/:1009, and the disarm pickup check :2263; src/magic.c and
src/interp.c read it nowhere). Direct dispatch — ROM do_function (mobprogs,
mob_hit's off-skill switch, damage()'s auto-flee) — therefore executes the
command body even at wait > 0.

Python's do_kick/do_rescue/do_backstab/do_bash/do_berserk/do_cast each
carried a non-ROM `if wait > 0: return "You are still recovering."` gate
(do_flee's was removed as FIGHT-101). This file locks the class:

1. Grep-guard (Layer A, tests/test_rng_determinism.py idiom): the string
   must not reappear in mud/commands/combat.py.
2. Behavioral: a fighting char at wait 5 direct-dispatching kick executes
   the ROM body (roll + WAIT_STATE), not a recovery refusal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.combat.engine import set_fighting
from mud.commands.combat import do_kick
from mud.world import create_test_character, initialize_world

_ROOM = 3005
_COMBAT_PY = Path(__file__).resolve().parents[2] / "mud" / "commands" / "combat.py"


def test_no_wait_gate_pattern_in_combat_commands() -> None:
    """mirrors ROM src/comm.c:619-623 — wait is interpreter-level only; no
    combat command may re-check it in-function."""
    source = _COMBAT_PY.read_text(encoding="utf-8")
    assert "You are still recovering." not in source, (
        "non-ROM in-function wait-gate found in mud/commands/combat.py — ROM "
        "gates wait only at the descriptor input loop (src/comm.c:619-623); "
        "see FIGHT-101/FIGHT-102"
    )


@pytest.fixture()
def _world():
    initialize_world("area/area.lst")


def test_kick_executes_at_positive_wait(_world) -> None:
    """mirrors ROM src/fight.c:3113-3137 do_kick — no wait read anywhere; a
    directly-dispatched kick at wait 5 runs the skill body (and re-applies
    the ROM WAIT_STATE beats), never a recovery refusal."""
    char = create_test_character("Kicker", _ROOM)
    char.is_npc = False
    char.level = 20
    char.ch_class = 3  # warrior — kick trains at level 8 (KICK-001 class gate)
    char.desc = object()
    char.skills["kick"] = 75
    char.wait = 5

    victim = create_test_character("Punchbag", _ROOM)
    victim.is_npc = True
    victim.level = 10
    victim.max_hit = 500
    victim.hit = 500
    victim.desc = None
    set_fighting(char, victim)

    result = do_kick(char, "")

    assert result != "You are still recovering.", (
        "do_kick must execute its ROM body at wait > 0 (direct dispatch bypasses interpreter wait, src/comm.c:619-623)"
    )
    assert int(getattr(char, "wait", 0) or 0) > 5, "ROM WAIT_STATE(gsn_kick beats) must still apply"
