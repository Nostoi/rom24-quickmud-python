"""Integration coverage for fight.c command-entry parity gaps."""

from __future__ import annotations

from mud.combat import engine as combat_engine
from mud.commands.combat import do_kill
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


def test_do_kill_uses_rom_multi_hit_sequence(monkeypatch) -> None:
    """ROM `src/fight.c:2815-2817` enters combat via `multi_hit()`, not one swing."""

    room = Room(vnum=9191, name="Arena", description="A combat test room.", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[room.vnum] = room

    attacker = Character(name="Hero", level=1, room=room, is_npc=False, pcdata=PCData())
    victim = Character(
        name="dummy",
        short_descr="a training dummy",
        level=1,
        room=room,
        is_npc=True,
        hit=500,
        max_hit=500,
    )
    attacker.position = Position.STANDING
    victim.position = Position.STANDING
    attacker.second_attack_skill = 100
    attacker.third_attack_skill = 100
    attacker.add_affect(AffectFlag.HASTE)

    room.add_character(attacker)
    room.add_character(victim)
    character_registry.append(attacker)
    character_registry.append(victim)

    calls: list[tuple[str, str, str | int | None]] = []

    def _record_attack_round(ch: Character, target: Character, dt: str | int | None = None) -> str:
        # mirrors ROM src/fight.c:209-244 — multi_hit drives repeated one_hit calls
        calls.append((ch.name, target.name, dt))
        ch.fighting = target
        target.fighting = ch
        ch.position = Position.FIGHTING
        target.position = Position.FIGHTING
        return f"hit {len(calls)}"

    monkeypatch.setattr(combat_engine, "attack_round", _record_attack_round)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    try:
        result = do_kill(attacker, "dummy")
    finally:
        room_registry.pop(room.vnum, None)
        if attacker in character_registry:
            character_registry.remove(attacker)
        if victim in character_registry:
            character_registry.remove(victim)

    assert result == "hit 1"
    assert len(calls) == 4
