"""EMOTE-NNN — ROM `do_emote` parity (src/act_comm.c:1067-1095).

Structurally identical to `do_say` — two `act()` calls, one TO_ROOM
and one TO_CHAR — so the same divergence shapes from the do_say
re-audit are expected:

- EMOTE-001 — TO_ROOM `$n` substitution must route through PERS()
  so invisible emoters render as "someone" to unaided listeners.
- EMOTE-002 — TO_CHAR `$n` must render as "You" (act() handles the
  self path); Python previously echoed the actor's real name.

ROM C reference:
    act ("$n $T", ch, NULL, argument, TO_ROOM);
    act ("$n $T", ch, NULL, argument, TO_CHAR);
"""

from __future__ import annotations

import re as _re

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


_ROM_COLOR_RE = _re.compile(r"\{.")


def _strip(text: str) -> str:
    return _ROM_COLOR_RE.sub("", text)


def test_emote_001_invisible_emoter_renders_as_someone_to_unaided_listener() -> None:
    """EMOTE-001 — invisible emoter's `$n` renders as "someone" via PERS().

    ROM C: src/act_comm.c:1091 + src/comm.c `act()` + src/handler.c:2618 `can_see`
    """
    from mud.models.constants import AffectFlag

    emoter = create_test_character("Emoghost", 3001)
    listener = create_test_character("Emoobserver", 3001)
    emoter.affected_by |= int(AffectFlag.INVISIBLE)
    assert not listener.has_affect(AffectFlag.DETECT_INVIS)

    process_command(emoter, "emote waves")

    delivered = [_strip(m) for m in listener.messages if "waves" in m]
    assert delivered, f"listener received no emote broadcast; messages={listener.messages}"
    assert any("Someone waves" in m for m in delivered), (
        f"PERS substitution missing for invisible emoter; got {delivered!r}"
    )
    assert not any("Emoghost" in m for m in delivered), (
        f"invisible emoter's real name leaked through PERS; got {delivered!r}"
    )


def test_emote_001_visible_emoter_renders_real_name_to_listener() -> None:
    """EMOTE-001 — visible emoter renders by real name (control case).

    Pins the both-sides-of-the-branch behaviour: with no invisibility,
    listeners see the emoter's actual name.
    """
    emoter = create_test_character("Emovisible", 3001)
    listener = create_test_character("Emotgt", 3001)

    process_command(emoter, "emote waves")

    delivered = [_strip(m) for m in listener.messages if "waves" in m]
    assert delivered, f"listener received no emote broadcast; messages={listener.messages}"
    assert any("Emovisible waves" in m for m in delivered), (
        f"visible emoter should render by name; got {delivered!r}"
    )


def test_emote_002_self_message_renders_you_not_actor_name() -> None:
    """EMOTE-002 — TO_CHAR `$n` substitutes to "You" (per act()).

    ROM C: src/act_comm.c:1092
        act ("$n $T", ch, NULL, argument, TO_CHAR);

    act() with TO_CHAR substitutes `$n` to "You" (capital, since
    `$n` begins the sentence) so the actor sees `"You <arg>"`.
    Python previously returned `f"{char.name} {args}"` so the actor
    saw their own name instead.
    """
    emoter = create_test_character("Emoself", 3001)
    out = process_command(emoter, "emote nods")
    assert _strip(out) == "You nods", (
        f"TO_CHAR `$n` should render as 'You'; got {out!r}"
    )
