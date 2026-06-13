"""FOLLOW-003 — "$n now follows you."/"$n stops following you." capitalize buf[0].

ROM `add_follower`/`stop_follower` (`src/act_comm.c:1603/1628`) deliver the
master-facing lines via `act("$n now follows you.", ch, NULL, master, TO_VICT)` /
`act("$n stops following you.", …)`, which capitalize the first visible char
(`src/comm.c:2376-2379`). The Python baked a lowercase `_display_name(follower)`, so
an NPC follower "a green goblin" rendered "a green goblin now follows you." vs ROM
"A green goblin …".
"""

from __future__ import annotations

from mud.characters.follow import add_follower, stop_follower
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def _pair() -> tuple[Character, Character]:
    room = Room(vnum=99224, name="Trail")
    master = Character(name="Ranger", is_npc=False, position=int(Position.STANDING))
    room.add_character(master)
    master.messages = []
    goblin = Character(name="goblin", is_npc=True, short_descr="a green goblin", position=int(Position.STANDING))
    room.add_character(goblin)
    goblin.messages = []
    return master, goblin


def test_followcap_add_follower_master_line_capitalized():
    master, goblin = _pair()
    add_follower(goblin, master)
    assert any("A green goblin now follows you." in m for m in master.messages), master.messages


def test_followcap_stop_follower_master_line_capitalized():
    master, goblin = _pair()
    add_follower(goblin, master)
    master.messages = []
    stop_follower(goblin)
    assert any("A green goblin stops following you." in m for m in master.messages), master.messages
