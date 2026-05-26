"""Probe: do_follow must notify the master and the follower per ROM.

ROM ``src/act_comm.c:1591-1607 add_follower``:

    void add_follower (CHAR_DATA * ch, CHAR_DATA * master)
    {
        ...
        if (can_see (master, ch))
            act ("$n now follows you.", ch, NULL, master, TO_VICT);
        act ("You now follow $N.", ch, NULL, master, TO_CHAR);
    }

The TO_VICT broadcast is load-bearing: without it, the master never
learns someone began following them — they cannot decide whether to
allow it, nofollow, or order their new tag-along.

Python has two parallel ``add_follower`` implementations:

- ``mud/characters/follow.py:add_follower`` (emits both messages,
  matches ROM).
- ``mud/commands/group_commands.py:add_follower`` (silent, no
  messages).

The command dispatcher registers
``mud/commands/group_commands.py:do_follow`` (`mud/commands/dispatcher.py:114, 320`),
which calls the silent variant. So players' ``follow X`` does NOT
notify X. ROM-divergent at the load-bearing command entry point.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9410) -> Room:
    room = Room(vnum=vnum, name="Follow Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def test_do_follow_notifies_master():
    """ROM src/act_comm.c:1603 — master sees `$n now follows you.`."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()

        follower = Character(
            name="follower",
            is_npc=False,
            level=10,
            room=room,
            position=int(Position.STANDING),
        )
        follower.messages = []
        room.people.append(follower)
        character_registry.append(follower)

        master = Character(
            name="master",
            is_npc=False,
            level=10,
            room=room,
            position=int(Position.STANDING),
        )
        master.messages = []
        room.people.append(master)
        character_registry.append(master)

        process_command(follower, "follow master")

        # ROM: master sees "follower now follows you."
        joined_master = "\n".join(master.messages).lower()
        assert (
            "follower" in joined_master and "now follows you" in joined_master
        ), (
            f"master must receive `$n now follows you.` broadcast "
            f"(ROM src/act_comm.c:1603); master.messages = {master.messages!r}"
        )

        # ROM: follower sees "You now follow master."
        joined_follower = "\n".join(follower.messages).lower()
        assert (
            "now follow" in joined_follower and "master" in joined_follower
        ), (
            f"follower must receive `You now follow $N.` "
            f"(ROM src/act_comm.c:1605); follower.messages = {follower.messages!r}"
        )

        # State assertions: master/leader fields per ROM lines 1599-1600.
        assert follower.master is master
        assert follower.leader is None
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9410, None)
