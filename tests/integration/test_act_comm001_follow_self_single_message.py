"""ACT_COMM-001 — `follow self` emits exactly one "stop following" message.

ROM `do_follow`'s self-target branch (`src/act_comm.c:1562-1571`), when the
actor is already following someone, calls `stop_follower(ch)` and **returns
silently** — the only message the actor sees is the
`act("You stop following $N.", ch, NULL, ch->master, TO_CHAR)` emitted *inside*
`stop_follower` (with the master's name).

Python's `do_follow` (`mud/commands/group_commands.py`) called
`stop_follower(char)` — which already appends `"You stop following {master}."`
to `char.messages` — **and then** returned a bare `"You stop following."` as the
TO_CHAR string, so the actor received the message twice (once named, once not).
The fix returns `""` from the self-branch, leaving `stop_follower` as the sole
emitter to match ROM's silent return.
"""

from __future__ import annotations

from mud.characters.follow import add_follower
from mud.commands.group_commands import do_follow
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9421) -> Room:
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


def test_follow_self_while_following_emits_single_named_message():
    # mirrors ROM src/act_comm.c:1569-1570 — `follow self` while following X calls
    # stop_follower (the sole message emitter) and returns silently.
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        follower = _make_char("alice", room)
        master = _make_char("bob", room)

        add_follower(follower, master)
        follower.messages = []  # discard the "You now follow bob." setup line

        result = do_follow(follower, "self")

        # ROM returns silently; stop_follower already delivered the named line.
        assert result == ""
        stop_lines = [m for m in follower.messages if "stop following" in m.lower()]
        assert stop_lines == ["You stop following bob."]
        assert follower.master is None
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)


def test_follow_self_without_master_unchanged():
    # ROM src/act_comm.c:1564-1567 — `follow self` with no master → "You already
    # follow yourself." (this branch is unaffected by the fix).
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        loner = _make_char("carol", room)

        assert do_follow(loner, "self") == "You already follow yourself."
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
