"""OLC-001 — `run_olc_editor` descriptor routing.

Mirrors ROM `src/comm.c:833-847` and `src/olc.c:37-63`: raw descriptor input
must route to `string_add` when `pString` is active, otherwise to the current
OLC editor when `editor != ED_NONE`, and only then fall through to the normal
command interpreter.
"""

from __future__ import annotations

from mud.commands import process_command
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.olc.editor_state import EditorMode, StringEdit
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _attach_session(char):
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return session


def test_process_command_routes_string_edit_before_olc_editor():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.pcdata.security = 9
    session = _attach_session(builder)
    session.editor = "aedit"
    session.editor_mode = EditorMode.AREA
    session.editor_state = {"area": builder.room.area}
    session.string_edit = StringEdit()

    result = process_command(builder, "first draft line")

    assert result == ""
    assert session.string_edit is not None
    assert session.string_edit.buffer == "first draft line\n\r"
    assert builder.room.area.name != "first draft line"


def test_process_command_routes_olc_input_via_editor_mode():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.pcdata.security = 9
    session = _attach_session(builder)
    session.editor = None
    session.editor_mode = EditorMode.AREA
    session.editor_state = {"area": builder.room.area}

    result = process_command(builder, 'name "Editor Routed Area"')

    assert result == "Name set."
    assert builder.room.area.name == "Editor Routed Area"


def test_process_command_falls_back_to_normal_interpreter_for_unknown_olc_command():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.pcdata.security = 9
    session = _attach_session(builder)
    session.editor = "aedit"
    session.editor_mode = EditorMode.AREA
    session.editor_state = {"area": builder.room.area}

    result = process_command(builder, "look")

    assert "Unknown area editor command:" not in result
    assert builder.room.name.lower() in result.lower()


def test_process_command_parses_at_prefixed_redit_entry_command():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.pcdata.security = 9
    session = _attach_session(builder)

    result = process_command(builder, "@redit")

    assert "room editor activated" in result.lower()
    assert session.editor == "redit"
    assert session.editor_mode == EditorMode.ROOM
