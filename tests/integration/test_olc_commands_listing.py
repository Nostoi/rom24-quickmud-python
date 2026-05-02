"""OLC-004/005 — ROM `commands` table listing.

Mirrors ROM `src/olc.c:153-209`: `commands` dispatches by active editor and
prints the current editor command table in five fixed-width columns.
"""

from __future__ import annotations

from mud.commands.build import (
    _interpret_aedit,
    _interpret_hedit,
    _interpret_medit,
    _interpret_oedit,
    _interpret_redit,
)
from mud.models.area import Area
from mud.models.help import HelpEntry
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room


class _StubChar:
    name = "Tester"
    is_npc = False
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    """Minimal descriptor shape used by the OLC interpreters."""

    def __init__(self, editor: str, state_key: str, value) -> None:
        self.editor = editor
        self.editor_state = {state_key: value}


def _first_row(output: str) -> str:
    return output.split("\n\r", 1)[0]


def test_aedit_commands_uses_rom_five_column_table() -> None:
    # mirrors ROM src/olc.c:153-175 and aedit_table at src/olc.c:216-238
    area = Area(vnum=10, name="Area", security=1, builders="Tester")
    session = _StubSession("aedit", "area", area)

    result = _interpret_aedit(session, _StubChar(), "commands")

    assert _first_row(result) == "age            builder        commands       create         filename       "
    assert result.endswith("\n\r")
    assert "Unknown area editor command" not in result


def test_redit_commands_lists_room_editor_table() -> None:
    room = Room(vnum=4200, name="Room")
    room.area = Area(vnum=42, name="Area", builders="Tester")
    session = _StubSession("redit", "room", room)

    result = _interpret_redit(session, _StubChar(), "commands")

    assert _first_row(result) == "commands       create         desc           ed             format         "
    assert "mreset" in result
    assert "Unknown room editor command" not in result


def test_oedit_commands_lists_object_editor_table() -> None:
    proto = ObjIndex(vnum=2000, name="object")
    proto.area = Area(vnum=20, name="Area", builders="Tester")
    session = _StubSession("oedit", "obj_proto", proto)

    result = _interpret_oedit(session, _StubChar(), "commands")

    assert _first_row(result) == "addaffect      addapply       commands       cost           create         "
    assert "condition" in result
    assert "Unknown object editor command" not in result


def test_medit_commands_lists_mobile_editor_table() -> None:
    proto = MobIndex(vnum=3000)
    proto.area = Area(vnum=30, name="Area", builders="Tester")
    session = _StubSession("medit", "mob_proto", proto)

    result = _interpret_medit(session, _StubChar(), "commands")

    assert _first_row(result) == "alignment      commands       create         desc           level          "
    assert "delmprog" in result
    assert "Unknown mobile editor command" not in result


def test_hedit_commands_lists_help_editor_table() -> None:
    help_entry = HelpEntry(keywords=["topic"], text="help text", level=0)
    session = _StubSession("hedit", "help", help_entry)

    result = _interpret_hedit(session, _StubChar(), "commands")

    assert _first_row(result) == "keyword        text           new            level          delete         "
    assert "show" in result
    assert "Unknown help editor command" not in result
