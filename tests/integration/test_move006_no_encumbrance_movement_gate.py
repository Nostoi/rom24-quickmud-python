"""MOVE-006 — ROM has no carry-weight movement gate.

ROM `src/act_move.c:move_char` gates movement only on move points
(`if (ch->move < move) "You are too exhausted."`), terrain, boats, and flags —
there is **no** carry-weight/carry-number check anywhere in its body, nor
anywhere else in `src/`. ROM enforces carry limits at *pickup/transfer* time
instead (`do_get`/`do_give`/`wear` → "you can't carry that much weight."), so a
player can never become overweight enough to need a movement gate.

QuickMUD invented a `"You are too encumbered to move."` early-return in
`move_character`. These tests pin the ROM behavior: an over-weight / over-count
character still moves freely.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Direction
from mud.models.room import Exit, Room
from mud.world.movement import can_carry_n, can_carry_w, move_character


def _rooms() -> tuple[Room, Room]:
    start = Room(vnum=6100, name="Start")
    dest = Room(vnum=6101, name="Destination")
    start.exits[Direction.NORTH.value] = Exit(to_room=dest)
    return start, dest


def test_overweight_character_moves_freely() -> None:
    """ROM act_move.c:move_char — no carry-weight gate; an overweight PC moves."""

    start, dest = _rooms()
    ch = Character(name="Packmule", move=100)
    start.add_character(ch)

    # Far over both caps — in ROM this state is unreachable via do_get, but if
    # forced it must NOT block movement (ROM gates only on move points).
    ch.carry_weight = can_carry_w(ch) + 500
    ch.carry_number = can_carry_n(ch) + 10

    result = move_character(ch, "north")

    assert "Destination" in result
    assert ch.room is dest


def test_coin_weight_does_not_block_movement() -> None:
    """ROM has no coin-weight movement penalty (only pickup-time caps)."""

    start, dest = _rooms()
    ch = Character(name="Hoarder", move=100)
    start.add_character(ch)
    ch.gold = 100_000  # enormous coin burden

    result = move_character(ch, "north")

    assert "Destination" in result
    assert ch.room is dest
