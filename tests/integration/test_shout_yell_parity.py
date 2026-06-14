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


def test_shout_005_sender_gate_matches_rom() -> None:
    """SHOUT-005 — `do_shout`'s only sender precondition is COMM_NOSHOUT.

    ROM `do_shout` (src/act_comm.c:813-820) gates the sender solely on
    COMM_NOSHOUT, then unconditionally `REMOVE_BIT(ch->comm, COMM_SHOUTSOFF)`
    and proceeds. The COMM_QUIET / COMM_NOCHANNELS sender gates belong to the
    `talk_channel` family (gossip/grats, act_comm.c:297-303), NOT to do_shout.
    Python wrongly borrowed all three. This test pins all three facets:

      (a) a COMM_NOCHANNELS sender can still shout;
      (b) a COMM_QUIET sender can still shout;
      (c) a COMM_SHOUTSOFF sender who shouts has SHOUTSOFF auto-cleared AND the
          shout is delivered (ROM `REMOVE_BIT` at act_comm.c:820, silent — no
          "you can hear shouts again" in this path).
    """
    from mud.models.constants import CommFlag

    # (a) NOCHANNELS sender — ROM do_shout has no such gate.
    nch = create_test_character("Shoutnch", 3001)
    nch_listener = create_test_character("Shoutnchear", 3001)
    nch.set_comm_flag(CommFlag.NOCHANNELS)
    out = do_shout(nch, "alpha")
    assert out == "You shout 'alpha'", f"NOCHANNELS sender wrongly blocked from shouting; got {out!r}"
    assert any("Shoutnch shouts 'alpha'" in _strip(m) for m in nch_listener.messages), (
        f"NOCHANNELS sender's shout not delivered; messages={nch_listener.messages}"
    )

    # (b) QUIET sender — ROM do_shout has no such gate.
    q = create_test_character("Shoutquiet", 3001)
    q_listener = create_test_character("Shoutquietear", 3001)
    q.set_comm_flag(CommFlag.QUIET)
    out = do_shout(q, "beta")
    assert out == "You shout 'beta'", f"QUIET sender wrongly blocked from shouting; got {out!r}"
    assert any("Shoutquiet shouts 'beta'" in _strip(m) for m in q_listener.messages), (
        f"QUIET sender's shout not delivered; messages={q_listener.messages}"
    )

    # (c) SHOUTSOFF sender — ROM auto-clears the flag and proceeds (silent).
    so = create_test_character("Shoutoff", 3001)
    so_listener = create_test_character("Shoutoffear", 3001)
    so.set_comm_flag(CommFlag.SHOUTSOFF)
    out = do_shout(so, "gamma")
    assert out == "You shout 'gamma'", f"SHOUTSOFF sender wrongly blocked instead of auto-cleared; got {out!r}"
    assert not so.has_comm_flag(CommFlag.SHOUTSOFF), (
        "ROM REMOVE_BIT(COMM_SHOUTSOFF) — flag must be auto-cleared when shouting content"
    )
    assert any("Shoutoff shouts 'gamma'" in _strip(m) for m in so_listener.messages), (
        f"SHOUTSOFF sender's shout not delivered after auto-clear; messages={so_listener.messages}"
    )
