"""INV-001 — the hand-rolled delivery helpers single-deliver to connected PCs.

Several modules carried their own copy of the "fire-and-forget + mailbox"
delivery helper that predated `push_message` and did BOTH channels:

    if writer: asyncio.create_task(send_to_char(...))   # live send
    if hasattr(x, "messages"): x.messages.append(...)    # AND mailbox

For a connected PC that double-delivers (async send now + mailbox drain on the
next prompt, `mud/net/connection.py:2002-2005`). These were migrated to
`push_message` (async-XOR-mailbox). This test exercises each migrated helper
directly with a connected PC (line once on the async channel, `messages == []`)
and a disconnected PC (mailbox fallback intact).

Covered: `mud/commands/group_commands.py:_send_to_char_sync`,
`mud/commands/thief_skills.py:_send_to_char_sync`,
`mud/mob_cmds.py:_append_message`, `mud/skills/handlers.py:_to_vict_send` and
`:_notvict_broadcast`.
"""

from __future__ import annotations

import asyncio

import pytest

from mud.commands.group_commands import _send_to_char_sync as group_send
from mud.commands.thief_skills import _send_to_char_sync as thief_send
from mud.mob_cmds import _append_message as mob_send
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import _notvict_broadcast, _to_vict_send


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str = "Conn") -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    return pc, conn


def _disconnected_pc(name: str = "Loner") -> Character:
    pc = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    pc.messages = []
    return pc


@pytest.mark.parametrize("helper", [group_send, thief_send, mob_send, _to_vict_send])
def test_single_recipient_helper_single_delivers_to_connected(helper) -> None:
    async def scenario():
        pc, conn = _connected_pc()
        helper(pc, "A test line.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(pc.messages)

    sent, mailbox = asyncio.run(scenario())
    assert sent.count("A test line.") == 1, f"{helper.__module__}.{helper.__name__}: sent={sent}"
    assert mailbox == [], f"{helper.__module__}.{helper.__name__} stranded line in mailbox: {mailbox}"


@pytest.mark.parametrize("helper", [group_send, thief_send, mob_send, _to_vict_send])
def test_single_recipient_helper_mailbox_fallback_when_disconnected(helper) -> None:
    pc = _disconnected_pc()
    helper(pc, "A test line.")
    assert pc.messages == ["A test line."], f"{helper.__module__}.{helper.__name__}: {pc.messages}"


def test_notvict_broadcast_single_delivers_and_excludes_actor_and_victim() -> None:
    async def scenario():
        room = Room(vnum=9460, name="R", description="", room_flags=0, sector_type=0)
        room.people = []
        actor, actor_conn = _connected_pc("Actor")
        victim, victim_conn = _connected_pc("Victim")
        bystander, bystander_conn = _connected_pc("Bystander")
        for c in (actor, victim, bystander):
            c.room = room
            room.people.append(c)
        _notvict_broadcast(room, actor, victim, "Something flashes.")
        for _ in range(5):
            await asyncio.sleep(0)
        return (
            actor_conn.sent,
            victim_conn.sent,
            bystander_conn.sent,
            list(bystander.messages),
        )

    actor_sent, victim_sent, bystander_sent, bystander_mailbox = asyncio.run(scenario())
    assert actor_sent == [], "actor must be excluded from TO_NOTVICT"
    assert victim_sent == [], "victim must be excluded from TO_NOTVICT"
    assert bystander_sent.count("Something flashes.") == 1, f"bystander sent={bystander_sent}"
    assert bystander_mailbox == [], f"bystander line stranded in mailbox: {bystander_mailbox}"
