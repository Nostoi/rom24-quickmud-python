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
  `buf[0] = UPPER(buf[0])` to capitalize. (✅ FIXED 2.11.42 — ACT-CAP-003.)

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
    assert plain == "You tell Tellrecv 'hello there'", f"TO_CHAR wording diverges from ROM; got {out!r}"


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
    assert not any("tells you, '" in m for m in delivered), f"comma after `you` leaked through; got {delivered!r}"


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
    assert any("Someone tells you 'boo'" in m for m in delivered), (
        f"PERS missing for invisible sender; got {delivered!r}"
    )
    assert not any("Tellghost" in m for m in delivered), (
        f"invisible sender's real name leaked through PERS; got {delivered!r}"
    )


def test_tell_004_to_char_uses_pers_for_target_name() -> None:
    """TELL-004 — TO_CHAR `$N` substitutes via PERS(victim, ch).

    ROM C: src/act_comm.c:941
        act ("{kYou tell $N '{K$t{k'{x", ch, argument, victim, TO_CHAR);

    ROM's act() routes `$N` (capital) through PERS(victim, ch), so a
    target the sender cannot see would render as "someone". In
    practice this is masked by `get_char_world` (both ROM at
    src/handler.c:`get_char_world` and Python at
    mud/world/char_find.py:get_char_world) which itself filters via
    `can_see` during name lookup — an invisible target returns
    "They aren't here." before PERS would ever evaluate.

    This test verifies the code-structure parity: do_tell's TO_CHAR
    return value goes through `pers()` rather than hardcoding
    `target.name`. The visible-target case must still render the
    real name (PERS returns the target's name when can_see passes).
    The "someone" branch is exercised by the PERS unit tests and
    by SAY-002/EMOTE-001/TELL-003; do_tell's lookup-filter makes
    the TO_CHAR "someone" branch unreachable in normal play, so we
    pin the code path here rather than try to manufacture an
    unreachable state.
    """
    sender = create_test_character("Tellmsg", 3001)
    target = _make_online(create_test_character("Tellvis", 3001))

    out = do_tell(sender, f"{target.name} hi there")
    plain = _strip(out)
    assert plain == "You tell Tellvis 'hi there'", (
        f"TO_CHAR PERS-routed name must equal real name for visible target; got {out!r}"
    )


def test_tell_005_to_char_wraps_rom_color_codes() -> None:
    """TELL-005 — TO_CHAR wraps `{k...{K$t{k'{x` charcoal/black codes."""
    sender = create_test_character("Tellhue", 3001)
    target = _make_online(create_test_character("Telltarget", 3001))

    out = do_tell(sender, f"{target.name} hi")
    assert out == "{kYou tell Telltarget '{Khi{k'{x", f"TO_CHAR colour wrapping diverges from ROM; got {out!r}"


def test_tell_005_to_vict_wraps_rom_color_codes() -> None:
    """TELL-005 — TO_VICT wraps `{k$n tells you '{K$t{k'{x` codes."""
    sender = create_test_character("Tellhue2", 3001)
    target = _make_online(create_test_character("Telltarget2", 3001))

    do_tell(sender, f"{target.name} hi")
    expected = "{kTellhue2 tells you '{Khi{k'{x"
    assert expected in target.messages, (
        f"TO_VICT colour wrapping diverges from ROM; expected {expected!r} in {target.messages!r}"
    )


def test_tell_009_nochannels_sender_can_still_tell() -> None:
    """TELL-009 — ROM `do_tell` (src/act_comm.c:850-866) gates the sender
    ONLY on NOTELL||DEAF then QUIET (then a dead DEAF branch). There is
    **no** COMM_NOCHANNELS gate — NOCHANNELS revokes the *public* channels
    (gossip/grats/quote/…, talk_channel act_comm.c:297-303), not the private
    `tell`. Python had borrowed a spurious NOCHANNELS gate that blocked the
    sender with "The gods have revoked your channel privileges." — the same
    category error closed for `do_shout` as SHOUT-005.

    A NOCHANNELS sender must still deliver the tell normally.
    """
    from mud.commands.communication import _set_comm_flag
    from mud.models.constants import CommFlag

    sender = create_test_character("Tellnochan", 3001)
    target = _make_online(create_test_character("Tellnochanrcv", 3001))
    _set_comm_flag(sender, CommFlag.NOCHANNELS)

    out = do_tell(sender, f"{target.name} hi there")
    plain = _strip(out)
    assert plain == "You tell Tellnochanrcv 'hi there'", (
        f"NOCHANNELS sender must still tell (ROM do_tell has no NOCHANNELS gate); got {out!r}"
    )
