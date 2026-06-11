"""RECALL-001 — do_recall combat recall must use gain_exp, not ch.exp -= lose.

ROM src/act_move.c:1609: ``gain_exp(ch, 0 - lose)``
ROM src/update.c:127: ``ch->exp = UMAX(exp_per_level(ch), ch->exp + gain)``

The XP floor prevents recall from pushing a player below their current level's
base XP threshold.  Python used ``ch.exp -= lose`` directly, which bypasses the
floor and can drive exp below the level floor.
"""

from __future__ import annotations

import pytest

from mud.advancement import exp_per_level
from mud.commands.session import do_recall
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_recall_exp_never_drops_below_floor() -> None:
    # mirrors ROM src/update.c:127 — UMAX(exp_per_level(ch), ch->exp + gain)
    # Use a non-temple room (3001 = ROOM_VNUM_TEMPLE) so recall actually fires.
    ch = create_test_character("Recaller", 2300)

    # Place exp just 10 above the level floor; lose=50 (no desc) would push below.
    floor = exp_per_level(ch)
    ch.exp = floor + 10
    ch.desc = None  # lose = 50 (no descriptor, ROM C line 1608)
    ch.position = int(Position.FIGHTING)
    ch.skills["recall"] = 0  # 80 * 0 // 100 = 0 → number_percent() < 0 is always False → success

    do_recall(ch, "")

    assert ch.exp >= floor, (
        f"RECALL-001: ch.exp ({ch.exp}) dropped below exp_per_level floor ({floor}) — "
        "do_recall must use gain_exp(ch, -lose), not ch.exp -= lose"
    )
