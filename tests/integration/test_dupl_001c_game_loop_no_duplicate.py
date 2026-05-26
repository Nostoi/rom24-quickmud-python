"""DUPL-001c regression: ``mud.game_loop._send_to_char`` must not double-deliver.

ROM C ``write_to_buffer`` writes once to the socket. Our Python equivalent
``mud.utils.messaging.push_message`` mirrors that: if the character has a
connection, schedule an async write and RETURN; only fall through to the
``messages`` mailbox when there is no connection.

The previous ``game_loop._send_to_char`` did both unconditionally —
connected PCs received the message via the async task AND via the
connection-drain loop emptying ``char.messages``
(``mud/net/connection.py:1966, 2240``). Tick-driven messages (plague,
light flicker, decay, etc.) were duplicated for every connected player.

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-001c).
"""

from __future__ import annotations

import asyncio

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


def test_game_loop_send_to_char_single_delivery() -> None:
    from mud.game_loop import _send_to_char as game_loop_send

    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = Character(name="Hero", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn
        game_loop_send(pc, "You writhe in agony from the plague.\r\n")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox = asyncio.run(scenario())
    assert len(conn.sent) == 1, f"async send fired {len(conn.sent)} times"
    assert mailbox == [], (
        "DUPL-001c: game_loop._send_to_char duplicate-delivered to both "
        "async socket and char.messages — connection read loop would replay."
    )


def test_game_loop_send_to_char_falls_back_to_mailbox_for_disconnected_char() -> None:
    from mud.game_loop import _send_to_char as game_loop_send

    pc = Character(name="ghost", is_npc=False)
    game_loop_send(pc, "You shiver and suffer.\r\n")
    assert any("shiver" in m for m in pc.messages)
