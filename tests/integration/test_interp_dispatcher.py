"""Integration tests for interp.c dispatcher behavior gaps.

ROM Reference: src/interp.c interpret() — empty input, snoop forwarding,
wiznet log mirror, punctuation aliases, prefix-match table order.
"""
from __future__ import annotations

import pytest

from mud.commands.dispatcher import COMMAND_INDEX, process_command
from mud.commands.communication import do_emote, do_gossip
from mud.commands.session import do_recall
from mud.models.character import Character


@pytest.fixture
def dispatcher_char(test_room):
    char = Character(
        name="DispatchTester",
        level=5,
        room=test_room,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.mark.parametrize("blank", ["", "   ", "\t", "  \t  "])
def test_interp_007_empty_input_returns_silently(dispatcher_char, blank):
    # mirrors ROM src/interp.c:401-404 — interpret() strips leading
    # whitespace and returns silently on empty input. Python previously
    # returned the literal "What?".
    assert process_command(dispatcher_char, blank) == ""


@pytest.mark.parametrize(
    "punct,handler",
    [
        (".", do_gossip),  # ROM src/interp.c:184
        (",", do_emote),  # ROM src/interp.c:186
        ("/", do_recall),  # ROM src/interp.c:272
    ],
)
def test_interp_008_punctuation_aliases_route_to_rom_handlers(punct, handler):
    # mirrors ROM src/interp.c:184,186,272 — `.` `,` `/` are single-char
    # aliases for gossip/emote/recall in cmd_table[].
    cmd = COMMAND_INDEX.get(punct)
    assert cmd is not None, f"punctuation alias {punct!r} missing from COMMAND_INDEX"
    assert cmd.func is handler
