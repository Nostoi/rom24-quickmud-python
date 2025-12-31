"""ROM parity tests for charm/control spells.

Spells covered:
- change_sex (magic.c:1922)
- charm_person (magic.c:1967)
- sleep (magic.c:7032)

These tests focus on save mechanics, affect application, and key ROM gating rules.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, ImmFlag, Position, RoomFlag, Sex
from mud.models.room import Room
from mud.skills.handlers import change_sex, charm_person, sleep
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""

    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "sex": overrides.get("sex", int(Sex.MALE)),
        "saving_throw": overrides.get("saving_throw", 0),
        "act": overrides.get("act", 0),
        "imm_flags": overrides.get("imm_flags", 0),
    }
    ch = Character(**base)
    for key, value in overrides.items():
        setattr(ch, key, value)
    return ch


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
        "room_flags": overrides.get("room_flags", 0),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


# =============================================================================
# change_sex
# =============================================================================


def test_change_sex_save_prevents_change():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=1)
    target = make_character(name="target", level=60, sex=int(Sex.FEMALE))

    old_sex = target.sex
    result = change_sex(caster, target)

    assert result is False
    assert target.sex == old_sex
    assert not target.has_spell_effect("change sex")


def test_change_sex_applies_effect_and_changes_sex_deterministically():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1, sex=int(Sex.MALE))

    old_sex = target.sex
    result = change_sex(caster, target)

    assert result is True
    assert target.has_spell_effect("change sex")

    effect = target.spell_effects.get("change sex")
    assert effect is not None
    assert effect.level == 40
    assert effect.duration == 80

    assert target.sex != old_sex
    assert target.sex in (int(Sex.NONE), int(Sex.MALE), int(Sex.FEMALE))
    assert effect.sex_delta == target.sex - old_sex

    # With seed 42, the first successful cast changes MALE -> NONE.
    assert target.sex == int(Sex.NONE)


def test_change_sex_duplicate_gating():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1, sex=int(Sex.MALE))

    assert change_sex(caster, target) is True

    # Second cast should short-circuit (already affected).
    sex_after_first = target.sex
    assert change_sex(caster, target) is False
    assert target.sex == sex_after_first


def test_change_sex_effect_reverses_on_remove():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1, sex=int(Sex.MALE))

    assert change_sex(caster, target) is True
    changed_sex = target.sex
    assert changed_sex != int(Sex.MALE)

    removed = target.remove_spell_effect("change sex")
    assert removed is not None
    assert target.sex == int(Sex.MALE)


# =============================================================================
# charm_person
# =============================================================================


def test_charm_person_save_prevents_charm():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=30)
    target = make_character(name="target", level=30, saving_throw=-100)

    result = charm_person(caster, target)

    assert result is False
    assert not target.has_affect(AffectFlag.CHARM)
    assert not target.has_spell_effect("charm person")
    assert target.master is None


def test_charm_person_applies_affect_and_following():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1)

    result = charm_person(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.CHARM)
    assert target.has_spell_effect("charm person")
    assert target.master is caster
    assert target.leader is caster

    effect = target.spell_effects.get("charm person")
    assert effect is not None
    assert effect.duration == 10  # level/4 with fuzzy roll unchanged at seed 42


def test_charm_person_cannot_charm_already_charmed_target():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1)

    assert charm_person(caster, target) is True

    # Second charm must fail without changing follow state.
    assert charm_person(caster, target) is False
    assert target.master is caster
    assert target.has_affect(AffectFlag.CHARM)


def test_charm_person_level_limit_blocks_charm():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=10)
    target = make_character(name="target", level=11)

    result = charm_person(caster, target)

    assert result is False
    assert target.master is None
    assert not target.has_affect(AffectFlag.CHARM)


def test_charm_person_caster_charmed_cannot_charm():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    caster.add_affect(AffectFlag.CHARM)
    target = make_character(name="target", level=1)

    assert charm_person(caster, target) is False
    assert target.master is None
    assert not target.has_affect(AffectFlag.CHARM)


def test_charm_person_room_law_blocks_charm_with_message():
    rng_mm.seed_mm(42)

    room = make_room(room_flags=int(RoomFlag.ROOM_LAW))
    caster = make_character(name="caster", level=40, room=room)
    target = make_character(name="target", level=1, room=room)

    result = charm_person(caster, target)

    assert result is False
    assert any("mayor" in msg.lower() for msg in caster.messages)
    assert not target.has_affect(AffectFlag.CHARM)
    assert target.master is None


def test_charm_person_target_charm_immune_blocks_charm():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="target", level=1, imm_flags=int(ImmFlag.CHARM))

    assert charm_person(caster, target) is False
    assert not target.has_affect(AffectFlag.CHARM)
    assert target.master is None


# =============================================================================
# sleep
# =============================================================================


def test_sleep_save_prevents_affect():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=30)
    target = make_character(name="target", level=10, saving_throw=-100)

    result = sleep(caster, target)

    assert result is False
    assert not target.has_affect(AffectFlag.SLEEP)
    assert not target.has_spell_effect("sleep")


def test_sleep_applies_affect_and_sets_position():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=20)
    target = make_character(name="target", level=1, position=Position.STANDING)

    result = sleep(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.SLEEP)
    assert target.has_spell_effect("sleep")
    assert target.position == Position.SLEEPING

    effect = target.spell_effects.get("sleep")
    assert effect is not None
    assert effect.duration == 24  # 4 + level


def test_sleep_duplicate_gating_if_already_affected():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=20)
    target = make_character(name="target", level=1)

    assert sleep(caster, target) is True

    # Second cast should short-circuit.
    assert sleep(caster, target) is False


def test_sleep_level_limit_blocks_sleep():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=10)
    target = make_character(name="target", level=20)

    assert sleep(caster, target) is False
    assert not target.has_affect(AffectFlag.SLEEP)


def test_sleep_undead_npc_is_immune():
    rng_mm.seed_mm(42)

    caster = make_character(name="caster", level=40)
    target = make_character(name="undead", level=1, is_npc=True, act=int(ActFlag.UNDEAD))

    assert sleep(caster, target) is False
    assert not target.has_affect(AffectFlag.SLEEP)
    assert not target.has_spell_effect("sleep")
