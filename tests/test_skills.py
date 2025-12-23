from pathlib import Path
from random import Random

import pytest

import mud.magic.effects as magic_effects
import mud.skills.handlers as skill_handlers
from mud.commands.combat import do_backstab, do_bash, do_berserk, do_rescue
from mud.config import get_pulse_violence
from mud.game_loop import SkyState, violence_tick, weather
from mud.math.c_compat import c_div
from mud.models.character import Character, character_registry
from mud.models.constants import (
    AffectFlag,
    ExtraFlag,
    ImmFlag,
    Position,
    RoomFlag,
    Stat,
    WeaponType,
)
from mud.models.room import Room
from mud.models.object import Object, ObjIndex
from mud.skills import SkillRegistry, SkillUseResult, load_skills, skill_registry
from mud.utils import rng_mm


def assert_attack_message(message: str, target: str) -> None:
    assert message.startswith("{2")
    assert target in message
    assert message.endswith("{x")


def load_registry() -> SkillRegistry:
    reg = SkillRegistry(rng=Random(0))
    reg.load(Path("data/skills.json"))
    return reg


def test_casting_uses_min_mana_and_beats() -> None:
    reg = load_registry()
    caster = Character(mana=35)
    target = Character()
    skill = reg.get("fireball")

    assert skill.min_mana == 15
    assert skill.beats == 12
    assert skill.slot == 26

    result = reg.use(caster, "fireball", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert isinstance(result.payload, int)
    assert result.cooldown == skill.cooldown
    assert caster.mana == 20  # 35 - min_mana 15
    expected_wait = max(1, skill.lag)
    assert caster.wait == expected_wait
    assert caster.cooldowns["fireball"] == 0  # Fireball has no cooldown in skills.json
    assert result.lag == expected_wait
    assert result.message == "You cast fireball."

    # Simulate wait recovery before a second cast
    caster.wait = 0
    caster.mana = 15
    second = reg.use(caster, "fireball", target)
    assert caster.mana == 0
    assert isinstance(second, SkillUseResult)


def test_cast_fireball_failure() -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.failure_rate = 1.0

    called: list[bool] = []

    def dummy(caster, target):  # pragma: no cover - test helper
        called.append(True)
        return 99

    reg.handlers["fireball"] = dummy

    caster = Character(mana=20)
    target = Character()
    result = reg.use(caster, "fireball", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is False
    assert result.payload is None
    assert "concentration" in result.message
    assert result.cooldown == skill.cooldown
    assert result.lag == max(1, skill.lag)
    assert caster.messages[-1] == result.message
    assert caster.mana == 5  # 20 - 15 mana cost = 5 (mana consumed even on failure)
    assert called == []


def test_skill_use_reports_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    caster = Character(
        mana=skill.min_mana * 2,
        is_npc=False,
        skills={"fireball": 75},
    )
    target = Character()

    # Provide enough rolls for: skill check + check_improve (range + percent) per use
    percent_rolls = iter([50, 1000, 1000, 999, 999, 999])
    range_rolls = iter([1, 1, 1, 1])

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    success = reg.use(caster, "fireball", target)
    assert isinstance(success, SkillUseResult)
    assert success.success is True
    assert success.message == "You cast fireball."
    assert isinstance(success.payload, int)

    caster.wait = 0

    failure = reg.use(caster, "fireball", target)
    assert isinstance(failure, SkillUseResult)
    assert failure.success is False
    assert failure.payload is None
    assert "concentration" in failure.message
    assert caster.messages[-1] == failure.message


def test_skill_use_advances_learned_percent(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.rating[0] = 4

    caster = Character(
        mana=20,
        ch_class=0,
        level=10,
        is_npc=False,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 50},
    )
    target = Character()

    initial_exp = caster.exp

    # Rolls needed: skill check (30 = success), check_improve gate (1 = pass), improvement chance (1 = improve)
    percent_rolls = iter([30, 1, 1])
    range_rolls = iter([10, 1])  # Fireball damage, check_improve gate

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert isinstance(result.payload, int)
    assert caster.skills["fireball"] == 51
    assert caster.exp >= initial_exp
    assert any("become better" in msg for msg in caster.messages)


def test_skill_failure_grants_learning_xp(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    skill.rating[0] = 4

    caster = Character(
        mana=20,
        ch_class=0,
        level=10,
        is_npc=False,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 50},
    )
    target = Character()

    initial_exp = caster.exp

    # Rolls: skill check (100 = fail), check_improve gate (1 = pass), improvement chance (10 = improve), increment (2)
    percent_rolls = iter([100, 10])
    range_rolls = iter([1, 2])  # check_improve gate, increment amount

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is False
    assert caster.skills["fireball"] == 52
    assert caster.exp >= initial_exp
    assert any("learn from your mistakes" in msg for msg in caster.messages)


def test_skill_use_sets_wait_state_and_blocks_until_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reg = load_registry()
    skill = reg.get("acid blast")
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "dice", lambda level, size: 60)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    caster = Character(mana=40, is_npc=False, skills={"acid blast": 100})
    caster.level = 30
    target = Character()

    expected_wait = max(1, skill.lag)
    result = reg.use(caster, "acid blast", target)
    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert result.payload == 60
    assert result.lag == expected_wait
    assert caster.wait == expected_wait
    assert caster.mana == 20
    assert caster.cooldowns.get("acid blast", 0) == skill.cooldown
    assert result.cooldown == skill.cooldown

    with pytest.raises(ValueError) as excinfo:
        reg.use(caster, "acid blast", target)
    assert "recover" in str(excinfo.value)
    assert caster.messages[-1] == "You are still recovering."
    assert caster.mana == 20


def test_burning_hands_damage_and_save(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(level=10)
    target = Character(hit=100, max_hit=100)

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: high)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    damage = skill_handlers.burning_hands(caster, target)
    assert damage == 58
    assert target.hit == 42

    target.hit = 100
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: True)

    halved = skill_handlers.burning_hands(caster, target)
    assert halved == 29
    assert target.hit == 71


def test_call_lightning_weather_gating(monkeypatch: pytest.MonkeyPatch) -> None:
    original_sky = weather.sky
    caster_room = Room(vnum=100, room_flags=0)
    target_room = caster_room

    caster = Character(level=18, room=caster_room, is_npc=False)
    target = Character(hit=120, max_hit=120, room=target_room, is_npc=True)
    caster_room.people.extend([caster, target])

    weather.sky = SkyState.CLOUDLESS
    target.hit = 120
    caster.messages.clear()

    blocked_weather = skill_handlers.call_lightning(caster, target)
    assert blocked_weather == 0
    assert caster.messages[-1] == "You need bad weather."
    assert target.hit == 120

    caster_room.room_flags = int(RoomFlag.ROOM_INDOORS)
    weather.sky = SkyState.LIGHTNING
    caster.messages.clear()

    blocked_indoor = skill_handlers.call_lightning(caster, target)
    assert blocked_indoor == 0
    assert caster.messages[-1] == "You must be out of doors."
    assert target.hit == 120

    caster_room.room_flags = 0
    weather.sky = SkyState.RAINING
    caster.messages.clear()
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 40)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    dealt = skill_handlers.call_lightning(caster, target)
    assert dealt == 40
    assert target.hit == 80
    assert "Mota's lightning strikes your foes!" in caster.messages

    weather.sky = original_sky


def test_skill_tick_only_reduces_cooldowns() -> None:
    reg = SkillRegistry()
    character = Character(wait=3)
    character.cooldowns = {"fireball": 1, "shield": 2}

    reg.tick(character)

    # Wait-state recovery happens during the per-pulse violence tick, not the skill tick.
    assert character.wait == 3
    assert character.cooldowns == {"shield": 1}


def test_skill_wait_adjusts_for_haste_and_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("acid blast")
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    haste_caster = Character(
        mana=20,
        is_npc=False,
        affected_by=int(AffectFlag.HASTE),
        skills={"acid blast": 100},
    )
    haste_target = Character()
    reg.use(haste_caster, "acid blast", haste_target)
    haste_pulses = max(1, c_div(skill.lag, 2))
    expected_haste = max(1, haste_pulses)
    assert haste_caster.wait == expected_haste

    slow_caster = Character(
        mana=20,
        is_npc=False,
        affected_by=int(AffectFlag.SLOW),
        skills={"acid blast": 100},
    )
    slow_target = Character()
    reg.use(slow_caster, "acid blast", slow_target)
    slow_pulses = skill.lag * 2
    expected_slow = max(1, slow_pulses)
    assert slow_caster.wait == expected_slow


def test_rescue_switches_tank_and_wait_state(monkeypatch: pytest.MonkeyPatch) -> None:
    load_skills(Path("data/skills.json"))
    skill = skill_registry.get("rescue")
    assert skill is not None

    rescuer = Character(name="Rescuer", level=40, is_npc=False, skills={"rescue": 75})
    ally = Character(name="Ally", is_npc=False)
    foe = Character(name="Ogre", is_npc=True)
    onlooker = Character(name="Onlooker", is_npc=False)

    room = Room(vnum=3001)
    for ch in (rescuer, ally, foe, onlooker):
        room.add_character(ch)

    ally.leader = rescuer
    ally.fighting = foe
    ally.position = Position.FIGHTING
    foe.fighting = ally
    foe.position = Position.FIGHTING

    rescuer.wait = 0
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    out = do_rescue(rescuer, "ally")

    assert out == "{5You rescue Ally!{x"
    assert rescuer.fighting is foe
    assert foe.fighting is rescuer
    assert ally.fighting is None
    assert rescuer.wait == skill_registry._compute_skill_lag(rescuer, skill)
    assert rescuer.cooldowns["rescue"] == skill.cooldown
    assert "{5You rescue Ally!{x" in rescuer.messages
    assert "{5Rescuer rescues you!{x" in ally.messages
    assert "{5Rescuer rescues Ally!{x" in onlooker.messages


def test_sanctuary_applies_affect_and_messages() -> None:
    caster = Character(name="Cleric", level=24, is_npc=False)
    target = Character(name="Tank", is_npc=False)
    observer = Character(name="Observer", is_npc=False)

    room = Room(vnum=3001)
    for ch in (caster, target, observer):
        room.add_character(ch)

    applied = skill_handlers.sanctuary(caster, target)

    assert applied is True
    assert target.has_affect(AffectFlag.SANCTUARY)
    effect = target.spell_effects["sanctuary"]
    assert effect.duration == c_div(caster.level, 6)
    assert effect.affect_flag == AffectFlag.SANCTUARY
    assert target.messages[-1] == "You are surrounded by a white aura."
    assert "Tank is surrounded by a white aura." in observer.messages
    assert "Tank is surrounded by a white aura." in caster.messages


def test_blindness_applies_affect_and_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Mage", level=18, is_npc=False)
    target = Character(name="Orc", hitroll=0)
    watcher = Character(name="Watcher", is_npc=False)

    room = Room(vnum=3001)
    for ch in (caster, target, watcher):
        room.add_character(ch)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    result = skill_handlers.blindness(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.BLIND)
    assert target.hitroll == -4
    effect = target.spell_effects["blindness"]
    assert effect.duration == 1 + caster.level
    assert effect.affect_flag == AffectFlag.BLIND
    assert effect.hitroll_mod == -4
    assert effect.wear_off_message == "You can see again."
    assert target.messages[-1] == "You are blinded!"
    assert "Orc appears to be blinded." in caster.messages
    assert "Orc appears to be blinded." in watcher.messages


def test_blindness_save_blocks_affect(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Mage", level=18, is_npc=False)
    target = Character(name="Orc")

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: True)

    before_messages = list(target.messages)
    result = skill_handlers.blindness(caster, target)

    assert result is False
    assert not target.has_affect(AffectFlag.BLIND)
    assert target.spell_effects == {}
    assert target.hitroll == 0
    assert target.messages == before_messages


def test_chill_touch_damage_and_strength_debuff(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Thera", level=20, is_npc=False)
    target = Character(
        name="Orc",
        hit=100,
        perm_stat=[15, 12, 12, 12, 12],
        mod_stat=[0, 0, 0, 0, 0],
    )
    watcher = Character(name="Watcher")

    room = Room(vnum=3001)
    for ch in (caster, target, watcher):
        room.add_character(ch)

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: high)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    damage = skill_handlers.chill_touch(caster, target)

    assert damage == 34
    assert target.hit == 66
    assert target.has_spell_effect("chill touch")
    effect = target.spell_effects["chill touch"]
    assert effect.duration == 6
    assert effect.level == 20
    assert effect.stat_modifiers[Stat.STR] == -1
    assert target.get_curr_stat(Stat.STR) == 14
    assert "Orc turns blue and shivers." in watcher.messages
    assert "Orc turns blue and shivers." in caster.messages


def test_colour_spray_blinds_and_rolls_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Thera", level=24, is_npc=False)
    target = Character(name="Bandit", hit=120)
    observer = Character(name="Watcher")

    room = Room(vnum=3001)
    for ch in (caster, target, observer):
        room.add_character(ch)

    damage_rolls = iter([80, 80])

    def fake_range(low: int, high: int) -> int:
        return next(damage_rolls)

    save_results = iter([False, False, True])

    def fake_save(level: int, victim: Character, dtype: int) -> bool:
        return next(save_results)

    monkeypatch.setattr(rng_mm, "number_range", fake_range)
    monkeypatch.setattr(skill_handlers, "saves_spell", fake_save)

    damage = skill_handlers.colour_spray(caster, target)

    assert damage == 80
    assert target.hit == 40
    assert target.has_affect(AffectFlag.BLIND)
    blind_effect = target.spell_effects["blindness"]
    expected_level = c_div(24, 2)
    assert blind_effect.level == expected_level
    assert blind_effect.duration == 1 + expected_level
    assert any("red" in message and "blue" in message and "yellow" in message for message in caster.messages)
    assert any("red" in message and "blue" in message and "yellow" in message for message in target.messages)
    assert any("red" in message and "blue" in message and "yellow" in message for message in observer.messages)

    new_target = Character(name="Scout", hit=120)
    new_room = Room(vnum=3002)
    for ch in (caster, new_target):
        new_room.add_character(ch)

    damage_halved = skill_handlers.colour_spray(caster, new_target)
    assert damage_halved == c_div(80, 2)
    assert new_target.hit == 120 - damage_halved
    assert "blindness" not in new_target.spell_effects


def test_curse_flags_object_and_penalizes_victim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caster = Character(name="Thera", level=24, is_npc=False)
    victim = Character(name="Aria", level=18, is_npc=False)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)

    applied = skill_handlers.curse(caster, victim)
    assert applied is True
    assert victim.has_affect(AffectFlag.CURSE)
    effect = victim.spell_effects.get("curse")
    assert effect is not None
    expected_mod = c_div(caster.level, 8)
    assert victim.hitroll == -expected_mod
    assert victim.saving_throw == expected_mod
    assert any("You feel unclean." in msg for msg in victim.messages)
    assert any("looks very uncomfortable" in msg for msg in caster.messages)

    caster.messages.clear()
    proto = ObjIndex(vnum=1000, short_descr="a silver dagger")
    obj = Object(instance_id=1, prototype=proto, level=10, extra_flags=int(ExtraFlag.BLESS))

    monkeypatch.setattr(skill_handlers, "saves_dispel", lambda level, spell_level, duration: False)

    cursed = skill_handlers.curse(caster, obj)
    assert cursed is True
    assert obj.extra_flags & int(ExtraFlag.EVIL)
    assert not (obj.extra_flags & int(ExtraFlag.BLESS))
    assert any("red aura" in msg for msg in caster.messages)
    assert any("malevolent aura" in msg for msg in caster.messages)


def test_charm_person_sets_affect_and_follower(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Enchanter", level=20, is_npc=False)
    target = Character(name="Guard", level=10, is_npc=True)
    observer = Character(name="Onlooker", is_npc=False)

    room = Room(vnum=3400)
    for ch in (caster, target, observer):
        room.add_character(ch)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)
    monkeypatch.setattr(rng_mm, "number_fuzzy", lambda base: base)

    result = skill_handlers.charm_person(caster, target)

    assert result is True
    assert target.master is caster
    assert target.leader is caster
    assert target.has_affect(AffectFlag.CHARM)

    effect = target.spell_effects["charm person"]
    assert effect.level == caster.level
    assert effect.duration == max(1, c_div(caster.level, 4))
    assert effect.affect_flag == AffectFlag.CHARM
    assert effect.wear_off_message == "You feel more self-confident."

    assert any(message.startswith("You now follow") for message in target.messages)
    assert "Isn't Enchanter just so nice?" in target.messages
    assert "Guard looks at you with adoring eyes." in caster.messages


def test_charm_person_requires_save_and_room_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Magistrate", level=18, is_npc=False)
    target = Character(name="Citizen", level=15, is_npc=False)

    room = Room(vnum=3450, room_flags=int(RoomFlag.ROOM_LAW))
    room.add_character(caster)
    room.add_character(target)

    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    result = skill_handlers.charm_person(caster, target)

    assert result is False
    assert target.master is None
    assert "charm person" not in target.spell_effects
    assert "The mayor does not allow charming in the city limits." in caster.messages

    caster.messages.clear()
    room.room_flags = 0
    target.imm_flags = int(ImmFlag.CHARM)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: True)

    result = skill_handlers.charm_person(caster, target)

    assert result is False
    assert target.master is None
    assert target.spell_effects == {}
    assert caster.messages == []


def test_shield_applies_ac_bonus_and_duration() -> None:
    caster = Character(name="Mage", level=18, is_npc=False)
    target = Character(name="Tank", is_npc=False)
    watcher = Character(name="Watcher", is_npc=False)

    room = Room(vnum=3001)
    for ch in (caster, target, watcher):
        room.add_character(ch)

    result = skill_handlers.shield(caster, target)

    assert result is True
    effect = target.spell_effects["shield"]
    assert effect.duration == 8 + caster.level
    # ROM initializes armor to [100,100,100,100], shield applies -20 to all = [80,80,80,80]
    assert target.armor == [80, 80, 80, 80]
    assert target.messages[-1] == "You are surrounded by a force shield."
    assert "Tank is surrounded by a force shield." in watcher.messages


def test_wait_state_recovery_matches_pulses() -> None:
    reg = load_registry()
    skill = reg.get("fireball")
    caster = Character(mana=30, is_npc=False, skills={"fireball": 100})
    target = Character()

    original_lag = skill.lag
    skill.lag = 7

    character_registry.append(caster)
    try:
        reg.use(caster, "fireball", target)
        assert caster.wait == 7

        for remaining in range(7, 0, -1):
            violence_tick()
            assert caster.wait == remaining - 1
    finally:
        character_registry.remove(caster)
        skill.lag = original_lag


def test_kick_success(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker = Character(
        name="Hero",
        level=20,
        is_npc=False,
        max_hit=100,
        hit=100,
        skills={"kick": 75},
    )
    victim = Character(name="Orc", level=10, is_npc=True, max_hit=100, hit=100)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 10)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 12)

    result = skill_handlers.kick(attacker, victim)

    assert_attack_message(result, "Orc")
    assert victim.hit == 88
    assert attacker.fighting is victim
    assert victim.fighting is attacker


def test_kick_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker = Character(
        name="Hero",
        level=20,
        is_npc=False,
        max_hit=100,
        hit=100,
        skills={"kick": 10},
    )
    victim = Character(name="Orc", level=10, is_npc=True, max_hit=100, hit=100)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 90)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 5)

    result = skill_handlers.kick(attacker, victim)

    assert result == "{2You miss Orc.{x"
    assert victim.hit == 100
    assert attacker.fighting is victim
    assert victim.fighting is attacker


def test_kick_requires_opponent() -> None:
    attacker = Character(name="Hero", level=10, is_npc=False, skills={"kick": 60})

    with pytest.raises(ValueError) as excinfo:
        skill_handlers.kick(attacker)

    assert "opponent" in str(excinfo.value)


class DummyRoom:
    def __init__(self) -> None:
        self.people: list[Character] = []


class DummyWeapon:
    def __init__(self, weapon_type: WeaponType = WeaponType.DAGGER, dice: tuple[int, int] = (2, 4)) -> None:
        self.item_type = "weapon"
        self.new_format = True
        self.value = [int(weapon_type), dice[0], dice[1], 0]
        self.weapon_stats: set[str] = set()


def test_backstab_uses_position_and_weapon(monkeypatch: pytest.MonkeyPatch) -> None:
    load_skills(Path("data/skills.json"))

    room = DummyRoom()
    attacker = Character(
        name="Rogue",
        level=20,
        is_npc=False,
        max_hit=100,
        hit=100,
        skills={"backstab": 75, "dagger": 100},
        position=Position.STANDING,
    )
    attacker.room = room
    attacker.equipment["wield"] = DummyWeapon()
    room.people.append(attacker)

    victim = Character(
        name="Guard",
        level=15,
        is_npc=True,
        max_hit=120,
        hit=120,
        position=Position.STANDING,
    )
    victim.room = room
    room.people.append(victim)

    percent_iter = iter([10, 5])

    def fake_percent() -> int:
        return next(percent_iter, 50)

    monkeypatch.setattr(rng_mm, "number_percent", fake_percent)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)

    result = do_backstab(attacker, "Guard")

    assert_attack_message(result, "Guard")
    assert attacker.wait == 24
    assert attacker.cooldowns.get("backstab", None) == 0
    assert attacker.fighting is victim
    assert victim.fighting is attacker
    assert victim.hit == 84  # 120 - (base 9 * dagger multiplier 4)


def test_bash_applies_wait_state(monkeypatch: pytest.MonkeyPatch) -> None:
    load_skills(Path("data/skills.json"))

    room = DummyRoom()
    attacker = Character(
        name="Warrior",
        level=30,
        is_npc=False,
        skills={"bash": 75},
        size=2,
        position=Position.FIGHTING,
    )
    attacker.room = room
    room.people.append(attacker)

    victim = Character(
        name="Ogre",
        level=25,
        is_npc=True,
        max_hit=150,
        hit=150,
        position=Position.FIGHTING,
    )
    victim.room = room
    room.people.append(victim)

    attacker.fighting = victim
    victim.fighting = attacker

    percent_iter = iter([10])

    def fake_percent() -> int:
        return next(percent_iter, 100)

    monkeypatch.setattr(rng_mm, "number_percent", fake_percent)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: b)

    result = do_bash(attacker, "")

    assert_attack_message(result, "Ogre")
    assert attacker.wait == 24
    assert attacker.cooldowns.get("bash", None) == 0
    assert victim.position == Position.RESTING
    assert victim.daze == 3 * get_pulse_violence()


def test_berserk_applies_rage_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    load_skills(Path("data/skills.json"))

    attacker = Character(
        name="Barbarian",
        level=20,
        is_npc=False,
        skills={"berserk": 75},
        max_hit=100,
        hit=40,
        mana=100,
        move=60,
        position=Position.FIGHTING,
        armor=[0, 0, 0, 0],
    )

    percent_iter = iter([10])

    def fake_percent() -> int:
        return next(percent_iter, 100)

    base_duration = max(1, c_div(attacker.level, 8))

    monkeypatch.setattr(rng_mm, "number_percent", fake_percent)
    monkeypatch.setattr(rng_mm, "number_fuzzy", lambda n: base_duration)

    result = do_berserk(attacker, "")

    assert result == "Your pulse races as you are consumed by rage!"
    assert attacker.wait == get_pulse_violence()
    assert attacker.mana == 50
    assert attacker.move == c_div(60, 2)
    assert attacker.hit == 80
    assert attacker.has_affect(AffectFlag.BERSERK)
    assert attacker.has_spell_effect("berserk")
    assert attacker.hitroll == max(1, c_div(attacker.level, 5))
    assert attacker.damroll == max(1, c_div(attacker.level, 5))
    assert attacker.armor == [40, 40, 40, 40]
    assert attacker.cooldowns.get("berserk", None) == 0


def test_acid_breath_applies_acid_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("acid breath")

    caster = Character(
        name="Ancient Dragon",
        level=40,
        hit=250,
        mana=skill.mana_cost + 25,
        is_npc=False,
        skills={"acid breath": 95},
    )
    target = Character(name="Knight", hit=320, max_hit=320, is_npc=True)

    monkeypatch.setattr(SkillRegistry, "_check_improve", lambda *args, **kwargs: None)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 200)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: a)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, victim, dtype: False)

    result = reg.use(caster, "acid breath", target)

    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert result.payload == 202
    assert target.hit == 118
    assert caster.wait == max(1, skill.lag)
    assert caster.mana == 25
    assert caster.cooldowns.get("acid breath", None) == 0
    assert result.cooldown == skill.cooldown
    assert result.lag == max(1, skill.lag)

    effects = getattr(target, "last_spell_effects", [])
    assert effects
    assert effects[-1] == {
        "effect": "acid",
        "level": 40,
        "damage": 202,
        "target": magic_effects.SpellTarget.CHAR,
    }


def test_fire_breath_hits_room_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = load_registry()
    skill = reg.get("fire breath")

    room = DummyRoom()
    caster = Character(
        name="Red Dragon",
        level=40,
        hit=250,
        mana=skill.mana_cost + 50,
        is_npc=True,
        skills={"fire breath": 100},
    )
    target = Character(name="Hero", hit=360, max_hit=360, is_npc=False)
    bystander = Character(name="Bystander", hit=180, max_hit=180, is_npc=False)

    room.people.extend([caster, target, bystander])
    caster.room = room
    target.room = room
    bystander.room = room

    monkeypatch.setattr(SkillRegistry, "_check_improve", lambda *args, **kwargs: None)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 200)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: a)

    def fake_saves(level, victim, dtype):  # pragma: no cover - helper
        return victim is not target

    monkeypatch.setattr(skill_handlers, "saves_spell", fake_saves)

    result = reg.use(caster, "fire breath", target)

    assert isinstance(result, SkillUseResult)
    assert result.success is True
    assert result.payload == 202
    assert target.hit == 158
    assert bystander.hit == 130
    assert caster.wait == max(1, skill.lag)
    assert caster.mana == skill.mana_cost + 50 - skill.mana_cost
    assert caster.cooldowns.get("fire breath", None) == 0
    assert result.cooldown == skill.cooldown
    assert result.lag == max(1, skill.lag)

    room_effects = getattr(room, "last_spell_effects", [])
    assert {"effect": "fire", "level": 40, "damage": 101, "target": magic_effects.SpellTarget.ROOM} in room_effects

    target_effects = getattr(target, "last_spell_effects", [])
    assert target_effects
    assert target_effects[-1] == {
        "effect": "fire",
        "level": 40,
        "damage": 202,
        "target": magic_effects.SpellTarget.CHAR,
    }

    bystander_effects = getattr(bystander, "last_spell_effects", [])
    assert {
        "effect": "fire",
        "level": 10,
        "damage": 25,
        "target": magic_effects.SpellTarget.CHAR,
    } in bystander_effects
