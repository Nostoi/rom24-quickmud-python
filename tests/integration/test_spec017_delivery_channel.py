"""SPEC-017 — spec_funs flavor messages reach connected PCs on the socket.

`mud/spec_funs.py:_append_message` was the last surviving "mailbox-only"
delivery helper after the INV-001 SINGLE-DELIVERY sweep (2.11.6–2.13.10)
migrated every other copy onto `push_message`:

    def _append_message(target, message):
        inbox = getattr(target, "messages", None)
        if isinstance(inbox, list):
            inbox.append(message)        # mailbox ONLY — never the socket

ROM `src/comm.c:act` writes spec-fun flavor (`$n utters the word 'fido'.`,
the mayor's proclamation, the janitor's pickups, fido gore, thief steal,
poison hiss, breath weapons …) straight to each recipient's descriptor via
`write_to_buffer`. For a *connected* PC the Python helper instead dropped the
line in `char.messages`, which the connection read loop only drains after the
player's NEXT command (`mud/net/connection.py`). An idle web-client player
watching the adept in the cage room therefore never saw the casting
announcement on a game tick — the user-visible "friendly mobs aren't casting"
symptom. Every spec-fun that narrates via `_broadcast_room` /
`_broadcast_room_message` inherited the same wrong channel.

Fix: route `_append_message` through `push_message` (loop-aware: async socket
send for connected PCs, mailbox fallback for tests/disconnected). This is the
INV-001 wrong-channel cousin — identical to the `mud/mob_cmds.py:_append_message`
migration in the 2.12.71 sweep.
"""

from __future__ import annotations

import asyncio

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.spec_funs import _append_message, _broadcast_room


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str = "Conn") -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    return pc, conn


def _disconnected_pc(name: str = "Loner") -> Character:
    pc = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    pc.messages = []
    return pc


def test_append_message_single_delivers_to_connected_pc() -> None:
    async def scenario():
        pc, conn = _connected_pc()
        _append_message(pc, "The healer utters the word 'fido'.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(pc.messages)

    sent, mailbox = asyncio.run(scenario())
    assert sent.count("The healer utters the word 'fido'.") == 1, (
        f"spec_funs._append_message must deliver to a connected PC's socket; sent={sent}"
    )
    assert mailbox == [], f"line stranded in mailbox for a connected PC: {mailbox}"


def test_append_message_mailbox_fallback_when_disconnected() -> None:
    pc = _disconnected_pc()
    _append_message(pc, "The healer utters the word 'fido'.")
    assert pc.messages == ["The healer utters the word 'fido'."], pc.messages


def test_broadcast_room_flavor_reaches_connected_bystander() -> None:
    """End-to-end: a spec-fun room broadcast (e.g. the adept's cast flavor)
    reaches an idle connected PC on the socket at tick time, not the mailbox."""

    async def scenario():
        room = Room(vnum=9461, name="Cage", description="", room_flags=0, sector_type=0)
        room.people = []

        mob = Character(name="the healer", is_npc=True, level=20, position=int(Position.STANDING))
        mob.room = room
        bystander, conn = _connected_pc("Watcher")
        bystander.room = room
        room.people.extend([mob, bystander])

        _broadcast_room(mob, "$n utters the word 'fido'.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(bystander.messages)

    sent, mailbox = asyncio.run(scenario())
    assert sent.count("The healer utters the word 'fido'.") == 1, f"bystander sent={sent}"
    assert mailbox == [], f"bystander flavor stranded in mailbox: {mailbox}"
