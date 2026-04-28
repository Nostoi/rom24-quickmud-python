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


def test_interp_014_colon_routes_to_do_immtalk():
    # mirrors ROM src/interp.c:356 — `:` is a cmd_table alias for do_immtalk.
    cmd = COMMAND_INDEX.get(":")
    assert cmd is not None
    assert cmd.func is do_immtalk


def test_interp_012_go_routes_to_do_enter():
    # mirrors ROM src/interp.c:263 — `go` is a cmd_table alias for do_enter.
    cmd = COMMAND_INDEX.get("go")
    assert cmd is not None
    assert cmd.func is do_enter


@pytest.mark.parametrize("name", ["junk", "tap"])
def test_interp_011_junk_tap_route_to_do_sacrifice(name):
    # mirrors ROM src/interp.c:228-229 — `junk` and `tap` are cmd_table
    # aliases for do_sacrifice.
    cmd = COMMAND_INDEX.get(name)
    assert cmd is not None
    assert cmd.func is do_sacrifice


@pytest.mark.parametrize(
    "raw,expected_head,expected_tail",
    [
        # Plain whitespace split.
        ("look around", "look", "around"),
        # Single-quoted leading token.
        ("'fire bolt' target", "fire bolt", "target"),
        # Double-quoted leading token.
        ('"hello world" foo', "hello world", "foo"),
        # ROM does NOT treat backslash as an escape — passes it through.
        (r"hi\there", r"hi\there", ""),
        # ROM lowercases the head; tail keeps original case.
        ("LOOK Around", "look", "Around"),
        # Empty quoted token.
        ("'' rest", "", "rest"),
        # Leading whitespace stripped.
        ("   look", "look", ""),
        # Trailing whitespace after head dropped before tail capture.
        ("get   sword", "get", "sword"),
    ],
)
def test_interp_015_one_argument_matches_rom(raw, expected_head, expected_tail):
    # mirrors ROM src/interp.c:766-798 — one_argument lowercases the
    # head, supports ' and " as quote sentinels (no nesting), treats
    # backslash literally, strips surrounding whitespace.
    from mud.commands.dispatcher import _one_argument

    head, tail = _one_argument(raw)
    assert head == expected_head
    assert tail == expected_tail


def test_interp_004_shout_requires_trust_3():
    # mirrors ROM src/interp.c:200 — {"shout", do_shout, POS_RESTING, 3, ...}
    cmd = COMMAND_INDEX["shout"]
    assert cmd.min_trust == 3


def test_interp_005_murder_requires_trust_5():
    # mirrors ROM src/interp.c:247 — {"murder", do_murder, POS_FIGHTING, 5, ...}
    cmd = COMMAND_INDEX["murder"]
    assert cmd.min_trust == 5


def test_interp_006_music_min_position_sleeping():
    # mirrors ROM src/interp.c:93 — {"music", do_music, POS_SLEEPING, 0, ...}
    from mud.models.constants import Position
    cmd = COMMAND_INDEX["music"]
    assert cmd.min_position == Position.SLEEPING


def test_interp_024_do_commands_preserves_12char_column_padding(test_room, monkeypatch):
    # mirrors ROM src/interp.c:803-825 — do_commands emits names as
    # "%-12s" (12-char left-justified), 6 per row, with no trailing
    # whitespace stripped from columns within a row.
    from mud.commands import dispatcher
    from mud.commands.info import do_commands as do_commands_fn

    short = dispatcher.Command("a", do_commands_fn)
    long_name = dispatcher.Command("xxxxxxxxxxxx", do_commands_fn)  # 12 chars
    third = dispatcher.Command("c", do_commands_fn)
    monkeypatch.setattr(dispatcher, "COMMANDS", [short, long_name, third], raising=False)

    char = Character(name="Mortal", level=1, trust=0, room=test_room, is_npc=False)
    test_room.people.append(char)
    try:
        result = do_commands_fn(char, "")
        # Three names, one row. ROM padding: each column is exactly 12 chars,
        # so total length is 36 chars + trailing newline. With rstrip Python
        # would compress "a           xxxxxxxxxxxxc           " to
        # "a           xxxxxxxxxxxxc" — 25 chars. Assert the un-stripped form.
        assert result == "a           xxxxxxxxxxxxc           " + "\n\r"
    finally:
        test_room.people.remove(char)


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
