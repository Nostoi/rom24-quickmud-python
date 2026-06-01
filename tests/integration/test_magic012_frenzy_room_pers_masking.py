"""Regression for MAGIC-012 (probe of FINDING-015 / INV-025 sweep, 2026-06-01).

ROM ``spell_frenzy`` (`src/magic.c:2961`) broadcasts the success room line as
``act("$n gets a wild look in $s eyes!", victim, NULL, NULL, TO_ROOM)``, so
``comm.c`` renders ``$n`` per recipient via ``PERS(victim, to)`` (an invisible
victim masks to "someone") and ``$s`` as the victim's gendered possessive
(his/her/its).

The Python ``frenzy`` handler baked ``_character_name(victim)`` and the literal
"their eyes" into a manual ``for occupant in room.people`` loop — neither masking
an invisible victim (INV-027) nor matching ROM's gendered possessive. The
INV-025 PERS-masking sweep converted ``_act_room`` call sites but missed handlers
using a hand-rolled room loop like this one.

ROM C: src/magic.c:2961 (spell_frenzy success room broadcast).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room(vnum: int = 3033) -> Room:
    room = Room(vnum=vnum, name="Arena")
    room.people = []
    return room


def test_frenzy_room_line_uses_gendered_possessive() -> None:
    caster = Character(name="Cleric", level=24, is_npc=False, alignment=400)
    target = Character(name="Paladin", level=20, is_npc=False, alignment=350, sex=int(Sex.MALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _room()
    for ch in (caster, target, witness):
        room.add_character(ch)
    witness.messages.clear()

    assert skill_handlers.frenzy(caster, target) is True

    # ROM `$s` → gendered possessive; a male victim renders "his", not "their".
    assert witness.messages[-1] == "Paladin gets a wild look in his eyes!", witness.messages


def test_frenzy_room_line_masks_invisible_victim() -> None:
    caster = Character(name="Cleric", level=24, is_npc=False, alignment=400)
    target = Character(name="Paladin", level=20, is_npc=False, alignment=350, sex=int(Sex.FEMALE))
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _room()
    for ch in (caster, target, witness):
        room.add_character(ch)
    # Witness cannot see an invisible victim → ROM `$n` masks to "someone"
    # (capitalized "Someone" at sentence start).
    target.add_affect(AffectFlag.INVISIBLE)
    witness.messages.clear()

    assert skill_handlers.frenzy(caster, target) is True

    assert witness.messages[-1] == "Someone gets a wild look in her eyes!", witness.messages
