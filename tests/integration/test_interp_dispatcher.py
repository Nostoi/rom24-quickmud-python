"""Integration tests for interp.c dispatcher behavior gaps.

ROM Reference: src/interp.c interpret() — empty input, snoop forwarding,
wiznet log mirror, punctuation aliases, prefix-match table order.
"""
from __future__ import annotations

from types import SimpleNamespace

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


def test_interp_002_snoop_forwards_logline_to_snooper(test_room):
    # mirrors ROM src/interp.c:491-496 — when ch->desc->snoop_by is set,
    # interpret() forwards the logline (input minus leading whitespace) to
    # the snooping descriptor prefixed with "% ".
    snooper = Character(
        name="Snooper",
        level=60,
        room=test_room,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    victim = Character(
        name="Victim",
        level=5,
        room=test_room,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    test_room.people.extend([snooper, victim])

    snooper.desc = SimpleNamespace(character=snooper, snoop_by=None)
    victim.desc = SimpleNamespace(character=victim, snoop_by=snooper.desc)

    process_command(victim, "look")

    assert "% look" in snooper.messages

    test_room.people.remove(snooper)
    test_room.people.remove(victim)


def test_interp_002_snoop_inactive_when_no_snooper(test_room):
    # mirrors ROM src/interp.c:491 guard — no snoop_by means no forward.
    char = Character(
        name="Lonely",
        level=5,
        room=test_room,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    test_room.people.append(char)
    char.desc = SimpleNamespace(character=char, snoop_by=None)

    process_command(char, "look")

    assert not any(msg.startswith("% ") for msg in char.messages)
    test_room.people.remove(char)
