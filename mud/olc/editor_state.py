"""Descriptor-level OLC editor state plumbing (OLC-INFRA-001).

Mirrors ROM `src/olc.h:53-59` (the `ED_*` editor enum), ROM `desc->pString`
(the string-buffer-being-edited pointer on the descriptor), and the input
dispatch decision tree at ROM `src/comm.c:833-847`.

The destinations (`string_add` for STRING-004, `run_olc_editor` for OLC-001)
are filed under their own gap IDs and are not invoked here — this module
only provides the data shapes and the routing decision.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum


class EditorMode(IntEnum):
    """Descriptor `editor` field values — mirrors ROM `src/olc.h:53-59`."""

    NONE = 0
    AREA = 1
    ROOM = 2
    OBJECT = 3
    MOBILE = 4
    MPCODE = 5
    HELP = 6


# ROM caps editor input at MAX_STRING_LENGTH-4 (= 4604) before truncation;
# see `src/string.c:121-286` (STRING-004). We pre-share the constant here so
# the eventual STRING-004 closure has a single source of truth.
MAX_STRING_EDIT_LENGTH = 4604


@dataclass
class StringEdit:
    """Mirrors ROM `desc->pString`: the buffer being edited plus the
    on-commit hook that writes the result back to its owner (room desc,
    mob desc, obj desc, ED text, mprog source, help text).

    `on_commit` is the Pythonic stand-in for ROM's `char **pString`
    pointer-to-pointer: ROM rewrites `*pString = str_dup(buffer)` on `~`
    or `@`; we call `on_commit(buffer)` instead.
    """

    buffer: str = ""
    on_commit: Callable[[str], None] | None = None
    max_length: int = MAX_STRING_EDIT_LENGTH


class DescriptorRoute(IntEnum):
    """Result of the input-dispatch decision tree."""

    NORMAL = 0
    STRING_EDIT = 1
    OLC_EDITOR = 2


def route_descriptor_input(session: object) -> DescriptorRoute:
    """Route raw input from a descriptor — mirrors ROM `src/comm.c:833-847`.

    Order matches ROM exactly:

    1. `desc->showstr_point` (paginator) — already handled upstream by
       `mud.net.connection._read_player_command` via `session.show_buffer`.
    2. `desc->pString != NULL` -> `STRING_EDIT` (calls `string_add`,
       STRING-004, deferred).
    3. `desc->editor != ED_NONE` -> `OLC_EDITOR` (calls `run_olc_editor`,
       OLC-001, deferred).
    4. Otherwise -> `NORMAL` (interpret / substitute_alias).
    """

    if getattr(session, "string_edit", None) is not None:
        return DescriptorRoute.STRING_EDIT
    if getattr(session, "editor_mode", EditorMode.NONE) != EditorMode.NONE:
        return DescriptorRoute.OLC_EDITOR
    return DescriptorRoute.NORMAL
