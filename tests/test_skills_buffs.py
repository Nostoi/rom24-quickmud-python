from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, ExtraFlag
from mud.game_loop import obj_update
from mud.models.obj import ObjIndex, ObjectData, object_registry
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int = 3000) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}")
    return room


def test_fly_applies_affect_and_messages() -> None:
    caster = Character(name="Aerin", level=20, is_npc=False)
    witness = Character(name="Watcher", level=10, is_npc=False)
    room = _make_room()
    room.add_character(caster)
    room.add_character(witness)

    assert skill_handlers.fly(caster) is True
    assert caster.has_affect(AffectFlag.FLYING)
    assert caster.has_spell_effect("fly")
    assert caster.messages[-1] == "Your feet rise off the ground."
    assert witness.messages[-1] == "Aerin's feet rise off the ground."

    assert skill_handlers.fly(caster) is False
    assert caster.messages[-1] == "You are already airborne."


def test_fly_reports_duplicates_for_other_targets() -> None:
    caster = Character(name="Mage", level=18, is_npc=False)
    target = Character(name="Scout", level=16, is_npc=False)
    room = _make_room(3001)
    room.add_character(caster)
    room.add_character(target)

    assert skill_handlers.fly(target) is True
    target.messages.clear()

    assert skill_handlers.fly(caster, target) is False
    assert caster.messages[-1] == "Scout doesn't need your help to fly."


def test_frenzy_applies_bonuses_and_messages() -> None:
    caster = Character(name="Cleric", level=24, is_npc=False, alignment=400)
    target = Character(name="Paladin", level=20, is_npc=False, alignment=350)
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _make_room(3002)
    room.add_character(caster)
    room.add_character(target)
    room.add_character(witness)
    witness.messages.clear()

    assert skill_handlers.frenzy(caster, target) is True

    effect = target.spell_effects.get("frenzy")
    assert effect is not None
    assert effect.duration == c_div(caster.level, 3)
    assert effect.hitroll_mod == c_div(caster.level, 6)
    assert effect.damroll_mod == c_div(caster.level, 6)
    assert effect.ac_mod == 10 * c_div(caster.level, 12)
    assert effect.wear_off_message == "Your rage ebbs."

    assert target.hitroll == effect.hitroll_mod
    assert target.damroll == effect.damroll_mod
    assert target.armor == [effect.ac_mod] * 4
    assert target.messages[-1] == "You are filled with holy wrath!"
    assert witness.messages[-1] == "Paladin gets a wild look in their eyes!"


def test_frenzy_blocks_duplicates_and_berserk() -> None:
    caster = Character(name="Cleric", level=30, is_npc=False, alignment=0)
    target = Character(name="Knight", level=28, is_npc=False, alignment=0)
    room = _make_room(3003)
    room.add_character(caster)
    room.add_character(target)

    target.apply_spell_effect(SpellEffect(name="frenzy", duration=5))

    assert skill_handlers.frenzy(caster, target) is False
    assert caster.messages[-1] == "Knight is already in a frenzy."

    target.spell_effects.clear()
    target.hitroll = 0
    target.damroll = 0
    target.armor = [0, 0, 0, 0]
    target.add_affect(AffectFlag.BERSERK)
    caster.messages.clear()

    assert skill_handlers.frenzy(caster, target) is False
    assert caster.messages[-1] == "Knight is already in a frenzy."


def test_frenzy_blocks_calm_and_alignment_mismatch() -> None:
    caster = Character(name="Priest", level=26, is_npc=False, alignment=400)
    caster.apply_spell_effect(SpellEffect(name="calm", duration=4, affect_flag=AffectFlag.CALM))

    assert skill_handlers.frenzy(caster) is False
    assert caster.messages[-1] == "Why don't you just relax for a while?"

    target = Character(name="Rogue", level=24, is_npc=False, alignment=-400)
    room = _make_room(3004)
    room.add_character(caster)
    room.add_character(target)
    caster.messages.clear()

    assert skill_handlers.frenzy(caster, target) is False
    assert caster.messages[-1] == "Your god doesn't seem to like Rogue"


def test_infravision_applies_affect_and_messages() -> None:
    caster = Character(name="Oracle", level=18, is_npc=False)
    witness = Character(name="Observer", level=12, is_npc=False)
    room = _make_room(3005)
    room.add_character(caster)
    room.add_character(witness)
    witness.messages.clear()

    assert skill_handlers.infravision(caster) is True
    effect = caster.spell_effects.get("infravision")
    assert effect is not None
    assert effect.duration == 2 * caster.level
    assert caster.has_affect(AffectFlag.INFRARED)
    assert caster.messages[-1] == "Your eyes glow red."
    assert witness.messages[-1] == "Oracle's eyes glow red."

    caster.messages.clear()
    assert skill_handlers.infravision(caster) is False
    assert caster.messages[-1] == "You can already see in the dark."

    target = Character(name="Scout", level=14, is_npc=False)
    room.add_character(target)
    target.messages.clear()

    assert skill_handlers.infravision(caster, target) is True
    caster.messages.clear()
    assert skill_handlers.infravision(caster, target) is False
    assert caster.messages[-1] == "Scout already has infravision."


def test_invis_handles_objects_and_characters() -> None:
    caster = Character(name="Magus", level=20, is_npc=False)
    target = Character(name="Shade", level=18, is_npc=False)
    witness = Character(name="Watcher", level=15, is_npc=False)
    room = _make_room(3006)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    prototype = ObjIndex(vnum=1010, short_descr="mysterious gem")
    obj = Object(instance_id=1, prototype=prototype, extra_flags=0)

    assert skill_handlers.invis(caster, obj) is True
    assert obj.extra_flags & int(ExtraFlag.INVIS)
    assert caster.messages[-1] == "mysterious gem fades out of sight."
    assert witness.messages[-1] == "mysterious gem fades out of sight."

    caster.messages.clear()
    assert skill_handlers.invis(caster, obj) is False
    assert caster.messages[-1] == "mysterious gem is already invisible."

    witness.messages.clear()
    assert skill_handlers.invis(caster, target) is True
    assert target.has_affect(AffectFlag.INVISIBLE)
    assert target.has_spell_effect("invis")
    assert target.messages[-1] == "You fade out of existence."
    assert witness.messages[-1] == "Shade fades out of existence."

    assert skill_handlers.invis(caster, target) is False


def test_invis_object_wears_off() -> None:
    caster = Character(name="Magus", level=24, is_npc=False)
    witness = Character(name="Watcher", level=12, is_npc=False)
    room = _make_room(3007)
    for character in (caster, witness):
        room.add_character(character)
        character.messages.clear()

    obj = ObjectData(item_type=int(0), short_descr="mysterious gem")
    obj.in_room = room
    room.contents.append(obj)
    object_registry.append(obj)

    try:
        assert skill_handlers.invis(caster, obj) is True
        assert obj.extra_flags & int(ExtraFlag.INVIS)
        assert caster.messages[-1] == "mysterious gem fades out of sight."
        assert witness.messages[-1] == "mysterious gem fades out of sight."

        caster.messages.clear()
        witness.messages.clear()

        effect = obj.affected[0]
        effect.duration = 0

        obj_update()

        assert not (obj.extra_flags & int(ExtraFlag.INVIS))
        assert witness.messages[-1] == "mysterious gem fades into view."
    finally:
        if obj in object_registry:
            object_registry.remove(obj)
        if obj in room.contents:
            room.contents.remove(obj)


def test_mass_invis_fades_group() -> None:
    caster = Character(name="Oracle", level=25, is_npc=False)
    caster.leader = caster
    ally = Character(name="Scout", level=20, is_npc=False)
    ally.leader = caster
    already_invis = Character(name="Shade", level=18, is_npc=False)
    already_invis.leader = caster
    already_invis.add_affect(AffectFlag.INVISIBLE)
    outsider = Character(name="Bystander", level=14, is_npc=False)

    room = _make_room(3008)
    for character in (caster, ally, already_invis, outsider):
        room.add_character(character)
        character.messages.clear()

    result = skill_handlers.mass_invis(caster)

    assert result is True
    assert caster.has_affect(AffectFlag.INVISIBLE)
    assert ally.has_affect(AffectFlag.INVISIBLE)
    assert not outsider.has_affect(AffectFlag.INVISIBLE)
    assert all("You slowly fade out of existence." not in msg for msg in already_invis.messages)

    ally_effect = ally.spell_effects.get("mass invis")
    assert ally_effect is not None
    assert ally_effect.duration == 24
    assert ally_effect.level == c_div(caster.level, 2)
    assert ally.messages[-1] == "You slowly fade out of existence."
    assert caster.messages[-1] == "Ok."
    assert any("slowly fades out of existence." in msg for msg in outsider.messages)
