"""DUPL-001 (conditions.py) regression: hunger/thirst/sober messages must
reach a connected PC's socket.

ROM ``src/handler.c:gain_condition`` calls ``send_to_char`` directly,
which in ROM writes to the descriptor's output buffer.  Python's
``mud/characters/conditions.py`` had a local ``_send_to_char`` stub that
appended ONLY to ``char.messages`` — connected players never received
hunger/thirst/sober notifications because the production delivery path
goes through ``asyncio.create_task(send_to_char(...))``, not the
``messages`` mailbox (which exists for tests / disconnected chars only,
per ``docs/divergences/MESSAGE_DELIVERY.md``).

After the DUPL-001 partial close, ``conditions.py`` delegates to
``mud/utils/messaging.py:send_to_char_buffered``.

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-001).
"""

from __future__ import annotations

import asyncio

from mud.characters.conditions import gain_condition
from mud.models.character import Character
from mud.models.constants import Condition


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


class _PCData:
    def __init__(self) -> None:
        # Hunger=0 (will fire), thirst=0, drunk=0
        self.condition = [0, 0, 0, 0]


def _make_pc(name: str) -> Character:
    pc = Character(name=name, is_npc=False, level=10)
    pc.pcdata = _PCData()
    return pc


def test_gain_condition_hunger_delivers_to_connected_pc() -> None:
    """Connected PCs must receive 'You are hungry.' on the async send channel."""

    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = _make_pc("Eddol")
        conn = _RecordingConn()
        pc.connection = conn

        # Pre-condition: hunger slot was 1 (about to tick to 0 and fire).
        pc.pcdata.condition[int(Condition.HUNGER)] = 1
        gain_condition(pc, Condition.HUNGER, -1)

        # Yield to let asyncio.create_task fire.
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox_after = asyncio.run(scenario())

    assert "You are hungry." in conn.sent, (
        "connected PC did not receive 'You are hungry.' on the socket — "
        "DUPL-001 conditions.py messages-only fallback regression. "
        "ROM src/handler.c:gain_condition calls send_to_char directly."
    )
    # Single-delivery contract: must NOT also be in mailbox.
    assert mailbox_after == [], (
        "duplicate-delivery: message appeared on both async socket AND "
        "char.messages — connection read loop would replay it."
    )


def test_gain_condition_thirst_delivers_to_disconnected_via_mailbox() -> None:
    pc = _make_pc("ghost")
    assert getattr(pc, "connection", None) is None

    pc.pcdata.condition[int(Condition.THIRST)] = 1
    gain_condition(pc, Condition.THIRST, -1)

    assert pc.messages == ["You are thirsty."]
