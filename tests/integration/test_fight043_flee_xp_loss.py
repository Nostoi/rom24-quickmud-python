"""FIGHT-043 enforcement — do_flee XP penalty.

ROM src/fight.c:3010-3019:
    if (!IS_NPC(ch)) {
        send_to_char("You flee from combat!\n\r", ch);
        if ((ch->class == 2) && (number_percent() < 3 * (ch->level / 2)))
            send_to_char("You snuck away safely.\n\r", ch);
        else {
            send_to_char("You lost 10 exp.\n\r", ch);
            gain_exp(ch, -10);
        }
    }

Python was missing this block entirely — successful flee never deducted 10 XP
for non-thieves and never ran the thief sneak check.

Mutation tests (both must be red before the fix):
  - Remove the gain_exp call → test_non_thief_flee_loses_10_exp fails
  - Remove the sneak check → test_thief_sneak_no_xp_loss fails
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mud.commands.combat import do_flee
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Exit, Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _mk_room(vnum: int, with_exit_to: Room | None = None) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    if with_exit_to is not None:
        room.exits = {0: Exit(to_room=with_exit_to, exit_info=0, keyword="", key=0)}
    else:
        room.exits = {}
    room_registry[vnum] = room
    return room


def _mk_fighter(name: str, room: Room, *, ch_class: int = 3, exp: int = 1000) -> Character:
    ch = Character(
        name=name,
        level=10,
        room=room,
        is_npc=False,
        hit=100,
        max_hit=100,
    )
    ch.ch_class = ch_class
    ch.exp = exp
    ch.position = Position.FIGHTING
    ch.wait = 0
    ch.move = 100
    ch.max_move = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def _mk_npc(name: str, room: Room) -> Character:
    npc = Character(name=name, level=5, room=room, is_npc=True, hit=50, max_hit=50)
    npc.position = Position.FIGHTING
    npc.wait = 0
    room.people.append(npc)
    character_registry.append(npc)
    return npc


@pytest.fixture()
def flee_rooms(request):
    """Two connected rooms; teardown removes them from the registry."""
    vnum_src, vnum_dst = getattr(request, "param", (9980, 9981))
    dst = Room(vnum=vnum_dst, name="Dest", description="", room_flags=0, sector_type=0)
    dst.people = []
    dst.contents = []
    dst.exits = {}
    src = _mk_room(vnum_src, with_exit_to=dst)
    room_registry[vnum_dst] = dst
    yield src, dst
    room_registry.pop(vnum_src, None)
    room_registry.pop(vnum_dst, None)


def test_non_thief_flee_loses_10_exp(flee_rooms):
    """ROM src/fight.c:3013-3019 — successful flee by a non-thief PC deducts 10 XP
    and emits 'You lost 10 exp.' Mutation: removing the gain_exp call must break this."""
    src, _ = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_fighter("hero", src, ch_class=3, exp=5000)  # warrior, ch_class=3; above floor (1000)
    pc.fighting = npc

    with (
        patch("mud.commands.combat.rng_mm.number_percent", return_value=1),  # flee succeeds
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),  # pick first exit
    ):
        result = do_flee(pc, "")

    assert pc.exp == 4990, f"Expected 4990 exp after flee penalty, got {pc.exp}"
    assert "You lost 10 exp." in result


def test_non_thief_flee_emits_flee_message(flee_rooms):
    """ROM src/fight.c:3011 — 'You flee from combat!' is delivered to the PC."""
    src, _ = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_fighter("hero", src, ch_class=0, exp=500)  # mage, ch_class=0
    pc.fighting = npc

    with (
        patch("mud.commands.combat.rng_mm.number_percent", return_value=1),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
    ):
        result = do_flee(pc, "")

    assert "You flee from combat!" in result


def test_thief_sneak_no_xp_loss(flee_rooms):
    """ROM src/fight.c:3012-3014 — thief with sneak success keeps all XP.
    Mutation: removing the sneak check must break this."""
    src, _ = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_fighter("rogue", src, ch_class=2, exp=5000)  # thief, ch_class=2; above floor (1000)
    pc.fighting = npc

    # number_percent is called twice:
    #   1. flee success check (return 1 — succeeds)
    #   2. thief sneak check (return 1 — 1 < 3*(10//2)=15 → sneak succeeds)
    call_count = 0

    def _fake_percent():
        nonlocal call_count
        call_count += 1
        return 1  # always low: flee succeeds AND sneak succeeds

    with (
        patch("mud.commands.combat.rng_mm.number_percent", side_effect=_fake_percent),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
    ):
        result = do_flee(pc, "")

    assert pc.exp == 5000, f"Thief sneak should preserve XP, got {pc.exp}"
    assert "You snuck away safely." in result
    assert "You lost 10 exp." not in result


def test_thief_sneak_fail_loses_xp(flee_rooms):
    """ROM src/fight.c:3012 — thief that fails the sneak check still loses 10 XP."""
    src, _ = flee_rooms
    npc = _mk_npc("monster", src)
    pc = _mk_fighter("rogue", src, ch_class=2, exp=5000)  # above floor (1000) so deduction lands
    pc.fighting = npc

    # flee succeeds (roll=1), sneak fails (roll=99 >= 15)
    calls = iter([1, 99])
    with (
        patch("mud.commands.combat.rng_mm.number_percent", side_effect=calls),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
    ):
        result = do_flee(pc, "")

    assert pc.exp == 4990, f"Thief sneak fail should lose 10 XP, got {pc.exp}"
    assert "You lost 10 exp." in result


def test_npc_flee_no_xp_loss(flee_rooms):
    """ROM src/fight.c:3010 — IS_NPC(ch) skips the XP block entirely."""
    src, _ = flee_rooms
    pc = _mk_fighter("hero", src, ch_class=3)
    mob = _mk_npc("monster", src)
    mob.fighting = pc
    mob.exp = 500  # NPCs shouldn't have exp modified

    with (
        patch("mud.commands.combat.rng_mm.number_percent", return_value=1),
        patch("mud.commands.combat.rng_mm.number_range", return_value=0),
    ):
        do_flee(mob, "")

    assert mob.exp == 500, "NPC flee must not deduct XP"
