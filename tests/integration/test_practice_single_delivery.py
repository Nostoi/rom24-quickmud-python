"""`do_practice` self lines must SINGLE-DELIVER to a connected PC.

INV-001 SINGLE-DELIVERY. `mud/commands/advancement.py:do_practice` built its
``"You practice $T."`` / ``"You are now learned at $T."`` line, appended it to
``char.messages`` (the mailbox) **and** returned it. The connection read loop
(`mud/net/connection.py:1980-2020`) sends a command's return value AND drains
``char.messages``, so a connected PC saw every practice line **twice** — the
exact double-delivery shape fixed for `do_kill` (FIGHT-020) and the combat
wait-state lines (INV-001 (d)). Observed live: ``practice magic`` printed
"You practice magic missile." twice per invocation.

ROM `src/act_info.c:2777-2788` delivers the self line via ``act(..., TO_CHAR)``
(one delivery) and the room line via ``act(..., TO_ROOM)``. The fix keeps the
return value (the single canonical self delivery) and the ``act_to_room``
broadcast, and drops the mailbox append.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import ActFlag, Position
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.skills import load_skills


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def test_no_practice_self_line_mailbox_append() -> None:
    """Grep-guard: do_practice must not append its self line to the mailbox.

    The self line must reach a connected PC via the command's return value only,
    not also via the drained ``char.messages`` mailbox (INV-001).
    """
    path = Path("mud/commands/advancement.py")
    offenders: list[str] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        code = line.split("#", 1)[0]
        if "char.messages.append(char_msg)" in code or "messages.append(char_msg)" in code:
            offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "do_practice appends its self line to char.messages AND returns it — the "
        "connection loop sends the return AND drains the mailbox, so a connected "
        "PC sees it twice (INV-001 SINGLE-DELIVERY). Drop the append, keep the "
        "return:\n" + "\n".join(offenders)
    )


def test_practice_line_delivers_once_to_connected_pc() -> None:
    """Behavioral: a connected PC sees the practice line exactly once."""

    load_skills(Path("data/skills.json"))

    async def scenario():
        room = Room(vnum=9410, name="Guild")
        pc = Character(name="Prentice", is_npc=False, level=10, position=int(Position.STANDING))
        pc.messages = []
        conn = _RecordingConn()
        pc.connection = conn
        room.add_character(pc)
        pc.practice = 5
        pc.skills["dagger"] = 1

        # A practice trainer (ACT_PRACTICE) in the room so do_practice proceeds.
        trainer = Character(name="Guildmaster", is_npc=True, level=30, position=int(Position.STANDING))
        trainer.act = int(ActFlag.PRACTICE)
        room.add_character(trainer)

        response = process_command(pc, "practice dagger")
        await send_to_char(pc, response)
        for _ in range(5):
            await asyncio.sleep(0)
        while pc.messages:
            await send_to_char(pc, pc.messages.pop(0))
        return conn.sent

    sent = asyncio.run(scenario())

    practice_lines = [s for s in sent if "dagger" in s.lower() and ("practice" in s.lower() or "learned" in s.lower())]
    assert len(practice_lines) == 1, (
        f"practice self line delivered {len(practice_lines)}x to connected PC "
        f"(expected 1 — INV-001 SINGLE-DELIVERY). Sent: {sent}"
    )
