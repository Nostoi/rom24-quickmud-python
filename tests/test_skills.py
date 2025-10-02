from pathlib import Path
from random import Random

import pytest

import mud.magic.effects as magic_effects
import mud.skills.handlers as skill_handlers
from mud.commands.combat import do_backstab, do_bash, do_berserk
from mud.game_loop import violence_tick
from mud.math.c_compat import c_div
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position, WeaponType
from mud.skills import SkillRegistry, load_skills
from mud.utils import rng_mm
from mud.config import get_pulse_violence


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
    assert result == 42
    assert caster.mana == 20  # 35 - min_mana 15
    expected_wait = max(1, skill.lag)
    assert caster.wait == expected_wait
    assert caster.cooldowns["fireball"] == 0  # Fireball has no cooldown in skills.json

    # Simulate wait recovery before a second cast
    caster.wait = 0
    caster.mana = 15
    reg.use(caster, "fireball", target)
    assert caster.mana == 0


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
    assert result is False
    assert caster.mana == 5  # 20 - 15 mana cost = 5 (mana consumed even on failure)
    assert called == []


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

    percent_rolls = iter([30, 1])
    range_rolls = iter([10])

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert result == 42
    assert caster.skills["fireball"] == 51
    assert caster.exp == 8
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

    percent_rolls = iter([100, 10])
    range_rolls = iter([10, 2])

    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(percent_rolls))
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: next(range_rolls))

    result = reg.use(caster, "fireball", target)
    assert result is False
    assert caster.skills["fireball"] == 52
    assert caster.exp == 8
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

    result = reg.use(caster, "acid blast", target)
    assert result == 60
    expected_wait = max(1, skill.lag)
    assert caster.wait == expected_wait
    assert caster.mana == 20
    assert caster.cooldowns.get("acid blast", 0) == skill.cooldown

    with pytest.raises(ValueError) as excinfo:
        reg.use(caster, "acid blast", target)
    assert "recover" in str(excinfo.value)
    assert caster.messages[-1] == "You are still recovering."
    assert caster.mana == 20


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

    assert result == "You hit Orc for 12 damage."
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

    assert result == "Your attack has no effect."
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

    assert result.startswith("You hit Guard for")
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

    assert result.startswith("You hit Ogre for")
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

    assert result == 202
    assert target.hit == 118
    assert caster.wait == max(1, skill.lag)
    assert caster.mana == 25
    assert caster.cooldowns.get("acid breath", None) == 0

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

    assert result == 202
    assert target.hit == 158
    assert bystander.hit == 130
    assert caster.wait == max(1, skill.lag)
    assert caster.mana == skill.mana_cost + 50 - skill.mana_cost
    assert caster.cooldowns.get("fire breath", None) == 0

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
