"""ROM parity tests for information spells.

Spells tested (ROM 2.4b6 references):
- identify:       src/magic.c:5117
- know_alignment: src/magic.c:5363
- locate_object:  src/magic.c:5503
- dispel_magic:   src/magic.c:3198

These tests assert QuickMUD handlers match the ROM-style semantics implemented in
`mud/skills/handlers.py`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import AffectFlag, ContainerFlag, ExtraFlag, ItemType, LEVEL_IMMORTAL, Sex
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills.handlers import dispel_magic, identify, know_alignment, locate_object
from mud.skills.metadata import ROM_SKILL_NAMES_BY_INDEX
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "trust": overrides.get("trust", 0),
        "is_npc": overrides.get("is_npc", False),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "alignment": overrides.get("alignment", 0),
        "sex": overrides.get("sex", int(Sex.EITHER)),
        "affected_by": overrides.get("affected_by", 0),
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


@pytest.fixture(autouse=True)
def _seed_and_isolate_world() -> Iterator[None]:
    rng_mm.seed_mm(42)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    try:
        room_registry.clear()
        character_registry.clear()
        yield
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


# ==========================================================================
# identify (src/magic.c:5117)
# ==========================================================================


def test_identify_weapon_reveals_weapon_stats_and_affects() -> None:
    caster = make_character(name="Appraiser", level=50)

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
        # Prototype (non-enchanted) affects should be displayed.
        Affect(where=1, type=0, level=0, duration=-1, location=19, modifier=2, bitvector=int(ExtraFlag.MAGIC))
    ]

    weapon = Object(instance_id=1, prototype=weapon_proto, level=40)
    weapon.extra_flags = int(ExtraFlag.BLESS | ExtraFlag.MAGIC)
    weapon.value = [0, 3, 5, 0, 0]
    weapon.affected.append(
        Affect(where=0, type=0, level=40, duration=6, location=18, modifier=3, bitvector=int(AffectFlag.HASTE))
    )

    assert identify(caster, weapon) is True

    assert caster.messages[0] == "Object 'flaming longsword' is type weapon, extra flags magic bless."
    assert caster.messages[1] == "Weight is 3, value is 1500, level is 40."
    assert caster.messages[2] == "Weapon type is exotic."
    assert caster.messages[3] == "Damage is 3d5 (average 9)."

    assert "Affects damage roll by 2." in caster.messages
    assert "Adds magic object flag." in caster.messages
    assert "Affects hit roll by 3, 6 hours." in caster.messages
    assert "Adds haste affect." in caster.messages


def test_identify_armor_reports_armor_class_line() -> None:
    caster = make_character(name="Appraiser", level=50)

    armor_proto = ObjIndex(
        vnum=2001,
        name="studded leather",
        short_descr="studded leather",
        item_type=int(ItemType.ARMOR),
        weight=20,
        cost=800,
    )
    armor = Object(instance_id=1, prototype=armor_proto, level=12)
    armor.value = [5, 5, 5, 3, 0]

    assert identify(caster, armor) is True

    assert caster.messages[0] == "Object 'studded leather' is type armor, extra flags none."
    assert caster.messages[1] == "Weight is 2, value is 800, level is 12."
    assert caster.messages[2] == "Armor class is 5 pierce, 5 bash, 5 slash, and 3 vs. magic."


def test_identify_container_weight_multiplier_present_when_not_100() -> None:
    caster = make_character(name="Appraiser", level=50)

    container_proto = ObjIndex(
        vnum=3000,
        name="merchant's chest",
        short_descr="merchant's chest",
        item_type=int(ItemType.CONTAINER),
        weight=40,
        cost=60,
    )
    container = Object(instance_id=1, prototype=container_proto, level=5)
    container.value = [50, int(ContainerFlag.CLOSEABLE | ContainerFlag.LOCKED), 0, 30, 75]

    assert identify(caster, container) is True

    assert caster.messages[2] == "Capacity: 50#  Maximum weight: 30#  flags: closable locked"
    assert caster.messages[3] == "Weight multiplier: 75%"


def test_identify_container_omits_weight_multiplier_when_100() -> None:
    caster = make_character(name="Appraiser", level=50)

    container_proto = ObjIndex(
        vnum=3001,
        name="plain sack",
        short_descr="a plain sack",
        item_type=int(ItemType.CONTAINER),
        weight=10,
        cost=1,
    )
    container = Object(instance_id=1, prototype=container_proto, level=1)
    container.value = [10, int(ContainerFlag.CLOSEABLE), 0, 10, 100]

    assert identify(caster, container) is True

    assert caster.messages[2] == "Capacity: 10#  Maximum weight: 10#  flags: closable"
    assert not any("Weight multiplier" in msg for msg in caster.messages)


def test_identify_drink_container_reports_liquid_name_and_color() -> None:
    caster = make_character(name="Appraiser", level=50)

    drink_proto = ObjIndex(
        vnum=3002,
        name="waterskin",
        short_descr="a waterskin",
        item_type=int(ItemType.DRINK_CON),
        weight=10,
        cost=5,
    )
    drink = Object(instance_id=1, prototype=drink_proto, level=1)
    drink.value = [10, 0, 0, 0, 0]

    assert identify(caster, drink) is True

    assert caster.messages[2] == "It holds clear-colored water."


def test_identify_scroll_reports_spell_names_by_skill_index() -> None:
    caster = make_character(name="Appraiser", level=50)

    scroll_proto = ObjIndex(
        vnum=1000,
        name="scroll of knowledge",
        short_descr="scroll of knowledge",
        item_type=int(ItemType.SCROLL),
        weight=20,
        cost=250,
    )
    scroll = Object(instance_id=1, prototype=scroll_proto, level=12)
    scroll.extra_flags = int(ExtraFlag.GLOW | ExtraFlag.MAGIC)
    scroll.value = [12, 1, 2, 3, 4]

    assert identify(caster, scroll) is True

    assert caster.messages[2] == "Level 12 spells of: 'acid blast' 'armor' 'bless' 'blindness'."


def test_identify_wand_reports_spell_name_from_value_slot() -> None:
    caster = make_character(name="Appraiser", level=50)
    magic_index = ROM_SKILL_NAMES_BY_INDEX.index("magic missile")

    wand_proto = ObjIndex(
        vnum=3003,
        name="oak wand",
        short_descr="oak wand",
        item_type=int(ItemType.WAND),
        weight=30,
        cost=200,
    )
    wand = Object(instance_id=1, prototype=wand_proto, level=18)
    wand.value = [18, 0, 3, magic_index, 0]

    assert identify(caster, wand) is True
    assert caster.messages[2] == "Has 3 charges of level 18 'magic missile'."


def test_identify_enchanted_objects_skip_prototype_affects() -> None:
    caster = make_character(name="Appraiser", level=50)

    weapon_proto = ObjIndex(
        vnum=2004,
        name="enchanted blade",
        short_descr="an enchanted blade",
        item_type=int(ItemType.WEAPON),
        weight=10,
        cost=200,
        new_format=True,
    )
    weapon_proto.affected = [
        Affect(where=1, type=0, level=0, duration=-1, location=19, modifier=2, bitvector=int(ExtraFlag.MAGIC))
    ]

    weapon = Object(instance_id=1, prototype=weapon_proto, level=10)
    weapon.enchanted = True
    weapon.value = [0, 1, 4, 0, 0]
    weapon.affected.append(
        Affect(where=0, type=0, level=10, duration=2, location=18, modifier=1, bitvector=int(AffectFlag.HASTE))
    )

    assert identify(caster, weapon) is True

    assert "Affects damage roll by 2." not in caster.messages
    assert "Adds magic object flag." not in caster.messages
    assert "Affects hit roll by 1, 2 hours." in caster.messages
    assert "Adds haste affect." in caster.messages


def test_identify_name_falls_back_to_short_descr_when_name_missing() -> None:
    caster = make_character(name="Appraiser", level=50)

    proto = ObjIndex(vnum=2010, name=None, short_descr="mysterious widget", item_type=int(ItemType.TRASH))
    obj = Object(instance_id=1, prototype=proto, level=1)

    assert identify(caster, obj) is True
    assert caster.messages[0].startswith("Object 'mysterious widget' is type")


# ==========================================================================
# know_alignment (src/magic.c:5363)
# ==========================================================================


@pytest.mark.parametrize(
    ("alignment", "expected"),
    [
        (750, "Subject has a pure and good aura."),
        (500, "Subject is of excellent moral character."),
        (150, "Subject is often kind and thoughtful."),
        (0, "Subject doesn't have a firm moral commitment."),
        (-200, "Subject lies to his friends."),
        (-500, "Subject is a black-hearted murderer."),
        (-900, "Subject is the embodiment of pure evil!"),
    ],
)
def test_know_alignment_reports_correct_band_message(alignment: int, expected: str) -> None:
    caster = make_character(name="Diviner", level=24)
    target = make_character(name="Subject", level=20, alignment=alignment, sex=int(Sex.MALE))

    message = know_alignment(caster, target)

    assert message == expected
    assert caster.messages[-1] == expected


def test_know_alignment_uses_female_pronoun_in_negative_band() -> None:
    caster = make_character(name="Diviner", level=24)
    target = make_character(name="Subject", level=20, alignment=-200, sex=int(Sex.FEMALE))

    message = know_alignment(caster, target)

    assert message == "Subject lies to her friends."


def test_know_alignment_self_message_uses_you() -> None:
    caster = make_character(name="Diviner", level=24, alignment=-120)

    message = know_alignment(caster)

    assert message == "You lie to your friends."
    assert caster.messages[-1] == "You lie to your friends."


# ==========================================================================
# locate_object (src/magic.c:5503)
# ==========================================================================


def test_locate_object_requires_search_argument() -> None:
    caster = make_character(name="Seer", level=20)

    assert locate_object(caster, "") is False
    assert caster.messages[-1] == "Nothing like that in heaven or earth."


def test_locate_object_finds_object_in_room_without_vnum_for_mortal() -> None:
    temple = make_room(vnum=3001, name="Temple of Magic")
    room_registry[temple.vnum] = temple

    caster = make_character(name="Diviner", level=50, trust=0)
    temple.add_character(caster)
    character_registry.append(caster)

    orb_proto = ObjIndex(vnum=1200, name="glowing orb", short_descr="a glowing orb")
    orb = Object(instance_id=1, prototype=orb_proto)
    temple.add_object(orb)

    caster.messages.clear()
    assert locate_object(caster, "orb") is True
    assert caster.messages[-1] == "One is in Temple of Magic."


def test_locate_object_finds_object_in_room_with_vnum_for_immortal() -> None:
    temple = make_room(vnum=3001, name="Temple of Magic")
    room_registry[temple.vnum] = temple

    caster = make_character(name="Diviner", level=LEVEL_IMMORTAL, trust=LEVEL_IMMORTAL)
    temple.add_character(caster)
    character_registry.append(caster)

    orb_proto = ObjIndex(vnum=1200, name="glowing orb", short_descr="a glowing orb")
    orb = Object(instance_id=1, prototype=orb_proto)
    temple.add_object(orb)

    caster.messages.clear()
    assert locate_object(caster, "orb") is True
    assert caster.messages[-1] == "One is in Temple of Magic [Room 3001]."


def test_locate_object_hides_invisible_carriers_unless_detect_invis() -> None:
    hall = make_room(vnum=3004, name="Hall of Shadows")
    room_registry[hall.vnum] = hall

    bearer = make_character(name="Shade", level=30, affected_by=int(AffectFlag.INVISIBLE))
    hall.add_character(bearer)
    character_registry.append(bearer)

    gem_proto = ObjIndex(vnum=1401, name="shadow gem", short_descr="a shadowy gem")
    gem = Object(instance_id=1, prototype=gem_proto)
    bearer.add_object(gem)

    caster = make_character(name="Diviner", level=LEVEL_IMMORTAL, trust=LEVEL_IMMORTAL)
    hall.add_character(caster)
    character_registry.append(caster)

    caster.messages.clear()
    assert locate_object(caster, "gem") is True
    assert caster.messages[-1] == "One is in somewhere."

    caster = make_character(
        name="Diviner",
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        affected_by=int(AffectFlag.DETECT_INVIS),
    )
    hall.add_character(caster)
    character_registry.append(caster)

    caster.messages.clear()
    assert locate_object(caster, "gem") is True
    assert caster.messages[-1] == "One is carried by Shade."


def test_locate_object_respects_nolocate_flag() -> None:
    room = make_room(vnum=3002, name="Hall of Echoes")
    room_registry[room.vnum] = room

    caster = make_character(name="Seer", level=50)
    room.add_character(caster)
    character_registry.append(caster)

    hidden_proto = ObjIndex(
        vnum=1300,
        name="hidden relic",
        short_descr="a hidden relic",
        extra_flags=int(ExtraFlag.NOLOCATE),
    )
    hidden = Object(instance_id=1, prototype=hidden_proto)
    room.add_object(hidden)

    caster.messages.clear()
    assert locate_object(caster, "relic") is False
    assert caster.messages[-1] == "Nothing like that in heaven or earth."


def test_locate_object_caps_results_for_mortals() -> None:
    # For mortals, max_found = 2 * level. Use a very low level and force detection success.
    room = make_room(vnum=3002, name="Hall of Echoes")
    room_registry[room.vnum] = room

    caster = make_character(name="Seer", level=1)
    room.add_character(caster)
    character_registry.append(caster)

    for idx in range(10):
        proto = ObjIndex(vnum=1500 + idx, name="tiny relic", short_descr="a tiny relic")
        room.add_object(Object(instance_id=idx + 1, prototype=proto))

    caster.messages.clear()

    # Ensure the RNG gate always passes even at level 1.
    original = rng_mm.number_percent
    try:
        rng_mm.number_percent = lambda: 1  # type: ignore[assignment]
        assert locate_object(caster, "relic") is True
    finally:
        rng_mm.number_percent = original  # type: ignore[assignment]

    found_lines = [msg for msg in caster.messages if msg.startswith("One is")]
    assert len(found_lines) == 2


def test_locate_object_matches_multiword_prefixes() -> None:
    room = make_room(vnum=3001, name="Temple of Magic")
    room_registry[room.vnum] = room

    caster = make_character(name="Seer", level=50)
    room.add_character(caster)
    character_registry.append(caster)

    orb_proto = ObjIndex(vnum=1600, name="glowing orb", short_descr="a glowing orb")
    room.add_object(Object(instance_id=1, prototype=orb_proto))

    caster.messages.clear()
    assert locate_object(caster, "glow orb") is True
    assert caster.messages[-1] == "One is in Temple of Magic."


def test_locate_object_finds_objects_inside_containers_via_holder_location() -> None:
    room = make_room(vnum=3001, name="Temple of Magic")
    room_registry[room.vnum] = room

    caster = make_character(name="Seer", level=LEVEL_IMMORTAL, trust=LEVEL_IMMORTAL)
    bearer = make_character(name="Bearer", level=30)
    room.add_character(caster)
    room.add_character(bearer)
    character_registry.extend([caster, bearer])

    satchel_proto = ObjIndex(vnum=1700, name="leather satchel", short_descr="a leather satchel")
    satchel = Object(instance_id=1, prototype=satchel_proto)
    bearer.add_object(satchel)

    ring_proto = ObjIndex(vnum=1701, name="gold ring", short_descr="a gold ring")
    ring = Object(instance_id=2, prototype=ring_proto)
    satchel.contained_items.append(ring)

    caster.messages.clear()
    assert locate_object(caster, "ring") is True
    assert caster.messages[-1] == "One is carried by Bearer."


# ==========================================================================
# dispel_magic (src/magic.c:3198)
# ==========================================================================


def test_dispel_magic_returns_false_when_target_has_no_effects() -> None:
    caster = make_character(name="Caster", level=30)
    target = make_character(name="Target", level=20)

    assert dispel_magic(caster, target) is False


def test_dispel_magic_removes_effect_and_affect_flag_and_emits_wear_off_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force `saves_dispel` to fail (dispel succeeds) regardless of computed save.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 100)

    caster = make_character(name="Caster", level=60)
    target = make_character(name="Target", level=20)

    target.apply_spell_effect(
        SpellEffect(
            name="fly",
            duration=10,
            level=10,
            affect_flag=AffectFlag.FLYING,
            wear_off_message="You slowly float to the ground.",
        )
    )
    assert target.has_spell_effect("fly")
    assert target.has_affect(AffectFlag.FLYING)

    assert dispel_magic(caster, target) is True

    assert not target.has_spell_effect("fly")
    assert not target.has_affect(AffectFlag.FLYING)

    assert any(msg.endswith("\n\r") and "float to the ground" in msg for msg in target.messages)


def test_dispel_magic_failed_dispel_decrements_effect_level(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force `saves_dispel` to succeed (target saves), so dispel fails and effect level degrades.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    caster = make_character(name="Caster", level=10)
    target = make_character(name="Target", level=20)

    target.apply_spell_effect(SpellEffect(name="haste", duration=10, level=50, affect_flag=AffectFlag.HASTE))

    assert dispel_magic(caster, target) is False

    effect = target.spell_effects.get("haste")
    assert effect is not None
    assert effect.level == 49
    assert target.has_affect(AffectFlag.HASTE)


def test_dispel_magic_permanent_effects_are_harder_to_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    # With a fixed roll, a permanent effect (duration=-1) should have a higher save and can resist
    # while a temporary effect of the same level is removed.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 60)

    caster = make_character(name="Caster", level=50)
    target = make_character(name="Target", level=20)

    target.apply_spell_effect(SpellEffect(name="haste", duration=10, level=50, affect_flag=AffectFlag.HASTE))
    target.apply_spell_effect(SpellEffect(name="sanctuary", duration=-1, level=50, affect_flag=AffectFlag.SANCTUARY))

    assert dispel_magic(caster, target) is True

    assert not target.has_spell_effect("haste")
    assert target.has_spell_effect("sanctuary")
    assert target.spell_effects["sanctuary"].level == 49


def test_dispel_magic_is_level_based(monkeypatch: pytest.MonkeyPatch) -> None:
    # With a fixed roll, higher dispel level should remove an effect that a lower level cannot.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 60)

    low_caster = make_character(name="LowCaster", level=40)
    high_caster = make_character(name="HighCaster", level=60)

    target_low = make_character(name="TargetLow", level=20)
    target_high = make_character(name="TargetHigh", level=20)

    target_low.apply_spell_effect(SpellEffect(name="shield", duration=10, level=50))
    target_high.apply_spell_effect(SpellEffect(name="shield", duration=10, level=50))

    assert dispel_magic(low_caster, target_low) is False
    assert target_low.has_spell_effect("shield")
    assert target_low.spell_effects["shield"].level == 49

    assert dispel_magic(high_caster, target_high) is True
    assert not target_high.has_spell_effect("shield")
