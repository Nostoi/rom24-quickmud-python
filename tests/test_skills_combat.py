from __future__ import annotations

from collections.abc import Callable

from types import SimpleNamespace

import pytest

from mud.combat import engine as combat_engine
from mud.models import Character
from mud.models.constants import AffectFlag, Position, Sector, WeaponType
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _patch_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    called: dict[str, bool] = {"shield": False, "parry": False, "dodge": False}

    def _make_recorder(name: str) -> Callable[[Character, Character], bool]:
        def _recorder(attacker: Character, victim: Character) -> bool:
            called[name] = True
            return False

        return _recorder

    monkeypatch.setattr(combat_engine, "check_shield_block", _make_recorder("shield"))
    monkeypatch.setattr(combat_engine, "check_parry", _make_recorder("parry"))
    monkeypatch.setattr(combat_engine, "check_dodge", _make_recorder("dodge"))

    return called


def _make_combatant(name: str, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, is_npc=False)
    char.max_hit = 200
    char.hit = 200
    char.position = Position.FIGHTING
    char.messages = []
    return char


def test_kick_bypasses_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> None:
    defenses_called = _patch_weapon_defenses(monkeypatch)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    kicker = _make_combatant("Warrior")
    kicker.skills["kick"] = 75

    victim = _make_combatant("Target", level=25)
    victim.is_npc = True

    result = skill_handlers.kick(kicker, target=victim, success=True, roll=0)

    assert isinstance(result, str)
    assert defenses_called == {"shield": False, "parry": False, "dodge": False}
    assert victim.hit < victim.max_hit


def test_bash_bypasses_weapon_defenses(monkeypatch: pytest.MonkeyPatch) -> None:
    defenses_called = _patch_weapon_defenses(monkeypatch)
    monkeypatch.setattr("mud.config.get_pulse_violence", lambda: 1)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    basher = _make_combatant("Knight")
    basher.skills["bash"] = 65

    victim = _make_combatant("Ogre", level=28)
    victim.is_npc = True

    result = skill_handlers.bash(basher, victim, success=True, chance=100)

    assert isinstance(result, str)
    assert defenses_called == {"shield": False, "parry": False, "dodge": False}
    assert victim.position == Position.RESTING


def test_dirt_kicking_blinds_and_sets_wait_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    room = Room(vnum=1000, sector_type=int(Sector.FIELD))

    kicker = _make_combatant("Scout", level=20)
    kicker.perm_stat = [18, 18, 18, 18, 18]
    kicker.mod_stat = [0] * len(kicker.perm_stat)
    kicker.skills["dirt kicking"] = 75

    target = _make_combatant("Bandit", level=18)
    target.perm_stat = [13, 13, 13, 13, 13]
    target.mod_stat = [0] * len(target.perm_stat)

    room.add_character(kicker)
    room.add_character(target)

    improvements: list[tuple[bool, int]] = []

    def _record_improve(ch: Character, name: str, success: bool, multiplier: int) -> None:
        improvements.append((success, multiplier))

    monkeypatch.setattr(skill_handlers, "check_improve", _record_improve)

    result = skill_handlers.dirt_kicking(kicker, target=target)

    assert result
    assert target.has_affect(AffectFlag.BLIND)
    assert "dirt kicking" in target.spell_effects
    assert kicker.wait == skill_handlers._skill_beats("dirt kicking")
    assert improvements == [(True, 2)]
    assert target.hit < target.max_hit
    assert any("can't see" in message for message in target.messages)


def test_disarm_strips_weapon_and_trains_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 0)

    room = Room(vnum=2000, sector_type=int(Sector.CITY))

    duelist = _make_combatant("Duelist", level=30)
    duelist.perm_stat = [18, 18, 18, 18, 18]
    duelist.mod_stat = [0] * len(duelist.perm_stat)
    duelist.skills.update({"disarm": 85, "hand to hand": 70, "sword": 80})

    mercenary = _make_combatant("Mercenary", level=28)
    mercenary.perm_stat = [14, 14, 14, 14, 14]
    mercenary.mod_stat = [0] * len(mercenary.perm_stat)
    mercenary.skills["sword"] = 60
    mercenary.carry_number = 1

    room.add_character(duelist)
    room.add_character(mercenary)

    prototype = SimpleNamespace(
        name="longsword",
        short_descr="a longsword",
        item_type="weapon",
        value=[int(WeaponType.SWORD), 0, 0, 0],
        level=20,
    )
    weapon = SimpleNamespace(
        prototype=prototype,
        value=[int(WeaponType.SWORD), 0, 0, 0],
        extra_flags=0,
        short_descr="a longsword",
        item_type="weapon",
        wear_loc=16,
        location=None,
    )
    mercenary.equipment["wield"] = weapon

    improvements: list[tuple[bool, int]] = []

    def _record(ch: Character, name: str, success: bool, multiplier: int) -> None:
        improvements.append((success, multiplier))

    monkeypatch.setattr(skill_handlers, "check_improve", _record)

    result = skill_handlers.disarm(duelist, target=mercenary)

    assert result is True
    assert weapon not in mercenary.equipment.values()
    assert weapon in room.contents
    assert improvements == [(True, 1)]
    assert duelist.wait == skill_handlers._skill_beats("disarm")
    assert any("disarms you" in message for message in mercenary.messages)


def test_trip_knocks_target_and_triggers_wait_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mud.config.get_pulse_violence", lambda: 4)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    room = Room(vnum=3000, sector_type=int(Sector.CITY))

    tripper = _make_combatant("Tripper", level=30)
    tripper.size = 2
    tripper.perm_stat = [18, 18, 18, 18, 18]
    tripper.mod_stat = [0] * len(tripper.perm_stat)
    tripper.skills["trip"] = 75

    victim = _make_combatant("Victim", level=25)
    victim.size = 2
    victim.perm_stat = [14, 14, 14, 14, 14]
    victim.mod_stat = [0] * len(victim.perm_stat)

    bystander = _make_combatant("Bystander", level=20)

    room.add_character(tripper)
    room.add_character(victim)
    room.add_character(bystander)

    improvements: list[tuple[bool, int]] = []

    def _record_improve(ch: Character, name: str, success: bool, multiplier: int) -> None:
        improvements.append((success, multiplier))

    monkeypatch.setattr(skill_handlers, "check_improve", _record_improve)

    result = skill_handlers.trip(tripper, target=victim)

    assert isinstance(result, str)
    assert victim.position == Position.RESTING
    assert victim.daze == 8
    assert victim.hit < victim.max_hit
    assert tripper.wait == skill_handlers._skill_beats("trip")
    assert improvements == [(True, 1)]
    assert any("trips you" in message for message in victim.messages)
    assert any("You trip" in message for message in tripper.messages)
    assert any("trips Victim" in message for message in bystander.messages)


def test_trip_checks_flying_and_self_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_percent", lambda: 50)

    room = Room(vnum=3001, sector_type=int(Sector.FIELD))

    tripper = _make_combatant("Acrobat", level=20)
    tripper.size = 2
    tripper.perm_stat = [17, 17, 17, 17, 17]
    tripper.mod_stat = [0] * len(tripper.perm_stat)
    tripper.skills["trip"] = 60

    victim = _make_combatant("Hovering", level=20)
    victim.size = 2
    victim.perm_stat = [15, 15, 15, 15, 15]
    victim.mod_stat = [0] * len(victim.perm_stat)
    victim.add_affect(AffectFlag.FLYING)

    room.add_character(tripper)
    room.add_character(victim)

    improvements: list[tuple[bool, int]] = []

    def _record_improve(ch: Character, name: str, success: bool, multiplier: int) -> None:
        improvements.append((success, multiplier))

    monkeypatch.setattr(skill_handlers, "check_improve", _record_improve)

    blocked = skill_handlers.trip(tripper, target=victim)

    assert blocked == ""
    assert victim.position == Position.FIGHTING
    assert tripper.wait == 0
    assert not improvements
    assert any("feet aren't on the ground" in message for message in tripper.messages)

    tripper.messages.clear()

    slip = skill_handlers.trip(tripper, target=tripper)

    assert slip == ""
    assert tripper.wait == skill_handlers._skill_beats("trip") * 2
    assert any("fall flat" in message for message in tripper.messages)
