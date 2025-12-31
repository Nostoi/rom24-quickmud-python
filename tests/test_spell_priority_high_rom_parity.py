"""ROM Parity Tests for High-Priority Spells.

Tests for critical gameplay spells that needed coverage:
- armor: Basic AC buff
- bless: Hitroll/save buff
- cure_light: Basic healing
- invis: Stealth utility
- plague: Disease debuff
- poison: Poison debuff

All tests follow ROM parity test style with deterministic RNG.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, DamageType, Position, Stat
from mud.skills.handlers import (
    armor,
    bless,
    cure_light,
    invis,
    plague,
    poison,
)
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
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


def test_armor_applies_ac_bonus():
    caster = make_character(level=20)
    target = make_character()

    result = armor(caster, target)

    assert result is True
    assert target.has_spell_effect("armor") is True
    effect = target.spell_effects["armor"]
    assert effect.ac_mod == -20
    assert effect.duration == 24
    assert effect.level == 20


def test_armor_rejects_if_already_affected():
    caster = make_character(level=20)
    target = make_character()

    armor(caster, target)
    result = armor(caster, target)

    assert result is False


def test_armor_self_target_defaults():
    caster = make_character(level=15)

    result = armor(caster, None)

    assert result is True
    assert caster.has_spell_effect("armor") is True
    effect = caster.spell_effects["armor"]
    assert effect.ac_mod == -20
    assert effect.duration == 24


def test_bless_applies_hitroll_and_save_bonus():
    caster = make_character(level=20)
    target = make_character()

    result = bless(caster, target)

    assert result is True
    assert target.has_spell_effect("bless") is True
    effect = target.spell_effects["bless"]
    # ROM formula: hitroll/save = level / 8, duration = 6 + level
    assert effect.hitroll_mod == 2  # 20 / 8 = 2 (C integer division)
    assert effect.saving_throw_mod == -2
    assert effect.duration == 26  # 6 + 20
    assert effect.level == 20


def test_bless_rejects_if_already_affected():
    caster = make_character(level=20)
    target = make_character()

    bless(caster, target)
    result = bless(caster, target)

    assert result is False


def test_bless_self_target_defaults():
    caster = make_character(level=15)

    result = bless(caster, None)

    assert result is True
    assert caster.has_spell_effect("bless") is True


def test_cure_light_healing_formula():
    rng_mm.seed_mm(42)

    caster = make_character(level=18)
    target = make_character(hit=50, max_hit=100)

    rng_mm.seed_mm(42)
    expected_heal = rng_mm.dice(1, 8) + 18 // 3

    rng_mm.seed_mm(42)
    result = cure_light(caster, target)

    assert result == expected_heal
    assert target.hit == min(50 + expected_heal, 100)


def test_cure_light_caps_at_max_hit():
    rng_mm.seed_mm(42)

    caster = make_character(level=30)
    target = make_character(hit=99, max_hit=100)

    cure_light(caster, target)

    assert target.hit == 100


def test_cure_light_self_target_defaults():
    rng_mm.seed_mm(42)

    caster = make_character(level=15, hit=50, max_hit=100)

    rng_mm.seed_mm(42)
    expected_heal = rng_mm.dice(1, 8) + 15 // 3

    rng_mm.seed_mm(42)
    result = cure_light(caster, None)

    assert result == expected_heal
    assert caster.hit == min(50 + expected_heal, 100)


def test_invis_applies_invisible_affect():
    caster = make_character(level=20)
    target = make_character()

    result = invis(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.INVISIBLE) is True
    effect = target.spell_effects["invis"]
    # ROM formula: duration = level + 12
    assert effect.duration == 32  # 20 + 12
    assert effect.level == 20


def test_invis_rejects_if_already_affected():
    caster = make_character(level=20)
    target = make_character()

    invis(caster, target)
    result = invis(caster, target)

    assert result is False


def test_invis_self_target_defaults():
    caster = make_character(level=15)

    result = invis(caster, None)

    assert result is True
    assert caster.has_affect(AffectFlag.INVISIBLE) is True


def test_plague_save_prevents_disease(monkeypatch):
    import mud.skills.handlers as spell_handlers

    caster = make_character(level=20)
    target = make_character()

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, victim, dam_type: True)

    result = plague(caster, target)

    assert result is False
    assert target.has_affect(AffectFlag.PLAGUE) is False


def test_plague_applies_str_penalty_and_affect():
    import mud.skills.handlers as spell_handlers
    from unittest.mock import patch

    def _no_save(level, victim, dam_type):
        return False

    caster = make_character(level=20)
    target = make_character()

    with patch.object(spell_handlers, "saves_spell", _no_save):
        result = plague(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.PLAGUE) is True
    effect = target.spell_effects["plague"]
    assert effect.stat_modifiers.get(Stat.STR, 0) == -5
    assert effect.duration == 20
    assert effect.level == 15


def test_plague_undead_immune():
    import mud.skills.handlers as spell_handlers
    from unittest.mock import patch

    caster = make_character(level=20)
    target = make_character()
    target.act = int(ActFlag.UNDEAD)

    def _no_save(level, victim, dam_type):
        return False

    with patch.object(spell_handlers, "saves_spell", _no_save):
        result = plague(caster, target)

    assert result is False


def test_poison_save_prevents_poison(monkeypatch):
    import mud.skills.handlers as spell_handlers

    caster = make_character(level=20)
    target = make_character()

    monkeypatch.setattr(spell_handlers, "saves_spell", lambda level, victim, dam_type: True)

    result = poison(caster, target)

    assert result is False
    assert target.has_affect(AffectFlag.POISON) is False


def test_poison_applies_poison_affect():
    import mud.skills.handlers as spell_handlers
    from unittest.mock import patch

    caster = make_character(level=20)
    target = make_character()

    def _no_save(level, victim, dam_type):
        return False

    with patch.object(spell_handlers, "saves_spell", _no_save):
        result = poison(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.POISON) is True
    effect = target.spell_effects["poison"]
    assert effect.stat_modifiers.get(Stat.STR, 0) == -2
    assert effect.duration == 20
    assert effect.level == 20


def test_poison_self_target_defaults():
    import mud.skills.handlers as spell_handlers
    from unittest.mock import patch

    caster = make_character(level=15)

    def _no_save(level, victim, dam_type):
        return False

    with patch.object(spell_handlers, "saves_spell", _no_save):
        result = poison(caster, caster)

    assert result is True
    assert caster.has_affect(AffectFlag.POISON) is True
