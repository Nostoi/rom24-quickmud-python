"""FIGHT-068 — do_bash must check victim position BEFORE the self-target check.

ROM ``do_bash`` (src/fight.c:2392-2403) checks ``victim->position < POS_FIGHTING``
("You'll have to let $M get back up first.", :2392-2397) **before** the
``victim == ch`` self-target check ("You try to bash your brains out, but
fail.", :2399-2403).  Python ``do_bash`` had the two early-return blocks in the
opposite order — it tested ``victim is char`` first.

Observable only in the edge case of bashing *yourself* while sitting/sleeping
(``position < POS_FIGHTING``): ROM emits the position line, Python emitted the
brains-out line.  This test bashes self while POS_SITTING and asserts the
position gate wins (ROM ordering).
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_bash
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_bash_self_while_sitting_hits_position_gate_first() -> None:
    # mirrors ROM src/fight.c:2392 — position check precedes the victim==ch check.
    basher = create_test_character("Basher", 3001)
    basher.skills["bash"] = 100
    basher.wait = 0
    basher.position = int(Position.SITTING)  # < POS_FIGHTING

    result = do_bash(basher, "Basher")

    assert result != "You try to bash your brains out, but fail.", (
        "do_bash checked victim==ch before position (FIGHT-068 order swap)"
    )
    assert "get back up first" in (result or ""), f"expected ROM position gate message, got {result!r}"
