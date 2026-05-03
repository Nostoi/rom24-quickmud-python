"""End-to-end regression: PC dies, then a follow-up command must not
replay the combat sequence.

Live repro from `~/mud-death.log` (2026-05-02T22:07:53→22:08:11) showed
the WS client receiving every combat message TWICE: once during the
death tick (immediate async send) and again after the player's next
``look`` (because ``mud/net/connection.py`` drained ``char.messages``
which had also been appended unconditionally).

After the fix in ``mud/combat/engine.py:_push_message`` (commit chain
beginning with the prompt-clamp fix), connected PCs receive each
message exactly once and ``char.messages`` is not used as a
secondary delivery channel.
"""

from __future__ import annotations

import asyncio
from typing import List

from mud.combat.engine import _push_message
from mud.models.character import Character


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: List[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)

    async def close(self) -> None:
        pass


def test_combat_messages_then_drain_does_not_replay() -> None:
    """Simulate the live death sequence:
    1. Combat tick pushes several messages to a connected PC.
    2. ``connection.py``'s read loop later drains ``pc.messages`` after
       the next command.
    3. The drain must not re-send messages that already went out via
       the async path.
    """

    async def scenario() -> tuple[list[str], list[str]]:
        pc = Character(name="Eddol", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn

        for line in [
            "the lizard scratches you.",
            "the lizard grazes you.",
            "You are mortally wounded, and will die soon, if not aided.",
            "the lizard grazes you.",
            "You have been KILLED!!",
        ]:
            _push_message(pc, line)

        # Drain the asyncio.create_task queue before any "next command".
        for _ in range(10):
            await asyncio.sleep(0)

        sent_during_tick = list(conn.sent)
        # Confirm the production path did not also stash anything in the
        # mailbox — this is the invariant the previous bug violated.
        assert pc.messages == [], pc.messages

        # Now drive the connection.py drain loop manually — same shape as
        # mud/net/connection.py:1756-1762 after process_command returns.
        from mud.net.protocol import send_to_char

        while pc.messages:
            msg = pc.messages.pop(0)
            await send_to_char(pc, msg)

        return sent_during_tick, list(conn.sent)

    sent_during_tick, sent_after_drain = asyncio.run(scenario())

    assert sent_during_tick.count("You have been KILLED!!") == 1
    assert sent_after_drain.count("You have been KILLED!!") == 1, (
        "KILLED!! was replayed by the read-loop drain — the duplicate-"
        "delivery bug is back."
    )
    assert len(sent_after_drain) == len(sent_during_tick), (
        "drain re-sent messages that already went out via the async path"
    )
