"""MOBCMD-020 — mpecho/mpechoaround/mpechoat capitalize buf[0] like ROM act().

ROM `do_mpecho` (`src/mob_cmds.c`) emits `act(argument, ch, NULL, NULL, TO_ROOM)`,
`do_mpechoaround` `act(argument, ch, NULL, victim, TO_NOTVICT)`, and `do_mpechoat`
`act(argument, ch, NULL, victim, TO_VICT)`. ROM's `act()` capitalizes the first
visible char of the delivered buffer (`src/comm.c:2376-2379`). The Python sent the
(already program-expanded) message raw, so a line that begins with an expanded
lowercase NPC short_descr leaked lowercase.
"""

from __future__ import annotations

from mud.mob_cmds import do_mpecho, do_mpechoaround, do_mpechoat
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def _room_with_actors() -> tuple[Character, Character, Character]:
    room = Room(vnum=99220, name="Cavern")
    mob = Character(name="goblinmob", is_npc=True, short_descr="a cave goblin", position=int(Position.STANDING))
    room.add_character(mob)
    mob.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    bystander = Character(name="Bystander", is_npc=False, position=int(Position.STANDING))
    room.add_character(bystander)
    bystander.messages = []
    return mob, goblin, bystander


def test_mobcmd020_mpecho_capitalizes_buf0():
    mob, _, bystander = _room_with_actors()
    do_mpecho(mob, "the ground trembles violently.")
    assert any("The ground trembles violently." in m for m in bystander.messages), bystander.messages


def test_mobcmd020_mpechoaround_capitalizes_buf0():
    mob, goblin, bystander = _room_with_actors()
    do_mpechoaround(mob, "goblin the cave walls shake.")
    assert any("The cave walls shake." in m for m in bystander.messages), bystander.messages
    assert not any("shake" in m for m in goblin.messages), goblin.messages


def test_mobcmd020_mpechoat_capitalizes_buf0():
    mob, goblin, _ = _room_with_actors()
    do_mpechoat(mob, "goblin you stagger from the blow.")
    assert any("You stagger from the blow." in m for m in goblin.messages), goblin.messages
