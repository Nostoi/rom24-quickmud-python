"""OLC-INFRA-001 — descriptor-level editor state plumbing.

Mirrors ROM `src/olc.h:53-59` (the `ED_*` editor enum), ROM `desc->pString`
(the string-buffer-being-edited pointer), and the input-dispatch decision
tree at ROM `src/comm.c:833-847`:

    if (d->showstr_point)        -> show_string  (already handled upstream)
    else if (d->pString)          -> string_add   (STRING-004, deferred)
    else if (d->editor != ED_NONE)-> run_olc_editor (OLC-001, deferred)
    else                          -> normal interpret/substitute_alias

This test covers only the routing-decision plumbing. The destinations
(`string_add`, `run_olc_editor`) are filed under their own gap IDs and
remain stubbed in this commit.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mud.models.character import Character
from mud.net.session import Session
from mud.olc.editor_state import DescriptorRoute, EditorMode, StringEdit, route_descriptor_input


def _make_session() -> Session:
    return Session(
        name="builder",
        character=Character(name="builder"),
        reader=MagicMock(),
        connection=MagicMock(),
    )


def test_session_defaults_to_none_editor_mode_and_no_string_edit() -> None:
    sess = _make_session()
    assert sess.editor_mode == EditorMode.NONE
    assert sess.string_edit is None


def test_editor_mode_enum_matches_rom_olc_h() -> None:
    # mirrors ROM src/olc.h:53-59
    assert EditorMode.NONE == 0
    assert EditorMode.AREA == 1
    assert EditorMode.ROOM == 2
    assert EditorMode.OBJECT == 3
    assert EditorMode.MOBILE == 4
    assert EditorMode.MPCODE == 5
    assert EditorMode.HELP == 6


def test_route_descriptor_input_default_is_normal() -> None:
    sess = _make_session()
    assert route_descriptor_input(sess) == DescriptorRoute.NORMAL


def test_route_descriptor_input_with_string_edit_returns_string_edit() -> None:
    sess = _make_session()
    sess.string_edit = StringEdit()
    assert route_descriptor_input(sess) == DescriptorRoute.STRING_EDIT


def test_route_descriptor_input_with_editor_mode_returns_olc_editor() -> None:
    sess = _make_session()
    sess.editor_mode = EditorMode.ROOM
    assert route_descriptor_input(sess) == DescriptorRoute.OLC_EDITOR


def test_string_edit_takes_precedence_over_editor_mode() -> None:
    # mirrors ROM src/comm.c:835-841 — `else if (d->pString)` is checked
    # BEFORE `run_olc_editor`, so an active string editor wins even when
    # the descriptor is also in OLC mode.
    sess = _make_session()
    sess.editor_mode = EditorMode.ROOM
    sess.string_edit = StringEdit()
    assert route_descriptor_input(sess) == DescriptorRoute.STRING_EDIT
