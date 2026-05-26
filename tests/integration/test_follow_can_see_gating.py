"""FOLLOW-001 / FOLLOW-002 — can_see gating on add_follower and stop_follower.

ROM ``src/act_comm.c:1602-1605`` (add_follower) and ``1625-1629``
(stop_follower) gate the TO_VICT/TO_CHAR "$n now follows you." /
"$n stops following you." broadcasts on ``can_see(master, ch)``
(plus ``ch->in_room != NULL`` on stop). Without those gates, an
invisible follower whose master lacks DETECT_INVIS still announces
itself — leaking the follower's identity.

``mud/characters/follow.py`` (the copy wired into combat death, shop
hires, skill handlers, and mob_cmds) emitted both messages
unconditionally. ``mud/commands/group_commands.py`` (the do_follow
command path) was already correct — see DUPL-018 in
``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md``.
"""

from __future__ import annotations

from mud.characters.follow import add_follower, stop_follower
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9420) -> Room:
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


def test_follow_001_add_follower_gates_master_message_on_can_see():
    """ROM src/act_comm.c:1602-1603 — `$n now follows you.` only when can_see(master, ch)."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        follower = _make_char("invisfollower", room)
        master = _make_char("master", room)

        # Follower is invisible; master lacks DETECT_INVIS → can_see is False.
        follower.add_affect(AffectFlag.INVISIBLE)

        add_follower(follower, master)

        joined_master = "\n".join(master.messages).lower()
        assert "now follows you" not in joined_master, (
            f"master must NOT see `$n now follows you.` when can_see(master, follower) "
            f"is False (ROM src/act_comm.c:1602); master.messages = {master.messages!r}"
        )

        # Follower-side message is unconditional (ROM line 1605).
        joined_follower = "\n".join(follower.messages).lower()
        assert "now follow" in joined_follower and "master" in joined_follower, (
            f"follower must still see `You now follow $N.` (ROM src/act_comm.c:1605); "
            f"follower.messages = {follower.messages!r}"
        )
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9420, None)


def test_follow_002_stop_follower_gates_both_messages_on_can_see_and_in_room():
    """ROM src/act_comm.c:1625-1629 — gated on can_see(master, ch) && in_room != NULL."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        follower = _make_char("invisfollower", room)
        master = _make_char("master", room)

        # Establish following relationship with visible follower so add_follower
        # delivers its messages normally.
        add_follower(follower, master)
        follower.messages.clear()
        master.messages.clear()

        # Now make follower invisible — master cannot see them.
        follower.add_affect(AffectFlag.INVISIBLE)

        stop_follower(follower)

        joined_master = "\n".join(master.messages).lower()
        assert "stops following you" not in joined_master, (
            f"master must NOT see `$n stops following you.` when can_see(master, "
            f"follower) is False (ROM src/act_comm.c:1625-1626); "
            f"master.messages = {master.messages!r}"
        )
        joined_follower = "\n".join(follower.messages).lower()
        assert "stop following" not in joined_follower, (
            f"follower must NOT see `You stop following $N.` when the can_see/in_room "
            f"gate is False (ROM src/act_comm.c:1625-1628); "
            f"follower.messages = {follower.messages!r}"
        )

        # State: detach still happens regardless of visibility.
        assert follower.master is None
        assert follower.leader is None
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9420, None)


def test_follow_002_stop_follower_skips_messages_when_in_room_is_none():
    """ROM src/act_comm.c:1625 — also gated on ch->in_room != NULL."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        follower = _make_char("ghost", room)
        master = _make_char("master", room)

        add_follower(follower, master)
        follower.messages.clear()
        master.messages.clear()

        # Detach follower from any room (mimics extracted/transferred state).
        if follower in room.people:
            room.people.remove(follower)
        follower.room = None

        stop_follower(follower)

        joined_master = "\n".join(master.messages).lower()
        assert "stops following you" not in joined_master, (
            f"master must NOT see message when follower->in_room is NULL "
            f"(ROM src/act_comm.c:1625); master.messages = {master.messages!r}"
        )
        assert follower.master is None
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9420, None)
