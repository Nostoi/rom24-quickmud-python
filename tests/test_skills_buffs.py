import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, ExtraFlag, Sex, Stat
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


def test_change_sex_applies_affect_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Illusionist", level=18, is_npc=False)
    target = Character(name="Volunteer", level=16, is_npc=False, sex=int(Sex.MALE))
    witness = Character(name="Witness", level=12, is_npc=False)
    room = _make_room(3050)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: int(Sex.FEMALE))

    assert skill_handlers.change_sex(caster, target) is True

    effect = target.spell_effects.get("change sex")
    assert effect is not None
    assert effect.duration == 2 * caster.level
    assert effect.sex_delta == int(Sex.FEMALE) - int(Sex.MALE)
    assert target.sex == int(Sex.FEMALE)
    assert target.messages[-1] == "You feel different."
    room_message = "Volunteer doesn't look like herself anymore..."
    assert witness.messages[-1] == room_message
    assert caster.messages[-1] == room_message


def test_change_sex_respects_duplicates_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Prankster", level=20, is_npc=False)
    target = Character(name="Guard", level=18, is_npc=False, sex=int(Sex.MALE))
    room = _make_room(3051)
    room.add_character(caster)
    room.add_character(target)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: int(Sex.FEMALE))

    assert skill_handlers.change_sex(caster, target) is True
    caster.messages.clear()

    assert skill_handlers.change_sex(caster, target) is False
    assert caster.messages[-1] == "Guard has already had their sex changed."

    target.remove_spell_effect("change sex")
    target.sex = int(Sex.MALE)
    target.messages.clear()
    caster.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: True)

    assert skill_handlers.change_sex(caster, target) is False
    assert "change sex" not in target.spell_effects
    assert target.sex == int(Sex.MALE)
    assert target.messages == []


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
    # ROM initializes armor to [100,100,100,100], frenzy adds +20 penalty = [120,120,120,120]
    assert target.armor == [100 + effect.ac_mod] * 4
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


def test_protection_evil_applies_save_bonus() -> None:
    caster = Character(name="Priest", level=20, is_npc=False)
    target = Character(name="Knight", level=18, is_npc=False)

    assert skill_handlers.protection_evil(caster, target) is True

    effect = target.spell_effects.get("protection evil")
    assert effect is not None
    assert effect.duration == 24
    assert effect.level == caster.level
    assert effect.saving_throw_mod == -1
    assert effect.affect_flag == AffectFlag.PROTECT_EVIL
    assert effect.wear_off_message == "You feel less protected."
    assert target.has_affect(AffectFlag.PROTECT_EVIL)
    assert target.saving_throw == -1
    assert target.messages[-1] == "You feel holy and pure."
    assert caster.messages[-1] == "Knight is protected from evil."

    caster.messages.clear()
    assert skill_handlers.protection_evil(caster, target) is False
    assert caster.messages[-1] == "Knight is already protected."

    target.remove_spell_effect("protection evil")
    assert not target.has_affect(AffectFlag.PROTECT_EVIL)
    assert target.saving_throw == 0
    target.messages.clear()
    caster.messages.clear()

    target.apply_spell_effect(
        SpellEffect(
            name="protection good",
            duration=24,
            level=target.level,
            saving_throw_mod=-1,
            affect_flag=AffectFlag.PROTECT_GOOD,
        )
    )

    assert skill_handlers.protection_evil(caster, target) is False
    assert caster.messages[-1] == "Knight is already protected."


def test_protection_good_applies_save_bonus() -> None:
    caster = Character(name="DarkCleric", level=22, is_npc=False)
    target = Character(name="Defender", level=20, is_npc=False)

    target.apply_spell_effect(
        SpellEffect(
            name="protection evil",
            duration=24,
            level=target.level,
            saving_throw_mod=-1,
            affect_flag=AffectFlag.PROTECT_EVIL,
        )
    )

    assert skill_handlers.protection_good(caster, target) is False
    assert caster.messages[-1] == "Defender is already protected."

    target.remove_spell_effect("protection evil")
    assert not target.has_affect(AffectFlag.PROTECT_EVIL)
    assert target.saving_throw == 0
    caster.messages.clear()
    target.messages.clear()

    assert skill_handlers.protection_good(caster, target) is True

    effect = target.spell_effects.get("protection good")
    assert effect is not None
    assert effect.duration == 24
    assert effect.level == caster.level
    assert effect.saving_throw_mod == -1
    assert effect.affect_flag == AffectFlag.PROTECT_GOOD
    assert effect.wear_off_message == "You feel less protected."
    assert target.has_affect(AffectFlag.PROTECT_GOOD)
    assert target.saving_throw == -1
    assert target.messages[-1] == "You feel aligned with darkness."
    assert caster.messages[-1] == "Defender is protected from good."

    target.messages.clear()
    assert skill_handlers.protection_good(target) is False
    assert target.messages[-1] == "You are already protected."


def test_stone_skin_applies_ac_and_messages() -> None:
    caster = Character(name="Geomancer", level=32, is_npc=False)
    target = Character(name="Sentinel", level=28, is_npc=False)
    witness = Character(name="Observer", level=18, is_npc=False)
    room = _make_room(3008)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    assert skill_handlers.stone_skin(caster, target) is True

    effect = target.spell_effects.get("stone skin")
    assert effect is not None
    assert effect.duration == caster.level
    assert effect.level == caster.level
    # ROM initializes armor to [100,100,100,100], stone skin applies -40 = [60,60,60,60]
    assert target.armor == [60, 60, 60, 60]

    assert target.messages[-1] == "Your skin turns to stone."
    room_message = "Sentinel's skin turns to stone."
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_stone_skin_rejects_duplicates() -> None:
    caster = Character(name="Invoker", level=30, is_npc=False)
    room = _make_room(3009)
    room.add_character(caster)
    caster.messages.clear()

    assert skill_handlers.stone_skin(caster) is True

    caster.messages.clear()
    assert skill_handlers.stone_skin(caster) is False
    assert caster.messages[-1] == "Your skin is already as hard as a rock."

    target = Character(name="Guardian", level=26, is_npc=False)
    room.add_character(target)
    target.messages.clear()

    assert skill_handlers.stone_skin(caster, target) is True

    caster.messages.clear()
    assert skill_handlers.stone_skin(caster, target) is False
    assert caster.messages[-1] == "Guardian is already as hard as can be."


def test_giant_strength_applies_strength_bonus() -> None:
    caster = Character(name="Battlemage", level=32, is_npc=False)
    target = Character(name="Warrior", level=28, is_npc=False)
    witness = Character(name="Onlooker", level=20, is_npc=False)
    room = _make_room(3010)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    assert skill_handlers.giant_strength(caster, target) is True

    effect = target.spell_effects.get("giant strength")
    assert effect is not None
    assert effect.duration == caster.level
    assert effect.stat_modifiers == {Stat.STR: 4}
    assert effect.wear_off_message == "You feel weaker."

    assert target.mod_stat[Stat.STR] == 4
    assert target.messages[-1] == "Your muscles surge with heightened power!"
    room_message = "Warrior's muscles surge with heightened power."
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_giant_strength_uses_override_item_level() -> None:
    caster = Character(name="Enchanter", level=12, is_npc=False)
    target = Character(name="Guardian", level=18, is_npc=False)
    witness = Character(name="Observer", level=18, is_npc=False)
    room = _make_room(3011)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    override_level = 24

    assert skill_handlers.giant_strength(caster, target, override_level=override_level) is True

    effect = target.spell_effects.get("giant strength")
    assert effect is not None
    assert effect.duration == override_level
    assert effect.level == override_level
    assert effect.stat_modifiers == {Stat.STR: 2}
    assert target.mod_stat[Stat.STR] == 2

    assert target.messages[-1] == "Your muscles surge with heightened power!"
    room_message = "Guardian's muscles surge with heightened power."
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_giant_strength_rejects_duplicates() -> None:
    caster = Character(name="Champion", level=25, is_npc=False)
    room = _make_room(3012)
    room.add_character(caster)

    assert skill_handlers.giant_strength(caster) is True

    caster.messages.clear()
    assert skill_handlers.giant_strength(caster) is False
    assert caster.messages[-1] == "You are already as strong as you can get!"


def test_haste_applies_affect_and_messages() -> None:
    caster = Character(name="Arcanist", level=32, is_npc=False)
    target = Character(name="Scout", level=24, is_npc=False)
    witness = Character(name="Witness", level=18, is_npc=False)
    room = _make_room(3013)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    assert skill_handlers.haste(caster, target) is True

    effect = target.spell_effects.get("haste")
    assert effect is not None
    assert effect.duration == c_div(caster.level, 4)
    assert effect.affect_flag == AffectFlag.HASTE
    assert effect.stat_modifiers == {Stat.DEX: 4}
    assert effect.wear_off_message == "You feel yourself slow down."
    assert target.has_affect(AffectFlag.HASTE)

    assert target.messages[-1] == "You feel yourself moving more quickly."
    room_message = "Scout is moving more quickly."
    assert caster.messages[-1] == "Ok."
    assert witness.messages[-1] == room_message

    caster.spell_effects.clear()
    caster.remove_affect(AffectFlag.HASTE)
    caster.messages.clear()

    assert skill_handlers.haste(caster) is True
    self_effect = caster.spell_effects.get("haste")
    assert self_effect is not None
    assert self_effect.duration == c_div(caster.level, 2)


def test_haste_uses_override_item_level() -> None:
    caster = Character(name="Sprinter", level=14, is_npc=False)
    target = Character(name="Runner", level=10, is_npc=False)
    witness = Character(name="Spectator", level=16, is_npc=False)
    room = _make_room(3014)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    override_level = 28

    assert skill_handlers.haste(caster, target, override_level=override_level) is True

    effect = target.spell_effects.get("haste")
    assert effect is not None
    assert effect.duration == c_div(override_level, 4)
    assert effect.level == override_level
    assert effect.stat_modifiers == {Stat.DEX: 3}
    assert target.has_affect(AffectFlag.HASTE)
    assert caster.messages[-1] == "Ok."
    room_message = "Runner is moving more quickly."
    assert target.messages[-1] == "You feel yourself moving more quickly."
    assert witness.messages[-1] == room_message

    target.remove_spell_effect("haste")
    target.remove_affect(AffectFlag.HASTE)
    target.messages.clear()
    caster.messages.clear()
    witness.messages.clear()

    self_override = 20

    assert skill_handlers.haste(caster, override_level=self_override) is True

    self_effect = caster.spell_effects.get("haste")
    assert self_effect is not None
    assert self_effect.duration == c_div(self_override, 2)
    assert self_effect.level == self_override
    assert self_effect.stat_modifiers == {Stat.DEX: 2}
    assert caster.has_affect(AffectFlag.HASTE)
    assert caster.messages[-1] == "You feel yourself moving more quickly."
    self_room_message = "Sprinter is moving more quickly."
    assert witness.messages[-1] == self_room_message


def test_haste_dispels_slow_or_blocks_duplicates(monkeypatch) -> None:
    caster = Character(name="Wizard", level=28, is_npc=False)
    target = Character(name="Runner", level=20, is_npc=False)
    witness = Character(name="Bystander", level=18, is_npc=False)
    room = _make_room(3015)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    target.apply_spell_effect(SpellEffect(name="haste", duration=5, level=20, affect_flag=AffectFlag.HASTE))

    assert skill_handlers.haste(caster, target) is False
    assert caster.messages[-1] == "Runner is already moving as fast as they can."

    target.remove_spell_effect("haste")
    caster.messages.clear()
    target.messages.clear()
    witness.messages.clear()

    target.apply_spell_effect(SpellEffect(name="slow", duration=6, level=20, affect_flag=AffectFlag.SLOW))

    rolls = iter([99, 0])
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: next(rolls))

    assert skill_handlers.haste(caster, target) is True
    assert not target.has_affect(AffectFlag.SLOW)
    assert "slow" not in target.spell_effects
    slowed_message = "Runner is moving less slowly."
    assert caster.messages[-1] == slowed_message
    assert witness.messages[-1] == slowed_message

    target.apply_spell_effect(SpellEffect(name="slow", duration=6, level=20, affect_flag=AffectFlag.SLOW))
    caster.messages.clear()
    target.messages.clear()

    assert skill_handlers.haste(caster, target) is False
    assert target.has_affect(AffectFlag.SLOW)
    assert target.messages[-1] == "You feel momentarily faster."
    assert caster.messages[-1] == "Spell failed."


def test_sneak_sets_affect_on_success(monkeypatch) -> None:
    caster = Character(name="Shadow", level=22, is_npc=False)
    caster.skills["sneak"] = 80
    caster.messages.clear()

    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 5)

    improvements: list[tuple[str, bool, int]] = []

    def record_check_improve(character, skill_name, success, amount) -> None:
        improvements.append((skill_name, success, amount))

    monkeypatch.setattr(skill_handlers, "check_improve", record_check_improve)

    assert skill_handlers.sneak(caster) is True
    assert caster.messages[0] == "You attempt to move silently."
    assert caster.has_affect(AffectFlag.SNEAK)

    effect = caster.spell_effects.get("sneak")
    assert effect is not None
    assert effect.duration == caster.level
    assert effect.affect_flag == AffectFlag.SNEAK

    assert improvements[-1] == ("sneak", True, 3)


def test_sneak_failure_trains_skill(monkeypatch) -> None:
    caster = Character(name="Scout", level=14, is_npc=False)
    caster.skills["sneak"] = 10
    caster.messages.clear()

    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 95)

    improvements: list[tuple[str, bool, int]] = []

    def record_check_improve(character, skill_name, success, amount) -> None:
        improvements.append((skill_name, success, amount))

    monkeypatch.setattr(skill_handlers, "check_improve", record_check_improve)

    assert skill_handlers.sneak(caster) is False
    assert caster.messages[0] == "You attempt to move silently."
    assert not caster.has_affect(AffectFlag.SNEAK)
    assert "sneak" not in caster.spell_effects

    assert improvements[-1] == ("sneak", False, 3)


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


def test_fireproof_applies_burn_proof_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Enchanter", level=28, is_npc=False)
    witness = Character(name="Observer", level=18, is_npc=False)
    room = _make_room(3010)
    for character in (caster, witness):
        room.add_character(character)
        character.messages.clear()

    prototype = ObjIndex(vnum=2010, short_descr="ancient scroll")
    obj = Object(instance_id=2, prototype=prototype, extra_flags=0)

    def fake_number_fuzzy(value: int) -> int:
        assert value == max(0, c_div(caster.level, 4))
        return 7

    monkeypatch.setattr(skill_handlers.rng_mm, "number_fuzzy", fake_number_fuzzy)

    assert skill_handlers.fireproof(caster, obj) is True
    assert obj.extra_flags & int(ExtraFlag.BURN_PROOF)
    assert obj.affected

    effect = obj.affected[-1]
    assert effect.level == caster.level
    assert effect.duration == 7
    assert effect.bitvector == int(ExtraFlag.BURN_PROOF)
    assert getattr(effect, "spell_name") == "fireproof"
    assert getattr(effect, "wear_off_message") == "$p's protective aura fades."

    assert caster.messages[-1] == "You protect ancient scroll from fire."
    assert witness.messages[-1] == "ancient scroll is surrounded by a protective aura."


def test_fireproof_rejects_already_protected() -> None:
    caster = Character(name="Enchanter", level=28, is_npc=False)
    room = _make_room(3011)
    room.add_character(caster)
    caster.messages.clear()

    prototype = ObjIndex(vnum=2011, short_descr="ancient scroll")
    obj = Object(instance_id=3, prototype=prototype, extra_flags=int(ExtraFlag.BURN_PROOF))

    assert skill_handlers.fireproof(caster, obj) is False
    assert caster.messages[-1] == "ancient scroll is already protected from burning."


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
