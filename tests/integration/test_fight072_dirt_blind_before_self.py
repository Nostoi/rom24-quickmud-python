"""FIGHT-072 — do_dirt must check AFF_BLIND BEFORE the self-target check.

ROM ``do_dirt`` (src/fight.c:2522-2532) checks ``IS_AFFECTED(victim, AFF_BLIND)``
("$E's already been blinded.", :2522-2526) **before** the ``victim == ch``
self-target check ("Very funny.", :2528-2532).  Python ``do_dirt`` had the two
early-return blocks in the opposite order — it tested ``victim is char`` first.

Observable only when dirt-kicking *yourself* while already blind: ROM emits the
blind line, Python emitted "Very funny.".  This test dirt-kicks self while
AFF_BLIND and asserts the blind gate wins (ROM ordering).  Sibling of FIGHT-068.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_dirt
from mud.models.constants import AffectFlag
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_dirt_self_while_blind_hits_blind_gate_first() -> None:
    # mirrors ROM src/fight.c:2522 — AFF_BLIND check precedes the victim==ch check.
    kicker = create_test_character("Kicker", 3001)
    kicker.skills["dirt kicking"] = 100
    kicker.affected_by = int(getattr(kicker, "affected_by", 0) or 0) | int(AffectFlag.BLIND)

    result = do_dirt(kicker, "Kicker")

    assert result != "Very funny.", "do_dirt checked victim==ch before AFF_BLIND (FIGHT-072 order swap)"
    assert "blind" in (result or "").lower(), f"expected ROM blind gate message, got {result!r}"
