"""DUPL-001b regression: ``combat/assist.py`` and ``skills/handlers.py``
``_send_to_char`` copies must not duplicate-deliver.

Both copies wrote to the async socket AND to ``char.messages`` (or
``char.send``).  The connection read loop drains ``char.messages`` after
the next command, so every assist/skill message would replay once per
prompt for connected PCs — the same single-delivery contract violation
fixed for DUPL-002 (``_push_message``) and DUPL-001 (conditions).

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-001b).
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


def test_combat_assist_send_to_char_single_delivery() -> None:
    from mud.combat.assist import _send_to_char as assist_send

    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = Character(name="Hero", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn
        assist_send(pc, "Hero rescues you!")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox = asyncio.run(scenario())
    assert len(conn.sent) == 1, f"async send fired {len(conn.sent)} times"
    assert mailbox == [], (
        "DUPL-001b: combat/assist _send_to_char duplicate-delivered to both "
        "async socket and char.messages — connection read loop would replay."
    )


def test_skills_handlers_send_to_char_single_delivery() -> None:
    from mud.skills.handlers import _send_to_char as skills_send

    async def scenario() -> tuple[_RecordingConn, list[str]]:
        pc = Character(name="Hero", is_npc=False)
        conn = _RecordingConn()
        pc.connection = conn
        skills_send(pc, "Your sanctuary fades.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn, list(pc.messages)

    conn, mailbox = asyncio.run(scenario())
    assert len(conn.sent) == 1, f"async send fired {len(conn.sent)} times"
    assert mailbox == [], (
        "DUPL-001b: skills/handlers _send_to_char duplicate-delivered to both "
        "async socket and char.messages — connection read loop would replay."
    )


def test_disconnected_fallback_still_works_both_modules() -> None:
    from mud.combat.assist import _send_to_char as assist_send
    from mud.skills.handlers import _send_to_char as skills_send

    pc1 = Character(name="ghost1", is_npc=False)
    pc2 = Character(name="ghost2", is_npc=False)
    assist_send(pc1, "msg1")
    skills_send(pc2, "msg2")

    assert any("msg1" in m for m in pc1.messages)
    assert "msg2" in pc2.messages
