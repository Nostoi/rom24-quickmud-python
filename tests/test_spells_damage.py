from __future__ import annotations

from collections.abc import Callable

from mud.affects.saves import saves_spell
from mud.game_loop import SkyState, weather
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import DamageType, Position, Sector
from mud.models.room import Room
from mud.skills.handlers import acid_blast, burning_hands, call_lightning
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": "mob",
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def _rom_acid_blast(level: int, victim: Character) -> int:
    damage = rng_mm.dice(max(level, 0), 12)
    if saves_spell(level, victim, DamageType.ACID):
        damage = c_div(damage, 2)
    return damage


def _rom_burning_hands(level: int, victim: Character) -> int:
    dam_each = [
        0,
        0,
        0,
        0,
        0,
        14,
        17,
        20,
        23,
        26,
        29,
        29,
        29,
        30,
        30,
        31,
        31,
        32,
        32,
        33,
        33,
        34,
        34,
        35,
        35,
        36,
        36,
        37,
        37,
        38,
        38,
        39,
        39,
        40,
        40,
        41,
        41,
        42,
        42,
        43,
        43,
        44,
        44,
        45,
        45,
        46,
        46,
        47,
        47,
        48,
        48,
    ]
    capped = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)
    if saves_spell(level, victim, DamageType.FIRE):
        damage = c_div(damage, 2)
    return damage


def _rom_call_lightning(level: int, victim: Character) -> int:
    dice_level = max(0, c_div(level, 2))
    damage = rng_mm.dice(dice_level, 8)
    if saves_spell(level, victim, DamageType.LIGHTNING):
        damage = c_div(damage, 2)
    return damage


def _assert_matches_rom(
    spell: Callable[[Character, Character | None], int],
    rom_func: Callable[[int, Character], int],
    seed: int,
    level: int,
) -> None:
    caster = make_character(level=level)
    victim = make_character(hit=120, max_hit=120, level=24)
    rom_victim = make_character(hit=120, max_hit=120, level=24)

    rng_mm.seed_mm(seed)
    expected = rom_func(level, rom_victim)
    rng_mm.seed_mm(seed)
    dealt = spell(caster, victim)

    assert dealt == expected
    assert victim.hit == 120 - dealt


def test_damage_spells_match_rom() -> None:
    _assert_matches_rom(acid_blast, _rom_acid_blast, seed=0xACE1, level=32)
    _assert_matches_rom(burning_hands, _rom_burning_hands, seed=0xBEEF, level=24)

    level = 36
    caster = make_character(level=level)
    victim = make_character(hit=120, max_hit=120, level=24)
    rom_victim = make_character(hit=120, max_hit=120, level=24)

    room = Room(vnum=1, name="Test", sector_type=int(Sector.FIELD))
    room.add_character(caster)
    room.add_character(victim)
    old_sky = weather.sky
    weather.sky = SkyState.RAINING

    try:
        rng_mm.seed_mm(0xABCD)
        expected = _rom_call_lightning(level, rom_victim)
        rng_mm.seed_mm(0xABCD)
        dealt = call_lightning(caster, victim)

        assert dealt == expected
        assert victim.hit == 120 - dealt
    finally:
        weather.sky = old_sky
