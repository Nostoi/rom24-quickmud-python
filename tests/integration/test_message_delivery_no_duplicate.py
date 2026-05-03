"""Combat messages must reach a connected PC exactly ONCE.

Regression for the live death-path bug where the WS client showed every
combat message twice — once via the immediate ``asyncio.create_task``
send in ``_push_message`` and again when ``mud/net/connection.py``'s
read loop drained ``char.messages`` after the next command.

ROM ``src/comm.c:write_to_buffer`` writes once to the descriptor's
output buffer; there is no replay channel. Per
``docs/divergences/MESSAGE_DELIVERY.md``, ``char.messages`` is the
queue fallback for disconnected characters and tests — connected PCs
must not also append to it.
"""

from __future__ import annotations

import asyncio
from typing import List

from mud.combat.engine import _push_message
from mud.models.character import Character


class _RecordingConn:
    """Minimal connection stub matching the duck-typed interface that
    ``mud.net.protocol.send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: List[str] = []
        self.closed = False

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)

    async def close(self) -> None:
        self.closed = True


def test_connected_pc_receives_message_once_no_mailbox_replay() -> None:
    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = Character(name="Eddol", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn

        _push_message(pc, "the lizard scratches you.")
        # Yield to let the asyncio.create_task fire.
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox_after = asyncio.run(scenario())

    assert len(conn.sent) == 1, f"async send fired {len(conn.sent)} times, expected 1"
    assert conn.sent[0] == "the lizard scratches you."
    assert mailbox_after == [], (
        "connected PCs must not have messages appended to char.messages — "
        "the connection.py read loop will drain it and replay every combat "
        "message after the next command (duplicate-delivery bug)."
    )


def test_disconnected_character_falls_back_to_mailbox() -> None:
    """Disconnected characters and tests still queue to mailbox.

    This preserves the existing test contract documented in
    ``docs/divergences/MESSAGE_DELIVERY.md``.
    """
    npc = Character(name="ghost", is_npc=True)
    assert getattr(npc, "connection", None) is None

    _push_message(npc, "you feel a chill.")

    assert npc.messages == ["you feel a chill."]
