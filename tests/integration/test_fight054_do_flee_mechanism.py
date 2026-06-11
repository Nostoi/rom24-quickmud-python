"""FIGHT-054 enforcement — do_flee movement mechanism.

ROM src/fight.c:2970-3030 do_flee uses a 6-attempt number_door() loop, a
per-attempt daze check (number_range(0, ch->daze) != 0 → skip), and a
ROOM_NO_MOB guard for NPCs.  Python used a fake dex-chance roll
(number_percent()) not present in ROM.

Key ROM contract (src/fight.c:2986-3003):
    was_in = ch->in_room;
    for (attempt = 0; attempt < 6; attempt++) {
        door = number_door();
        if ((pexit = was_in->exit[door]) == 0
            || pexit->u1.to_room == NULL
            || IS_SET(pexit->exit_info, EX_CLOSED)
            || number_range(0, ch->daze) != 0
            || (IS_NPC(ch) && IS_SET(pexit->u1.to_room->room_flags, ROOM_NO_MOB)))
            continue;
        move_char(ch, door, FALSE);
        if ((now_in = ch->in_room) == was_in) continue;
        ...success path...
    }
    send_to_char("PANIC! You couldn't escape!\\n\\r", ch);

Mutation tests (must be red before the fix):
  - test_fight054_loop_calls_number_door_six_times: fails because current code
    never calls number_door() at all.
  - test_fight054_daze_blocks_flee: fails because current code has no daze check.
  - test_fight054_room_no_mob_blocks_npc: fails because current code has no
    ROOM_NO_MOB check.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mud.commands.combat import do_flee
from mud.models.character import Character, character_registry
from mud.models.constants import Position, RoomFlag
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _mk_room_list(vnum: int, exit0_to: Room | None = None) -> Room:
    """Build a Room with a proper 6-slot exits list (ROM: EXIT_DATA *exit[6])."""
    room = Room(vnum=vnum, name=f"Room {vnum}", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    # Use the canonical list-of-6 format that Room.exits declares
    room.exits = [None] * 6
    if exit0_to is not None:
        room.exits[0] = Exit(to_room=exit0_to, exit_info=0, keyword="north", key=0)
    room_registry[vnum] = room
    return room


def _mk_fighter(name: str, room: Room, *, ch_class: int = 3, exp: int = 5000) -> Character:
    ch = Character(name=name, level=10, room=room, is_npc=False, hit=100, max_hit=100)
    ch.ch_class = ch_class
    ch.exp = exp
    ch.position = Position.FIGHTING
    ch.wait = 0
    ch.move = 100
    ch.max_move = 100
    ch.daze = 0
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def _mk_npc(name: str, room: Room) -> Character:
    npc = Character(name=name, level=5, room=room, is_npc=True, hit=50, max_hit=50)
    npc.position = Position.FIGHTING
    npc.wait = 0
    npc.daze = 0
    room.people.append(npc)
    character_registry.append(npc)
    return npc


@pytest.fixture()
def flee_rooms():
    dst = Room(vnum=9991, name="Dest", description="", room_flags=0, sector_type=0)
    dst.people = []
    dst.contents = []
    dst.exits = [None] * 6
    src = _mk_room_list(9990, exit0_to=dst)
    room_registry[9991] = dst
    yield src, dst
    room_registry.pop(9990, None)
    room_registry.pop(9991, None)


def test_fight054_loop_calls_number_door_six_times():
    """ROM fight.c:2986-3001 — loop calls number_door() up to 6 times then panics.

    Current Python code never calls number_door() — it uses number_percent() for
    a dex-chance roll instead.  This test fails before the fix because 0 calls
    to number_door are recorded instead of 6.
    """
    # Room with no exits (all None) — every attempt fails
    room = _mk_room_list(9992)
    room_registry[9992] = room

    npc = _mk_npc("monster", room)
    pc = _mk_fighter("hero", room)
    pc.fighting = npc

    door_calls: list[int] = []

    def _counting_door() -> int:
        door_calls.append(1)
        return 0  # always attempt door 0, which is None

    with patch("mud.commands.combat.rng_mm.number_door", side_effect=_counting_door):
        result = do_flee(pc, "")

    room_registry.pop(9992, None)
    # mirrors ROM src/fight.c:2986: for (attempt = 0; attempt < 6; attempt++)
    assert len(door_calls) == 6, f"ROM loop makes exactly 6 number_door() calls; got {len(door_calls)}"
    assert "PANIC" in result


def test_fight054_daze_blocks_flee(flee_rooms):
    """ROM fight.c:2994 — number_range(0, ch->daze) != 0 skips the exit.

    When daze > 0, every attempt may be blocked by the daze roll.  With
    number_range always returning 1 (non-zero), all 6 attempts are blocked.
    Current Python code has no daze check — it always succeeds on a valid exit.
    """
    src, dst = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_fighter("hero", src)
    pc.fighting = npc
    pc.daze = 5  # non-zero → daze check fires

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),  # always try door 0
        patch("mud.commands.combat.rng_mm.number_range", return_value=1),  # daze != 0 → skip
    ):
        result = do_flee(pc, "")

    # mirrors ROM src/fight.c:2994: number_range(0, ch->daze) != 0 → continue
    assert "PANIC" in result, "Daze should have blocked all 6 flee attempts"
    assert pc.room is src, "Character should still be in original room"


def test_fight054_room_no_mob_blocks_npc(flee_rooms):
    """ROM fight.c:2996-2998 — IS_NPC(ch) && IS_SET(room_flags, ROOM_NO_MOB) → skip.

    NPCs cannot flee into ROOM_NO_MOB rooms.  Current Python code has no
    ROOM_NO_MOB check, so NPCs flee successfully into these rooms.
    """
    src, dst = flee_rooms
    dst.room_flags = int(RoomFlag.ROOM_NO_MOB)

    pc = _mk_fighter("hero", src)
    mob = _mk_npc("monster", src)
    mob.fighting = pc

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),  # always try door 0
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),  # no daze block
    ):
        result = do_flee(mob, "")

    # mirrors ROM src/fight.c:2996-2998: ROOM_NO_MOB blocks NPC movement
    assert "PANIC" in result, "NPC should be blocked from fleeing into ROOM_NO_MOB room"
    assert mob.room is src, "NPC should still be in original room"


def test_fight054_successful_flee_uses_number_door(flee_rooms):
    """ROM fight.c:2989 — flee uses number_door(), not number_percent().

    A successful flee calls number_door() to pick a direction, not a dex-percent
    roll.  This test verifies that flee succeeds via number_door() and does NOT
    use number_percent() for the exit-selection decision.
    """
    src, dst = flee_rooms
    npc = _mk_npc("monster", src)
    # Warrior (ch_class=3): no thief-sneak check → number_percent never called
    pc = _mk_fighter("hero", src, ch_class=3, exp=5000)
    pc.fighting = npc

    percent_calls: list[int] = []

    with (
        patch("mud.commands.combat.rng_mm.number_door", return_value=0),  # pick door 0 (valid exit)
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),  # daze=0: not called anyway
        patch(
            "mud.commands.combat.rng_mm.number_percent",
            side_effect=lambda: percent_calls.append(1) or 99,
        ),
    ):
        result = do_flee(pc, "")

    # mirrors ROM src/fight.c:2989: door = number_door() drives exit selection
    assert "You flee from combat!" in result, f"Expected successful flee, got: {result!r}"
    assert pc.room is dst, "PC should have moved to dst room"
    # number_percent must NOT be called for the flee-success decision (warrior has no sneak)
    assert len(percent_calls) == 0, (
        f"number_percent() should not be called for warrior flee exit selection; called {len(percent_calls)} time(s)"
    )


def test_fight054_not_fighting_sets_position_standing():
    """ROM fight.c:2978-2982 — when not fighting, set POS_STANDING if POS_FIGHTING.

    ROM explicitly sets ch->position = POS_STANDING before returning 'not fighting'
    message when the character was in FIGHTING position.
    """
    room = _mk_room_list(9993)
    room_registry[9993] = room
    pc = _mk_fighter("hero", room)
    pc.fighting = None
    pc.position = Position.FIGHTING  # ROM resets this to STANDING

    result = do_flee(pc, "")

    room_registry.pop(9993, None)
    # mirrors ROM src/fight.c:2979-2980: if (ch->position == POS_FIGHTING) ch->position = POS_STANDING
    assert pc.position == Position.STANDING, f"Expected STANDING after flee-while-not-fighting, got {pc.position}"
    assert "aren't fighting" in result
