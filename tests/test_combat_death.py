from __future__ import annotations

import pytest

from mud.combat.death import death_cry, raw_kill
from mud.combat.engine import attack_round
from mud.combat.kill_table import get_kill_data, reset_kill_table
from mud.groups import xp as xp_module
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import (
    AffectFlag,
    ExtraFlag,
    FormFlag,
    ItemType,
    PartFlag,
    PlayerFlag,
    Position,
    MAX_LEVEL,
    ROOM_VNUM_ALTAR,
    Stat,
    WearLocation,
    OBJ_VNUM_GUTS,
)
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.utils import rng_mm
from mud.wiznet import WiznetFlag
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def reset_characters() -> None:
    character_registry.clear()
    yield
    character_registry.clear()


@pytest.fixture(autouse=True)
def reset_kill_stats() -> None:
    reset_kill_table()
    yield
    reset_kill_table()


def _ensure_world() -> None:
    initialize_world("area/area.lst")


def _make_victim(name: str, room, *, level: int = 10, hit_points: int = 5, gold: int = 0, silver: int = 0) -> Character:
    victim = Character(name=name, is_npc=True, level=level)
    victim.hit = hit_points
    victim.max_hit = hit_points
    victim.gold = gold
    victim.silver = silver
    room.add_character(victim)
    return victim


def _add_loot(victim: Character, vnum: int, short_descr: str) -> Object:
    proto = ObjIndex(vnum=vnum, short_descr=short_descr)
    loot = Object(instance_id=None, prototype=proto)
    victim.add_object(loot)
    return loot


def test_death_cry_spawns_gore_and_notifies_neighbors(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    room = attacker.room
    assert room is not None

    neighbor_room = None
    for exit_data in room.exits:
        if exit_data and exit_data.to_room is not None:
            neighbor_room = exit_data.to_room
            break
    assert neighbor_room is not None

    observer = create_test_character("Observer", room.vnum)
    observer.messages = []
    neighbor = create_test_character("Neighbor", neighbor_room.vnum)
    neighbor.messages = []

    victim = _make_victim("Victim", room)
    victim.parts = int(PartFlag.GUTS)
    victim.form = int(FormFlag.EDIBLE)

    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 2)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: high)

    existing_objects = {id(obj) for obj in room.contents}

    death_cry(victim)

    new_objects = [obj for obj in room.contents if id(obj) not in existing_objects]
    gore = next(obj for obj in new_objects if getattr(obj.prototype, "vnum", None) == OBJ_VNUM_GUTS)

    assert gore.timer == 7
    assert gore.short_descr is not None and "Victim" in gore.short_descr
    assert any("guts" in message for message in observer.messages)
    assert any("death cry" in message for message in neighbor.messages)


def test_raw_kill_awards_group_xp_and_creates_corpse(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    ally = create_test_character("Ally", 3001)
    ally.leader = attacker
    room = attacker.room
    assert room is not None

    victim = _make_victim("Victim", room, gold=12, silver=3, hit_points=1)
    loot = _add_loot(victim, 6000, "a battered trinket")

    attacker.level = 10
    attacker.hitroll = 100
    attacker.damroll = 12
    ally.level = 10

    calls: list[tuple[Character, int]] = []

    def fake_xp_compute(gch: Character, vic: Character, total_levels: int) -> int:
        calls.append((gch, total_levels))
        return 100

    monkeypatch.setattr(xp_module, "xp_compute", fake_xp_compute)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)

    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    existing_ids = {id(obj) for obj in room.contents}

    attack_round(attacker, victim)

    assert victim not in room.people

    new_objects = [obj for obj in room.contents if id(obj) not in existing_ids]
    corpse_candidates = [obj for obj in new_objects if getattr(obj, "item_type", None) == int(ItemType.CORPSE_NPC)]
    assert len(corpse_candidates) == 1
    corpse = corpse_candidates[0]
    assert corpse.gold == 12
    assert corpse.silver == 3
    assert loot in corpse.contained_items

    assert attacker.exp == 100
    assert ally.exp == 100
    assert any(msg == "You receive 100 experience points." for msg in attacker.messages)
    assert any(msg == "You receive 100 experience points." for msg in ally.messages)
    assert len(calls) == 2
    assert {id(gch) for gch, _ in calls} == {id(attacker), id(ally)}


def test_auto_flags_trigger_and_wiznet_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOLOOT | PlayerFlag.AUTOGOLD | PlayerFlag.AUTOSAC)
    attacker.hitroll = 100
    attacker.damroll = 10
    room = attacker.room
    assert room is not None

    victim = _make_victim("Victim", room, gold=7, silver=4, hit_points=1)
    loot = _add_loot(victim, 6001, "a gleaming idol")

    immortal = Character(name="Immortal", is_npc=False)
    immortal.is_admin = True
    immortal.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_MOBDEATHS)
    immortal.messages = []
    character_registry.append(immortal)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)

    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    existing_ids = {id(obj) for obj in room.contents}

    attack_round(attacker, victim)
    assert loot in attacker.inventory
    assert attacker.gold == 7
    assert attacker.silver == 4

    new_objects = [obj for obj in room.contents if id(obj) not in existing_ids]
    corpse = next(obj for obj in new_objects if getattr(obj, "item_type", None) == int(ItemType.CORPSE_NPC))
    assert corpse.gold == 0
    assert corpse.silver == 0
    assert corpse.contained_items == []

    assert any("got toasted by Attacker" in message for message in immortal.messages)
    assert any("quickly gather" in message for message in attacker.messages)


def test_raw_kill_updates_kill_counters() -> None:
    _ensure_world()
    hunter = create_test_character("Hunter", 3001)
    room = hunter.room
    assert room is not None

    prototype = MobIndex(vnum=99991, short_descr="prototype foe", level=12)
    prototype.killed = 0

    victim = Character(name="Prototype Foe", is_npc=True, level=12)
    victim.prototype = prototype
    room.add_character(victim)

    corpse = raw_kill(victim)

    assert corpse is not None
    assert prototype.killed == 1
    assert get_kill_data(12).killed == 1
    assert victim not in room.people

    second = Character(name="Prototype Foe", is_npc=True, level=MAX_LEVEL + 7)
    second.prototype = prototype
    room.add_character(second)

    raw_kill(second)

    assert prototype.killed == 2
    assert get_kill_data(12).killed == 1
    assert get_kill_data(MAX_LEVEL - 1).killed == 1
    assert second not in room.people


def test_group_gain_zaps_anti_alignment_items(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    room = attacker.room
    assert room is not None

    observer = create_test_character("Observer", room.vnum)
    observer.messages = []

    victim = _make_victim("Victim", room)
    attacker.level = 10
    attacker.alignment = -400
    attacker.messages = []

    proto = ObjIndex(vnum=9000, short_descr="a holy talisman")
    amulet = Object(instance_id=None, prototype=proto)
    amulet.extra_flags = int(ExtraFlag.ANTI_EVIL)
    attacker.equip_object(amulet, "neck")

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 25)

    xp_module.group_gain(attacker, victim)

    assert amulet not in attacker.equipment.values()
    assert amulet in room.contents
    assert amulet.wear_loc == int(WearLocation.NONE)
    assert any("You are zapped by" in message for message in attacker.messages)
    assert any("is zapped by" in message for message in observer.messages)


def test_player_kill_clears_pk_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Victim", 3001)
    victim.act = int(PlayerFlag.KILLER)
    victim.hit = 1
    victim.max_hit = 1

    attacker.hitroll = 100
    attacker.damroll = 10

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)

    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)
    assert victim.act & int(PlayerFlag.KILLER) == 0
    assert victim.position == Position.RESTING
    assert victim.hit >= 1
    assert victim.room is not None
    assert victim.room.vnum == ROOM_VNUM_ALTAR


def test_player_kill_resets_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Victim", 3001)

    attacker.hitroll = 100
    attacker.damroll = 10

    victim.race = 2  # elf -> default INFRARED affect
    victim.hit = 1
    victim.max_hit = 1
    victim.mana = 0
    victim.move = 0
    victim.clan = 2  # rom clan hall
    victim.hitroll = 0
    victim.damroll = 0
    victim.saving_throw = 0
    victim.mod_stat = [0, 0, 0, 0, 0]
    victim.add_affect(AffectFlag.POISON)
    victim.armor = [25, 25, 25, 25]

    effect = SpellEffect(
        name="sanctuary",
        duration=10,
        level=40,
        hitroll_mod=5,
        damroll_mod=3,
        saving_throw_mod=-2,
        affect_flag=AffectFlag.SANCTUARY,
        stat_modifiers={Stat.STR: 2},
    )
    victim.apply_spell_effect(effect)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)

    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    assert victim.spell_effects == {}
    assert victim.affected_by == int(AffectFlag.INFRARED)
    assert victim.hitroll == 0
    assert victim.damroll == 0
    assert victim.saving_throw == 0
    assert victim.mod_stat[Stat.STR] == 0
    assert victim.armor == [100, 100, 100, 100]
    assert victim.position == Position.RESTING
    assert victim.hit == 1
    assert victim.mana == 1
    assert victim.move == 1
    assert victim.fighting is None
    assert victim.room is not None
    assert victim.room.vnum == ROOM_VNUM_ALTAR
