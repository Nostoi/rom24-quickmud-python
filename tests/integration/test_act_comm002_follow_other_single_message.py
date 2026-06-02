"""ACT_COMM-002 — normal `follow <other>` emits exactly one "You now follow X." message.

ROM `do_follow`'s success path (`src/act_comm.c:1586-1587`) calls
`add_follower(ch, victim)` and `return;` (void). The sole TO_CHAR emitter of the
follower's confirmation is `add_follower`'s
`act("You now follow $N.", ch, NULL, master, TO_CHAR)` (`:1605`) — `do_follow`
itself sends nothing.

Python's `add_follower` (`mud/commands/group_commands.py`) already appends
`"You now follow {master}."` to `char.messages`, **and then** `do_follow` *also*
returned `f"You now follow {victim}."`. The command loop sends the return value
*and* drains `char.messages`, so a connected actor saw the line twice. The fix
returns `""` from the success path, leaving `add_follower` the sole emitter to
match ROM's void return.
"""

from __future__ import annotations

from mud.commands.group_commands import do_follow
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9422) -> Room:
    room = Room(vnum=vnum, name="Follow Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_char(name: str, room: Room) -> Character:
    ch = Character(
        name=name,
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_follow_other_emits_single_named_message():
    # mirrors ROM src/act_comm.c:1586-1605 — do_follow calls add_follower (sole
    # TO_CHAR emitter) and returns void; the actor sees "You now follow X." once.
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        follower = _make_char("alice", room)
        master = _make_char("bob", room)

        result = do_follow(follower, "bob")

        # ROM returns void; add_follower already delivered the named line.
        assert result == ""
        follow_lines = [m for m in follower.messages if "you now follow" in m.lower()]
        assert follow_lines == ["You now follow bob."]
        assert follower.master is master
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
