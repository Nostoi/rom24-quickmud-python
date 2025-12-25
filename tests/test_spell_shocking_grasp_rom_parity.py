from __future__ import annotations

from mud.affects.saves import saves_spell
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import DamageType, Position
from mud.skills.handlers import shocking_grasp
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


def _rom_shocking_grasp(level: int, victim: Character) -> int:
    """ROM L4337-4354: shocking grasp damage table with save-for-half."""
    dam_each = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        20,
        25,
        29,
        33,
        36,
        39,
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
        49,
        49,
        50,
        50,
        51,
        51,
        52,
        52,
        53,
        53,
        54,
        54,
        55,
        55,
        56,
        56,
        57,
        57,
    ]
    capped_level = max(0, min(level, len(dam_each) - 1))
    base = dam_each[capped_level]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)
    if saves_spell(level, victim, DamageType.LIGHTNING):
        damage = c_div(damage, 2)
    return damage


def test_shocking_grasp_low_level():
    """ROM L4337: Level 7 deals 20 base damage."""
    caster = make_character(level=7)
    victim = make_character(hit=100, max_hit=100, level=7)
    rom_victim = make_character(hit=100, max_hit=100, level=7)

    rng_mm.seed_mm(0x1234)
    expected = _rom_shocking_grasp(7, rom_victim)
    rng_mm.seed_mm(0x1234)
    dealt = shocking_grasp(caster, victim)

    assert dealt == expected
    assert victim.hit == 100 - dealt


def test_shocking_grasp_high_level():
    """ROM L4337: Level 50 deals 57 base damage."""
    caster = make_character(level=50)
    victim = make_character(hit=150, max_hit=150, level=30)
    rom_victim = make_character(hit=150, max_hit=150, level=30)

    rng_mm.seed_mm(0xABCD)
    expected = _rom_shocking_grasp(50, rom_victim)
    rng_mm.seed_mm(0xABCD)
    dealt = shocking_grasp(caster, victim)

    assert dealt == expected
    assert victim.hit == 150 - dealt


def test_shocking_grasp_level_capping():
    """ROM L4347-4348: Level capped to table bounds."""
    caster = make_character(level=100)  # Beyond table size
    victim = make_character(hit=200, max_hit=200, level=50)
    rom_victim = make_character(hit=200, max_hit=200, level=50)

    rng_mm.seed_mm(0xBEEF)
    expected = _rom_shocking_grasp(100, rom_victim)  # Should use last table entry (57)
    rng_mm.seed_mm(0xBEEF)
    dealt = shocking_grasp(caster, victim)

    assert dealt == expected


def test_shocking_grasp_save_for_half():
    """ROM L4350-4351: Saving throw halves damage."""
    caster = make_character(level=20)
    victim = make_character(hit=100, max_hit=100, level=40)  # High level = better saves

    # Multiple seeds to find one where save succeeds
    for seed in range(100):
        rng_mm.seed_mm(seed)
        rom_victim = make_character(hit=100, max_hit=100, level=40)
        expected = _rom_shocking_grasp(20, rom_victim)

        rng_mm.seed_mm(seed)
        victim.hit = 100  # Reset
        dealt = shocking_grasp(caster, victim)

        assert dealt == expected, f"Seed {seed}: dealt={dealt} expected={expected}"


def test_shocking_grasp_damage_range():
    """ROM L4349: Damage ranges from base/2 to base*2."""
    caster = make_character(level=30)
    damages = []

    for seed in range(50):
        victim = make_character(hit=200, max_hit=200, level=1)  # Low level to avoid saves
        rng_mm.seed_mm(seed)
        dealt = shocking_grasp(caster, victim)
        damages.append(dealt)

    # Level 30 has base 47, so range is 23-94 (before saves)
    # With saves, minimum is 11 (23/2), max is 94
    assert min(damages) >= 11, f"Min damage {min(damages)} below expected 11"
    assert max(damages) <= 94, f"Max damage {max(damages)} above expected 94"


def test_shocking_grasp_updates_position():
    """Damage updates victim position if reduced to 0 or below."""
    caster = make_character(level=40)
    victim = make_character(hit=10, max_hit=100, level=1)

    rng_mm.seed_mm(0xDEAD)
    dealt = shocking_grasp(caster, victim)

    # Should reduce hit below 0 and update position
    assert victim.hit < 0
    assert victim.position != Position.STANDING  # Should be dead/mortal/etc
