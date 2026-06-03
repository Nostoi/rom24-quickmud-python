"""ACT_COMM-003 — `stop_follower` delivers both lines on the right channel.

INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family. ROM
`stop_follower` (`src/act_comm.c:1625-1628`) writes both lines straight to the
descriptor via `act()` — immediate, single-channel delivery:

    act ("$n stops following you.", ch, NULL, ch->master, TO_VICT);  # master
    act ("You stop following $N.", ch, NULL, ch->master, TO_CHAR);   # follower

`add_follower` (the sibling primitive) was already migrated to `push_message`,
which routes a connected PC's line to the async socket send and falls back to
the `char.messages` mailbox only for disconnected chars / tests. But
`stop_follower` still used raw `char.messages.append(...)` for both lines — so a
**connected** PC dropped from a follow (e.g. `die_follower` iterating the
registry on a leader's extract/death, or charm wearing off mid-tick) received
the line **late**, on its next prompt's mailbox drain, instead of immediately
like ROM's `act()`.

Existing follow tests (`test_act_comm001_*`, `test_follow_can_see_gating`) use
**disconnected** chars, for which `push_message` falls back to the mailbox — so
they false-green against the unfixed code. This test uses **connected** PCs and
asserts the lines reach the connection channel with the mailbox left empty,
which is the only way to exercise the fix.
"""

from __future__ import annotations

import asyncio

from mud.characters.follow import add_follower, stop_follower
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _make_room(vnum: int = 9422) -> Room:
    room = Room(vnum=vnum, name="Follow Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _connected_pc(name: str, room: Room) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=10, room=room, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    room.people.append(pc)
    character_registry.append(pc)
    return pc, conn


def test_stop_follower_delivers_both_lines_on_connection_channel() -> None:
    # mirrors ROM src/act_comm.c:1625-1628 — both act() lines write to the
    # descriptor immediately; a connected PC must receive via the async push,
    # not the mailbox fallback.
    snapshot = list(character_registry)
    character_registry.clear()
    try:

        async def scenario():
            room = _make_room()
            follower, follower_conn = _connected_pc("alice", room)
            master, master_conn = _connected_pc("bob", room)

            add_follower(follower, master)
            # Let add_follower's own async push tasks fire, then clear setup state.
            for _ in range(5):
                await asyncio.sleep(0)
            follower_conn.sent.clear()
            master_conn.sent.clear()
            follower.messages.clear()
            master.messages.clear()

            stop_follower(follower)
            for _ in range(5):
                await asyncio.sleep(0)

            return (
                follower_conn.sent,
                follower.messages,
                master_conn.sent,
                master.messages,
            )

        follower_sent, follower_mailbox, master_sent, master_mailbox = asyncio.run(scenario())

        # TO_CHAR — follower sees "You stop following bob." on the async channel.
        assert any("stop following" in s.lower() for s in follower_sent), (
            f"follower's TO_CHAR line not on the async channel (MAGIC-003 wrong-channel shape); sent={follower_sent}"
        )
        assert follower_mailbox == [], f"follower line stranded in mailbox: {follower_mailbox}"

        # TO_VICT — master sees "alice stops following you." on the async channel.
        assert any("stops following you" in s.lower() for s in master_sent), (
            f"master's TO_VICT line not on the async channel (MAGIC-003 wrong-channel shape); sent={master_sent}"
        )
        assert master_mailbox == [], f"master line stranded in mailbox: {master_mailbox}"
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9422, None)
