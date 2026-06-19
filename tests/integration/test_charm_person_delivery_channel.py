"""INV-001 — charm_person's caster-facing lines must reach a connected PC on the
socket, not the mailbox alone.

ROM `spell_charm_person` (`src/magic.c`) writes every caster line straight to
the descriptor:
  - 1358 `send_to_char("You like yourself even better!", ch)` (self-charm)
  - 1371 `send_to_char("The mayor does not allow charming in the city limits.", ch)`
  - 1390 `act("$N looks at you with adoring eyes.", ch, NULL, victim, TO_CHAR)`

The Python port appended all three straight to `caster.messages`, the mailbox the
connection read loop only drains after the caster's *next* command — invisible to
an idle connected PC at cast time (INV-001 SINGLE-DELIVERY wrong-channel class,
same shape as SPEC-017).

Fix: route every caster line through `_send_to_char` (`push_message`: async
socket for connected PCs *xor* mailbox fallback for tests/disconnected).
"""

from __future__ import annotations

import asyncio

import pytest

from mud.models.character import Character
from mud.models.constants import Position, RoomFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.skills.handlers import charm_person


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_pc(name: str, **kw) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, position=int(Position.STANDING), **kw)
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    return pc, conn


def test_self_charm_line_reaches_connected_caster_on_socket() -> None:
    async def scenario():
        room = Room(vnum=99311, name="Grove")
        caster, conn = _connected_pc("Mage", level=40, ch_class=0)
        room.add_character(caster)
        assert charm_person(caster, target=caster) is False
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())
    line = "You like yourself even better!"
    assert any(line in m for m in sent), f"self-charm line must reach connected caster's socket; sent={sent}"
    assert not any(line in m for m in mailbox), f"self-charm line stranded in mailbox for a connected PC: {mailbox}"


def test_room_law_line_reaches_connected_caster_on_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario():
        room = Room(vnum=99312, name="City Square", room_flags=int(RoomFlag.ROOM_LAW))
        caster, conn = _connected_pc("Mage", level=40, ch_class=0)
        room.add_character(caster)
        goblin = Character(name="goblin", is_npc=True, level=10, position=int(Position.STANDING))
        room.add_character(goblin)
        goblin.messages = []
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)
        assert charm_person(caster, target=goblin) is False
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())
    line = "The mayor does not allow charming in the city limits."
    assert any(line in m for m in sent), f"ROOM_LAW line must reach connected caster's socket; sent={sent}"
    assert not any(line in m for m in mailbox), f"ROOM_LAW line stranded in mailbox for a connected PC: {mailbox}"


def test_adoring_eyes_line_reaches_connected_caster_on_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario():
        room = Room(vnum=99313, name="Grove")
        caster, conn = _connected_pc("Mage", level=40, ch_class=0)
        room.add_character(caster)
        goblin = Character(
            name="goblin", is_npc=True, short_descr="a green goblin", level=10, position=int(Position.STANDING)
        )
        room.add_character(goblin)
        goblin.messages = []
        monkeypatch.setattr(skill_handlers, "saves_spell", lambda *a, **k: False)
        assert charm_person(caster, target=goblin) is True
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())
    line = "looks at you with adoring eyes."
    assert any(line in m for m in sent), f"adoring-eyes TO_CHAR line must reach connected caster's socket; sent={sent}"
    assert not any(line in m for m in mailbox), f"adoring-eyes line stranded in mailbox for a connected PC: {mailbox}"
