"""TELL-NNN — ROM `do_tell` parity (src/act_comm.c:845-950).

The 2026-05-22 re-audit of `do_tell` against the live Python
implementation surfaced six divergences:

- TELL-001 — TO_CHAR wording: ROM `"You tell $N '$t'"` (no comma).
  Python emits `"You tell {target.name}, '{message}'"`.
- TELL-002 — TO_VICT wording: ROM `"$n tells you '$t'"` (no comma).
  Python emits `"{sender.name} tells you, '{message}'"`.
- TELL-003 — TO_VICT `$n` routes through PERS(ch, victim); invisible
  sender shows as "someone" to listeners without DETECT_INVIS.
  Python hardcodes `sender.name`.
- TELL-004 — TO_CHAR `$N` routes through PERS(ch, ch). Python
  hardcodes `target.name`; if sender cannot see target (target
  incog above sender's trust), sender still gets the name.
- TELL-005 — Both lines wrapped with `{k...{K...{k...{x` charcoal
  colour codes. Python emits no codes.
- TELL-006 — Buffered tells (linkdead/AFK/note-writing) call
  `buf[0] = UPPER(buf[0])` to capitalize. (Deferred — minor.)

ROM C reference:
    act ("{kYou tell $N '{K$t{k'{x", ch, argument, victim, TO_CHAR);
    act_new ("{k$n tells you '{K$t{k'{x", ch, argument, victim, TO_VICT,
             POS_DEAD);
"""

from __future__ import annotations

import re as _re

import pytest

from mud.commands.communication import do_tell
from mud.models.character import character_registry
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()
    yield
    character_registry.clear()


_ROM_COLOR_RE = _re.compile(r"\{.")


def _strip(text: str) -> str:
    return _ROM_COLOR_RE.sub("", text)


def _make_online(target):
    """Attach a fake `desc` so `_handle_buffered_tell` treats target as
    connected and runs the live `_deliver_tell` path rather than
    short-circuiting on the linkdead branch."""
    target.desc = object()
    return target


def test_tell_001_to_char_wording_drops_comma() -> None:
    """TELL-001 — TO_CHAR `"You tell $N '$t'"` (no comma)."""
    sender = create_test_character("Tellsender", 3001)
    target = _make_online(create_test_character("Tellrecv", 3001))

    out = do_tell(sender, f"{target.name} hello there")
    plain = _strip(out)
    assert plain == "You tell Tellrecv 'hello there'", (
        f"TO_CHAR wording diverges from ROM; got {out!r}"
    )


def test_tell_002_to_vict_wording_drops_comma() -> None:
    """TELL-002 — TO_VICT `"$n tells you '$t'"` (no comma)."""
    sender = create_test_character("Tellsender2", 3001)
    target = _make_online(create_test_character("Tellrecv2", 3001))

    do_tell(sender, f"{target.name} hello again")
    delivered = [_strip(m) for m in target.messages if "tells you" in m]
    assert delivered, f"target received no tell; messages={target.messages}"
    assert any("Tellsender2 tells you 'hello again'" in m for m in delivered), (
        f"TO_VICT wording diverges from ROM `$n tells you '$t'`; got {delivered!r}"
    )
    assert not any("tells you, '" in m for m in delivered), (
        f"comma after `you` leaked through; got {delivered!r}"
    )


def test_tell_003_invisible_sender_renders_as_someone_to_target() -> None:
    """TELL-003 — TO_VICT `$n` substitutes via PERS(ch, victim)."""
    from mud.models.constants import AffectFlag

    sender = create_test_character("Tellghost", 3001)
    target = _make_online(create_test_character("Tellobserver", 3001))
    sender.affected_by |= int(AffectFlag.INVISIBLE)
    assert not target.has_affect(AffectFlag.DETECT_INVIS)

    do_tell(sender, f"{target.name} boo")
    delivered = [_strip(m) for m in target.messages if "tells you" in m]
    assert delivered, f"target received no tell; messages={target.messages}"
    assert any("someone tells you 'boo'" in m for m in delivered), (
        f"PERS missing for invisible sender; got {delivered!r}"
    )
    assert not any("Tellghost" in m for m in delivered), (
        f"invisible sender's real name leaked through PERS; got {delivered!r}"
    )


def test_tell_004_invisible_target_renders_as_someone_to_sender() -> None:
    """TELL-004 — TO_CHAR `$N` substitutes via PERS(ch, victim).

    If the sender cannot see the target (target invisible, sender
    lacks DETECT_INVIS), the sender's TO_CHAR text should render the
    target as "someone" — same PERS rule, observed from the sender
    side this time. ROM act() routes `$N` (capital) through
    PERS(victim, ch).
    """
    from mud.models.constants import AffectFlag

    sender = create_test_character("Tellblind", 3001)
    target = _make_online(create_test_character("Tellhidden", 3001))
    target.affected_by |= int(AffectFlag.INVISIBLE)
    assert not sender.has_affect(AffectFlag.DETECT_INVIS)

    out = do_tell(sender, f"{target.name} psst")
    plain = _strip(out)
    assert plain == "You tell someone 'psst'", (
        f"PERS missing for invisible target in TO_CHAR; got {out!r}"
    )
    assert "Tellhidden" not in out, (
        f"invisible target's real name leaked through PERS; got {out!r}"
    )


def test_tell_005_to_char_wraps_rom_color_codes() -> None:
    """TELL-005 — TO_CHAR wraps `{k...{K$t{k'{x` charcoal/black codes."""
    sender = create_test_character("Tellhue", 3001)
    target = _make_online(create_test_character("Telltarget", 3001))

    out = do_tell(sender, f"{target.name} hi")
    assert out == "{kYou tell Telltarget '{Khi{k'{x", (
        f"TO_CHAR colour wrapping diverges from ROM; got {out!r}"
    )


def test_tell_005_to_vict_wraps_rom_color_codes() -> None:
    """TELL-005 — TO_VICT wraps `{k$n tells you '{K$t{k'{x` codes."""
    sender = create_test_character("Tellhue2", 3001)
    target = _make_online(create_test_character("Telltarget2", 3001))

    do_tell(sender, f"{target.name} hi")
    expected = "{kTellhue2 tells you '{Khi{k'{x"
    assert expected in target.messages, (
        f"TO_VICT colour wrapping diverges from ROM; "
        f"expected {expected!r} in {target.messages!r}"
    )
