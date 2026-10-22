"""OLC_ACT-015: `redit heal`/`redit mana` emit ROM's exact success message.

ROM src/olc_act.c:1807-1822 (redit_heal) and :1824-1839 (redit_mana) both send
a bare `"Heal rate set.\\n\\r"` / `"Mana rate set.\\n\\r"` on success — the
builder is NOT told the value. Python previously appended `" to {n}."`, leaking
the numeric value ROM never echoes.
"""

from __future__ import annotations

from mud.commands.build import _interpret_redit
from mud.models.area import Area
from mud.models.room import Room


class _StubChar:
    name = "Tester"
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    def __init__(self, room: Room) -> None:
        self.editor = "room"
        self.editor_state = {"room": room}


def _session_for(room: Room) -> _StubSession:
    return _StubSession(room)


def _room() -> Room:
    room = Room(vnum=4200, name="Old Room")
    room.area = Area(vnum=42, name="A", builders="Tester")
    return room


def test_redit_heal_emits_rom_message() -> None:
    room = _room()
    result = _interpret_redit(_session_for(room), _StubChar(), "heal 150")
    assert result == "Heal rate set."
    assert room.heal_rate == 150


def test_redit_mana_emits_rom_message() -> None:
    room = _room()
    result = _interpret_redit(_session_for(room), _StubChar(), "mana 200")
    assert result == "Mana rate set."
    assert room.mana_rate == 200
