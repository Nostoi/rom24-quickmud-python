from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int = 3000) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}")
    return room


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
