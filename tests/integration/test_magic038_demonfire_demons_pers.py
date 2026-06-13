"""MAGIC-038 — demonfire's "demons of Hell" lines use PERS + ROM TO_ROOM topology.

ROM `spell_demonfire` (`src/magic.c`):
  - `act("$n calls forth the demons of Hell upon $N!", ch, NULL, victim, TO_ROOM)`
  - `act("$n has assailed you with the demons of Hell!", ch, NULL, victim, TO_VICT)`
  - `send_to_char("You conjure forth the demons of hell!\n\r", ch)`

`$n` = PERS(actor=caster), `$N` = PERS(victim). TO_ROOM = every occupant EXCEPT the
actor (caster) — so the **victim also receives** the "calls forth" line. The Python
baked the keywords AND excluded the victim from the room loop (TO_NOTVICT topology).
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import demonfire


def test_magic038_demonfire_calls_forth_is_to_room_includes_victim_with_pers():
    room = Room(vnum=99212, name="Pit")
    caster = Character(
        name="Warlock", level=40, ch_class=0, is_npc=False, alignment=-1000, position=int(Position.STANDING)
    )
    room.add_character(caster)
    caster.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    observer = Character(name="Witness", is_npc=False, position=int(Position.STANDING))
    room.add_character(observer)
    observer.messages = []

    demonfire(caster, target=goblin)

    expected = "Warlock calls forth the demons of Hell upon a green goblin!"
    # TO_ROOM reaches the observer AND the victim; never the caster (the actor).
    assert any(expected in m for m in observer.messages), observer.messages
    assert any(expected in m for m in goblin.messages), goblin.messages
    assert not any("calls forth" in m for m in caster.messages), caster.messages
    # TO_VICT: the victim is addressed in 2nd person.
    assert any("Warlock has assailed you with the demons of Hell!" in m for m in goblin.messages), goblin.messages
