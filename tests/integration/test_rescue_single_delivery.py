"""`rescue` must SINGLE-DELIVER each line and push them to the right channel.

FIGHT-029 / INV-001 SINGLE-DELIVERY family — the `do_rescue`/`do_surrender`
shape. ROM `do_rescue` (`src/fight.c:3089-3091`) is **void** and writes all
three success lines straight to the descriptor via `act()`:

    act ("{5You rescue $N!{x", ch, NULL, victim, TO_CHAR);   # rescuer
    act ("{5$n rescues you!{x", ch, NULL, victim, TO_VICT);  # victim
    act ("{5$n rescues $N!{x", ch, NULL, victim, TO_NOTVICT);# room

There is no return-value channel. The Python port had two distinct bugs:

1. **Rescuer double-delivery** (the `do_kill`/FIGHT-020 shape): `rescue()`
   did `caster.messages.append(char_msg)` AND `do_rescue` returned that same
   line. The connection loop (`mud/net/connection.py`) sends a command's
   return value AND drains `char.messages`, so a connected PC rescuer received
   "You rescue X!" **twice**.

2. **Victim/room wrong-channel** (the MAGIC-003 shape): the TO_VICT and
   TO_NOTVICT lines were appended to `target.messages` / `occupant.messages`
   only. `char.messages` is a fallback for disconnected chars / tests
   (`mud/utils/messaging.py`, AGENTS.md "Message Delivery"); a **connected**
   victim/bystander must receive via the async `send_to_char` push so the line
   reaches their live prompt immediately, not on their next command's drain.

A pure double-delivery count test (the kill template) catches (1) but
**false-greens on (2)** — the victim/room legs are not duplicated, just
delayed in the mailbox. So this file splits the shape: rescuer → count-once;
victim + bystander → push-present + mailbox-empty (the MAGIC-003 template).
"""

from __future__ import annotations

import asyncio

from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.utils import rng_mm


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


def test_rescue_single_delivers_all_three_legs_to_connected_pcs(monkeypatch) -> None:
    # Force the rescue skill check to succeed so the three success legs fire.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    async def scenario():
        room = Room(vnum=9300, name="Battlefield")
        rescuer, rescuer_conn = _connected_pc("Rescuer", room)
        ally, ally_conn = _connected_pc("Ally", room)
        witness, witness_conn = _connected_pc("Witness", room)

        foe = Character(name="Ogre", is_npc=True, level=20, position=int(Position.FIGHTING))
        room.add_character(foe)

        # Ally is the tank under attack; rescuer + ally are grouped so the
        # NPC-opponent kill-stealing guard (src/fight.c:3075) is satisfied.
        ally.leader = rescuer
        ally.fighting = foe
        ally.position = int(Position.FIGHTING)
        foe.fighting = ally
        rescuer.skills["rescue"] = 100
        rescuer.wait = 0

        # Mirror mud/net/connection.py's per-command delivery for the actor:
        # send the command's return value, let the fire-and-forget push tasks
        # fire, then drain the actor's mailbox (must be empty by INV-001).
        response = process_command(rescuer, "rescue Ally")
        await send_to_char(rescuer, response)
        for _ in range(5):
            await asyncio.sleep(0)
        while rescuer.messages:
            await send_to_char(rescuer, rescuer.messages.pop(0))

        # The victim/bystander are NOT actors this tick — they must already have
        # received via the async push. Do NOT drain their mailboxes.
        return (
            rescuer_conn.sent,
            ally_conn.sent,
            ally.messages,
            witness_conn.sent,
            witness.messages,
        )

    rescuer_sent, ally_sent, ally_mailbox, witness_sent, witness_mailbox = asyncio.run(scenario())

    # (1) Rescuer success line delivered exactly ONCE (no return-value double).
    rescuer_lines = [s for s in rescuer_sent if "You rescue" in s]
    assert len(rescuer_lines) == 1, (
        f"rescuer success line delivered {len(rescuer_lines)}x to connected PC "
        f"(expected 1 — SINGLE-DELIVERY/FIGHT-029). Sent: {rescuer_sent}"
    )

    # (2a) Victim line on the async push channel, mailbox left empty.
    assert any("rescues you" in s for s in ally_sent), (
        f"victim line not on the async channel (MAGIC-003 wrong-channel shape); sent={ally_sent}"
    )
    assert ally_mailbox == [], f"victim line stranded in mailbox: {ally_mailbox}"

    # (2b) Room broadcast on the bystander's push channel, mailbox empty.
    assert any("rescues Ally" in s for s in witness_sent), (
        f"room line not on the async channel (MAGIC-003 wrong-channel shape); sent={witness_sent}"
    )
    assert witness_mailbox == [], f"room line stranded in mailbox: {witness_mailbox}"
