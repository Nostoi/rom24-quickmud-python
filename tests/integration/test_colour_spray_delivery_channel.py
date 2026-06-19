"""INV-001 — colour_spray's caster flavor line must reach a connected PC on the
socket, not the mailbox alone.

ROM `spell_colour_spray` (`src/magic.c:1437`) routes the spray flavor through
`damage()` (the spell dam_message system) — a descriptor write, not a deferred
mailbox queue. The Python port emits a caster/target/room flavor triple; the
target and room legs already deliver via `_send_to_char` (INV-001, 2.12.72) but
the caster leg appended straight to `caster.messages`, the mailbox the
connection read loop only drains after the caster's *next* command. An idle
connected caster therefore would not see their own spray line at cast time
(INV-001 SINGLE-DELIVERY wrong-channel class, same shape as SPEC-017).

Fix: route the caster leg through `_send_to_char` too, matching its already-
migrated target/room siblings.
"""

from __future__ import annotations

import asyncio

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def test_colour_spray_caster_line_reaches_connected_caster_on_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario():
        room = Room(vnum=3001, name="Arena")
        caster = Character(name="Thera", level=24, is_npc=False, position=int(Position.STANDING))
        caster.messages = []
        conn = _RecordingConn()
        caster.connection = conn
        target = Character(name="Bandit", hit=120, position=int(Position.STANDING))
        target.messages = []
        for ch in (caster, target):
            room.add_character(ch)

        monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: True)
        skill_handlers.colour_spray(caster, target)
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())

    def is_spray(m: str) -> bool:
        return "red" in m and "blue" in m and "yellow" in m

    assert any(is_spray(m) for m in sent), f"caster spray line must reach connected caster's socket; sent={sent}"
    assert not any(is_spray(m) for m in mailbox), f"caster spray line stranded in mailbox for a connected PC: {mailbox}"
