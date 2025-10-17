from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, ExtraFlag, ItemType, LEVEL_IMMORTAL, Sex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm
from mud.models.character import character_registry
from mud.registry import room_registry


def _make_room(vnum: int = 3000) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}")
    return room


def test_locate_object_finds_visible_items() -> None:
    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    try:
        room_registry.clear()
        character_registry.clear()

        temple = Room(vnum=3001, name="Temple of Magic")
        room_registry[temple.vnum] = temple

        caster = Character(name="Diviner", level=LEVEL_IMMORTAL, is_npc=False)
        temple.add_character(caster)
        character_registry.append(caster)

        orb_proto = ObjIndex(vnum=1200, name="glowing orb", short_descr="a glowing orb")
        orb = Object(instance_id=None, prototype=orb_proto)
        temple.add_object(orb)

        bearer = Character(name="Bearer", level=30, is_npc=False)
        temple.add_character(bearer)
        character_registry.append(bearer)

        satchel_proto = ObjIndex(vnum=1201, name="leather satchel", short_descr="a leather satchel")
        satchel = Object(instance_id=None, prototype=satchel_proto)
        bearer.add_object(satchel)

        caster.messages.clear()
        assert skill_handlers.locate_object(caster, "orb") is True
        assert caster.messages[-1] == "One is in Temple of Magic [Room 3001]."

        caster.messages.clear()
        assert skill_handlers.locate_object(caster, "satchel") is True
        assert caster.messages[-1] == "One is carried by Bearer."
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_locate_object_blocks_nolocate_and_level() -> None:
    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    try:
        room_registry.clear()
        character_registry.clear()

        hall = Room(vnum=3002, name="Hall of Echoes")
        room_registry[hall.vnum] = hall

        caster = Character(name="Seer", level=20, is_npc=False)
        hall.add_character(caster)
        character_registry.append(caster)

        hidden_proto = ObjIndex(
            vnum=1300,
            name="hidden relic",
            short_descr="a hidden relic",
            extra_flags=int(ExtraFlag.NOLOCATE),
        )
        hidden = Object(instance_id=None, prototype=hidden_proto)
        hall.add_object(hidden)

        ancient_proto = ObjIndex(vnum=1301, name="ancient relic", short_descr="an ancient relic", level=60)
        ancient = Object(instance_id=None, prototype=ancient_proto)
        hall.add_object(ancient)

        caster.messages.clear()
        assert skill_handlers.locate_object(caster, "relic") is False
        assert caster.messages[-1] == "Nothing like that in heaven or earth."
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_locate_object_respects_detection_chance(monkeypatch: pytest.MonkeyPatch) -> None:
    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    try:
        room_registry.clear()
        character_registry.clear()

        glade = Room(vnum=3003, name="Forest Glade")
        room_registry[glade.vnum] = glade

        caster = Character(name="Seeker", level=20, is_npc=False)
        glade.add_character(caster)
        character_registry.append(caster)

        relic_proto = ObjIndex(vnum=1400, name="ancient relic", short_descr="an ancient relic")
        relic = Object(instance_id=None, prototype=relic_proto)
        glade.add_object(relic)

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 95)

        caster.messages.clear()
        assert skill_handlers.locate_object(caster, "relic") is False
        assert caster.messages[-1] == "Nothing like that in heaven or earth."
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_locate_object_hides_invisible_carriers(monkeypatch: pytest.MonkeyPatch) -> None:
    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    try:
        room_registry.clear()
        character_registry.clear()

        hall = Room(vnum=3004, name="Hall of Shadows")
        room_registry[hall.vnum] = hall

        caster = Character(name="Diviner", level=LEVEL_IMMORTAL, is_npc=False)
        hall.add_character(caster)
        character_registry.append(caster)

        bearer = Character(name="Shade", level=30, is_npc=False, affected_by=int(AffectFlag.INVISIBLE))
        hall.add_character(bearer)
        character_registry.append(bearer)

        gem_proto = ObjIndex(vnum=1401, name="shadow gem", short_descr="a shadowy gem")
        gem = Object(instance_id=None, prototype=gem_proto)
        bearer.add_object(gem)

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)

        caster.messages.clear()
        assert skill_handlers.locate_object(caster, "gem") is True
        assert caster.messages[-1] == "One is in somewhere."
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_lore_appraises_known_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Sage", level=40, is_npc=False, skills={"lore": 80})
    wand_proto = ObjIndex(
        vnum=2200,
        name="ancient wand",
        short_descr="an ancient wand",
        item_type=int(ItemType.WAND),
    )
    wand = Object(instance_id=None, prototype=wand_proto)
    wand.value = [15, 0, 3, 0, 0]
    caster.add_object(wand)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 5)

    caster.messages.clear()
    result = skill_handlers.lore(caster, wand)

    assert result is True
    assert caster.messages[0] == "Object 'ancient wand' is type wand, extra flags none."
    assert caster.wait == skill_handlers._skill_beats("lore")


def test_lore_fails_without_skill() -> None:
    caster = Character(name="Novice", level=10, is_npc=False, skills={"lore": 0})
    relic_proto = ObjIndex(vnum=2201, name="mysterious relic", short_descr="a mysterious relic")
    relic = Object(instance_id=None, prototype=relic_proto)
    caster.add_object(relic)

    caster.messages.clear()
    result = skill_handlers.lore(caster, relic)

    assert result is False
    assert caster.messages[-1] == "You don't know anything about that."
    assert caster.wait == skill_handlers._skill_beats("lore")


def test_detect_invis_applies_affect_and_blocks_duplicates() -> None:
    caster = Character(name="Seer", level=24, is_npc=False)
    room = _make_room(3001)
    room.add_character(caster)

    assert skill_handlers.detect_invis(caster) is True
    assert caster.has_affect(AffectFlag.DETECT_INVIS)
    assert caster.has_spell_effect("detect invis")
    assert caster.messages[-1] == "Your eyes tingle."

    assert skill_handlers.detect_invis(caster) is False
    assert caster.messages[-1] == "You can already see invisible."


def test_detect_evil_applies_affect_and_notifies_caster() -> None:
    caster = Character(name="Cleric", level=18, is_npc=False)
    target = Character(name="Scout", level=12, is_npc=False)
    room = _make_room(3002)
    room.add_character(caster)
    room.add_character(target)

    assert skill_handlers.detect_evil(caster, target) is True
    assert target.has_affect(AffectFlag.DETECT_EVIL)
    assert target.messages[-1] == "Your eyes tingle."
    assert caster.messages[-1] == "Ok."

    assert skill_handlers.detect_evil(caster, target) is False
    assert caster.messages[-1] == "Scout can already detect evil."


def test_detect_poison_reports_food_status() -> None:
    caster = Character(name="Inspector", level=10, is_npc=False)
    food_proto = ObjIndex(
        vnum=1010,
        name="bread",
        short_descr="a loaf of bread",
        item_type=int(ItemType.FOOD),
    )
    food = Object(instance_id=None, prototype=food_proto)
    food.value = [5, 0, 0, 1, 0]

    assert skill_handlers.detect_poison(caster, food) is True
    assert caster.messages[-1] == "You smell poisonous fumes."

    safe_food = Object(instance_id=None, prototype=food_proto)
    safe_food.value = [5, 0, 0, 0, 0]

    assert skill_handlers.detect_poison(caster, safe_food) is True
    assert caster.messages[-1] == "It looks delicious."

    weapon_proto = ObjIndex(
        vnum=2010,
        name="sword",
        short_descr="a sword",
        item_type=int(ItemType.WEAPON),
    )
    weapon = Object(instance_id=None, prototype=weapon_proto)

    assert skill_handlers.detect_poison(caster, weapon) is True
    assert caster.messages[-1] == "It doesn't look poisoned."


def test_faerie_fire_applies_glow_and_ac_penalty() -> None:
    caster = Character(name="Illusionist", level=18, is_npc=False)
    target = Character(name="Rogue", level=16, is_npc=False)
    room = _make_room(3003)
    room.add_character(caster)
    room.add_character(target)

    starting_ac = list(target.armor)

    assert skill_handlers.faerie_fire(caster, target) is True

    penalty = 2 * caster.level
    assert target.has_affect(AffectFlag.FAERIE_FIRE)
    assert target.has_spell_effect("faerie fire")
    assert target.armor == [ac + penalty for ac in starting_ac]
    assert target.messages[-1] == "You are surrounded by a pink outline."
    assert caster.messages[-1] == "Rogue is surrounded by a pink outline."


def test_faerie_fire_rejects_duplicates() -> None:
    caster = Character(name="Illusionist", level=18, is_npc=False)
    target = Character(name="Rogue", level=16, is_npc=False)
    room = _make_room(3004)
    room.add_character(caster)
    room.add_character(target)

    assert skill_handlers.faerie_fire(caster, target) is True

    caster.messages.clear()
    target.messages.clear()
    previous_armor = list(target.armor)

    assert skill_handlers.faerie_fire(caster, target) is False
    assert target.armor == previous_armor
    assert caster.messages[-1] == "Rogue is already surrounded by a pink outline."


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
def test_know_alignment_reports_aura(alignment: int, expected: str) -> None:
    caster = Character(name="Diviner", level=24, is_npc=False)
    target = Character(
        name="Subject",
        level=20,
        is_npc=False,
        alignment=alignment,
        sex=int(Sex.MALE),
    )
    room = _make_room(3010)
    room.add_character(caster)
    room.add_character(target)

    caster.messages.clear()

    message = skill_handlers.know_alignment(caster, target)

    assert message == expected
    assert caster.messages[-1] == expected


@pytest.mark.parametrize(
    ("alignment", "expected"),
    [
        (700, "Subject is of excellent moral character."),
        (350, "Subject is often kind and thoughtful."),
        (100, "Subject doesn't have a firm moral commitment."),
        (-100, "Subject lies to her friends."),
        (-350, "Subject is a black-hearted murderer."),
        (-700, "Subject is the embodiment of pure evil!"),
    ],
)
def test_know_alignment_bounds_edges(alignment: int, expected: str) -> None:
    caster = Character(name="Oracle", level=22, is_npc=False)
    target = Character(
        name="Subject",
        level=18,
        is_npc=False,
        alignment=alignment,
        sex=int(Sex.FEMALE),
    )
    room = _make_room(3011)
    room.add_character(caster)
    room.add_character(target)

    caster.messages.clear()

    message = skill_handlers.know_alignment(caster, target)

    assert message == expected
    assert caster.messages[-1] == expected

    caster.messages.clear()
    caster.alignment = -120

    self_message = skill_handlers.know_alignment(caster)

    assert self_message == "You lie to your friends."
    assert caster.messages[-1] == "You lie to your friends."
