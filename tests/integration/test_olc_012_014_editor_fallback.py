"""OLC-012/013/014 — ``redit``/``oedit``/``medit`` fallback to ``interpret()``.

ROM reference: src/olc.c:474-527 (redit), 532-584 (oedit), 589-641 (medit).

When an unknown command is typed inside an OLC editor, ROM falls back to the
standard command interpreter:

    /* Default to Standard Interpreter. */
    interpret (ch, arg);

Python implements this via ``_should_fallback_from_olc()`` in dispatcher.py:
when ``_interpret_redit/oedit/medit`` returns an "Unknown * editor command:"
string, ``_process_descriptor_input`` returns ``None``, causing
``process_command`` to re-process the full input through normal dispatch.
"""

from __future__ import annotations

import pytest

from mud.commands.build import (
    _interpret_medit,
    _interpret_oedit,
    _interpret_redit,
)
from mud.commands.dispatcher import _should_fallback_from_olc, process_command
from mud.models.constants import LEVEL_HERO
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


# ── Unit: _should_fallback_from_olc ─────────────────────────────────────────
# mirrors ROM src/olc.c:474-527 — "Default to Standard Interpreter" branch.

def test_should_fallback_room_editor():
    """``_should_fallback_from_olc`` triggers on unknown room editor command."""
    assert _should_fallback_from_olc("Unknown room editor command.")


def test_should_fallback_object_editor():
    assert _should_fallback_from_olc("Unknown object editor command: foo")


def test_should_fallback_mobile_editor():
    assert _should_fallback_from_olc("Unknown mobile editor command: bar")


def test_should_fallback_area_editor():
    assert _should_fallback_from_olc("Unknown area editor command: baz")


def test_should_not_fallback_on_valid_result():
    """Known-good results must NOT trigger fallback."""
    assert not _should_fallback_from_olc("Name set.")
    assert not _should_fallback_from_olc("Room reset.")
    assert not _should_fallback_from_olc("")
    assert not _should_fallback_from_olc("Wear flag toggled.")
    assert not _should_fallback_from_olc("Exiting mobile editor.")


# ── Unit: _interpret_* returns correct sentinel strings ──────────────────────

def _make_redit_session():
    from mud.registry import room_registry
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "redit"
    room = room_registry.get(3001)
    session.editor_state = {"room": room}
    return char, session


def _make_oedit_session():
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "oedit"
    proto = ObjIndex(vnum=50001, name="test sword", short_descr="a test sword")
    session.editor_state = {"obj_proto": proto}
    return char, session


def _make_medit_session():
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "medit"
    proto = MobIndex(vnum=60001, player_name="test mob")
    session.editor_state = {"mob_proto": proto}
    return char, session


def test_redit_unknown_cmd_returns_fallback_sentinel():
    """``_interpret_redit`` returns the exact string that triggers OLC fallback.

    ROM src/olc.c:519-521 — unknown command hits ``interpret(ch, arg)`` path.
    """
    char, session = _make_redit_session()
    result = _interpret_redit(session, char, "say hello world")
    assert _should_fallback_from_olc(result), (
        f"Expected a fallback-triggering string from redit, got: {result!r}"
    )


def test_oedit_unknown_cmd_returns_fallback_sentinel():
    """``_interpret_oedit`` returns the exact string that triggers OLC fallback.

    ROM src/olc.c:575-577 — unknown command hits ``interpret(ch, arg)`` path.
    """
    char, session = _make_oedit_session()
    result = _interpret_oedit(session, char, "say hello world")
    assert _should_fallback_from_olc(result), (
        f"Expected a fallback-triggering string from oedit, got: {result!r}"
    )


def test_medit_unknown_cmd_returns_fallback_sentinel():
    """``_interpret_medit`` returns the exact string that triggers OLC fallback.

    ROM src/olc.c:631-633 — unknown command hits ``interpret(ch, arg)`` path.
    """
    char, session = _make_medit_session()
    result = _interpret_medit(session, char, "say hello world")
    assert _should_fallback_from_olc(result), (
        f"Expected a fallback-triggering string from medit, got: {result!r}"
    )


# ── Integration: process_command routes fallback through normal dispatch ──────

def test_redit_fallback_executes_normal_command():
    """Unknown command in active redit session falls through to normal interpreter.

    ROM src/olc.c:519-521: ``interpret(ch, arg)`` — full original input
    re-dispatched through the standard command table.
    """
    char, session = _make_redit_session()
    result = process_command(char, "look")
    # 'look' is a standard command; should not return an "Unknown ... command:" string
    assert not _should_fallback_from_olc(result), (
        f"look should have been dispatched normally, got: {result!r}"
    )
    assert "unknown" not in result.lower() or "editor" not in result.lower(), (
        f"look should not produce an editor error, got: {result!r}"
    )


def test_oedit_fallback_executes_normal_command():
    """Unknown command in active oedit session falls through to normal interpreter.

    ROM src/olc.c:575-577.
    """
    char, session = _make_oedit_session()
    result = process_command(char, "look")
    assert not _should_fallback_from_olc(result), (
        f"look should have been dispatched normally, got: {result!r}"
    )
    assert "unknown" not in result.lower() or "editor" not in result.lower(), (
        f"look should not produce an editor error, got: {result!r}"
    )


def test_medit_fallback_executes_normal_command():
    """Unknown command in active medit session falls through to normal interpreter.

    ROM src/olc.c:631-633.
    """
    char, session = _make_medit_session()
    result = process_command(char, "look")
    assert not _should_fallback_from_olc(result), (
        f"look should have been dispatched normally, got: {result!r}"
    )
    assert "unknown" not in result.lower() or "editor" not in result.lower(), (
        f"look should not produce an editor error, got: {result!r}"
    )


def test_redit_known_command_does_not_fallback():
    """Known redit commands are dispatched by the OLC handler, not the fallback."""
    char, session = _make_redit_session()
    result = process_command(char, "show")
    # 'show' is a known redit command; result should come from _interpret_redit
    assert not _should_fallback_from_olc(result), f"Got: {result!r}"


def test_oedit_known_command_does_not_fallback():
    """Known oedit commands are dispatched by the OLC handler."""
    char, session = _make_oedit_session()
    result = process_command(char, "show")
    assert not _should_fallback_from_olc(result), f"Got: {result!r}"


def test_medit_known_command_does_not_fallback():
    """Known medit commands are dispatched by the OLC handler."""
    char, session = _make_medit_session()
    result = process_command(char, "show")
    assert not _should_fallback_from_olc(result), f"Got: {result!r}"
