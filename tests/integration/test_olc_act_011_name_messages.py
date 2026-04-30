"""OLC_ACT-011: All four `*_name` builders emit ROM's exact "Name set." message.

ROM src/olc_act.c:683-700 (aedit_name), :1770-1787 (redit_name),
:2990-3010 (oedit_name), :3913-3931 (medit_name) all send
`"Name set.\\n\\r"` on success.
"""

from __future__ import annotations

from mud.commands.build import (
    _interpret_aedit,
    _interpret_medit,
    _interpret_oedit,
    _interpret_redit,
)
from mud.models.area import Area
from mud.models.constants import ActFlag
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room


class _StubChar:
    name = "Tester"
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    """Minimal stub — `_interpret_*` only reads editor/editor_state."""

    def __init__(self, state_key: str, value) -> None:
        self.editor = state_key
        self.editor_state = {state_key: value}


def _session_for(state_key: str, value) -> _StubSession:
    return _StubSession(state_key, value)


def test_aedit_name_emits_rom_message() -> None:
    area = Area(vnum=10, name="Old", security=1, builders="Tester")
    session = _session_for("area", area)
    result = _interpret_aedit(session, _StubChar(), "name New Area Name")
    assert result == "Name set."


def test_redit_name_emits_rom_message() -> None:
    room = Room(vnum=4200, name="Old Room")
    room.area = Area(vnum=42, name="A", builders="Tester")
    session = _session_for("room", room)
    result = _interpret_redit(session, _StubChar(), "name A Better Name")
    assert result == "Name set."


def test_oedit_name_emits_rom_message() -> None:
    proto = ObjIndex(vnum=2000, name="old keywords")
    proto.area = Area(vnum=20, name="A", builders="Tester")
    session = _session_for("obj_proto", proto)
    result = _interpret_oedit(session, _StubChar(), "name sword weapon blade")
    assert result == "Name set."


def test_medit_name_emits_rom_message() -> None:
    proto = MobIndex(vnum=3000)
    proto.player_name = "old"
    proto.area = Area(vnum=30, name="A", builders="Tester")
    proto.act_flags = int(ActFlag.IS_NPC)
    session = _session_for("mob_proto", proto)
    result = _interpret_medit(session, _StubChar(), "name guard soldier")
    assert result == "Name set."
