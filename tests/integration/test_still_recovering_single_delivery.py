"""`"You are still recovering."` must SINGLE-DELIVER to a connected PC.

INV-001 (d) — SINGLE-DELIVERY family, the FIGHT-029 fail-path shape. Seven
`mud/commands/combat.py` commands (`do_kick`, `do_rescue`, `do_backstab`,
`do_bash`, `do_berserk`, `do_flee`, `do_cast`) gate on the wait-state and, when
the actor is still recovering, did ``char.messages.append("You are still
recovering.")`` **and** ``return "You are still recovering."``. The connection
read loop (`mud/net/connection.py:1980-2000`) sends a command's return value AND
drains ``char.messages``, so a connected PC received the line **twice** — the
exact INV-001 double-delivery shape fixed for `do_kill` (FIGHT-020),
`do_surrender`, and `do_rescue` (FIGHT-029).

The message itself is NOT a ROM line — ROM gates wait at the interpreter level
(silent). INV-001 (d) is delivery-channel only: the fix keeps the return (the
single canonical delivery) and drops the mailbox append. The message-existence
divergence is out of scope here.

NOTE on `mud/skills/registry.py:163`: it also appends "You are still
recovering." but is deliberately EXCLUDED from this sweep — it `raise`s
``ValueError("still recovering")`` rather than returning the line, has no
production callers (only tests call ``SkillRegistry.use``), and the connection
loop sends a generic error string on exception, never the exception text. So its
append is a single mailbox delivery in a test-only path, not a double. The
"drop append, keep return" fix structurally does not apply (there is no return).
See `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` INV-001 (d).

This file follows the grep-guard idiom (`tests/test_rng_determinism.py`,
`tests/test_equipment_key_convention.py`): the scanner locks every site —
including any future re-addition — while the behavioral test demonstrates the
single delivery end-to-end.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.skills import load_skills


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str, room: Room, *, level: int = 30) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=level, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    room.add_character(pc)
    return pc, conn


def test_no_still_recovering_mailbox_append_in_combat_commands() -> None:
    """Grep-guard: no combat command may append the recovery line to the mailbox.

    Locks all 7 wait-state sites (and any future re-addition) in one assertion —
    the line must reach a connected PC via the command's return value only, not
    also via the drained ``char.messages`` mailbox (INV-001 SINGLE-DELIVERY).
    """
    path = Path("mud/commands/combat.py")
    offenders: list[str] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        code = line.split("#", 1)[0]  # ignore comments that cite the anti-pattern
        if 'append("You are still recovering.")' in code or "append('You are still recovering.')" in code:
            offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "combat command appends the recovery line to char.messages AND returns it "
        "— the connection loop sends the return AND drains the mailbox, so a "
        "connected PC sees it twice (INV-001 SINGLE-DELIVERY). Drop the append, "
        "keep the return:\n" + "\n".join(offenders)
    )


def test_kick_while_recovering_delivers_recovery_line_once() -> None:
    """Behavioral: a connected PC sees "You are still recovering." exactly once."""

    # The kick skill must be registered or do_kick's wait-guard (under
    # `if skill is not None`) is never reached.
    load_skills(Path("data/skills.json"))

    async def scenario():
        room = Room(vnum=9400, name="Arena")
        pc, conn = _connected_pc("Kicker", room, level=60)
        mob = Character(name="Ogre", is_npc=True, level=20, position=int(Position.FIGHTING))
        room.add_character(mob)

        pc.fighting = mob
        pc.position = int(Position.FIGHTING)
        mob.fighting = pc
        pc.skills["kick"] = 100
        pc.wait = 10  # already recovering → the wait-state guard fires

        # Mirror mud/net/connection.py's per-command delivery: send the return
        # value, let any fire-and-forget push tasks fire, then drain the mailbox.
        response = process_command(pc, "kick")
        await send_to_char(pc, response)
        for _ in range(5):
            await asyncio.sleep(0)
        while pc.messages:
            await send_to_char(pc, pc.messages.pop(0))
        return conn.sent

    sent = asyncio.run(scenario())

    recovering = [s for s in sent if "still recovering" in s]
    assert len(recovering) == 1, (
        f"recovery line delivered {len(recovering)}x to connected PC (expected 1 "
        f"— SINGLE-DELIVERY/INV-001 (d)). Sent: {sent}"
    )
