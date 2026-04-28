"""Integration tests for interp.c dispatcher behavior gaps.

ROM Reference: src/interp.c interpret() — empty input, snoop forwarding,
wiznet log mirror, punctuation aliases, prefix-match table order.
"""
from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
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
