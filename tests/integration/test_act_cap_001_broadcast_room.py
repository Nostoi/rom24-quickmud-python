"""ACT-CAP-001 (broadcast_room half) — `protocol.broadcast_room` capitalizes
the first visible char of the delivered act() line, ROM `act_new` style.

ROM delivers room broadcasts via `act(..., TO_ROOM)` (movement "$n leaves $T."
`src/act_move.c:197`, doors "$n opens $p." `src/act_move.c:384`, wear/drop/get,
spell room lines, …), and `act_new` (`src/comm.c:2376-2379`) upper-cases the
first visible char of every such line (with the `{`-colour-code kludge → cap
`buf[2]`). `mud/net/protocol.py:broadcast_room` is the Python `act(TO_ROOM)`
delivery boundary for ~64 command/skill/movement callers, but it delivered the
caller's baked string verbatim — so an NPC-led or object-led line (e.g.
`"the goblin arrives."`, `"a sword glows."`) reached players uncapped.

`broadcast_room` is a *terminal* delivery primitive — its argument IS the
delivered line, one baked string for every recipient — so the cap is applied
once at function entry (not per-recipient PERS like `_broadcast_pos_change`).
`broadcast_room` does no PERS masking (a separate, known INV-027-family
divergence), so these tests assert the capitalization *property*, not the
rendered name.

Scope note: `broadcast_global` is deliberately NOT capped — it is mixed
(channels are `act()`, but ROM weather is `send_to_char`, `src/update.c`
`weather_update`). The parallel `room.broadcast` Room-method primitive is an
uncapped cousin filed as ACT-CAP-002.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.room import Room
from mud.net.protocol import broadcast_room


def _room_with_listener() -> tuple[Room, Character]:
    room = Room(vnum=99941, name="ACT-CAP-001 probe room")
    listener = Character(name="listener-pc", is_npc=False)
    listener.messages = []  # no connection → mailbox-append delivery path
    room.add_character(listener)
    return room, listener


def test_broadcast_room_caps_plain_line() -> None:
    # mirrors ROM act("$n arrives.", ..., TO_ROOM) → src/comm.c:2376 caps buf[0].
    room, listener = _room_with_listener()
    broadcast_room(room, "the goblin arrives.")
    assert listener.messages, "listener received nothing"
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"first char not capitalized: {msg!r}"
    assert "goblin arrives." in msg, msg


def test_broadcast_room_caps_after_color_kludge() -> None:
    # mirrors ROM act("{R...{x", ..., TO_ROOM) → the `{`-kludge caps buf[2]
    # (the char after the 2-char {X colour code), leaving the code intact.
    room, listener = _room_with_listener()
    broadcast_room(room, "{Rthe goblin explodes!{x")
    msg = listener.messages[-1]
    assert msg.startswith("{R"), f"colour code mangled: {msg!r}"
    assert msg[2].isupper(), f"char after colour code not capitalized: {msg!r}"
    assert "goblin explodes!" in msg, msg


def test_broadcast_room_leaves_already_capital_unchanged() -> None:
    # A PC-name-led or "The …"-led line is already capital — the cap is a no-op,
    # never a corruption.
    room, listener = _room_with_listener()
    broadcast_room(room, "Bob has arrived.")
    assert listener.messages[-1] == "Bob has arrived."
