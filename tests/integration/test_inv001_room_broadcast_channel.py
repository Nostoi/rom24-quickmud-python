"""INV-001 — Room.broadcast single-delivers to a connected occupant.

ROOM-BCAST-001 / INV-001 SINGLE-DELIVERY. `Room.broadcast` is a primitive used
across production paths (mob speech `spec_funs`, reconnect / link-loss
`mud/net/connection.py`, item zap `mud/groups/xp.py`, AI `mud/ai`, mob commands
`mud/mob_cmds.py`). Its own docstring says connected chars receive the line
"immediately via fire-and-forget asyncio task. The queue fallback exists for
tests." — but the code did BOTH: `if writer: create_task(send_to_char(...))`
AND an unconditional `char.messages.append(...)`. For a connected occupant the
async send arrives immediately and the connection read loop
(`mud/net/connection.py:2002-2005`) drains the mailbox on the next prompt → the
line is delivered **twice**. (`broadcast_room`/`broadcast_global` in
`mud/net/protocol.py` were fixed to XOR in 2.11.6; `Room.broadcast` was the
parallel primitive that was missed.)

Existing Room.broadcast tests use **disconnected** chars (mailbox-only → count
1) and so false-green against the doubled code. This test uses a connected
occupant and asserts the line once on the async channel with `messages == []`.
"""

from __future__ import annotations

import asyncio

from mud.models.constants import Position
from mud.models.room import Room


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str, room: Room) -> tuple[object, _RecordingConn]:
    from mud.models.character import Character

    pc = Character(name=name, is_npc=False, level=10, room=room, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    room.people.append(pc)
    return pc, conn


def test_room_broadcast_single_delivers_to_connected_occupant() -> None:
    async def scenario():
        room = Room(vnum=9450, name="Broadcast Room", description="", room_flags=0, sector_type=0)
        room.people = []
        listener, conn = _connected_pc("Listener", room)
        room.broadcast("A bell tolls in the distance.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(listener.messages)

    sent, mailbox = asyncio.run(scenario())
    delivered = [s for s in sent if "bell tolls" in s.lower()]
    assert len(delivered) == 1, f"Room.broadcast delivered {len(delivered)}x on async channel; sent={sent}"
    assert mailbox == [], f"Room.broadcast line stranded in mailbox (double-delivery): {mailbox}"


def test_room_broadcast_disconnected_occupant_uses_mailbox() -> None:
    # The mailbox fallback must still work for a disconnected char (tests / linkdead).
    from mud.models.character import Character

    room = Room(vnum=9451, name="Broadcast Room", description="", room_flags=0, sector_type=0)
    room.people = []
    loner = Character(name="Loner", is_npc=False, level=10, room=room, position=int(Position.STANDING))
    loner.messages = []
    room.people.append(loner)

    room.broadcast("A bell tolls in the distance.")

    assert any("bell tolls" in m.lower() for m in loner.messages), (
        f"disconnected occupant must receive via mailbox fallback; messages={loner.messages}"
    )
