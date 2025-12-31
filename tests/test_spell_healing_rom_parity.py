from __future__ import annotations

from unittest.mock import patch

from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position
from mud.skills.handlers import (
    cure_blindness,
    cure_critical,
    cure_disease,
    cure_poison,
    cure_serious,
    refresh,
)
from mud.utils import rng_mm

ROM_MAGIC_C_CURE_BLINDNESS_REF = "src/magic.c:1598"
ROM_MAGIC_C_CURE_CRITICAL_REF = "src/magic.c:1624"
ROM_MAGIC_C_CURE_DISEASE_REF = "src/magic.c:1640"
ROM_MAGIC_C_CURE_POISON_REF = "src/magic.c:1684"
ROM_MAGIC_C_CURE_SERIOUS_REF = "src/magic.c:1708"
ROM_MAGIC_C_REFRESH_REF = "src/magic.c:4200"


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "position": overrides.get("position", Position.STANDING),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "is_npc": overrides.get("is_npc", True),
        "alignment": overrides.get("alignment", 0),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def _apply_spell_effect(
    target: Character,
    *,
    name: str,
    level: int,
    duration: int,
    flag: AffectFlag,
) -> None:
    effect = SpellEffect(name=name, duration=duration, level=level, affect_flag=flag)
    applied = target.apply_spell_effect(effect)
    assert applied is True


def _rom_cure_critical(level: int) -> int:
    return rng_mm.dice(3, 8) + level - 6


def _rom_cure_serious(level: int) -> int:
    return rng_mm.dice(2, 8) + c_div(level, 2)


def test_cure_critical_healing_formula_matches_rom():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(hit=10, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_critical(30)

    rng_mm.seed_mm(42)
    healed = cure_critical(caster, target)

    assert healed == expected
    assert target.hit == 10 + expected


def test_cure_critical_caps_at_max_hit():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(hit=195, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_critical(30)

    rng_mm.seed_mm(42)
    healed = cure_critical(caster, target)

    assert healed == expected
    assert target.hit == 200


def test_cure_critical_defaults_target_to_caster():
    rng_mm.seed_mm(42)
    caster = make_character(level=30, hit=10, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_critical(30)

    rng_mm.seed_mm(42)
    healed = cure_critical(caster)

    assert healed == expected
    assert caster.hit == 10 + expected


def test_cure_serious_healing_formula_matches_rom():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(hit=10, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_serious(30)

    rng_mm.seed_mm(42)
    healed = cure_serious(caster, target)

    assert healed == expected
    assert target.hit == 10 + expected


def test_cure_serious_uses_c_integer_division_for_level_bonus():
    caster = make_character(level=31)
    target = make_character(hit=10, max_hit=999)

    rng_mm.seed_mm(42)
    dice_part = rng_mm.dice(2, 8)

    rng_mm.seed_mm(42)
    healed = cure_serious(caster, target)

    assert healed == dice_part + c_div(31, 2)


def test_cure_serious_caps_at_max_hit():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(hit=195, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_serious(30)

    rng_mm.seed_mm(42)
    healed = cure_serious(caster, target)

    assert healed == expected
    assert target.hit == 200


def test_cure_serious_defaults_target_to_caster():
    rng_mm.seed_mm(42)
    caster = make_character(level=30, hit=10, max_hit=200)

    rng_mm.seed_mm(42)
    expected = _rom_cure_serious(30)

    rng_mm.seed_mm(42)
    healed = cure_serious(caster)

    assert healed == expected
    assert caster.hit == 10 + expected


def test_cure_blindness_self_target_returns_false_when_not_blind():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)

    assert caster.has_affect(AffectFlag.BLIND) is False
    assert caster.has_spell_effect("blindness") is False

    result = cure_blindness(caster)

    assert result is False


def test_cure_blindness_removes_blindness_effect_on_success():
    rng_mm.seed_mm(42)
    caster = make_character(level=50)
    target = make_character(level=10)

    _apply_spell_effect(target, name="blindness", level=10, duration=5, flag=AffectFlag.BLIND)

    with patch("mud.affects.saves.saves_dispel", return_value=False):
        result = cure_blindness(caster, target)

    assert result is True
    assert target.has_spell_effect("blindness") is False
    assert target.has_affect(AffectFlag.BLIND) is False


def test_cure_blindness_self_target_removes_blindness_effect_on_success():
    rng_mm.seed_mm(42)
    caster = make_character(level=50)

    _apply_spell_effect(caster, name="blindness", level=10, duration=5, flag=AffectFlag.BLIND)

    with patch("mud.affects.saves.saves_dispel", return_value=False):
        result = cure_blindness(caster)

    assert result is True
    assert caster.has_spell_effect("blindness") is False
    assert caster.has_affect(AffectFlag.BLIND) is False


def test_cure_blindness_failed_dispel_decrements_effect_level():
    rng_mm.seed_mm(42)
    caster = make_character(level=1)
    target = make_character(level=10)

    _apply_spell_effect(target, name="blindness", level=50, duration=5, flag=AffectFlag.BLIND)

    with patch("mud.affects.saves.saves_dispel", return_value=True):
        result = cure_blindness(caster, target)

    assert result is False
    assert target.has_spell_effect("blindness") is True
    assert target.has_affect(AffectFlag.BLIND) is True
    assert target.spell_effects["blindness"].level == 49


def test_cure_disease_self_target_returns_false_when_not_ill():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)

    assert caster.has_affect(AffectFlag.PLAGUE) is False
    assert caster.has_spell_effect("plague") is False

    result = cure_disease(caster)

    assert result is False


def test_cure_disease_removes_plague_effect_on_success():
    rng_mm.seed_mm(42)
    caster = make_character(level=50)
    target = make_character(level=10)

    _apply_spell_effect(target, name="plague", level=10, duration=5, flag=AffectFlag.PLAGUE)

    with patch("mud.affects.saves.saves_dispel", return_value=False):
        result = cure_disease(caster, target)

    assert result is True
    assert target.has_spell_effect("plague") is False
    assert target.has_affect(AffectFlag.PLAGUE) is False


def test_cure_disease_failed_dispel_decrements_effect_level():
    rng_mm.seed_mm(42)
    caster = make_character(level=1)
    target = make_character(level=10)

    _apply_spell_effect(target, name="plague", level=50, duration=5, flag=AffectFlag.PLAGUE)

    with patch("mud.affects.saves.saves_dispel", return_value=True):
        result = cure_disease(caster, target)

    assert result is False
    assert target.has_spell_effect("plague") is True
    assert target.has_affect(AffectFlag.PLAGUE) is True
    assert target.spell_effects["plague"].level == 49


def test_cure_poison_self_target_returns_false_when_not_poisoned():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)

    assert caster.has_affect(AffectFlag.POISON) is False
    assert caster.has_spell_effect("poison") is False

    result = cure_poison(caster)

    assert result is False


def test_cure_poison_removes_poison_effect_on_success():
    rng_mm.seed_mm(42)
    caster = make_character(level=50)
    target = make_character(level=10)

    _apply_spell_effect(target, name="poison", level=10, duration=5, flag=AffectFlag.POISON)

    with patch("mud.affects.saves.saves_dispel", return_value=False):
        result = cure_poison(caster, target)

    assert result is True
    assert target.has_spell_effect("poison") is False
    assert target.has_affect(AffectFlag.POISON) is False


def test_cure_poison_failed_dispel_decrements_effect_level():
    rng_mm.seed_mm(42)
    caster = make_character(level=1)
    target = make_character(level=10)

    _apply_spell_effect(target, name="poison", level=50, duration=5, flag=AffectFlag.POISON)

    with patch("mud.affects.saves.saves_dispel", return_value=True):
        result = cure_poison(caster, target)

    assert result is False
    assert target.has_spell_effect("poison") is True
    assert target.has_affect(AffectFlag.POISON) is True
    assert target.spell_effects["poison"].level == 49


def test_refresh_increases_move_by_level():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(move=10, max_move=200)

    result = refresh(caster, target)

    assert result is True
    assert target.move == 40


def test_refresh_caps_at_max_move():
    rng_mm.seed_mm(42)
    caster = make_character(level=30)
    target = make_character(move=195, max_move=200)

    result = refresh(caster, target)

    assert result is True
    assert target.move == 200


def test_refresh_defaults_target_to_caster():
    rng_mm.seed_mm(42)
    caster = make_character(level=30, move=10, max_move=200)

    result = refresh(caster)

    assert result is True
    assert caster.move == 40
