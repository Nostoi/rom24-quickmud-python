from __future__ import annotations

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import ExtraFlag, ItemType, Position, WearLocation
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object
from mud.skills.handlers import enchant_armor, enchant_weapon, fireproof
from mud.utils import rng_mm


_TO_OBJECT = 1
_APPLY_NONE = 0
_APPLY_AC = 17
_APPLY_HITROLL = 18
_APPLY_DAMROLL = 19


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
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


def make_object(**overrides) -> Object:
    proto = ObjIndex(
        vnum=overrides.get("vnum", 1),
        name=overrides.get("name", "object"),
        short_descr=overrides.get("short_descr", "an object"),
        item_type=overrides.get("item_type", ItemType.ARMOR),
        level=overrides.get("level", 10),
        extra_flags=overrides.get("extra_flags", 0),
        weight=overrides.get("weight", 10),
    )
    obj = Object(instance_id=None, prototype=proto)

    # Mirror prototype defaults for commonly accessed runtime fields.
    obj.level = proto.level
    obj.extra_flags = int(proto.extra_flags or 0)
    obj.wear_loc = overrides.get("wear_loc", int(WearLocation.NONE))

    if "affected" in overrides:
        obj.affected = overrides["affected"]

    for key, value in overrides.items():
        setattr(obj, key, value)
    return obj


def _advance_percent(count: int) -> None:
    for _ in range(count):
        rng_mm.number_percent()


def _affects_with_location(obj: Object, location: int) -> list[Affect]:
    return [a for a in (getattr(obj, "affected", []) or []) if getattr(a, "location", None) == location]


def _single_affect_modifier(obj: Object, location: int) -> int:
    affects = _affects_with_location(obj, location)
    assert len(affects) == 1
    return int(getattr(affects[0], "modifier", 0) or 0)


def test_enchant_armor_success_adds_magic_and_ac_affect():
    caster = make_character(level=30)
    armor = make_object(item_type=ItemType.ARMOR, level=10, short_descr="test armor")
    caster.add_object(armor)

    rng_mm.seed_mm(42)
    ok = enchant_armor(caster, armor)

    assert ok is True
    assert armor.enchanted is True
    assert armor.extra_flags & int(ExtraFlag.MAGIC)
    assert not (armor.extra_flags & int(ExtraFlag.GLOW))
    assert armor.level == 11

    assert _single_affect_modifier(armor, _APPLY_AC) == -1
    assert _affects_with_location(armor, _APPLY_AC)[0].level == 30


def test_enchant_armor_updates_existing_ac_affect_in_place():
    caster = make_character(level=30)
    armor = make_object(
        item_type=ItemType.ARMOR,
        level=10,
        short_descr="test armor",
        affected=[
            Affect(
                where=_TO_OBJECT,
                type=0,
                level=1,
                duration=-1,
                location=_APPLY_AC,
                modifier=-2,
                bitvector=0,
            )
        ],
    )
    caster.add_object(armor)

    rng_mm.seed_mm(42)
    ok = enchant_armor(caster, armor)

    assert ok is True
    assert len(_affects_with_location(armor, _APPLY_AC)) == 1
    assert _single_affect_modifier(armor, _APPLY_AC) == -3


def test_enchant_armor_level_based_strength_low_level_stays_normal():
    # RNG: with seed 42, the 13th number_percent() is 78.
    caster = make_character(level=10)
    armor = make_object(item_type=ItemType.ARMOR, level=10, short_descr="test armor")
    caster.add_object(armor)

    rng_mm.seed_mm(42)
    _advance_percent(12)
    ok = enchant_armor(caster, armor)

    assert ok is True
    assert _single_affect_modifier(armor, _APPLY_AC) == -1
    assert not (armor.extra_flags & int(ExtraFlag.GLOW))


def test_enchant_armor_level_based_strength_high_level_can_be_stronger():
    # Same roll as above (78), but the high-level threshold is lower, triggering the stronger branch.
    caster = make_character(level=90)
    armor = make_object(item_type=ItemType.ARMOR, level=10, short_descr="test armor")
    caster.add_object(armor)

    rng_mm.seed_mm(42)
    _advance_percent(12)
    ok = enchant_armor(caster, armor)

    assert ok is True
    assert _single_affect_modifier(armor, _APPLY_AC) == -2
    assert armor.extra_flags & int(ExtraFlag.GLOW)


def test_enchant_armor_miscast_wipes_affects_and_flags():
    # Push fail up to the maximum clamp (85) so result=23 falls under fail//3.
    caster = make_character(level=0)
    armor = make_object(
        item_type=ItemType.ARMOR,
        level=10,
        short_descr="test armor",
        extra_flags=int(ExtraFlag.MAGIC | ExtraFlag.GLOW),
        affected=[
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_HITROLL, modifier=1, bitvector=0),
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_DAMROLL, modifier=1, bitvector=0),
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_NONE, modifier=0, bitvector=0),
        ],
    )
    caster.add_object(armor)

    rng_mm.seed_mm(42)
    ok = enchant_armor(caster, armor)

    assert ok is False
    assert armor.enchanted is True
    assert armor.affected == []
    assert armor.extra_flags == 0


def test_enchant_weapon_success_adds_hit_and_dam_affects_and_magic():
    caster = make_character(level=30)
    weapon = make_object(item_type=ItemType.WEAPON, level=10, short_descr="test weapon")
    caster.add_object(weapon)

    rng_mm.seed_mm(42)
    ok = enchant_weapon(caster, weapon)

    assert ok is True
    assert weapon.enchanted is True
    assert weapon.extra_flags & int(ExtraFlag.MAGIC)
    assert not (weapon.extra_flags & int(ExtraFlag.GLOW))
    assert weapon.level == 11

    assert _single_affect_modifier(weapon, _APPLY_HITROLL) == 1
    assert _single_affect_modifier(weapon, _APPLY_DAMROLL) == 1


def test_enchant_weapon_updates_existing_hit_and_dam_affects_in_place():
    caster = make_character(level=30)
    weapon = make_object(
        item_type=ItemType.WEAPON,
        level=10,
        short_descr="test weapon",
        affected=[
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_HITROLL, modifier=2, bitvector=0),
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_DAMROLL, modifier=2, bitvector=0),
        ],
    )
    caster.add_object(weapon)

    rng_mm.seed_mm(42)
    ok = enchant_weapon(caster, weapon)

    assert ok is True
    assert len(_affects_with_location(weapon, _APPLY_HITROLL)) == 1
    assert len(_affects_with_location(weapon, _APPLY_DAMROLL)) == 1
    assert _single_affect_modifier(weapon, _APPLY_HITROLL) == 3
    assert _single_affect_modifier(weapon, _APPLY_DAMROLL) == 3


def test_enchant_weapon_level_based_strength_can_change_added_amount():
    # RNG: with seed 42, the 8th number_percent() is 95.
    caster_low = make_character(level=10)
    caster_high = make_character(level=90)

    weapon_low = make_object(item_type=ItemType.WEAPON, level=10, short_descr="test weapon")
    weapon_high = make_object(item_type=ItemType.WEAPON, level=10, short_descr="test weapon")
    caster_low.add_object(weapon_low)
    caster_high.add_object(weapon_high)

    rng_mm.seed_mm(42)
    _advance_percent(7)
    ok_low = enchant_weapon(caster_low, weapon_low)

    rng_mm.seed_mm(42)
    _advance_percent(7)
    ok_high = enchant_weapon(caster_high, weapon_high)

    assert ok_low is True
    assert ok_high is True
    assert _single_affect_modifier(weapon_low, _APPLY_HITROLL) == 1
    assert _single_affect_modifier(weapon_high, _APPLY_HITROLL) == 2
    assert weapon_high.extra_flags & int(ExtraFlag.GLOW)


def test_enchant_weapon_sets_hum_when_bonus_exceeds_four():
    caster = make_character(level=90)
    weapon = make_object(
        item_type=ItemType.WEAPON,
        level=10,
        short_descr="test weapon",
        affected=[
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_HITROLL, modifier=3, bitvector=0),
            Affect(where=_TO_OBJECT, type=0, level=1, duration=-1, location=_APPLY_DAMROLL, modifier=3, bitvector=0),
        ],
    )
    caster.add_object(weapon)

    rng_mm.seed_mm(42)
    _advance_percent(7)  # Use the 8th roll (95) to force the stronger +2 branch.
    ok = enchant_weapon(caster, weapon)

    assert ok is True
    assert _single_affect_modifier(weapon, _APPLY_HITROLL) == 5
    assert _single_affect_modifier(weapon, _APPLY_DAMROLL) == 5
    assert weapon.extra_flags & int(ExtraFlag.HUM)


def test_fireproof_applies_burn_proof_flag_and_affect():
    caster = make_character(level=30)
    obj = make_object(item_type=ItemType.ARMOR, level=10, short_descr="test object")

    rng_mm.seed_mm(42)
    ok = fireproof(caster, obj)

    assert ok is True
    assert obj.extra_flags & int(ExtraFlag.BURN_PROOF)

    burn_affects = [
        a for a in (obj.affected or []) if int(getattr(a, "bitvector", 0) or 0) == int(ExtraFlag.BURN_PROOF)
    ]
    assert len(burn_affects) == 1
    assert burn_affects[0].where == _TO_OBJECT
    assert burn_affects[0].location == _APPLY_NONE
    assert getattr(burn_affects[0], "spell_name", None) == "fireproof"


def test_fireproof_duration_matches_number_fuzzy():
    caster = make_character(level=40)
    obj = make_object(item_type=ItemType.ARMOR, level=10, short_descr="test object")

    rng_mm.seed_mm(42)
    expected = rng_mm.number_fuzzy(max(0, c_div(40, 4)))

    rng_mm.seed_mm(42)
    ok = fireproof(caster, obj)

    assert ok is True
    burn_affects = [a for a in (obj.affected or []) if getattr(a, "spell_name", None) == "fireproof"]
    assert len(burn_affects) == 1
    assert burn_affects[0].duration == expected


def test_fireproof_returns_false_if_already_protected():
    caster = make_character(level=30)
    obj = make_object(
        item_type=ItemType.ARMOR,
        level=10,
        short_descr="test object",
        extra_flags=int(ExtraFlag.BURN_PROOF),
        affected=[],
    )

    rng_mm.seed_mm(42)
    ok = fireproof(caster, obj)

    assert ok is False
    assert obj.extra_flags & int(ExtraFlag.BURN_PROOF)
    assert obj.affected == []
