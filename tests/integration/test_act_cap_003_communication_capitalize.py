"""ACT-CAP-003 — communication command capitalization parity (INV-029 cousin).

ROM ``src/comm.c:2376-2379`` (``act_new``) upper-cases the first visible
letter of every rendered ``act()`` line, with a kludge for leading ``{X``
colour codes: ``buf[0]=='{'`` → cap ``buf[2]``, else cap ``buf[0]``.
``UPPER`` flips ASCII ``a``–``z`` only.

``do_say`` (``src/act_comm.c:777``), ``do_tell``
(``src/act_comm.c:941-942``), and ``do_shout``
(``src/act_comm.c:836``) all route through ``act()``/``act_new()``,
so their per-listener lines are capitalized by ROM. The Python
equivalents built f-strings that bypassed ``capitalize_act_line``,
so an invisible speaker's ``"someone says…"`` rendered lowercase
where ROM renders ``"Someone says…"``.
"""

from __future__ import annotations

import re as _re

import pytest

from mud.commands.communication import do_reply, do_say, do_shout, do_tell
from mud.models.character import character_registry
from mud.world import create_test_character, initialize_world

_ROM_COLOR_RE = _re.compile(r"\{[a-zA-Z0-9]")


def _strip(text: str) -> str:
    return _ROM_COLOR_RE.sub("", text)


def _make_online(target):
    target.desc = object()
    return target


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    initialize_world("area/area.lst")
    yield
    character_registry.clear()


class TestSayCapitalization:
    """ACT-CAP-003: do_say room broadcast is capitalized (ROM act_new).

    mirroring ROM src/comm.c:2376-2379 — act_new upper-cases first
    visible letter.  do_say's TO_ROOM line is
        act("{6$n says '{7$T{6'{x", ch, NULL, argument, TO_ROOM)
    which renders e.g. "{6Someone says 'hello'{x}" — the '{6' colour
    code means cap position 2.
    """

    def test_say_room_message_is_capitalized(self) -> None:
        speaker = create_test_character(name="speaker", room_vnum=3001)
        listener = create_test_character(name="listener", room_vnum=3001)
        do_say(speaker, "hello")
        msg = listener.messages[-1]
        # After capitalization: '{6' prefix → cap at position 2 → 'S'
        # "Speaker says 'hello'" not "speaker says 'hello'"
        plain = _strip(msg)
        assert plain.startswith("Speaker "), f"say room message not capitalized: {msg!r} → {plain!r}"

    def test_say_invisible_speaker_capitalized(self) -> None:
        """Invisible speaker renders as 'Someone' (PERS) — still capitalized."""
        from mud.models.constants import AffectFlag

        speaker = create_test_character(name="ghostspeaker", room_vnum=3001)
        listener = create_test_character(name="saylistener", room_vnum=3001)
        speaker.affected_by |= int(AffectFlag.INVISIBLE)
        do_say(speaker, "boo")
        msg = listener.messages[-1]
        plain = _strip(msg)
        assert plain.startswith("Someone "), f"invisible say not capitalized/PERS: {msg!r} → {plain!r}"


class TestTellCapitalization:
    """ACT-CAP-003: do_tell TO_VICT line is capitalized (ROM act_new).

    mirroring ROM src/act_comm.c:942 —
        act_new("{k$n tells you '{K$t{k'{x", ch, argument, victim, TO_VICT, POS_DEAD)
    '{k' prefix → cap position 2.
    """

    def test_tell_target_message_is_capitalized(self) -> None:
        sender = create_test_character(name="Tellsender", room_vnum=3001)
        target = _make_online(create_test_character(name="Telltarget", room_vnum=3001))
        do_tell(sender, f"{target.name} hello")
        delivered = [m for m in target.messages if "tells you" in m]
        assert delivered, f"target received no tell; messages={target.messages}"
        msg = delivered[-1]
        plain = _strip(msg)
        assert plain.startswith("Tellsender "), f"tell target message not capitalized: {msg!r} → {plain!r}"

    def test_tell_invisible_sender_capitalized(self) -> None:
        from mud.models.constants import AffectFlag

        sender = create_test_character(name="ghostteller", room_vnum=3001)
        target = _make_online(create_test_character(name="Tellvis", room_vnum=3001))
        sender.affected_by |= int(AffectFlag.INVISIBLE)
        do_tell(sender, f"{target.name} secret")
        delivered = [m for m in target.messages if "tells you" in m]
        assert delivered, f"target received no tell; messages={target.messages}"
        msg = delivered[-1]
        plain = _strip(msg)
        assert plain.startswith("Someone "), f"invisible tell not capitalized/PERS: {msg!r} → {plain!r}"


class TestReplyCapitalization:
    """ACT-CAP-003: do_reply delegates to do_tell — inherits capitalization."""

    def test_reply_target_message_is_capitalized(self) -> None:
        speaker = create_test_character(name="Replyer", room_vnum=3001)
        target = _make_online(create_test_character(name="Replytarget", room_vnum=3001))
        do_tell(target, f"{speaker.name} hi")
        speaker.reply = target
        do_reply(speaker, "reply back")
        delivered = [m for m in target.messages if "tells you" in m]
        assert delivered, f"target received no reply; messages={target.messages}"
        msg = delivered[-1]
        plain = _strip(msg)
        assert plain.startswith("Replyer "), f"reply target message not capitalized: {msg!r} → {plain!r}"


class TestShoutCapitalization:
    """ACT-CAP-003: do_shout per-listener line is capitalized (ROM act_new).

    mirroring ROM src/act_comm.c:836 —
        act("$n shouts '$t'", ch, argument, d->character, TO_VICT)
    No colour-code prefix, so cap position 0 (plain name first).
    """

    def test_shout_listener_message_is_capitalized(self) -> None:
        speaker = create_test_character(name="shouter", room_vnum=3001)
        listener = create_test_character(name="shoutlistener", room_vnum=3001)
        listener.comm = 0  # no SHOUTSOFF/QUIET
        do_shout(speaker, "hello")
        msg = listener.messages[-1]
        # "Shouter shouts 'hello'" — first letter capitalized
        plain = _strip(msg)
        assert plain[0].isupper(), f"shout listener message not capitalized: {msg!r} → {plain!r}"
