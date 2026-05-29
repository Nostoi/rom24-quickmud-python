"""Room/global broadcasts must reach a connected PC exactly ONCE (INV-001).

`mud/net/protocol.py:broadcast_room`/`broadcast_global` appended to BOTH the
async `send_to_char` task AND `char.messages` for every recipient. For a
connected PC that double-delivers: the async send fires immediately, and the
connection read loop (`mud/net/connection.py`) drains `char.messages` after the
next command — so every room broadcast (death/position-change/say/arrival
routed through these helpers) replayed once more on the next prompt. Same
SINGLE-DELIVERY contract as `_push_message`/INV-001 (and the FIGHT-020 `do_kill`
fix): a connected PC receives via the async send only; `char.messages` is the
mailbox fallback for disconnected characters and tests, never both.

Surfaced by the FIGHT-020 death-path delivery test, which saw the death
broadcasts (`{RVictim is DEAD!!{x`, `... hits the ground ... DEAD.`) delivered
twice to the connected killer.
"""

from __future__ import annotations

import asyncio

from mud.models.character import Character, character_registry
from mud.models.room import Room
from mud.net.protocol import broadcast_global, broadcast_room, send_to_char


class _RecordingConn:
    """Connection stub matching the duck-typed interface send_to_char uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


async def _deliver(pc: Character, conn: _RecordingConn) -> list[str]:
    """Replay the connection loop's post-command delivery: let the fire-and-forget
    async sends fire, then drain the mailbox (which must be empty for a PC)."""
    for _ in range(5):
        await asyncio.sleep(0)
    while pc.messages:
        await send_to_char(pc, pc.messages.pop(0))
    return list(conn.sent)


def test_broadcast_room_delivers_to_connected_pc_once() -> None:
    async def scenario() -> list[str]:
        room = Room(vnum=9100)
        pc = Character(name="Obs", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn
        room.add_character(pc)
        broadcast_room(room, "A dragon flies overhead.")
        return await _deliver(pc, conn)

    sent = asyncio.run(scenario())
    assert sent.count("A dragon flies overhead.") == 1, (
        f"broadcast_room delivered the line {sent.count('A dragon flies overhead.')}x "
        f"to the connected PC (expected 1 — SINGLE-DELIVERY/INV-001). Sends: {sent}"
    )


def test_broadcast_global_delivers_to_connected_pc_once() -> None:
    async def scenario() -> list[str]:
        pc = Character(name="Globber", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn
        character_registry.append(pc)
        try:
            broadcast_global("Someone shouts something.", channel="shout")
            return await _deliver(pc, conn)
        finally:
            character_registry.remove(pc)

    sent = asyncio.run(scenario())
    assert sent.count("Someone shouts something.") == 1, (
        f"broadcast_global delivered the line {sent.count('Someone shouts something.')}x "
        f"to the connected PC (expected 1 — SINGLE-DELIVERY/INV-001). Sends: {sent}"
    )


def test_broadcast_room_falls_back_to_mailbox_when_disconnected() -> None:
    """Disconnected characters / tests still queue to the mailbox (the existing
    contract that ~195 broadcast call sites and their tests rely on)."""
    room = Room(vnum=9101)
    npc = Character(name="ghost", is_npc=True)
    assert getattr(npc, "connection", None) is None
    room.add_character(npc)

    broadcast_room(room, "A chill passes through the room.")

    assert npc.messages == ["A chill passes through the room."]
