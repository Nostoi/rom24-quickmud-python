"""Integration tests for interp.c dispatcher behavior gaps.

ROM Reference: src/interp.c interpret() — empty input, snoop forwarding,
wiznet log mirror, punctuation aliases, prefix-match table order.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.commands.dispatcher import COMMAND_INDEX, process_command
from mud.commands.combat import do_kill
from mud.commands.communication import do_emote, do_gossip, do_immtalk
from mud.commands.equipment import do_wear
from mud.commands.inventory import do_get
from mud.commands.movement import do_enter
from mud.commands.obj_manipulation import do_sacrifice
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


@pytest.mark.parametrize(
    "name,handler",
    [
        ("hit", do_kill),  # ROM src/interp.c:88
    ],
)
def test_interp_009_hit_routes_to_do_kill(name, handler):
    # mirrors ROM src/interp.c:88 — `hit` dispatches to do_kill (single
    # canonical combat handler), not a separate stub.
    cmd = COMMAND_INDEX.get(name)
    assert cmd is not None
    assert cmd.func is handler


def test_interp_010_take_routes_to_do_get():
    # mirrors ROM src/interp.c:226 — `take` is a cmd_table alias for do_get.
    cmd = COMMAND_INDEX.get("take")
    assert cmd is not None
    assert cmd.func is do_get


@pytest.mark.parametrize("name", ["junk", "tap"])
def test_interp_011_junk_tap_route_to_do_sacrifice(name):
    # mirrors ROM src/interp.c:228-229 — `junk` and `tap` are cmd_table
    # aliases for do_sacrifice.
    cmd = COMMAND_INDEX.get(name)
    assert cmd is not None
    assert cmd.func is do_sacrifice


def test_interp_003_logged_command_mirrors_to_wiznet_secure(test_room, monkeypatch):
    # mirrors ROM src/interp.c:468-489 — when a command is logged
    # (PLR_LOG, LOG_ALWAYS, or fLogAll), the dispatcher mirrors
    # "Log <name>: <logline>" to wiznet's WIZ_SECURE channel.
    captured: list[tuple[str, object, object, object, object, int]] = []

    def fake_wiznet(message, sender_ch_or_flag=None, obj=None, flag=None, flag_skip=None, min_level=0):
        captured.append((message, sender_ch_or_flag, obj, flag, flag_skip, min_level))

    from mud.admin_logging import admin as admin_module

    monkeypatch.setattr(admin_module, "wiznet", fake_wiznet)

    char = Character(
        name="Logger",
        level=60,
        room=test_room,
        hit=100,
        max_hit=100,
        is_npc=False,
    )
    char.log_commands = True  # force the logged-command path
    test_room.people.append(char)
    try:
        process_command(char, "look")

        assert captured, "wiznet was not invoked for a logged command"
        message, _sender, _obj, flag, _flag_skip, _min_level = captured[0]
        from mud.wiznet import WiznetFlag

        assert flag is WiznetFlag.WIZ_SECURE
        assert message.startswith("Log Logger: ")
    finally:
        test_room.people.remove(char)
