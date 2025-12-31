from __future__ import annotations

import pytest
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import AffectFlag, ExtraFlag, ItemType, Position, WearLocation, WeaponType
from mud.models.object import Object
from mud.models.obj import Affect, ObjIndex
from mud.skills.handlers import identify, know_alignment, locate_object, dispel_magic
from mud.utils import rng_mm
from mud.registry import room_registry

def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "alignment": overrides.get("alignment", 0),
    }
    char = Character(**base)
    char.messages = []
    for key, value in overrides.items():
        setattr(char, key, value)
    return char

def make_object(**overrides) -> Object:
    proto_base = {
        "vnum": overrides.get("vnum", 1),
        "name": overrides.get("name", "object"),
        "short_descr": overrides.get("short_descr", "a test object"),
        "level": overrides.get("level", 1),
        "weight": overrides.get("weight", 10),
        "cost": overrides.get("cost", 100),
        "item_type": overrides.get("item_type", ItemType.TRASH),
        "extra_flags": overrides.get("extra_flags", 0),
        "value": overrides.get("value", [0, 0, 0, 0, 0]),
    }
    proto = ObjIndex(**proto_base)
    
    obj_base = {
        "instance_id": overrides.get("instance_id", 1),
        "prototype": proto,
        "level": proto.level,
        "value": list(proto.value),
        "cost": proto.cost,
        "extra_flags": int(proto.extra_flags) if isinstance(proto.extra_flags, int) else 0,
    }
    obj = Object(**obj_base)
    return obj

def test_identify_basic():
    caster = make_character(name="Caster", level=50)
    # WeaponType.SWORD is 1
    obj = make_object(name="sword", short_descr="a sharp sword", item_type=ItemType.WEAPON, value=[1, 4, 5, 0, 0])
    
    identify(caster, obj)
    
    msgs = "".join(caster.messages)
    assert "Object 'sword' is type weapon" in msgs
    assert "Weight is 1, value is 100, level is 1" in msgs
    assert "Weapon type is sword" in msgs
    assert "Damage is 4 to 5" in msgs

def test_identify_container():
    caster = make_character(name="Caster", level=50)
    # value[0] = capacity, value[1] = flags, value[3] = max_weight, value[4] = weight_mult
    obj = make_object(name="bag", short_descr="a small bag", item_type=ItemType.CONTAINER, value=[50, 1, 0, 10, 100])
    
    identify(caster, obj)
    
    msgs = "".join(caster.messages)
    assert "Capacity: 50#  Maximum weight: 10#  flags: closable" in msgs

def test_know_alignment_pure_good():
    caster = make_character(name="Caster")
    target = make_character(name="Saint", alignment=1000)
    
    know_alignment(caster, target)
    
    assert "Saint has a pure and good aura." in caster.messages

def test_know_alignment_pure_evil():
    caster = make_character(name="Caster")
    target = make_character(name="Demon", alignment=-1000)
    
    know_alignment(caster, target)
    
    assert "Demon is the embodiment of pure evil!" in caster.messages

def test_locate_object_basic():
    caster = make_character(name="Caster", level=50, is_npc=False)
    obj = make_object(name="unique_item", short_descr="a unique item")
    
    # Mock world iteration
    import mud.skills.handlers
    original_iterate = mud.skills.handlers._iterate_world_objects
    mud.skills.handlers._iterate_world_objects = lambda: [(obj, None)]
    
    try:
        locate_object(caster, "unique_item")
        msgs = "".join(caster.messages)
        assert "One is in somewhere." in msgs
    finally:
        mud.skills.handlers._iterate_world_objects = original_iterate

def test_locate_object_nolocate():
    caster = make_character(name="Caster", level=50, is_npc=False)
    obj = make_object(name="hidden_item", extra_flags=int(ExtraFlag.NOLOCATE))
    
    import mud.skills.handlers
    original_iterate = mud.skills.handlers._iterate_world_objects
    mud.skills.handlers._iterate_world_objects = lambda: [(obj, None)]
    
    try:
        locate_object(caster, "hidden_item")
        msgs = "".join(caster.messages)
        assert "Nothing like that in heaven or earth." in msgs
    finally:
        mud.skills.handlers._iterate_world_objects = original_iterate

def test_dispel_magic_success():
    caster = make_character(name="Caster", level=50)
    target = make_character(name="Target", level=10)
    target.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10, wear_off_message="Your armor fades."))
    
    rng_mm.seed_mm(0) # Ensure success
    dispel_magic(caster, target)
    
    assert "armor" not in target.spell_effects
    assert "Your armor fades." in "".join(target.messages)

def test_dispel_magic_failure():
    caster = make_character(name="Caster", level=1)
    target = make_character(name="Target", level=50)
    target.apply_spell_effect(SpellEffect(name="sanctuary", duration=10, level=50))
    
    rng_mm.seed_mm(1000) # Ensure failure
    dispel_magic(caster, target)
    
    assert "sanctuary" in target.spell_effects
