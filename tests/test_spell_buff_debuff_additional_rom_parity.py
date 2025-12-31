"""ROM parity tests for additional buff/debuff spells.

Tests for:
- blindness
- calm
- curse
- shield
- fly
- pass_door
- protection_evil
- protection_good
- infravision

These cover remaining core buff/debuff spells with ROM-matching formulas.
All tests use deterministic RNG seeding and check AffectFlag + modifiers + durations.
"""

from __future__ import annotations

from mud.combat.engine import set_fighting
from mud.math.c_compat import c_div
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import (
    blindness,
    calm,
    curse,
    fly,
    infravision,
    pass_door,
    protection_evil,
    protection_good,
    shield,
)
from mud.utils import rng_mm
from mud.models.character import Character


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""
    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def _cast_until_applied(
    *,
    spell_fn,
    caster,
    target,
    effect_name: str,
    max_attempts: int = 25,
) -> bool:
    """Retry a spell that has a save check.

    Used to avoid brittle tests when deterministic RNG + saves can block application.
    """

    for _ in range(max_attempts):
        if spell_fn(caster, target):
            if getattr(target, "has_spell_effect", None) and target.has_spell_effect(effect_name):
                return True
            # Some spells gate on affect flags only; if it returned True, accept.
            return True
    return False


# ============================================================================
# BLINDNESS TESTS (ROM src/magic.c:1372)
# ============================================================================


def test_blindness_applies_affect_flag_blind():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=60)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=blindness, caster=caster, target=target, effect_name="blindness")

    assert applied is True
    assert target.has_affect(AffectFlag.BLIND)
    assert target.has_spell_effect("blindness")


def test_blindness_hitroll_modifier_is_minus_4():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=60)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=blindness, caster=caster, target=target, effect_name="blindness")
    assert applied is True

    effect = target.spell_effects.get("blindness")
    assert effect is not None
    assert effect.hitroll_mod == -4


def test_blindness_duration_formula_is_1_plus_level():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=37)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=blindness, caster=caster, target=target, effect_name="blindness")
    assert applied is True

    effect = target.spell_effects.get("blindness")
    assert effect is not None
    assert effect.duration == 1 + 37


def test_blindness_duplicate_gating_by_affect_or_spell_effect():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=60)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=blindness, caster=caster, target=target, effect_name="blindness")
    assert applied is True

    # Second cast should be blocked by existing affect/effect
    rng_mm.seed_mm(42)
    assert blindness(caster, target) is False


# ============================================================================
# CALM TESTS (ROM src/magic.c:1525)
# ============================================================================


def test_calm_stops_fighting_for_all_room_occupants():
    rng_mm.seed_mm(42)

    room = make_room()

    caster = make_character(name="Cleric", level=50, room=room)
    fighter1 = make_character(name="F1", level=10, room=room)
    fighter2 = make_character(name="F2", level=10, room=room)

    room.people = [caster, fighter1, fighter2]

    set_fighting(fighter1, fighter2)
    set_fighting(fighter2, fighter1)

    assert fighter1.position == Position.FIGHTING
    assert fighter2.position == Position.FIGHTING

    assert calm(caster) is True

    assert fighter1.fighting is None
    assert fighter2.fighting is None
    assert fighter1.position != Position.FIGHTING
    assert fighter2.position != Position.FIGHTING


def test_calm_applies_room_wide_affect_flag_and_penalties():
    rng_mm.seed_mm(42)

    room = make_room()
    caster = make_character(name="Cleric", level=40, room=room)
    npc = make_character(name="npc", level=15, room=room, is_npc=True)
    pc = make_character(name="pc", level=15, room=room, is_npc=False)

    room.people = [caster, npc, pc]

    # Force at least one fighting occupant to avoid early mlevel==0 behavior assumptions.
    set_fighting(npc, pc)

    applied = _cast_until_applied(spell_fn=calm, caster=caster, target=None, effect_name="calm")
    assert applied is True

    assert npc.has_affect(AffectFlag.CALM)
    assert pc.has_affect(AffectFlag.CALM)

    npc_effect = npc.spell_effects.get("calm")
    pc_effect = pc.spell_effects.get("calm")
    assert npc_effect is not None
    assert pc_effect is not None

    # ROM port applies -2 for NPC, -5 for PC (see handler implementation).
    assert npc_effect.hitroll_mod == -2
    assert npc_effect.damroll_mod == -2
    assert pc_effect.hitroll_mod == -5
    assert pc_effect.damroll_mod == -5


def test_calm_duration_formula_is_level_div_4_floor():
    rng_mm.seed_mm(42)

    room = make_room()
    caster = make_character(name="Cleric", level=39, room=room)
    npc = make_character(name="npc", level=10, room=room, is_npc=True)
    room.people = [caster, npc]

    set_fighting(npc, caster)

    assert calm(caster) is True

    effect = npc.spell_effects.get("calm")
    assert effect is not None
    assert effect.duration == c_div(39, 4)


def test_calm_duplicate_gating_blocks_if_already_calm():
    rng_mm.seed_mm(42)

    room = make_room()
    caster = make_character(name="Cleric", level=50, room=room)
    npc = make_character(name="npc", level=10, room=room)
    room.people = [caster, npc]

    set_fighting(npc, caster)

    assert calm(caster) is True

    # Second attempt should fail because occupant has CALM already.
    rng_mm.seed_mm(42)
    assert calm(caster) is False


# ============================================================================
# CURSE TESTS (ROM src/magic.c:2585)
# ============================================================================


def test_curse_applies_affect_flag_curse():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=60)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=curse, caster=caster, target=target, effect_name="curse")
    assert applied is True

    assert target.has_affect(AffectFlag.CURSE)
    assert target.has_spell_effect("curse")


def test_curse_hitroll_modifier_formula_is_negative_level_div_8():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=25)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=curse, caster=caster, target=target, effect_name="curse")
    assert applied is True

    effect = target.spell_effects.get("curse")
    assert effect is not None

    expected = -c_div(25, 8)
    assert effect.hitroll_mod == expected


def test_curse_saving_throw_modifier_formula_is_positive_level_div_8():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=25)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=curse, caster=caster, target=target, effect_name="curse")
    assert applied is True

    effect = target.spell_effects.get("curse")
    assert effect is not None

    expected = c_div(25, 8)
    assert effect.saving_throw_mod == expected


def test_curse_duration_formula_is_2_times_level():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=33)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=curse, caster=caster, target=target, effect_name="curse")
    assert applied is True

    effect = target.spell_effects.get("curse")
    assert effect is not None
    assert effect.duration == 2 * 33


def test_curse_duplicate_gating():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=60)
    target = make_character(name="Target", level=1)

    applied = _cast_until_applied(spell_fn=curse, caster=caster, target=target, effect_name="curse")
    assert applied is True

    rng_mm.seed_mm(42)
    assert curse(caster, target) is False


# ============================================================================
# SHIELD TESTS (ROM src/magic.c:6902)
# ============================================================================


def test_shield_applies_ac_modifier_minus_20():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert shield(caster, target) is True
    assert target.has_spell_effect("shield")

    effect = target.spell_effects.get("shield")
    assert effect is not None
    assert effect.ac_mod == -20


def test_shield_duration_formula_is_8_plus_level():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=44)
    target = make_character(name="Target", level=15)

    assert shield(caster, target) is True

    effect = target.spell_effects.get("shield")
    assert effect is not None
    assert effect.duration == 8 + 44


def test_shield_duplicate_gating():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert shield(caster, target) is True

    rng_mm.seed_mm(42)
    assert shield(caster, target) is False


# ============================================================================
# FLY TESTS (ROM src/magic.c:4179)
# ============================================================================


def test_fly_applies_affect_flag_flying():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert fly(caster, target) is True
    assert target.has_affect(AffectFlag.FLYING)
    assert target.has_spell_effect("fly")


def test_fly_duration_formula_is_level_plus_3():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=21)
    target = make_character(name="Target", level=15)

    assert fly(caster, target) is True

    effect = target.spell_effects.get("fly")
    assert effect is not None
    assert effect.duration == 21 + 3


def test_fly_duplicate_gating_blocks_recast():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert fly(caster, target) is True

    rng_mm.seed_mm(42)
    assert fly(caster, target) is False


# ============================================================================
# PASS_DOOR TESTS (ROM src/magic.c:5850)
# ============================================================================


def test_pass_door_applies_affect_flag_pass_door():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=40)
    target = make_character(name="Target", level=15)

    assert pass_door(caster, target) is True
    assert target.has_affect(AffectFlag.PASS_DOOR)
    assert target.has_spell_effect("pass door")


def test_pass_door_duration_uses_number_fuzzy_on_level_div_4():
    # With seed 42, base_duration=10 and number_fuzzy(10) returns 10.
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=40)
    target = make_character(name="Target", level=15)

    assert pass_door(caster, target) is True

    effect = target.spell_effects.get("pass door")
    assert effect is not None
    assert effect.duration == 10


def test_pass_door_duplicate_gating():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=40)
    target = make_character(name="Target", level=15)

    assert pass_door(caster, target) is True

    rng_mm.seed_mm(42)
    assert pass_door(caster, target) is False


# ============================================================================
# PROTECTION EVIL/GOOD TESTS (ROM src/magic.c:6378, 6420)
# ============================================================================


def test_protection_evil_applies_affect_flag_and_save_bonus():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=30)
    target = make_character(name="Target", level=15)

    assert protection_evil(caster, target) is True
    assert target.has_affect(AffectFlag.PROTECT_EVIL)
    assert target.has_spell_effect("protection evil")

    effect = target.spell_effects.get("protection evil")
    assert effect is not None
    assert effect.saving_throw_mod == -1
    assert effect.duration == 24


def test_protection_good_applies_affect_flag_and_save_bonus():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=30)
    target = make_character(name="Target", level=15)

    assert protection_good(caster, target) is True
    assert target.has_affect(AffectFlag.PROTECT_GOOD)
    assert target.has_spell_effect("protection good")

    effect = target.spell_effects.get("protection good")
    assert effect is not None
    assert effect.saving_throw_mod == -1
    assert effect.duration == 24


def test_protection_mutual_exclusion_evil_blocks_if_good_present():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=30)
    target = make_character(name="Target", level=15)

    assert protection_good(caster, target) is True

    rng_mm.seed_mm(42)
    assert protection_evil(caster, target) is False


def test_protection_mutual_exclusion_good_blocks_if_evil_present():
    rng_mm.seed_mm(42)

    caster = make_character(name="Cleric", level=30)
    target = make_character(name="Target", level=15)

    assert protection_evil(caster, target) is True

    rng_mm.seed_mm(42)
    assert protection_good(caster, target) is False


# ============================================================================
# INFRAVISION TESTS (ROM src/magic.c:5211)
# ============================================================================


def test_infravision_applies_affect_flag_infrared():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert infravision(caster, target) is True
    assert target.has_affect(AffectFlag.INFRARED)
    assert target.has_spell_effect("infravision")


def test_infravision_duration_formula_is_2_times_level():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=18)
    target = make_character(name="Target", level=15)

    assert infravision(caster, target) is True

    effect = target.spell_effects.get("infravision")
    assert effect is not None
    assert effect.duration == 2 * 18


def test_infravision_duplicate_gating_blocks_recast():
    rng_mm.seed_mm(42)

    caster = make_character(name="Mage", level=30)
    target = make_character(name="Target", level=15)

    assert infravision(caster, target) is True

    rng_mm.seed_mm(42)
    assert infravision(caster, target) is False
