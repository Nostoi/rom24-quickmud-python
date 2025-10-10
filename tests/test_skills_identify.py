from mud.models.character import Character
from mud.models.constants import (
    AffectFlag,
    ContainerFlag,
    ExtraFlag,
    ItemType,
    WeaponFlag,
    WeaponType,
)
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object
from mud.skills import handlers as skill_handlers
from mud.skills.metadata import ROM_SKILL_NAMES_BY_INDEX


def _make_caster() -> Character:
    return Character(name="Appraiser", level=50, is_npc=False)


def test_identify_reports_scroll_spells() -> None:
    caster = _make_caster()
    scroll_proto = ObjIndex(
        vnum=1000,
        name="scroll of knowledge",
        short_descr="scroll of knowledge",
        item_type=int(ItemType.SCROLL),
        weight=20,
        cost=250,
    )
    scroll = Object(instance_id=None, prototype=scroll_proto, level=12)
    scroll.extra_flags = int(ExtraFlag.GLOW | ExtraFlag.MAGIC)
    scroll.value = [12, 1, 2, 3, 4]

    assert skill_handlers.identify(caster, scroll) is True
    assert caster.messages[0] == "Object 'scroll of knowledge' is type scroll, extra flags glow magic."
    assert caster.messages[1] == "Weight is 2, value is 250, level is 12."
    assert (
        caster.messages[2]
        == "Level 12 spells of: 'acid blast' 'armor' 'bless' 'blindness'."
    )


def test_identify_formats_weapon_stats_and_affects() -> None:
    caster = _make_caster()
    weapon_proto = ObjIndex(
        vnum=2000,
        name="flaming longsword",
        short_descr="flaming longsword",
        item_type=int(ItemType.WEAPON),
        weight=30,
        cost=1500,
        new_format=True,
    )
    weapon_proto.affected = [
        Affect(where=1, type=0, level=0, duration=-1, location=19, modifier=2, bitvector=int(ExtraFlag.MAGIC))
    ]
    weapon = Object(instance_id=1, prototype=weapon_proto, level=40)
    weapon.extra_flags = int(ExtraFlag.BLESS | ExtraFlag.MAGIC)
    weapon.value = [int(WeaponType.SWORD), 3, 5, 0, int(WeaponFlag.FLAMING | WeaponFlag.POISON)]
    weapon.affected.append(
        Affect(where=0, type=0, level=40, duration=6, location=18, modifier=3, bitvector=int(AffectFlag.HASTE))
    )

    assert skill_handlers.identify(caster, weapon) is True
    assert caster.messages[0] == "Object 'flaming longsword' is type weapon, extra flags magic bless."
    assert caster.messages[1] == "Weight is 3, value is 1500, level is 40."
    assert caster.messages[2] == "Weapon type is sword."
    assert caster.messages[3] == "Damage is 3d5 (average 9)."
    assert caster.messages[4] == "Weapons flags: flaming poison"
    assert caster.messages[5] == "Affects damage roll by 2."
    assert caster.messages[6] == "Adds magic object flag."
    assert caster.messages[7] == "Affects hit roll by 3, 6 hours."
    assert caster.messages[8] == "Adds haste affect."


def test_identify_describes_container_and_wand() -> None:
    caster = _make_caster()
    container_proto = ObjIndex(
        vnum=3000,
        name="merchant's chest",
        short_descr="merchant's chest",
        item_type=int(ItemType.CONTAINER),
        weight=40,
        cost=60,
    )
    container = Object(instance_id=None, prototype=container_proto, level=5)
    container.value = [50, int(ContainerFlag.CLOSEABLE | ContainerFlag.LOCKED), 0, 30, 75]

    assert skill_handlers.identify(caster, container) is True
    assert caster.messages == [
        "Object 'merchant's chest' is type container, extra flags none.",
        "Weight is 4, value is 60, level is 5.",
        "Capacity: 50#  Maximum weight: 30#  flags: closable locked",
        "Weight multiplier: 75%",
    ]

    caster.messages.clear()
    magic_index = ROM_SKILL_NAMES_BY_INDEX.index("magic missile")
    wand_proto = ObjIndex(
        vnum=3001,
        name="oak wand",
        short_descr="oak wand",
        item_type=int(ItemType.WAND),
        weight=30,
        cost=200,
    )
    wand = Object(instance_id=None, prototype=wand_proto, level=18)
    wand.value = [18, 0, 3, magic_index, 0]

    assert skill_handlers.identify(caster, wand) is True
    assert caster.messages[0] == "Object 'oak wand' is type wand, extra flags none."
    assert caster.messages[1] == "Weight is 3, value is 200, level is 18."
    assert caster.messages[2] == "Has 3 charges of level 18 'magic missile'."
