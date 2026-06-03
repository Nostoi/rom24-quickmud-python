"""SAY-NNN — ROM `do_say` parity (src/act_comm.c:768-791).

A 2026-05-22 re-audit of `act_comm.c` against the live Python
implementation surfaced four divergences from ROM `do_say` despite
`ACT_COMM_C_AUDIT.md` previously claiming "100% VERIFIED":

- SAY-001 — wording: ROM emits `"You say '<msg>'"` and `"$n says '<msg>'"`
  (no comma). Python emitted `"You say, '<msg>'"` / `"... says, '<msg>'"`.
- SAY-002 — `$n` substitution: ROM routes the speaker name through
  `PERS()` so invisible/hidden speakers appear as "someone". Python
  hardcodes `char.name`.
- SAY-003 — color codes: ROM wraps the message in
  `"{6...{7$T{6'{x"` (cyan/white). Python emits no codes.
- SAY-004 — double-delivery: Python calls both
  `room.broadcast` and `broadcast_room`, which do identical work,
  so connected players receive every `say` twice (INV-001
  SINGLE-DELIVERY violation).

These tests pin the ROM-exact behavior. They live under
`tests/integration/` so the `rng_mm.seed_mm(12345)` autouse fixture
applies — `do_say` itself doesn't roll RNG, but other tests in this
module may grow that need it.
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.models.character import character_registry
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()
    yield
    character_registry.clear()


import re as _re

_ROM_COLOR_RE = _re.compile(r"\{.")


def _strip_rom_colors(text: str) -> str:
    """Strip ROM `{X` colour-code escapes for plain-text comparisons."""
    return _ROM_COLOR_RE.sub("", text)


def test_say_001_room_broadcast_drops_comma() -> None:
    """SAY-001 — TO_ROOM wording matches ROM `"$n says '$T'"`.

    ROM C: src/act_comm.c:776
        act ("{6$n says '{7$T{6'{x", ch, NULL, argument, TO_ROOM);

    Stripping ROM colour codes, the rendered text is
    `"<name> says 'hello'"` — no comma after `says`. Python previously
    emitted `"<name> says, 'hello'"`.
    """
    speaker = create_test_character("Sayspeaker", 3001)
    listener = create_test_character("Saylistener", 3001)

    process_command(speaker, "say hello")

    delivered = [_strip_rom_colors(m) for m in listener.messages if "says" in m and "hello" in m]
    assert delivered, f"listener received no say broadcast; messages={listener.messages}"
    assert any("Sayspeaker says 'hello'" in m for m in delivered), (
        f"TO_ROOM wording diverges from ROM `$n says '$T'`; got {delivered!r}"
    )
    assert not any("says, '" in m for m in delivered), f"comma after `says` leaked through; got {delivered!r}"


def test_say_001_to_char_drops_comma() -> None:
    """SAY-001 — TO_CHAR wording matches ROM `"You say '$T'"`.

    ROM C: src/act_comm.c:777
        act ("{6You say '{7$T{6'{x", ch, NULL, argument, TO_CHAR);
    """
    speaker = create_test_character("Sayself", 3001)
    out = process_command(speaker, "say hello")
    assert _strip_rom_colors(out) == "You say 'hello'", f"TO_CHAR wording diverges from ROM `You say '$T'`; got {out!r}"


def test_say_004_listener_receives_broadcast_exactly_once() -> None:
    """SAY-004 — listener receives the TO_ROOM broadcast exactly once.

    ROM C: src/act_comm.c:776 issues a single `act()` to TO_ROOM,
    which routes the formatted message to every target in
    `ch->in_room->people` exactly once. Python previously called BOTH
    `char.room.broadcast(message, ...)` AND `broadcast_room(char.room,
    message, ...)`. The two helpers do identical work (iterate
    `room.people`, fire-and-forget websocket send, append to
    `char.messages`), so every `say` was delivered twice (INV-001
    SINGLE-DELIVERY violation).

    This test pins single-delivery by counting how many copies of the
    rendered broadcast land in `listener.messages` after one `say`.
    """
    speaker = create_test_character("Sayemitter", 3001)
    listener = create_test_character("Sayrecipient", 3001)

    process_command(speaker, "say hello")

    expected = "Sayemitter says 'hello'"
    delivered = [m for m in listener.messages if _strip_rom_colors(m) == expected]
    assert len(delivered) == 1, (
        f"INV-001 SINGLE-DELIVERY violation on do_say — listener got "
        f"{len(delivered)} copies of {expected!r}; full messages: "
        f"{listener.messages!r}"
    )


def test_say_003_to_char_wraps_rom_color_codes() -> None:
    """SAY-003 — TO_CHAR output wraps the ROM `{6...{7$T{6'{x` codes.

    ROM C: src/act_comm.c:777
        act ("{6You say '{7$T{6'{x", ch, NULL, argument, TO_CHAR);

    The literal template stores `{6` (cyan/green frame), `{7` (white
    message body), and `{x` (reset). The ANSI translation layer at
    `mud/net/ansi.py` consumes these on websocket send. Python
    previously emitted no codes, so the say channel rendered in the
    default terminal colour and the framing-vs-body contrast ROM
    relies on was lost.
    """
    speaker = create_test_character("Sayhue", 3001)
    out = process_command(speaker, "say hi")
    assert out == "{6You say '{7hi{6'{x", f"TO_CHAR colour wrapping diverges from ROM; got {out!r}"


def test_say_003_to_room_wraps_rom_color_codes() -> None:
    """SAY-003 — TO_ROOM output wraps the ROM `{6...{7$T{6'{x` codes.

    ROM C: src/act_comm.c:776
        act ("{6$n says '{7$T{6'{x", ch, NULL, argument, TO_ROOM);
    """
    speaker = create_test_character("Sayhuesrc", 3001)
    listener = create_test_character("Sayhuetgt", 3001)

    process_command(speaker, "say hi")

    expected = "{6Sayhuesrc says '{7hi{6'{x"
    assert expected in listener.messages, (
        f"TO_ROOM colour wrapping diverges from ROM; expected {expected!r} in {listener.messages!r}"
    )


def test_say_002_invisible_speaker_renders_as_someone_to_unaided_listener() -> None:
    """SAY-002 — invisible speaker's `$n` renders as "someone" via PERS().

    ROM C: src/act_comm.c:776 + src/comm.c `act()` + src/handler.c:2618 `can_see`
        act ("{6$n says '{7$T{6'{x", ch, NULL, argument, TO_ROOM);

    ROM's `act()` substitutes `$n` through the PERS() macro:
        #define PERS(ch, looker) (can_see (looker, ch) ? \\
            (IS_NPC(ch) ? ch->short_descr : ch->name) : "someone")

    So when an invisible speaker says something, listeners without
    `detect_invis` see `"someone says '<msg>'"`, not the speaker's
    real name. Python previously hardcoded `char.name` in the
    broadcast, leaking the invisible speaker's identity.

    NOTE: The TO_CHAR (self) message still references the speaker as
    "You", which ROM bypasses through act() type=TO_CHAR before PERS
    even runs — unchanged here.
    """
    from mud.models.constants import AffectFlag

    speaker = create_test_character("Sayghost", 3001)
    listener = create_test_character("Sayobserver", 3001)
    # Speaker turns invisible; listener has no DETECT_INVIS, so can_see
    # returns False and PERS() should render "someone".
    speaker.affected_by |= int(AffectFlag.INVISIBLE)
    assert not listener.has_affect(AffectFlag.DETECT_INVIS)

    process_command(speaker, "say boo")

    # Listener must see "Someone says 'boo'", NOT "Sayghost says 'boo'".
    # ACT-CAP-003: capitalize_act_line caps the '{6' prefix → 'S' per ROM act_new.
    delivered = [_strip_rom_colors(m) for m in listener.messages if "says" in m and "boo" in m]
    assert delivered, f"listener received no say broadcast; messages={listener.messages}"
    assert any("Someone says 'boo'" in m for m in delivered), (
        f"PERS substitution missing for invisible speaker; got {delivered!r}"
    )
    assert not any("Sayghost" in m for m in delivered), (
        f"invisible speaker's real name leaked through PERS; got {delivered!r}"
    )


def test_say_002_invisible_speaker_seen_by_detect_invis_listener() -> None:
    """SAY-002 — invisible speaker IS visible to listener with DETECT_INVIS.

    ROM C: src/handler.c:2641-2643 — `IS_AFFECTED(victim, AFF_INVISIBLE)
    && !IS_AFFECTED(ch, AFF_DETECT_INVIS)` returns FALSE only when the
    observer LACKS detect-invis. With detect-invis, can_see returns
    TRUE and PERS renders the real name.

    Pins the both-sides-of-the-branch behaviour.
    """
    from mud.models.constants import AffectFlag

    speaker = create_test_character("Sayghost2", 3001)
    listener = create_test_character("Sayseer", 3001)
    speaker.affected_by |= int(AffectFlag.INVISIBLE)
    listener.affected_by |= int(AffectFlag.DETECT_INVIS)

    process_command(speaker, "say boo")

    delivered = [_strip_rom_colors(m) for m in listener.messages if "says" in m and "boo" in m]
    assert delivered, f"listener received no say broadcast; messages={listener.messages}"
    assert any("Sayghost2 says 'boo'" in m for m in delivered), (
        f"detect-invis listener should see real name; got {delivered!r}"
    )
    assert not any("someone" in m for m in delivered), (
        f"detect-invis listener should NOT see 'someone'; got {delivered!r}"
    )
