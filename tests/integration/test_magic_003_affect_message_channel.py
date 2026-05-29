"""MAGIC-003 — affect spells must deliver via the canonical single-delivery
channel (``_send_to_char``/``push_message``), not the raw ``char.messages``
mailbox (INV-001 SINGLE-DELIVERY family).

ROM ``spell_shield``/``spell_sanctuary``/``spell_blindness``/``spell_weaken``
each send a victim line (``send_to_char`` TO_VICT) and a room broadcast
(``act`` TO_ROOM). The Python handlers applied the affect correctly but
delivered those lines by appending directly to ``target.messages`` /
``occupant.messages``. Per ``mud/utils/messaging.py`` (DUPL-002) and AGENTS.md
"Message Delivery", ``char.messages`` is a fallback for tests and disconnected
characters only — a **connected** PC must receive via the async
``send_to_char`` task fired by ``push_message`` (so combat/magic output reaches
the live prompt immediately, mirroring ROM ``write_to_buffer``). A raw
``.append`` strands the line in the mailbox until the next command drains it,
so a connected bystander sees the room broadcast late (and the differential
harness, reading the descriptor, sees nothing).

Mailbox-only assertions cannot catch this: for a *disconnected* char both
``push_message`` and a raw ``.append`` land in ``.messages``. These tests use
**connected** PCs and assert the line arrives on the connection's immediate
send channel, with the mailbox left empty.

ROM C: src/magic.c:4326-4327 (spell_shield), :4296-4297 (spell_sanctuary),
:888-889 (spell_blindness), :4580-4581 (spell_weaken).
"""

from __future__ import annotations

import asyncio

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers


class _RecordingConn:
    """Connection stub matching the duck-typed interface send_to_char uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str, room: Room, *, level: int = 30) -> tuple[Character, _RecordingConn]:
    pc = Character(
        name=name,
        is_npc=False,
        level=level,
        ch_class=0,
        perm_stat=[18, 18, 18, 18, 18],
        position=int(Position.STANDING),
    )
    conn = _RecordingConn()
    pc.connection = conn
    pc.messages = []
    room.add_character(pc)
    return pc, conn


# (handler, self/victim line, room-broadcast line for a caster named "Caster")
_CASES = [
    ("shield", "You are surrounded by a force shield.", "Caster is surrounded by a force shield."),
    ("sanctuary", "You are surrounded by a white aura.", "Caster is surrounded by a white aura."),
    ("blindness", "You are blinded!", "Caster appears to be blinded."),
    ("weaken", "You feel your strength slip away.", "Caster looks tired and weak."),
]


@pytest.mark.parametrize("handler_name,self_msg,room_msg", _CASES)
def test_affect_spell_delivers_to_connected_pc_via_async_channel(
    monkeypatch, handler_name, self_msg, room_msg
) -> None:
    # blindness/weaken roll saves_spell; force the affect to land so the
    # delivery channel — not the save roll — is what's under test.
    monkeypatch.setattr(handlers, "saves_spell", lambda *a, **k: False)
    handler = getattr(handlers, handler_name)

    async def scenario():
        room = Room(vnum=99300, name="Chapel")
        caster, caster_conn = _connected_pc("Caster", room)
        bystander, bystander_conn = _connected_pc("Witness", room)

        # Self-cast (target == caster): the victim line goes to the caster, the
        # room broadcast goes to the bystander (the TO_ROOM act excludes $n).
        applied = handler(caster, caster)
        assert applied, f"{handler_name} affect should have applied"

        # Let the fire-and-forget async sends fire (do NOT drain .messages — a
        # connected PC must already have received via the connection).
        for _ in range(5):
            await asyncio.sleep(0)
        return caster_conn.sent, caster.messages, bystander_conn.sent, bystander.messages

    caster_sent, caster_mailbox, bystander_sent, bystander_mailbox = asyncio.run(scenario())

    # Victim line: delivered on the caster's connection, mailbox left empty.
    assert self_msg in caster_sent, f"{handler_name}: victim line not on async channel; sent={caster_sent}"
    assert caster_mailbox == [], f"{handler_name}: victim line stranded in mailbox: {caster_mailbox}"

    # Room broadcast: delivered on the bystander's connection, mailbox empty.
    assert room_msg in bystander_sent, f"{handler_name}: room line not on async channel; sent={bystander_sent}"
    assert bystander_mailbox == [], f"{handler_name}: room line stranded in mailbox: {bystander_mailbox}"


@pytest.mark.parametrize("handler_name,self_msg", [(h, s) for h, s, _ in _CASES])
def test_affect_spell_falls_back_to_mailbox_when_disconnected(monkeypatch, handler_name, self_msg) -> None:
    """Disconnected characters / tests still queue to the mailbox — the
    ~existing contract that the mailbox-reading affect tests rely on."""
    monkeypatch.setattr(handlers, "saves_spell", lambda *a, **k: False)
    handler = getattr(handlers, handler_name)

    room = Room(vnum=99301, name="Chapel")
    caster = Character(
        name="Hermit",
        is_npc=False,
        level=30,
        ch_class=0,
        perm_stat=[18, 18, 18, 18, 18],
        position=int(Position.STANDING),
    )
    caster.messages = []
    room.add_character(caster)
    assert getattr(caster, "connection", None) is None

    applied = handler(caster, caster)
    assert applied
    assert any(self_msg in m for m in caster.messages), caster.messages
