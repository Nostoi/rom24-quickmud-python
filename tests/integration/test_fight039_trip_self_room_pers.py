"""FIGHT-039 — trip self-trip lines: ``{5..{x`` colour, ``$n`` PERS, ``$s`` possessive.

When you trip yourself (``victim == ch``), ROM ``do_trip`` (`src/fight.c:2697-2703`)
emits two coloured lines:
  * ``:2699`` send_to_char — ``"{5You fall flat on your face!{x"`` to the tripper.
  * ``:2701`` act(TO_ROOM) — ``"{5$n trips over $s own feet!{x"``, so ``comm.c``
    renders ``$n`` per recipient via ``PERS`` (an invisible tripper masks to
    "someone") and ``$s`` as the tripper's gendered possessive (his/her/its),
    inside the ``{5``/``{x`` colour codes.

Python dropped the colour on the self line, and the room line baked the name
(no ``$n`` masking), used literal "their" (not ``$s``), dropped the colour, and
delivered via the ``messages.append`` mailbox channel instead of per-recipient
``act_to_room``.

ROM C: src/fight.c:2699-2701 (do_trip self-trip).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _lit_room(vnum: int = 3066) -> Room:
    room = Room(vnum=vnum, name="Court", sector_type=int(Sector.CITY))
    room.people = []
    return room


def test_trip_self_lines_colour_pers_and_possessive() -> None:
    caster = Character(name="Scout", level=20, is_npc=False, sex=int(Sex.MALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _lit_room()
    for ch in (caster, witness):
        room.add_character(ch)
    caster.messages.clear()
    witness.messages.clear()

    skill_handlers.trip(caster, caster)

    # ROM :2699 — coloured self line.
    assert "{5You fall flat on your face!{x" in caster.messages, caster.messages
    # ROM :2701 — $n→name (visible), $s→"his" (male), colour preserved.
    assert witness.messages[-1] == "{5Scout trips over his own feet!{x", witness.messages


def test_trip_self_room_line_masks_invisible_tripper() -> None:
    caster = Character(name="Scout", level=20, is_npc=False, sex=int(Sex.FEMALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _lit_room()
    for ch in (caster, witness):
        room.add_character(ch)
    caster.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    skill_handlers.trip(caster, caster)

    # Invisible tripper → $n masks to "Someone"; $s still renders "her".
    assert witness.messages[-1] == "{5Someone trips over her own feet!{x", witness.messages
