"""INV-001 — remaining inline delivery sites single-deliver to connected PCs.

Second batch of the INV-001 wrong-channel sweep: inline (non-helper) sites that
did `if writer: create_task(send_to_char(...))` + unconditional
`*.messages.append(...)` (double-delivery) or a bare cross-character mailbox
append (late). All migrated to `push_message` / `_send_to_char` (async-XOR-
mailbox). This covers the cleanly-isolable surfaces:

- `mud/combat/engine.py:_broadcast_pos_change` (position-transition room line) — double.
- `mud/commands/position.py:do_wake` (`$n wakes you.` TO_VICT) — double.
- `mud/skills/say_spell.py:broadcast_spell_words` (spell incantation) — cross-char late.

(`mud/wiznet.py` is a deliberate exception — its reconnect-announce callers run
synchronously outside an event loop, so `push_message`'s `create_task` would
raise; left mailbox-only and filed for a dedicated fix.)

The load-bearing assertion is `recipient.messages == []` with a CONNECTED
recipient (pre-fix the line is stranded/duplicated in the mailbox; post-fix the
async channel is the sole delivery). The other migrated inline sites this batch
(combat split, liquids pour, give changer, several handlers spell loops) share
the exact same one-line swap and are guarded by the full suite.
"""

from __future__ import annotations

import asyncio

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str, room: Room | None = None, *, ch_class: int = 0) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING), ch_class=ch_class)
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    if room is not None:
        pc.room = room
        room.people.append(pc)
    return pc, conn


def _room(vnum: int) -> Room:
    r = Room(vnum=vnum, name="R", description="", room_flags=0, sector_type=0)
    r.people = []
    return r


def test_broadcast_pos_change_single_delivers_to_connected_listener() -> None:
    from mud.combat.engine import _broadcast_pos_change

    async def scenario():
        room = _room(9470)
        victim, _ = _connected_pc("Victim", room)
        listener, conn = _connected_pc("Listener", room)
        _broadcast_pos_change(victim, "{name} collapses to the ground.")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(listener.messages)

    sent, mailbox = asyncio.run(scenario())
    hits = [s for s in sent if "collapses" in s.lower()]
    assert len(hits) == 1, f"pos-change delivered {len(hits)}x on async channel; sent={sent}"
    assert mailbox == [], f"pos-change line stranded in mailbox (double-delivery): {mailbox}"


def test_do_wake_single_delivers_to_connected_victim() -> None:
    from mud.commands.position import do_wake

    async def scenario():
        room = _room(9471)
        waker, _ = _connected_pc("Waker", room)
        victim, conn = _connected_pc("Sleeper", room)
        victim.position = int(Position.SLEEPING)
        do_wake(waker, "Sleeper")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(victim.messages)

    sent, mailbox = asyncio.run(scenario())
    hits = [s for s in sent if "wakes you" in s.lower()]
    assert len(hits) == 1, f"wake delivered {len(hits)}x on async channel; sent={sent}"
    assert mailbox == [], f"wake line stranded in mailbox (double-delivery): {mailbox}"


def test_say_spell_words_single_deliver_to_connected_occupant() -> None:
    from mud.skills.say_spell import broadcast_spell_words

    async def scenario():
        room = _room(9472)
        caster, _ = _connected_pc("Caster", room, ch_class=0)
        occupant, conn = _connected_pc("Occupant", room, ch_class=0)
        broadcast_spell_words(caster, "armor")
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(occupant.messages)

    sent, mailbox = asyncio.run(scenario())
    assert len(sent) == 1, f"say-spell delivered {len(sent)}x on async channel; sent={sent}"
    assert mailbox == [], f"say-spell line stranded in mailbox: {mailbox}"
