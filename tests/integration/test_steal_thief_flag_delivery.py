"""INV-001 — the "*** You are now a THIEF!! ***" promotion line must reach a
connected PC on the socket, not the mailbox alone.

ROM `src/act_obj.c:2256-2261` (`do_steal` failure, PC-on-PC) sets `PLR_THIEF`
and writes the promotion line via `send_to_char` — a single delivery channel to
the descriptor.  The Python port's `_steal_failure` (`mud/commands/thief_skills.py`)
appended straight to `char.messages`, the mailbox the connection read loop only
drains after the player's NEXT command.  A connected thief therefore would not
see "*** You are now a THIEF!! ***" until they typed something — the INV-001
SINGLE-DELIVERY wrong-channel class (same shape as SPEC-017).

Fix: route the line through `_send_to_char_sync` → `push_message` (loop-aware:
async socket for connected PCs, mailbox fallback for tests/disconnected).
"""

from __future__ import annotations

import asyncio

from mud.commands.thief_skills import _steal_failure
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=20, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    return pc, conn


def test_thief_promotion_reaches_connected_thief_on_socket() -> None:
    async def scenario():
        room = Room(vnum=3001, name="Temple", description="", room_flags=0, sector_type=0)
        room.people = []

        thief, thief_conn = _connected_pc("Thief")
        thief.room = room
        victim, _ = _connected_pc("Victim")
        victim.room = room
        room.people.extend([thief, victim])

        _steal_failure(thief, victim)
        for _ in range(5):
            await asyncio.sleep(0)
        return thief_conn.sent, list(thief.messages)

    sent, mailbox = asyncio.run(scenario())
    promo = "*** You are now a THIEF!! ***\n"
    assert sent.count(promo) == 1, f"THIEF promotion must reach the connected thief's socket; sent={sent}"
    assert promo not in mailbox, f"THIEF promotion stranded in mailbox for a connected PC: {mailbox}"


def test_thief_promotion_mailbox_fallback_when_disconnected() -> None:
    """Disconnected/test fallback: with no connection the line lands in the mailbox."""
    room = Room(vnum=3001, name="Temple", description="", room_flags=0, sector_type=0)
    room.people = []

    thief = Character(name="Thief", is_npc=False, level=20, position=int(Position.STANDING))
    thief.messages = []
    thief.room = room
    victim = Character(name="Victim", is_npc=False, level=20, position=int(Position.STANDING))
    victim.messages = []
    victim.room = room
    room.people.extend([thief, victim])

    _steal_failure(thief, victim)

    assert "*** You are now a THIEF!! ***\n" in thief.messages
