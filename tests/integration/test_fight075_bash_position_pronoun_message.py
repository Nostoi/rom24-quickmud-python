"""FIGHT-075 — do_bash position-gate message renders ROM's ``$M`` pronoun.

ROM ``do_bash`` (src/fight.c:2394) emits
``act("You'll have to let $M get back up first.", ch, NULL, victim, TO_CHAR)``
— ``$M`` is the *objective* pronoun of the victim (him/her/it).  Python
``do_bash`` (~combat.py:446) returned the literal "You'll have to let them get
back up first." — no ``$M`` rendering.

Same act()-render class as FIGHT-073/TRIP-001/FIGHT-064.  This test bashes a
male victim who is sitting (``position < POS_FIGHTING``) and asserts the message
renders "him" rather than the literal "them".
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_bash
from mud.models.constants import Position, Sex
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_bash_position_message_renders_objective_pronoun() -> None:
    # mirrors ROM src/fight.c:2394 — act("...$M...") renders victim objective pronoun.
    basher = create_test_character("Basher", 3001)
    basher.skills["bash"] = 100
    basher.wait = 0

    victim = create_test_character("Victim", 3001)
    victim.sex = int(Sex.MALE)
    victim.position = int(Position.SITTING)  # < POS_FIGHTING

    result = do_bash(basher, "Victim")

    assert "get back up first" in (result or ""), f"expected position gate message, got {result!r}"
    assert "him" in (result or ""), f"expected ROM $M pronoun render ('him'), got {result!r}"
    assert "them" not in (result or ""), f"literal 'them' should be replaced by $M, got {result!r}"
