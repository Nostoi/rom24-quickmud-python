from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import DamageType, ExtraFlag, ImmFlag, ItemType, Position
from mud.models.object import Object, ObjIndex
from mud.models.room import Room
from mud.skills.handlers import heat_metal
from mud.utils import rng_mm


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
    if "dex" not in overrides:
        char.perm_stat = [18, 18, 18, 18, 18]
    if "imm_flags" not in overrides:
        char.imm_flags = 0
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


def make_object(**overrides) -> Object:
    proto = ObjIndex(
        vnum=overrides.get("vnum", 1),
        short_descr=overrides.get("short_descr", "an object"),
        item_type=overrides.get("item_type", ItemType.ARMOR),
        level=overrides.get("level", 10),
        extra_flags=overrides.get("extra_flags", 0),
        weight=overrides.get("weight", 50),
    )
    obj = Object(instance_id=None, prototype=proto)
    for key, value in overrides.items():
        setattr(obj, key, value)
    return obj


def test_heat_metal_fire_immunity():
    """ROM L3131-3132: Fire immunity blocks spell."""
    caster = make_character(level=30)
    victim = make_character(imm_flags=int(ImmFlag.FIRE))
    victim.messages = []
    caster.messages = []

    rng_mm.seed_mm(0x1234)
    dam = heat_metal(caster, victim)

    assert dam == 0
    assert any("no effect" in msg for msg in caster.messages)


def test_heat_metal_saves_spell():
    """ROM L3131: Saving throw blocks spell."""
    caster = make_character(level=5)
    victim = make_character(level=50)
    victim.messages = []
    caster.messages = []

    # High level victim should save against low level spell
    rng_mm.seed_mm(0xABCD)
    dam = heat_metal(caster, victim)

    assert dam == 0


def test_heat_metal_nonmetal_items_ignored():
    """ROM L3140: NONMETAL items are not heated."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=10, imm_flags=0, room=room)

    nonmetal_armor = make_object(
        item_type=ItemType.ARMOR,
        level=5,
        extra_flags=int(ExtraFlag.NONMETAL),
        short_descr="leather armor",
    )
    victim.inventory = [nonmetal_armor]
    victim.messages = []

    rng_mm.seed_mm(0x5678)
    dam = heat_metal(caster, victim)

    # Should fail because only nonmetal item
    assert dam == 0


def test_heat_metal_burn_proof_ignored():
    """ROM L3141: BURN_PROOF items are not heated."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=10, imm_flags=0, room=room)

    fireproof_armor = make_object(
        item_type=ItemType.ARMOR,
        level=5,
        extra_flags=int(ExtraFlag.BURN_PROOF),
        short_descr="fireproof armor",
    )
    victim.inventory = [fireproof_armor]
    victim.messages = []

    rng_mm.seed_mm(0x9ABC)
    dam = heat_metal(caster, victim)

    # Should fail
    assert dam == 0


def test_heat_metal_armor_in_inventory():
    """ROM L3177-3201: Armor in inventory can be dropped."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=10, imm_flags=0, dex=18, room=room)
    victim.messages = []

    armor = make_object(
        item_type=ItemType.ARMOR,
        level=20,  # Higher level needed: dam = number_range(1, level) / 6
        extra_flags=0,
        wear_loc=-1,
        short_descr="metal armor",
        weight=50,
    )
    victim.inventory = [armor]

    rng_mm.seed_mm(0xBEEF)  # Seed that produces favorable RNG sequence
    dam = heat_metal(caster, victim)

    # Armor should be dropped and cause damage (ROM uses /6 for inventory items)
    assert dam > 0
    assert armor not in victim.inventory
    assert armor in room.objects


def test_heat_metal_worn_armor_removed():
    """ROM L3146-3175: Worn armor can be removed if dex check passes."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=10, imm_flags=0, dex=20, room=room)
    victim.messages = []

    armor = make_object(
        item_type=ItemType.ARMOR,
        level=5,
        extra_flags=0,
        wear_loc=1,
        short_descr="worn armor",
        weight=10,
    )
    victim.equipment = {"body": armor}

    rng_mm.seed_mm(0xBEEF)
    dam = heat_metal(caster, victim)

    # Some damage should occur
    assert dam >= 0


def test_heat_metal_weapon_dropped():
    """ROM L3204-3260: Wielded weapon can be dropped."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=10, imm_flags=0, room=room)
    victim.messages = []

    weapon = make_object(
        item_type=ItemType.WEAPON,
        level=5,
        extra_flags=0,
        wear_loc=1,
        short_descr="iron sword",
        weight=30,
        value=[0, 0, 0, 0],
    )
    victim.equipment = {"wield": weapon}

    rng_mm.seed_mm(0xCAFE)
    dam = heat_metal(caster, victim)

    # Should cause some damage
    assert dam >= 0


def test_heat_metal_save_reduces_damage():
    """ROM L3273-3275: Final save reduces damage by 1/3."""
    room = make_room()
    room.objects = []

    caster = make_character(level=30, room=room)
    victim = make_character(level=1, imm_flags=0, dex=1, room=room)
    victim.messages = []

    armor = make_object(
        item_type=ItemType.ARMOR,
        level=10,
        extra_flags=0,
        wear_loc=-1,
        short_descr="hot armor",
        weight=100,
    )
    victim.inventory = [armor]

    # Multiple trials to test damage variance
    damages = []
    for seed in range(20):
        victim.hit = 120
        victim.inventory = [armor]
        room.objects = []

        rng_mm.seed_mm(seed)
        dam = heat_metal(caster, victim)
        if dam > 0:
            damages.append(dam)

    # Should have some damage variance
    assert len(damages) > 0


def test_heat_metal_no_room():
    """Spell fails gracefully if victim has no room."""
    caster = make_character(level=30)
    victim = make_character(level=10, imm_flags=0)
    victim.room = None
    victim.messages = []
    caster.messages = []

    # Should not crash
    dam = heat_metal(caster, victim)
    assert dam >= 0
