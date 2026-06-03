"""SHOUT-NNN / YELL-NNN — ROM `do_shout` (act_comm.c:795-841) and
`do_yell` (act_comm.c:1033-1064) parity.

The 2026-05-23 re-audit found four divergences:

- SHOUT-001 — TO_CHAR `"You shout '$T'"` (no comma). Python had
  `"You shout, '..'"`.
- SHOUT-002 — TO_VICT `"$n shouts '$t'"` (no comma). Python had
  `"{name} shouts, '..'"`.
- SHOUT-003 — TO_VICT `$n` routes through PERS — invisible shouter
  shows as `"someone"` to listeners without DETECT_INVIS. Python
  hardcoded `char.name`.
- YELL-001 — TO_VICT `$n` routes through PERS — same as SHOUT-003.
  (Python's `do_yell` already gets the wording right; only PERS is
  missing.)

Neither ROM `do_shout` nor `do_yell` use colour codes (unlike say
`{6...{x` and tell `{k...{x`), so no SHOUT/YELL colour gap.
"""

from __future__ import annotations

import re as _re

import pytest

from mud.commands.communication import do_shout, do_yell
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


def test_shout_001_to_char_wording_drops_comma() -> None:
    """SHOUT-001 — TO_CHAR `"You shout '$T'"` (no comma)."""
    shouter = create_test_character("Shoutsender", 3001)
    out = do_shout(shouter, "hello")
    assert out == "You shout 'hello'", f"TO_CHAR wording diverges from ROM `You shout '$T'`; got {out!r}"


def test_shout_002_to_vict_wording_drops_comma() -> None:
    """SHOUT-002 — TO_VICT `"$n shouts '$t'"` (no comma)."""
    shouter = create_test_character("Shoutsrc", 3001)
    listener = create_test_character("Shoutlistener", 3001)

    do_shout(shouter, "world")
    delivered = [_strip(m) for m in listener.messages if "shouts" in m]
    assert delivered, f"listener received no shout; messages={listener.messages}"
    assert any("Shoutsrc shouts 'world'" in m for m in delivered), (
        f"TO_VICT wording diverges from ROM; got {delivered!r}"
    )
    assert not any("shouts, '" in m for m in delivered), f"comma after `shouts` leaked through; got {delivered!r}"


def test_shout_003_invisible_shouter_renders_as_someone_to_listener() -> None:
    """SHOUT-003 — TO_VICT `$n` substitutes via PERS(ch, listener)."""
    from mud.models.constants import AffectFlag

    shouter = create_test_character("Shoutghost", 3001)
    listener = create_test_character("Shoutobserver", 3001)
    shouter.affected_by |= int(AffectFlag.INVISIBLE)
    assert not listener.has_affect(AffectFlag.DETECT_INVIS)

    do_shout(shouter, "boo")
    delivered = [_strip(m) for m in listener.messages if "shouts" in m]
    assert delivered, f"listener received no shout; messages={listener.messages}"
    assert any("Someone shouts 'boo'" in m for m in delivered), f"PERS missing for invisible shouter; got {delivered!r}"
    assert not any("Shoutghost" in m for m in delivered), (
        f"invisible shouter's real name leaked through PERS; got {delivered!r}"
    )


def test_yell_001_invisible_yeller_renders_as_someone_to_listener() -> None:
    """YELL-001 — TO_VICT `$n` substitutes via PERS(ch, listener).

    Same PERS pattern as SHOUT-003 / SAY-002 / EMOTE-001 / TELL-003.
    Python's `do_yell` already gets the no-comma wording right; only
    PERS substitution is missing.
    """
    from mud.models.constants import AffectFlag

    yeller = create_test_character("Yellghost", 3001)
    listener = create_test_character("Yellobserver", 3001)
    yeller.affected_by |= int(AffectFlag.INVISIBLE)
    assert not listener.has_affect(AffectFlag.DETECT_INVIS)

    do_yell(yeller, "boo")
    delivered = [_strip(m) for m in listener.messages if "yells" in m]
    assert delivered, f"listener received no yell; messages={listener.messages}"
    assert any("Someone yells 'boo'" in m for m in delivered), f"PERS missing for invisible yeller; got {delivered!r}"
    assert not any("Yellghost" in m for m in delivered), (
        f"invisible yeller's real name leaked through PERS; got {delivered!r}"
    )
