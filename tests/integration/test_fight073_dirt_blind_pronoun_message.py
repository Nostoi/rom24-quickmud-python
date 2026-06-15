"""FIGHT-073 — do_dirt BLIND message must render ROM's `$E` pronoun + wording.

ROM ``do_dirt`` (src/fight.c:2524) emits
``act("$E's already been blinded.", ch, NULL, victim, TO_CHAR)`` — ``$E`` is the
subjective pronoun of the victim (He/She/It, first letter capitalized by
act_new's buf[0] kludge).  Python ``do_dirt`` returned the literal
``"They're already blinded."`` — no ``$E`` rendering, wrong wording ("They're"
vs "$E's", "blinded" vs "been blinded").

This test dirt-kicks an already-blind MALE victim and asserts the rendered ROM
message ("He's already been blinded.").  Same act()-rendering class as
FIGHT-073's siblings TRIP-001/FIGHT-064.
"""

from __future__ import annotations

import pytest

from mud.commands.combat import do_dirt
from mud.models.constants import AffectFlag, Sex
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_dirt_blind_message_renders_subjective_pronoun() -> None:
    # mirrors ROM src/fight.c:2524 — act("$E's already been blinded.", ...).
    kicker = create_test_character("Kicker", 3001)
    kicker.skills["dirt kicking"] = 100

    victim = create_test_character("Victim", 3001)
    victim.sex = Sex.MALE
    victim.affected_by = int(getattr(victim, "affected_by", 0) or 0) | int(AffectFlag.BLIND)

    result = do_dirt(kicker, "Victim")

    assert result == "He's already been blinded.", f"expected ROM $E-rendered blind line, got {result!r}"
