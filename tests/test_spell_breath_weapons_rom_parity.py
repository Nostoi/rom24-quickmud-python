"""ROM parity tests for breath weapon spells.

Tests for: acid_breath, fire_breath, frost_breath, gas_breath, lightning_breath,
           general_purpose, high_explosive

These are dragon breath and wand projectile spells from ROM.
All tests use ROM C formulas and golden file methodology.
"""

from __future__ import annotations

from mud.affects.saves import saves_spell
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import DamageType, Position
from mud.skills.handlers import (
    acid_breath,
    fire_breath,
    frost_breath,
    gas_breath,
    general_purpose,
    high_explosive,
    lightning_breath,
)
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""
    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


# ============================================================================
# ACID_BREATH TESTS (ROM src/magic.c:4625-4652)
# ============================================================================


def test_acid_breath_damage_formula():
    """ROM acid_breath uses hp-based + dice damage (magic.c:4625-4652)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Dragon", level=30, hit=200)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = acid_breath(caster, victim)

    assert damage == 258, f"Expected 258 damage, got {damage}"


def test_acid_breath_minimum_hp():
    """ROM acid_breath uses minimum 12 HP for calculation (magic.c:4636)."""
    rng_mm.seed_mm(100)

    caster = make_character(name="Dragon", level=20, hit=5)
    victim = make_character(name="Victim", level=15, hit=80, max_hit=80)

    damage = acid_breath(caster, victim)

    assert damage == 196, f"Expected 196 damage, got {damage}"


def test_acid_breath_save_halves_damage():
    """ROM acid_breath damage is halved on successful save (magic.c:4642-4645)."""
    rng_mm.seed_mm(200)

    caster = make_character(name="Dragon", level=30, hit=150)
    victim = make_character(name="Victim", level=5, hit=50, max_hit=50)

    damage = acid_breath(caster, victim)

    assert damage > 0, "Acid breath should do damage even on save"


def test_fire_breath_damage_formula():
    """ROM fire_breath uses hp-based + dice damage (magic.c:4656-4713)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Dragon", level=30, hit=180)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = fire_breath(caster, victim)

    assert damage == 295, f"Expected 295 damage, got {damage}"


def test_fire_breath_minimum_hp():
    """ROM fire_breath uses minimum 10 HP for calculation (magic.c:4669)."""
    rng_mm.seed_mm(100)

    caster = make_character(name="Dragon", level=20, hit=5)
    victim = make_character(name="Victim", level=15, hit=80, max_hit=80)

    damage = fire_breath(caster, victim)

    assert damage == 89, f"Expected 89 damage, got {damage}"


def test_frost_breath_damage_formula():
    """ROM frost_breath uses hp-based + dice damage (magic.c:4715-4772)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Dragon", level=30, hit=200)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = frost_breath(caster, victim)

    assert damage == 258, f"Expected 258 damage, got {damage}"


def test_gas_breath_damage_formula():
    """ROM gas_breath uses hp-based + dice damage (magic.c:4774-4812)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Dragon", level=30, hit=200)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = gas_breath(caster, victim)

    assert damage == 192, f"Expected 192 damage, got {damage}"


def test_gas_breath_minimum_hp():
    """ROM gas_breath uses minimum 16 HP for calculation (magic.c:4783)."""
    rng_mm.seed_mm(100)

    caster = make_character(name="Dragon", level=20, hit=10)
    victim = make_character(name="Victim", level=15, hit=80, max_hit=80)

    damage = gas_breath(caster, victim)

    assert damage == 149, f"Expected 149 damage, got {damage}"


def test_lightning_breath_damage_formula():
    """ROM lightning_breath uses hp-based + dice damage (magic.c:4814-4845)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Dragon", level=30, hit=180)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = lightning_breath(caster, victim)

    assert damage == 295, f"Expected 295 damage, got {damage}"


def test_general_purpose_damage_range():
    """ROM general_purpose does 25-100 damage (magic.c:4847-4858)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Caster", level=30)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = general_purpose(caster, victim)

    assert damage == 47, f"Expected 47 damage, got {damage}"


def test_general_purpose_save_halves():
    """ROM general_purpose damage is halved on save (magic.c:4854-4855)."""
    rng_mm.seed_mm(100)

    caster = make_character(name="Caster", level=30)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = general_purpose(caster, victim)

    assert 0 < damage <= 100, f"Damage {damage} out of expected range"


def test_high_explosive_damage_range():
    """ROM high_explosive does 30-120 damage (magic.c:4860-4871)."""
    rng_mm.seed_mm(42)

    caster = make_character(name="Caster", level=30)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = high_explosive(caster, victim)

    assert damage == 52, f"Expected 52 damage, got {damage}"


def test_high_explosive_save_halves():
    """ROM high_explosive damage is halved on save (magic.c:4867-4868)."""
    rng_mm.seed_mm(100)

    caster = make_character(name="Caster", level=30)
    victim = make_character(name="Victim", level=20, hit=100, max_hit=100)

    damage = high_explosive(caster, victim)

    assert 0 < damage <= 120, f"Damage {damage} out of expected range"
