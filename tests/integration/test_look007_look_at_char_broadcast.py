"""LOOK-007 — looking at a character broadcasts ROM show_char_to_char_1 lines.

ROM `show_char_to_char_1` (`src/act_info.c:438-446`), gated by `can_see(victim, ch)`:
  - self-look: `act("$n looks at $mself.", ch, NULL, NULL, TO_ROOM)`
  - look at other: `act("$n looks at you.", ch, NULL, victim, TO_VICT)` +
    `act("$n looks at $N.", ch, NULL, victim, TO_NOTVICT)`

The Python `_look_char` returned only the description string and emitted no
broadcast at all — the victim was never told they were being looked at, and the
room saw nothing.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position, Sex
from mud.models.room import Room
from mud.world.look import look


def _setup() -> tuple[Character, Character, Character]:
    room = Room(vnum=99223, name="Plaza")
    char = Character(name="Bob", is_npc=False, sex=int(Sex.MALE), position=int(Position.STANDING))
    room.add_character(char)
    char.messages = []
    elf = Character(name="elf", is_npc=True, short_descr="a tall elf", position=int(Position.STANDING))
    room.add_character(elf)
    elf.messages = []
    witness = Character(name="Wanda", is_npc=False, position=int(Position.STANDING))
    room.add_character(witness)
    witness.messages = []
    return char, elf, witness


def test_look007_look_at_other_broadcasts_to_vict_and_notvict():
    char, elf, witness = _setup()

    look(char, "elf")

    # TO_VICT: the looked-at character is told.
    assert any("Bob looks at you." in m for m in elf.messages), elf.messages
    # TO_NOTVICT: the room sees it (PERS), but not the victim.
    assert any("Bob looks at a tall elf." in m for m in witness.messages), witness.messages
    assert not any("Bob looks at a tall elf." in m for m in elf.messages), elf.messages
    # The looker is not spammed with their own look broadcast.
    assert not any("looks at" in m for m in char.messages), char.messages


def test_look007_look_at_self_broadcasts_to_room():
    char, _, witness = _setup()

    look(char, "Bob")

    assert any("Bob looks at himself." in m for m in witness.messages), witness.messages
