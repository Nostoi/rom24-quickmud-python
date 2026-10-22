"""FIGHT-096 — check_assist's assist emote must render through ROM act() semantics.

ROM src/fight.c:121/173: do_function (rch, &do_emote, "screams and attacks!");
do_emote (src/act_comm.c) renders via act():

    act ("$n $T", ch, NULL, argument, TO_ROOM);
    act ("$n $T", ch, NULL, argument, TO_CHAR);

act_new resolves $n via PERS (NPC short_descr, can-see gated) and upper-cases the
first letter of each rendered line — observers see "The drunk screams and
attacks!" (capital T), and the emoting character receives its OWN line too
(TO_CHAR). The pre-fix Python _emote hand-rolled f"{char.name} {message}" from
the raw lowercase name and excluded the actor — surfaced by the first
check_assist_cross_room C-oracle capture (C: "The drunk screams and attacks!",
Python: "the drunk screams and attacks!").
"""

from __future__ import annotations

import pytest

from mud.combat.assist import _emote
from mud.world import create_test_character, initialize_world

# Midgaard temple — lit, so PERS(actor, observer) resolves the short_descr
# instead of "someone" (room 2300 is FOREST; visibility flaps on
# time_info.sunlight, the fragility test_fight053 documents).
_PLAIN_ROOM = 3001


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_fight096_emote_renders_act_capitalized_to_observers() -> None:
    """Observer sees the NPC short_descr capitalized — ROM act() line-start cap."""
    observer = create_test_character("Watcher", _PLAIN_ROOM)
    observer.is_npc = False
    observer.messages.clear()

    drunk = create_test_character("drunk", _PLAIN_ROOM)
    drunk.is_npc = True
    drunk.short_descr = "the drunk"

    _emote(drunk, "screams and attacks!")

    assert any("The drunk screams and attacks!" in msg for msg in observer.messages), (
        f"expected act()-capitalized NPC short_descr render; got {observer.messages!r}"
    )


def test_fight096_emote_reaches_the_actor_too() -> None:
    """ROM do_emote sends the TO_CHAR line — the emoting char sees its own emote."""
    observer = create_test_character("Watcher2", _PLAIN_ROOM)
    observer.is_npc = False

    drunk = create_test_character("drunk2", _PLAIN_ROOM)
    drunk.is_npc = True
    drunk.short_descr = "the drunk"
    drunk.messages.clear()

    _emote(drunk, "screams and attacks!")

    assert any("The drunk screams and attacks!" in msg for msg in drunk.messages), (
        f"expected ROM do_emote TO_CHAR self-line; got {drunk.messages!r}"
    )
