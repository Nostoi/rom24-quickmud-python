"""Magic effect messages must reach a connected PC exactly ONCE.

DUPL-002 regression: ``mud/magic/effects.py`` carried a divergent copy of
``_push_message`` that appended to ``char.messages`` even for connected
characters.  The connection read loop drains ``char.messages`` after the
next command, so every magic effect message replayed once — the same
duplicate-delivery bug that ``mud/combat/engine.py:_push_message`` already
fixed.

ROM ``src/comm.c:write_to_buffer`` writes once to the descriptor's output
buffer.  See ``docs/divergences/MESSAGE_DELIVERY.md`` and the audit row at
``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-002).
"""

from __future__ import annotations

import asyncio

from mud.magic.effects import _push_message
from mud.models.character import Character


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)

    async def close(self) -> None:
        self.closed = True


def test_magic_effect_message_single_delivery_for_connected_pc() -> None:
    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = Character(name="Eddol", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn

        _push_message(pc, "You feel a chill sink deep into your bones.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox_after = asyncio.run(scenario())

    assert len(conn.sent) == 1, f"async send fired {len(conn.sent)} times, expected 1"
    assert conn.sent[0] == "You feel a chill sink deep into your bones."
    assert mailbox_after == [], (
        "connected PCs must not have magic effect messages appended to "
        "char.messages — the connection read loop replays them after the "
        "next command (DUPL-002 duplicate-delivery bug)."
    )


def test_magic_effect_message_disconnected_falls_back_to_mailbox() -> None:
    npc = Character(name="ghost", is_npc=True)
    assert getattr(npc, "connection", None) is None

    _push_message(npc, "Your muscles stop responding.")

    assert npc.messages == ["Your muscles stop responding."]
