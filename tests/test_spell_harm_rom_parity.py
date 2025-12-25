from __future__ import annotations

from mud.affects.saves import saves_spell
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import DamageType, Position
from mud.skills.handlers import harm
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


def _rom_harm(level: int, victim: Character) -> int:
    """ROM L3053-3057: harm damage formula."""
    victim_hit = int(getattr(victim, "hit", 0) or 0)
    dice_roll = rng_mm.dice(1, 4)
    dam = max(20, victim_hit - dice_roll)

    if saves_spell(level, victim, DamageType.HARM):
        dam = min(50, c_div(dam, 2))

    dam = min(100, dam)
    return dam


def test_harm_minimum_damage():
    """ROM L3053: Minimum damage is 20."""
    caster = make_character(level=30)
    victim = make_character(hit=10, max_hit=100, level=30)
    rom_victim = make_character(hit=10, max_hit=100, level=30)

    rng_mm.seed_mm(0x1234)
    expected = _rom_harm(30, rom_victim)
    rng_mm.seed_mm(0x1234)
    dealt = harm(caster, victim)

    assert dealt == expected
    assert dealt >= 20


def test_harm_normal_damage():
    """ROM L3053: Normal damage is victim_hit - dice(1,4)."""
    caster = make_character(level=30)
    victim = make_character(hit=80, max_hit=100, level=1)
    rom_victim = make_character(hit=80, max_hit=100, level=1)

    rng_mm.seed_mm(0xABCD)
    expected = _rom_harm(30, rom_victim)
    rng_mm.seed_mm(0xABCD)
    dealt = harm(caster, victim)

    assert dealt == expected
    assert victim.hit == 80 - dealt


def test_harm_save_reduces_damage():
    """ROM L3054-3055: Save reduces to min(50, dam/2)."""
    caster = make_character(level=10)
    victim = make_character(hit=100, max_hit=100, level=50)

    damages = []
    for seed in range(50):
        rng_mm.seed_mm(seed)
        rom_victim = make_character(hit=100, max_hit=100, level=50)
        expected = _rom_harm(10, rom_victim)

        rng_mm.seed_mm(seed)
        victim.hit = 100
        dealt = harm(caster, victim)

        assert dealt == expected
        damages.append(dealt)

    assert any(d <= 50 for d in damages)


def test_harm_capped_at_100():
    """ROM L3056: Damage capped at 100."""
    caster = make_character(level=30)
    victim = make_character(hit=500, max_hit=500, level=1)

    for seed in range(20):
        victim.hit = 500
        rng_mm.seed_mm(seed)
        dealt = harm(caster, victim)
        assert dealt <= 100


def test_harm_updates_position():
    """Harm updates victim position if killed."""
    caster = make_character(level=30)
    victim = make_character(hit=19, max_hit=100, level=1)

    rng_mm.seed_mm(0xDEAD)
    dealt = harm(caster, victim)

    assert victim.hit < 0
    assert victim.position != Position.STANDING


def test_harm_requires_both_chars():
    """Harm requires caster and target."""
    caster = make_character(level=30)

    try:
        harm(caster, None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "target" in str(e).lower()

    try:
        harm(None, caster)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "caster" in str(e).lower()


def test_harm_variance_from_dice():
    """ROM L3053: Damage varies by dice(1,4)."""
    caster = make_character(level=30)

    damages = []
    for seed in range(30):
        victim = make_character(hit=100, max_hit=100, level=1)
        rng_mm.seed_mm(seed)
        dealt = harm(caster, victim)
        damages.append(dealt)

    unique_damages = set(damages)
    assert len(unique_damages) >= 3
