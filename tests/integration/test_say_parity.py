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


def test_say_001_room_broadcast_drops_comma() -> None:
    """SAY-001 — TO_ROOM wording matches ROM `"$n says '$T'"`.

    ROM C: src/act_comm.c:776
        act ("{6$n says '{7$T{6'{x", ch, NULL, argument, TO_ROOM);

    Stripping ANSI colour codes, the rendered text is `"<name> says 'hello'"` —
    no comma after `says`. Python previously emitted `"<name> says, 'hello'"`.
    """
    speaker = create_test_character("Sayspeaker", 3001)
    listener = create_test_character("Saylistener", 3001)

    process_command(speaker, "say hello")

    delivered = [m for m in listener.messages if "says" in m and "hello" in m]
    assert delivered, f"listener received no say broadcast; messages={listener.messages}"
    assert any("Sayspeaker says 'hello'" in m for m in delivered), (
        f"TO_ROOM wording diverges from ROM `$n says '$T'`; got {delivered!r}"
    )
    assert not any("says, '" in m for m in delivered), (
        f"comma after `says` leaked through; got {delivered!r}"
    )


def test_say_001_to_char_drops_comma() -> None:
    """SAY-001 — TO_CHAR wording matches ROM `"You say '$T'"`.

    ROM C: src/act_comm.c:777
        act ("{6You say '{7$T{6'{x", ch, NULL, argument, TO_CHAR);
    """
    speaker = create_test_character("Sayself", 3001)
    out = process_command(speaker, "say hello")
    assert out == "You say 'hello'", (
        f"TO_CHAR wording diverges from ROM `You say '$T'`; got {out!r}"
    )


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
    delivered = [m for m in listener.messages if m == expected]
    assert len(delivered) == 1, (
        f"INV-001 SINGLE-DELIVERY violation on do_say — listener got "
        f"{len(delivered)} copies of {expected!r}; full messages: "
        f"{listener.messages!r}"
    )
