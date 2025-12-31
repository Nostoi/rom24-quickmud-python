"""Additional ROM parity tests for damage spells.

Covers:
- cause_critical, cause_light, cause_serious
- chill_touch, colour_spray
- lightning_bolt, magic_missile
- chain_lightning
- demonfire, dispel_evil, dispel_good
- earthquake
- energy_drain
- flamestrike

These tests follow existing ROM parity test style:
- deterministic RNG via rng_mm.seed_mm(42)
- compute expected outcomes from ROM-style formulas/tables
- assert handler results match expected and damage types are correct
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, DamageType, Position, Stat
from mud.models.room import Room
from mud.skills.handlers import (
    cause_critical,
    cause_light,
    cause_serious,
    chain_lightning,
    chill_touch,
    colour_spray,
    demonfire,
    dispel_evil,
    dispel_good,
    earthquake,
    energy_drain,
    flamestrike,
    lightning_bolt,
    magic_missile,
)
from mud.utils import rng_mm

import mud.skills.handlers as spell_handlers


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""

    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "alignment": overrides.get("alignment", 0),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def _patch_apply_damage(
    monkeypatch,
    *,
    record: list[tuple[int, int | None, str | int | None]],
) -> None:
    """Patch mud.combat.engine.apply_damage to avoid combat engine state and defensive skills.

    Records tuples of: (damage, dam_type, dt).
    Also disables _is_safe_spell and defensive skills (parry/dodge/shield_block).
    """
    from mud.combat import engine

    def _fake_apply_damage(attacker, victim, damage, dam_type=None, *, dt=None, immune=False, show=True):  # noqa: ARG001
        record.append((int(damage), int(dam_type) if dam_type is not None else None, dt))
        victim.hit -= int(damage)
        return ""

    def _safe_spell_patch(caster, victim, *, area=False):
        if area and victim is caster:
            return True
        return False

    monkeypatch.setattr(spell_handlers, "apply_damage", _fake_apply_damage)
    monkeypatch.setattr(engine, "check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr(engine, "check_shield_block", lambda *args, **kwargs: False)
    monkeypatch.setattr(spell_handlers, "_is_safe_spell", _safe_spell_patch)


# ==============================================================================
# CAUSE_* spells
# ==============================================================================


def test_cause_critical_rom_formula_and_damage_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    target = make_character(hit=100, max_hit=100)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = max(0, rng_mm.dice(3, 8) + 30 - 6)

    rng_mm.seed_mm(42)
    dealt = cause_critical(caster, target)

    assert dealt == expected
    assert target.hit == 100 - expected
    assert calls == [(expected, int(DamageType.HARM), "spell")]


def test_cause_light_rom_formula_level_division(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=31)
    target = make_character(hit=100, max_hit=100)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = max(0, rng_mm.dice(1, 8) + c_div(31, 3))

    rng_mm.seed_mm(42)
    dealt = cause_light(caster, target)

    assert dealt == expected
    assert target.hit == 100 - expected
    assert calls == [(expected, int(DamageType.HARM), "spell")]


def test_cause_serious_rom_formula_level_half(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    target = make_character(hit=150, max_hit=150)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = max(0, rng_mm.dice(2, 8) + c_div(30, 2))

    rng_mm.seed_mm(42)
    dealt = cause_serious(caster, target)

    assert dealt == expected
    assert target.hit == 150 - expected
    assert calls == [(expected, int(DamageType.HARM), "spell")]


def test_cause_spells_validation_require_target_and_handle_level_zero(monkeypatch):
    caster = make_character(level=30)
    target = make_character(level=30)

    with pytest.raises(ValueError):
        cause_critical(caster, None)
    with pytest.raises(ValueError):
        cause_light(caster, None)
    with pytest.raises(ValueError):
        cause_serious(caster, None)

    with pytest.raises(ValueError):
        cause_critical(None, target)

    caster0 = make_character(level=0)
    target0 = make_character(hit=100, max_hit=100)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = max(0, rng_mm.dice(3, 8) - 6)

    rng_mm.seed_mm(42)
    dealt = cause_critical(caster0, target0)

    assert dealt == expected
    assert dealt >= 0


# ==============================================================================
# CHILL_TOUCH
# ==============================================================================


_CHILL_TOUCH_DAM_EACH = [
    0,
    0,
    0,
    6,
    7,
    8,
    9,
    12,
    13,
    13,
    13,
    14,
    14,
    14,
    15,
    15,
    15,
    16,
    16,
    16,
    17,
    17,
    17,
    18,
    18,
    18,
    19,
    19,
    19,
    20,
    20,
    20,
    21,
    21,
    21,
    22,
    22,
    22,
    23,
    23,
    23,
    24,
    24,
    24,
    25,
    25,
    25,
    26,
    26,
    26,
    27,
]


def _rom_damage_from_table(dam_each: list[int] | tuple[int, ...], level: int) -> int:
    capped = max(0, min(level, len(dam_each) - 1))
    base = int(dam_each[capped])
    return rng_mm.number_range(c_div(base, 2), base * 2)


def test_chill_touch_damage_save_for_half_and_no_debuff(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    victim = make_character(hit=120, max_hit=120)

    observed: list[tuple[int, int]] = []

    def _always_save(level, target, dam_type):  # noqa: ARG001
        observed.append((int(level), int(dam_type)))
        return True

    monkeypatch.setattr(spell_handlers, "saves_spell", _always_save)

    rng_mm.seed_mm(42)
    expected_raw = _rom_damage_from_table(_CHILL_TOUCH_DAM_EACH, 30)
    expected = c_div(expected_raw, 2)

    rng_mm.seed_mm(42)
    dealt = chill_touch(caster, victim)

    assert dealt == expected
    assert victim.hit == 120 - expected
    assert observed == [(30, int(DamageType.COLD))]
    assert not victim.has_spell_effect("chill touch")


def test_chill_touch_failed_save_applies_strength_penalty(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    victim = make_character(hit=120, max_hit=120)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    rng_mm.seed_mm(42)
    expected = _rom_damage_from_table(_CHILL_TOUCH_DAM_EACH, 30)

    rng_mm.seed_mm(42)
    dealt = chill_touch(caster, victim)

    assert dealt == expected
    assert victim.hit == 120 - expected
    assert victim.has_spell_effect("chill touch")
    effect = victim.spell_effects.get("chill touch")
    assert effect is not None
    assert effect.duration == 6
    assert effect.stat_modifiers.get(Stat.STR) == -1


def test_chill_touch_validation_requires_target_and_handles_level_zero(monkeypatch):
    caster = make_character(level=30)
    with pytest.raises(ValueError):
        chill_touch(caster, None)

    caster0 = make_character(level=0)
    victim0 = make_character(hit=50, max_hit=50)

    observed: list[tuple[int, int]] = []

    def _save(level, target, dam_type):  # noqa: ARG001
        observed.append((int(level), int(dam_type)))
        return True

    monkeypatch.setattr(spell_handlers, "saves_spell", _save)

    rng_mm.seed_mm(42)
    dealt = chill_touch(caster0, victim0)

    assert dealt == 0
    assert observed == [(0, int(DamageType.COLD))]


# ==============================================================================
# COLOUR_SPRAY
# ==============================================================================


_COLOUR_SPRAY_DAM_EACH = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    30,
    35,
    40,
    45,
    50,
    55,
    55,
    55,
    56,
    57,
    58,
    58,
    59,
    60,
    61,
    61,
    62,
    63,
    64,
    64,
    65,
    66,
    67,
    67,
    68,
    69,
    70,
    70,
    71,
    72,
    73,
    73,
    74,
    75,
    76,
    76,
    77,
    78,
    79,
    79,
]


def test_colour_spray_damage_table_and_save_for_half(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20)
    victim = make_character(hit=200, max_hit=200)

    observed: list[tuple[int, int]] = []

    def _save(level, target, dam_type):  # noqa: ARG001
        observed.append((int(level), int(dam_type)))
        return True

    monkeypatch.setattr(spell_handlers, "saves_spell", _save)

    rng_mm.seed_mm(42)
    expected_raw = _rom_damage_from_table(_COLOUR_SPRAY_DAM_EACH, 20)
    expected = c_div(expected_raw, 2)

    rng_mm.seed_mm(42)
    dealt = colour_spray(caster, victim)

    assert dealt == expected
    assert victim.hit == 200 - expected
    assert observed == [(20, int(DamageType.LIGHT))]


def test_colour_spray_failed_save_calls_blindness_at_half_level(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=21)
    victim = make_character(hit=200, max_hit=200)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    observed_level: dict[str, int] = {}

    def _fake_blindness(c, t):
        observed_level["level"] = int(getattr(c, "level", 0) or 0)
        t.apply_spell_effect(spell_handlers.SpellEffect(name="blindness", duration=1, level=observed_level["level"]))
        return True

    monkeypatch.setattr(spell_handlers, "blindness", _fake_blindness)

    rng_mm.seed_mm(42)
    dealt = colour_spray(caster, victim)

    assert dealt > 0
    assert observed_level["level"] == c_div(21, 2)
    assert caster.level == 21
    assert victim.has_spell_effect("blindness")


def test_colour_spray_validation_requires_target_and_handles_level_zero(monkeypatch):
    caster = make_character(level=20)
    with pytest.raises(ValueError):
        colour_spray(caster, None)

    caster0 = make_character(level=0)
    victim0 = make_character(hit=50, max_hit=50)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    rng_mm.seed_mm(42)
    dealt = colour_spray(caster0, victim0)

    assert dealt == 0


# ==============================================================================
# LIGHTNING_BOLT
# ==============================================================================


_LIGHTNING_BOLT_DAM_EACH = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    25,
    28,
    31,
    34,
    37,
    40,
    40,
    41,
    42,
    42,
    43,
    44,
    44,
    45,
    46,
    46,
    47,
    48,
    48,
    49,
    50,
    50,
    51,
    52,
    52,
    53,
    54,
    54,
    55,
    56,
    56,
    57,
    58,
    58,
    59,
    60,
    60,
    61,
    62,
    62,
    63,
    64,
)


def test_lightning_bolt_damage_table_parity_and_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=35)
    victim = make_character(hit=200, max_hit=200)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = _rom_damage_from_table(list(_LIGHTNING_BOLT_DAM_EACH), 35)

    rng_mm.seed_mm(42)
    dealt = lightning_bolt(caster, victim)

    assert dealt == expected
    assert victim.hit == 200 - expected
    assert calls == [(expected, int(DamageType.LIGHTNING), "lightning bolt")]


def test_lightning_bolt_save_for_half(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=35)
    victim = make_character(hit=200, max_hit=200)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected_raw = _rom_damage_from_table(list(_LIGHTNING_BOLT_DAM_EACH), 35)
    expected = c_div(expected_raw, 2)

    rng_mm.seed_mm(42)
    dealt = lightning_bolt(caster, victim)

    assert dealt == expected
    assert calls[0][1] == int(DamageType.LIGHTNING)


def test_lightning_bolt_validation_requires_target_and_handles_level_zero(monkeypatch):
    caster = make_character(level=35)
    with pytest.raises(ValueError):
        lightning_bolt(caster, None)

    caster0 = make_character(level=0)
    victim0 = make_character(hit=10, max_hit=10)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    dealt = lightning_bolt(caster0, victim0)

    assert dealt == 0
    assert calls == [(0, int(DamageType.LIGHTNING), "lightning bolt")]


# ==============================================================================
# MAGIC_MISSILE
# ==============================================================================


_MAGIC_MISSILE_DAM_EACH = (
    0,
    3,
    3,
    4,
    4,
    5,
    6,
    6,
    6,
    6,
    6,
    7,
    7,
    7,
    7,
    7,
    8,
    8,
    8,
    8,
    8,
    9,
    9,
    9,
    9,
    9,
    10,
    10,
    10,
    10,
    10,
    11,
    11,
    11,
    11,
    11,
    12,
    12,
    12,
    12,
    12,
    13,
    13,
    13,
    13,
    13,
    14,
    14,
    14,
    14,
    14,
)


def test_magic_missile_damage_table_parity_and_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    victim = make_character(hit=120, max_hit=120)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = _rom_damage_from_table(list(_MAGIC_MISSILE_DAM_EACH), 30)

    rng_mm.seed_mm(42)
    dealt = magic_missile(caster, victim)

    assert dealt == expected
    assert victim.hit == 120 - expected
    assert calls == [(expected, int(DamageType.ENERGY), "magic missile")]


def test_magic_missile_save_for_half(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    victim = make_character(hit=120, max_hit=120)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    rng_mm.seed_mm(42)
    expected_raw = _rom_damage_from_table(list(_MAGIC_MISSILE_DAM_EACH), 30)
    expected = c_div(expected_raw, 2)

    rng_mm.seed_mm(42)
    dealt = magic_missile(caster, victim)

    assert dealt == expected


def test_magic_missile_validation_requires_target():
    caster = make_character(level=30)
    with pytest.raises(ValueError):
        magic_missile(caster, None)


# ==============================================================================
# CHAIN_LIGHTNING
# ==============================================================================


def _patch_saves_spell(monkeypatch, func: Callable[[int, Character, int], bool]) -> None:
    monkeypatch.setattr(spell_handlers, "saves_spell", func)


def test_chain_lightning_validation_requires_target_and_same_room():
    caster = make_character(level=30)
    target = make_character(level=20)

    assert chain_lightning(caster, target) is False

    with pytest.raises(ValueError):
        chain_lightning(caster, None)


def test_chain_lightning_requires_positive_level():
    room = Room(vnum=1000, name="Test")
    caster = make_character(level=0)
    target = make_character(level=1)
    room.add_character(caster)
    room.add_character(target)

    assert chain_lightning(caster, target) is False


def test_chain_lightning_bounces_with_level_decay(monkeypatch):
    rng_mm.seed_mm(42)

    room = Room(vnum=1000, name="Test")
    caster = make_character(name="Caster", level=10)
    v1 = make_character(name="V1", hit=200, max_hit=200)
    v2 = make_character(name="V2", hit=200, max_hit=200)
    v3 = make_character(name="V3", hit=200, max_hit=200)

    room.add_character(caster)
    room.add_character(v1)
    room.add_character(v2)
    room.add_character(v3)

    _patch_saves_spell(monkeypatch, lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected1 = rng_mm.dice(10, 6)
    expected2 = rng_mm.dice(6, 6)
    expected3 = rng_mm.dice(2, 6)

    rng_mm.seed_mm(42)
    hit = chain_lightning(caster, v1)

    assert hit is True
    assert v1.hit == 200 - expected1
    assert v2.hit == 200 - expected2
    assert v3.hit == 200 - expected3

    assert calls[0][1] == int(DamageType.LIGHTNING)


def test_chain_lightning_save_reduces_to_third(monkeypatch):
    rng_mm.seed_mm(42)

    room = Room(vnum=1000, name="Test")
    caster = make_character(level=10)
    victim = make_character(hit=200, max_hit=200)
    room.add_character(caster)
    room.add_character(victim)

    _patch_saves_spell(monkeypatch, lambda level, target, dam_type: True)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected_hit1 = c_div(rng_mm.dice(10, 6), 3)
    expected_caster = c_div(rng_mm.dice(6, 6), 3)
    expected_hit2 = c_div(rng_mm.dice(2, 6), 3)

    rng_mm.seed_mm(42)
    hit = chain_lightning(caster, victim)

    assert hit is True
    assert victim.hit == 200 - expected_hit1 - expected_hit2
    assert calls[0][1] == int(DamageType.LIGHTNING)


# ==============================================================================
# DEMONFIRE
# ==============================================================================


def test_demonfire_self_targets_non_evil_player(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=10, hit=100, max_hit=100, is_npc=False, alignment=1000)
    victim = make_character(level=10, hit=100, max_hit=100, alignment=-1000)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    rng_mm.seed_mm(42)
    expected = rng_mm.dice(10, 10)

    rng_mm.seed_mm(42)
    dealt = demonfire(caster, victim)

    assert dealt == expected
    assert caster.hit == 100 - expected
    assert victim.hit == 100


def test_demonfire_save_for_half_and_damage_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=10, hit=100, max_hit=100, is_npc=True)
    victim = make_character(level=10, hit=100, max_hit=100)

    observed: list[int] = []

    def _save(level, target, dam_type):  # noqa: ARG001
        observed.append(int(dam_type))
        return True

    monkeypatch.setattr(spell_handlers, "saves_spell", _save)

    rng_mm.seed_mm(42)
    expected = c_div(rng_mm.dice(10, 10), 2)

    rng_mm.seed_mm(42)
    dealt = demonfire(caster, victim)

    assert dealt == expected
    assert observed[0] == int(DamageType.NEGATIVE)


def test_demonfire_validation_requires_caster_and_level_zero_minimum_one(monkeypatch):
    with pytest.raises(ValueError):
        demonfire(None, make_character())

    caster = make_character(level=0, hit=100, max_hit=100, is_npc=True)
    victim = make_character(level=10, hit=100, max_hit=100)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    rng_mm.seed_mm(42)
    expected = rng_mm.dice(1, 10)

    rng_mm.seed_mm(42)
    dealt = demonfire(caster, victim)

    assert dealt == expected


# ==============================================================================
# DISPEL_EVIL / DISPEL_GOOD
# ==============================================================================


def test_dispel_evil_alignment_gating_good_and_neutral_targets(monkeypatch):
    caster = make_character(level=20, is_npc=True)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    good = make_character(level=20, hit=100, max_hit=100, alignment=1000)
    neutral = make_character(level=20, hit=100, max_hit=100, alignment=0)

    rng_mm.seed_mm(42)
    assert dispel_evil(caster, good) == 0
    assert good.hit == 100

    rng_mm.seed_mm(42)
    assert dispel_evil(caster, neutral) == 0
    assert neutral.hit == 100


def test_dispel_good_alignment_gating_evil_and_neutral_targets(monkeypatch):
    caster = make_character(level=20, is_npc=True)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    evil = make_character(level=20, hit=100, max_hit=100, alignment=-1000)
    neutral = make_character(level=20, hit=100, max_hit=100, alignment=0)

    rng_mm.seed_mm(42)
    assert dispel_good(caster, evil) == 0
    assert evil.hit == 100

    rng_mm.seed_mm(42)
    assert dispel_good(caster, neutral) == 0
    assert neutral.hit == 100


def test_dispel_evil_damage_formula_and_save_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20, is_npc=True)
    victim = make_character(level=20, hit=100, max_hit=100, alignment=-1000)

    observed: list[int] = []

    def _no_save(level, target, dam_type):  # noqa: ARG001
        observed.append(int(dam_type))
        return False

    monkeypatch.setattr(spell_handlers, "saves_spell", _no_save)

    rng_mm.seed_mm(42)
    expected = rng_mm.dice(20, 4)

    rng_mm.seed_mm(42)
    dealt = dispel_evil(caster, victim)

    assert dealt == expected
    assert victim.hit == 100 - expected
    assert observed == [int(DamageType.HOLY)]


def test_dispel_good_damage_formula_and_save_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20, is_npc=True)
    victim = make_character(level=20, hit=100, max_hit=100, alignment=1000)

    observed: list[int] = []

    def _no_save(level, target, dam_type):  # noqa: ARG001
        observed.append(int(dam_type))
        return False

    monkeypatch.setattr(spell_handlers, "saves_spell", _no_save)

    rng_mm.seed_mm(42)
    expected = rng_mm.dice(20, 4)

    rng_mm.seed_mm(42)
    dealt = dispel_good(caster, victim)

    assert dealt == expected
    assert victim.hit == 100 - expected
    assert observed == [int(DamageType.NEGATIVE)]


def test_dispel_spells_save_for_half(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20, is_npc=True)
    victim_evil = make_character(level=20, hit=200, max_hit=200, alignment=-1000)
    victim_good = make_character(level=20, hit=200, max_hit=200, alignment=1000)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    rng_mm.seed_mm(42)
    expected_evil = c_div(rng_mm.dice(20, 4), 2)

    rng_mm.seed_mm(42)
    dealt_evil = dispel_evil(caster, victim_evil)

    assert dealt_evil == expected_evil

    rng_mm.seed_mm(42)
    expected_good = c_div(rng_mm.dice(20, 4), 2)

    rng_mm.seed_mm(42)
    dealt_good = dispel_good(caster, victim_good)

    assert dealt_good == expected_good


# ==============================================================================
# EARTHQUAKE
# ==============================================================================


def test_earthquake_requires_caster_and_room():
    with pytest.raises(ValueError):
        earthquake(None)

    caster = make_character(level=30)
    assert earthquake(caster) is False


def test_earthquake_hits_room_occupants_and_respects_flying_immunity(monkeypatch):
    rng_mm.seed_mm(42)

    room = Room(vnum=2000, name="QuakeRoom")
    caster = make_character(level=30)
    grounded = make_character(name="Grounded", hit=200, max_hit=200)
    flying = make_character(name="Flying", hit=200, max_hit=200)

    room.add_character(caster)
    room.add_character(grounded)
    room.add_character(flying)
    flying.add_affect(AffectFlag.FLYING)

    snapshot = list(character_registry)
    character_registry.clear()
    character_registry.extend([caster, grounded, flying])

    try:
        calls: list[tuple[int, int | None, str | int | None]] = []
        _patch_apply_damage(monkeypatch, record=calls)

        rng_mm.seed_mm(42)
        expected_ground = 30 + rng_mm.dice(2, 8)

        rng_mm.seed_mm(42)
        result = earthquake(caster)

        assert result is True
        assert grounded.hit == 200 - expected_ground
        assert flying.hit == 200  # immune (0 damage)
        assert caster.hit == 120  # not damaged

        assert any(call[1] == int(DamageType.BASH) for call in calls)
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)


# ==============================================================================
# ENERGY_DRAIN
# ==============================================================================


def test_energy_drain_save_negates(monkeypatch):
    caster = make_character(level=30, hit=100, max_hit=100)
    victim = make_character(level=30, hit=100, max_hit=100, mana=100, move=100)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    dealt = energy_drain(caster, victim)

    assert dealt == 0
    assert victim.hit == 100
    assert victim.mana == 100
    assert victim.move == 100


def test_energy_drain_effects_xp_mana_move_and_damage(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20, hit=50, max_hit=50, alignment=0)
    victim = make_character(level=20, hit=120, max_hit=120, mana=100, move=100)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    xp_log: dict[str, int] = {}

    def _fake_gain_exp(ch, amount):  # noqa: ARG001
        xp_log["amount"] = int(amount)

    monkeypatch.setattr(spell_handlers, "gain_exp", _fake_gain_exp)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected_xp = rng_mm.number_range(c_div(20, 2), c_div(3 * 20, 2))
    expected_damage = rng_mm.dice(1, 20)

    rng_mm.seed_mm(42)
    dealt = energy_drain(caster, victim)

    assert xp_log["amount"] == -expected_xp
    assert victim.mana == 50
    assert victim.move == 50
    assert caster.hit == 50 + expected_damage

    assert dealt == expected_damage
    assert calls == [(expected_damage, int(DamageType.NEGATIVE), "energy drain")]


def test_energy_drain_low_level_victim_is_killed(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=20, hit=77, max_hit=77)
    victim = make_character(level=2, hit=50, max_hit=50)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    expected_damage = 77 + 1

    dealt = energy_drain(caster, victim)

    assert dealt == expected_damage
    assert calls == [(expected_damage, int(DamageType.NEGATIVE), "energy drain")]


# ==============================================================================
# FLAMESTRIKE
# ==============================================================================


def test_flamestrike_damage_formula_and_type(monkeypatch):
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    victim = make_character(hit=200, max_hit=200)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: False)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    dice_count = 6 + c_div(30, 2)
    expected = rng_mm.dice(dice_count, 8)

    rng_mm.seed_mm(42)
    dealt = flamestrike(caster, victim)

    assert dealt == expected
    assert calls == [(expected, int(DamageType.FIRE), "flamestrike")]


def test_flamestrike_save_for_half_and_level_zero(monkeypatch):
    caster0 = make_character(level=0)
    victim = make_character(hit=200, max_hit=200)

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, target, dam_type: True)

    calls: list[tuple[int, int | None, str | int | None]] = []
    _patch_apply_damage(monkeypatch, record=calls)

    rng_mm.seed_mm(42)
    expected = c_div(rng_mm.dice(6, 8), 2)

    rng_mm.seed_mm(42)
    dealt = flamestrike(caster0, victim)

    assert dealt == expected
    assert calls[0][1] == int(DamageType.FIRE)


def test_flamestrike_validation_requires_target():
    caster = make_character(level=30)
    with pytest.raises(ValueError):
        flamestrike(caster, None)
