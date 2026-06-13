"""MOBCMD-021 — mpasound capitalizes buf[0] like ROM act().

ROM `do_mpasound` (`src/mob_cmds.c`) temporarily relocates the mob into each
adjacent room and emits `act(argument, ch, NULL, NULL, TO_ROOM)`, which capitalizes
the first visible char (`src/comm.c:2376-2379`). The Python's `_broadcast` to each
adjacent room sent the message raw, so a sound beginning with a lowercase word
leaked lowercase to listeners in neighbouring rooms.
"""

from __future__ import annotations

from mud.mob_cmds import do_mpasound
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Exit, Room


def test_mobcmd021_mpasound_capitalizes_buf0():
    room_a = Room(vnum=99221, name="Cavern")
    room_b = Room(vnum=99222, name="Tunnel")
    room_a.exits[0] = Exit(to_room=room_b)

    mob = Character(name="goblinmob", is_npc=True, short_descr="a cave goblin", position=int(Position.STANDING))
    room_a.add_character(mob)
    listener = Character(name="Wanderer", is_npc=False, position=int(Position.STANDING))
    room_b.add_character(listener)
    listener.messages = []

    do_mpasound(mob, "the cavern echoes with a distant roar.")

    assert any("The cavern echoes with a distant roar." in m for m in listener.messages), listener.messages
