import pytest

from mud.models import Character
from mud.models.character import SpellEffect
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    ExtraFlag,
    ItemType,
    Sector,
    Stat,
    WeaponFlag,
    WeaponType,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_character(name: str, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.max_hit = 200
    char.hit = 200
    char.messages = []
    char.perm_stat = [18, 18, 18, 18, 18]
    char.mod_stat = [0] * len(char.perm_stat)
    return char


def _make_weapon(vnum: int, short_descr: str) -> Object:
    prototype = ObjIndex(
        vnum=vnum,
        short_descr=short_descr,
        item_type=int(ItemType.WEAPON),
        value=[int(WeaponType.SWORD), 2, 4, 0, 0],
        new_format=True,
    )
    weapon = Object(
        instance_id=vnum,
        prototype=prototype,
        value=list(prototype.value),
        extra_flags=0,
    )
    return weapon


def _make_food(vnum: int, short_descr: str, *, extra_flags: int = 0) -> Object:
    prototype = ObjIndex(
        vnum=vnum,
        short_descr=short_descr,
        item_type=int(ItemType.FOOD),
        value=[0, 0, 0, 0, 0],
    )
    food = Object(
        instance_id=vnum,
        prototype=prototype,
        value=list(prototype.value),
        extra_flags=extra_flags,
    )
    return food


def test_weaken_applies_strength_penalty_and_affect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    room = Room(vnum=4000, sector_type=int(Sector.CITY))

    caster = _make_character("Cleric", level=30)
    target = _make_character("Ogre", level=25)
    watcher = _make_character("Watcher", level=20)

    room.add_character(caster)
    room.add_character(target)
    room.add_character(watcher)

    result = skill_handlers.weaken(caster, target=target)

    assert result is True
    assert target.has_affect(AffectFlag.WEAKEN)
    assert target.has_spell_effect("weaken")

    effect = target.spell_effects["weaken"]
    expected_penalty = -skill_handlers.c_div(caster.level, 5)
    assert effect.stat_modifiers.get(Stat.STR) == expected_penalty
    assert effect.duration == skill_handlers.c_div(caster.level, 2)

    base_strength = 18
    assert target.get_curr_stat(Stat.STR) == base_strength + expected_penalty
    assert any("strength slip away" in message for message in target.messages)
    assert any("looks tired and weak" in message for message in watcher.messages)


def test_weaken_respects_save_and_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4001, sector_type=int(Sector.FIELD))

    caster = _make_character("Invoker", level=40)
    target = _make_character("Brute", level=35)

    room.add_character(caster)
    room.add_character(target)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: True)

    resisted = skill_handlers.weaken(caster, target=target)

    assert resisted is False
    assert not target.has_spell_effect("weaken")
    assert not target.has_affect(AffectFlag.WEAKEN)

    target.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    applied = skill_handlers.weaken(caster, target=target)

    assert applied is True
    assert target.has_spell_effect("weaken")
    initial_message_count = len(target.messages)

    duplicate = skill_handlers.weaken(caster, target=target)

    assert duplicate is False
    assert len(target.messages) == initial_message_count


def test_poison_envenoms_weapon_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4300, sector_type=int(Sector.CITY))

    caster = _make_character("Assassin", level=32)
    witness = _make_character("Watcher", level=26)
    for character in (caster, witness):
        room.add_character(character)
        character.messages.clear()

    weapon = _make_weapon(3300, "serrated dagger")

    assert skill_handlers.poison(caster, weapon) is True

    assert weapon.value[4] & int(WeaponFlag.POISON)
    assert getattr(weapon, "weapon_flags") & int(WeaponFlag.POISON)
    assert weapon.affected

    effect = weapon.affected[-1]
    assert effect.level == skill_handlers.c_div(caster.level, 2)
    assert effect.duration == skill_handlers.c_div(caster.level, 8)
    assert effect.bitvector == int(WeaponFlag.POISON)
    assert getattr(effect, "wear_off_message") == "The poison on $p dries up."

    success_message = "serrated dagger is coated with deadly venom."
    assert caster.messages[-1] == success_message
    assert witness.messages[-1] == success_message

    caster.messages.clear()
    assert skill_handlers.poison(caster, weapon) is False
    assert caster.messages[-1] == "serrated dagger is already envenomed."


def test_poison_rejects_protected_weapon() -> None:
    room = Room(vnum=4301, sector_type=int(Sector.FIELD))

    caster = _make_character("Assassin", level=30)
    room.add_character(caster)
    caster.messages.clear()

    weapon = _make_weapon(3301, "blessed blade")
    weapon.extra_flags = int(ExtraFlag.BLESS)

    assert skill_handlers.poison(caster, weapon) is False
    assert caster.messages[-1] == "You can't seem to envenom blessed blade."


def test_poison_taints_food_and_messages() -> None:
    room = Room(vnum=4302, sector_type=int(Sector.CITY))

    caster = _make_character("Herbalist", level=28)
    witness = _make_character("Bystander", level=20)
    for character in (caster, witness):
        room.add_character(character)
        character.messages.clear()

    food = _make_food(4400, "loaf of bread")

    assert skill_handlers.poison(caster, food) is True
    assert food.value[3] == 1

    taint_message = "loaf of bread is infused with poisonous vapors."
    assert caster.messages[-1] == taint_message
    assert witness.messages[-1] == taint_message

    caster.messages.clear()
    food.extra_flags = int(ExtraFlag.BLESS)
    assert skill_handlers.poison(caster, food) is False
    assert caster.messages[-1] == "Your spell fails to corrupt loaf of bread."


def test_poison_afflicts_character_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4303, sector_type=int(Sector.CITY))

    caster = _make_character("Alchemist", level=35)
    target = _make_character("Victim", level=30)
    witness = _make_character("Onlooker", level=22)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    assert skill_handlers.poison(caster, target) is True
    assert target.has_affect(AffectFlag.POISON)
    assert target.has_spell_effect("poison")

    effect = target.spell_effects["poison"]
    assert effect.duration == caster.level
    assert effect.stat_modifiers == {Stat.STR: -2}
    assert effect.wear_off_message == "You feel less sick."
    assert target.mod_stat[Stat.STR] == -2

    assert target.messages[-1] == "You feel very sick."
    assert witness.messages[-1] == "Victim looks very ill."


def test_poison_save_prevents_affect(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4304, sector_type=int(Sector.FIELD))

    caster = _make_character("Alchemist", level=35)
    target = _make_character("Victim", level=30)
    witness = _make_character("Onlooker", level=22)
    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: True)

    assert skill_handlers.poison(caster, target) is False
    assert "poison" not in target.spell_effects
    assert target.messages[-1] == "You feel momentarily ill, but it passes."
    assert witness.messages[-1] == "Victim turns slightly green, but it passes."


def test_slow_applies_affect_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4100, sector_type=int(Sector.CITY))

    caster = _make_character("Sorcerer", level=32)
    target = _make_character("Runner", level=28)
    witness = _make_character("Observer", level=26)

    for character in (caster, target, witness):
        room.add_character(character)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    applied = skill_handlers.slow(caster, target)

    assert applied is True
    assert target.has_affect(AffectFlag.SLOW)
    assert target.has_spell_effect("slow")

    effect = target.spell_effects["slow"]
    expected_modifier = -1
    for threshold in (18, 25, 32):
        if caster.level >= threshold:
            expected_modifier -= 1
    assert effect.duration == skill_handlers.c_div(caster.level, 2)
    assert effect.stat_modifiers == {Stat.DEX: expected_modifier}
    assert effect.wear_off_message == "You feel yourself speed up."

    assert target.messages[-1] == "You feel yourself slowing d o w n..."
    room_message = "Runner starts to move in slow motion."
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_slow_uses_override_item_level(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4102, sector_type=int(Sector.FIELD))

    caster = _make_character("Mage", level=18)
    target = _make_character("Scout", level=16)
    witness = _make_character("Watcher", level=14)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    override_level = 24

    assert (
        skill_handlers.slow(caster, target, override_level=override_level) is True
    )

    effect = target.spell_effects["slow"]
    expected_modifier = -1
    for threshold in (18, 25, 32):
        if override_level >= threshold:
            expected_modifier -= 1

    assert effect.duration == skill_handlers.c_div(override_level, 2)
    assert effect.level == override_level
    assert effect.stat_modifiers == {Stat.DEX: expected_modifier}

    assert target.messages[-1] == "You feel yourself slowing d o w n..."
    room_message = "Scout starts to move in slow motion."
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_slow_dispels_haste_or_handles_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4101, sector_type=int(Sector.FIELD))

    caster = _make_character("Wizard", level=30)
    target = _make_character("Sprinter", level=25)
    witness = _make_character("Bystander", level=22)

    for character in (caster, target, witness):
        room.add_character(character)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    target.apply_spell_effect(
        SpellEffect(
            name="haste",
            duration=6,
            level=20,
            affect_flag=AffectFlag.HASTE,
            stat_modifiers={Stat.DEX: 2},
        )
    )

    rolls = iter([99, 0])
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: next(rolls))

    assert skill_handlers.slow(caster, target) is True
    assert "haste" not in target.spell_effects
    slowed_message = "Sprinter is moving less quickly."
    assert caster.messages[-1] == slowed_message
    assert witness.messages[-1] == slowed_message

    target.apply_spell_effect(
        SpellEffect(
            name="haste",
            duration=6,
            level=20,
            affect_flag=AffectFlag.HASTE,
            stat_modifiers={Stat.DEX: 2},
        )
    )
    caster.messages.clear()
    target.messages.clear()

    assert skill_handlers.slow(caster, target) is False
    assert target.has_spell_effect("haste")
    assert target.messages[-1] == "You feel momentarily slower."
    assert caster.messages[-1] == "Spell failed."

    target.remove_spell_effect("haste")
    caster.messages.clear()
    target.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: True)
    assert skill_handlers.slow(caster, target) is False
    assert target.messages[-1] == "You feel momentarily lethargic."
    assert caster.messages[-1] == "Nothing seemed to happen."


def test_plague_applies_affect_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4200, sector_type=int(Sector.CITY))

    caster = _make_character("Cleric", level=28)
    target = _make_character("Patient", level=24)
    witness = _make_character("Observer", level=22)

    for character in (caster, target, witness):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    assert skill_handlers.plague(caster, target) is True
    assert target.has_affect(AffectFlag.PLAGUE)
    assert target.has_spell_effect("plague")

    effect = target.spell_effects["plague"]
    assert effect.duration == caster.level
    assert effect.level == skill_handlers.c_div(3 * caster.level, 4)
    assert effect.stat_modifiers == {Stat.STR: -5}
    assert effect.affect_flag == AffectFlag.PLAGUE
    assert effect.wear_off_message == "Your sores vanish."
    assert target.mod_stat[Stat.STR] == -5

    target_message = "You scream in agony as plague sores erupt from your skin."
    room_message = "Patient screams in agony as plague sores erupt from their skin."
    assert target.messages[-1] == target_message
    assert caster.messages[-1] == room_message
    assert witness.messages[-1] == room_message


def test_plague_respects_saves_and_undead(monkeypatch: pytest.MonkeyPatch) -> None:
    room = Room(vnum=4201, sector_type=int(Sector.FIELD))

    caster = _make_character("Priest", level=30)
    target = _make_character("Ghoul", level=26)

    for character in (caster, target):
        room.add_character(character)
        character.messages.clear()

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: True)

    assert skill_handlers.plague(caster, target) is False
    assert "plague" not in target.spell_effects
    assert caster.messages[-1] == "Ghoul seems to be unaffected."
    assert target.messages == []

    caster.messages.clear()
    target.messages.clear()
    target.is_npc = True
    target.act = int(ActFlag.UNDEAD)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: False)

    assert skill_handlers.plague(caster, target) is False
    assert "plague" not in target.spell_effects
    assert caster.messages[-1] == "Ghoul seems to be unaffected."
    assert target.messages == []


def test_sleep_level_gate_is_silent_failure() -> None:
    caster = _make_character("Illusionist", level=18)
    target = _make_character("Veteran", level=25)

    caster.messages.clear()
    target.messages.clear()

    result = skill_handlers.sleep(caster, target)

    assert result is False
    assert target.spell_effects.get("sleep") is None
    assert not caster.messages
    assert not target.messages


def test_sleep_save_is_silent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = _make_character("Enchanter", level=32)
    target = _make_character("Scout", level=30)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dam: True)

    caster.messages.clear()
    target.messages.clear()

    result = skill_handlers.sleep(caster, target)

    assert result is False
    assert target.spell_effects.get("sleep") is None
    assert not caster.messages
    assert not target.messages
