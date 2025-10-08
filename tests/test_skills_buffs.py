from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag
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
