"""Integration coverage for fight.c damage-path safe-room parity."""

from __future__ import annotations

from mud.combat.engine import attack_round
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import DamageType, Position, RoomFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


def test_attack_round_does_no_damage_after_fight_moves_into_safe_room(monkeypatch) -> None:
    """ROM `src/fight.c:725-733` re-checks `is_safe()` inside `damage()`."""

    arena = Room(vnum=9292, name="Arena", description="Unsafe room.", room_flags=0, sector_type=0)
    sanctuary = Room(
        vnum=9293,
        name="Sanctuary",
        description="Safe room.",
        room_flags=int(RoomFlag.ROOM_SAFE),
        sector_type=0,
    )
    for room in (arena, sanctuary):
        room.people = []
        room.contents = []
        room_registry[room.vnum] = room

    attacker = Character(
        name="Hero",
        level=10,
        room=arena,
        is_npc=False,
        pcdata=PCData(),
        hitroll=100,
        damroll=5,
        dam_type=int(DamageType.BASH),
    )
    victim = Character(
        name="dummy",
        short_descr="a training dummy",
        level=10,
        room=arena,
        is_npc=True,
        hit=100,
        max_hit=100,
    )
    attacker.position = Position.FIGHTING
    victim.position = Position.FIGHTING
    attacker.skills["hand to hand"] = 100
    attacker.fighting = victim
    victim.fighting = attacker

    arena.add_character(attacker)
    arena.add_character(victim)
    character_registry.append(attacker)
    character_registry.append(victim)

    arena.remove_character(attacker)
    arena.remove_character(victim)
    sanctuary.add_character(attacker)
    sanctuary.add_character(victim)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: low)

    try:
        result = attack_round(attacker, victim)
    finally:
        for room in (arena, sanctuary):
            room_registry.pop(room.vnum, None)
        if attacker in character_registry:
            character_registry.remove(attacker)
        if victim in character_registry:
            character_registry.remove(victim)

    assert result == ""
    assert victim.hit == 100
