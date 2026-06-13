"""MAGIC-036 — dispel_evil/good TO_ROOM "protected" lines use PERS + $S, exclude actor.

ROM (`src/magic.c`, both `act(…, ch, NULL, victim, TO_ROOM)`):
  - `spell_dispel_evil` is_good `:2024` `act("Mota protects $N.", …, TO_ROOM)`
  - `spell_dispel_good` is_evil `:2053` `act("$N is protected by $S evil.", …, TO_ROOM)`

TO_ROOM = every occupant EXCEPT the actor (caster). `$N` = PERS(victim) (NPC
short_descr, capitalized at buf[0]); `$S` = victim's possessive (his/her/its). The
Python baked the keyword `name`, used "name's evil" instead of `$S`, AND
over-delivered the line to the caster (ROM TO_ROOM excludes the actor).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import dispel_evil, dispel_good


def _setup(victim_alignment: int) -> tuple[Character, Character, Character]:
    room = Room(vnum=99210, name="Arena")
    caster = Character(name="Mage", level=40, ch_class=0, is_npc=False, alignment=0, position=int(Position.STANDING))
    room.add_character(caster)
    caster.messages = []
    goblin = Character(
        name="goblin",
        is_npc=True,
        short_descr="a green goblin",
        alignment=victim_alignment,
        position=int(Position.STANDING),
    )
    room.add_character(goblin)
    witness = Character(name="Watcher", is_npc=False, alignment=0, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []
    return caster, goblin, witness


def test_magic036_dispel_evil_good_victim_mota_protects_to_room_excludes_caster():
    caster, goblin, witness = _setup(victim_alignment=1000)

    assert dispel_evil(caster, target=goblin) == 0
    # TO_ROOM: the witness (not the caster) receives the PERS-rendered, capitalized line.
    assert any("Mota protects a green goblin." in m for m in witness.messages), witness.messages
    assert not any("Mota protects" in m for m in caster.messages), caster.messages


def test_magic036_dispel_good_evil_victim_protected_by_S_evil_to_room_excludes_caster():
    caster, goblin, witness = _setup(victim_alignment=-1000)

    assert dispel_good(caster, target=goblin) == 0
    # $N caps buf[0]; $S = victim possessive (sexless NPC -> "its").
    assert any("A green goblin is protected by its evil." in m for m in witness.messages), witness.messages
    assert not any("is protected by" in m for m in caster.messages), caster.messages
