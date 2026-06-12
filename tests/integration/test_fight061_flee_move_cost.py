"""FIGHT-061 enforcement — do_flee sector-based move cost, PC guard, exhaustion check.

ROM src/fight.c:3002 calls move_char(ch, door, FALSE).  ROM src/act_move.c:115-193
inside move_char only deducts movement for !IS_NPC(ch) using the sector-based formula:

    move = movement_loss[in_sector] + movement_loss[out_sector];
    move /= 2;
    if (IS_AFFECTED(ch, AFF_FLYING) || IS_AFFECTED(ch, AFF_HASTE)) move /= 2;
    if (IS_AFFECTED(ch, AFF_SLOW)) move *= 2;
    if (ch->move < move) { send_to_char("You are too exhausted.", ch); return; }
    ch->move -= move;

Python used a flat `max(0, char.move - c_div(char.max_move, 10))` applied to ALL
characters after a successful flee, introducing three divergences:
  1. Wrong cost formula (max_move/10 instead of sector-average)
  2. Missing PC-only guard (NPCs had move deducted)
  3. Missing exhaustion check (insufficient move still allowed flee)

Mutation tests (must be red before the fix):
  - test_fight061_pc_flee_uses_sector_cost: fails because Python deducts max_move/10 = 10
    instead of the correct FIELD→FIELD sector cost = 2.
  - test_fight061_npc_flee_no_move_deduction: fails because Python deducts move from NPCs.
  - test_fight061_exhausted_pc_cannot_flee: fails because Python ignores exhaustion
    and allows the flee regardless of char.move.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mud.commands.combat import do_flee
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Exit, Room
from mud.registry import room_registry

# FIELD sector type (index 2 in ROM movement_loss array, cost 2)
# movement_loss[FIELD] = 2, so FIELD→FIELD cost = (2+2)//2 = 2
_SECTOR_FIELD = 2


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _mk_flee_rooms(src_vnum: int = 8880, dst_vnum: int = 8881) -> tuple[Room, Room]:
    """Two FIELD-sector rooms connected by exit 0."""
    dst = Room(
        vnum=dst_vnum,
        name="Dest Field",
        description="",
        room_flags=0,
        sector_type=_SECTOR_FIELD,
    )
    dst.people = []
    dst.contents = []
    dst.exits = [None] * 6

    src = Room(
        vnum=src_vnum,
        name="Src Field",
        description="",
        room_flags=0,
        sector_type=_SECTOR_FIELD,
    )
    src.people = []
    src.contents = []
    src.exits = [None] * 6
    src.exits[0] = Exit(to_room=dst, exit_info=0, keyword="north", key=0)

    room_registry[src_vnum] = src
    room_registry[dst_vnum] = dst
    return src, dst


@pytest.fixture()
def flee_rooms():
    src, dst = _mk_flee_rooms()
    yield src, dst
    room_registry.pop(8880, None)
    room_registry.pop(8881, None)


def _mk_pc(name: str, room: Room, *, move: int, max_move: int = 100) -> Character:
    pc = Character(name=name, level=10, room=room, is_npc=False, hit=100, max_hit=100)
    pc.ch_class = 3  # warrior — no sneak roll
    pc.exp = 5000
    pc.position = Position.FIGHTING
    pc.wait = 0
    pc.move = move
    pc.max_move = max_move
    pc.daze = 0
    pc.affected_by = 0
    room.people.append(pc)
    character_registry.append(pc)
    return pc


def _mk_npc(name: str, room: Room, *, move: int = 50) -> Character:
    npc = Character(name=name, level=5, room=room, is_npc=True, hit=50, max_hit=50)
    npc.position = Position.FIGHTING
    npc.wait = 0
    npc.daze = 0
    npc.move = move
    npc.max_move = 100
    npc.affected_by = 0
    room.people.append(npc)
    character_registry.append(npc)
    return npc


def test_fight061_pc_flee_uses_sector_cost(flee_rooms):
    """ROM act_move.c:173-193 — PC flee deducts (in_loss+out_loss)/2, not max_move/10.

    FIELD→FIELD: movement_loss[FIELD]=2, cost=(2+2)//2=2.
    PC starts with move=5.  ROM deducts 2 → move==3.
    Current Python deducts c_div(max_move, 10) = 10 → max(0, 5-10) = 0. (wrong)
    """
    src, dst = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_pc("hero", src, move=5, max_move=100)
    pc.fighting = npc

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
        patch("mud.commands.combat.rng_mm.number_percent", return_value=99),
    ):
        result = do_flee(pc, "")

    # mirrors ROM src/act_move.c:193: ch->move -= move  (sector average = 2, not max_move/10 = 10)
    assert "You flee from combat!" in result, f"Expected successful flee, got: {result!r}"
    assert pc.room is dst, "PC should have moved to destination room"
    assert pc.move == 3, (
        f"ROM sector cost FIELD→FIELD = 2; expected move=3 (5-2), got {pc.move}. "
        "Bug: current code uses max_move/10=10 giving max(0,5-10)=0."
    )


def test_fight061_npc_flee_no_move_deduction(flee_rooms):
    """ROM act_move.c:115 — move cost is inside !IS_NPC(ch) block; NPCs don't pay.

    NPC flees successfully.  ROM never deducts movement from NPCs.
    Current Python deducts c_div(max_move, 10) from all characters. (wrong)
    """
    src, dst = flee_rooms
    pc = _mk_pc("hero", src, move=100)
    npc = _mk_npc("monster", src, move=50)
    npc.fighting = pc

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
    ):
        do_flee(npc, "")

    # mirrors ROM src/act_move.c:115: if (!IS_NPC(ch)) { ... ch->move -= move; }
    assert npc.room is dst, "NPC should have moved to destination room"
    assert npc.move == 50, (
        f"NPCs must not lose move points on flee (ROM IS_NPC guard); got {npc.move}. "
        "Bug: current code deducts max_move/10=10, giving move=40."
    )


def test_fight061_exhausted_pc_cannot_flee(flee_rooms):
    """ROM act_move.c:186-190 — if ch->move < move, move_char returns without moving.

    When a PC has fewer move points than the sector cost (FIELD→FIELD=2), every
    flee attempt fails with the exhaustion early-return in move_char, causing
    the 6-attempt loop to exhaust and produce 'PANIC'.

    Current Python deducts max(0, char.move - max_move/10) unconditionally,
    so the character always flees successfully even with move=0. (wrong)
    """
    src, dst = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_pc("hero", src, move=1, max_move=100)  # move=1 < FIELD→FIELD cost=2
    pc.fighting = npc

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
        patch("mud.commands.combat.rng_mm.number_percent", return_value=99),
    ):
        result = do_flee(pc, "")

    # mirrors ROM src/act_move.c:186-190: ch->move < move → move_char returns,
    # now_in == was_in → loop continues → all 6 attempts fail → PANIC
    assert "PANIC" in result, f"Exhausted PC (move=1 < cost=2) should fail to flee. Got: {result!r}"
    assert pc.room is src, "Exhausted PC should remain in original room"
