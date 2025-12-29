from __future__ import annotations

import pytest

from mud.combat.death import death_cry, raw_kill
from mud.combat.engine import attack_round
from mud.combat.kill_table import get_kill_data, reset_kill_table
from mud.advancement import exp_per_level
from mud.characters.follow import add_follower
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
    OBJ_VNUM_CORPSE_NPC,
    RoomFlag,
    Stat,
    WearLocation,
    WearFlag,
    OBJ_VNUM_GUTS,
)
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex, object_registry
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

    base_attacker_exp = exp_per_level(attacker)
    base_ally_exp = exp_per_level(ally)
    attacker.exp = base_attacker_exp
    ally.exp = base_ally_exp

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

    assert attacker.exp == base_attacker_exp + 100
    assert ally.exp == base_ally_exp + 100
    assert any(msg == "You receive 100 experience points." for msg in attacker.messages)
    assert any(msg == "You receive 100 experience points." for msg in ally.messages)
    assert len(calls) == 2
    assert {id(gch) for gch, _ in calls} == {id(attacker), id(ally)}


def test_auto_flags_trigger_and_wiznet_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOLOOT | PlayerFlag.AUTOGOLD)
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


def test_autosacrifice_removes_empty_corpse(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOLOOT | PlayerFlag.AUTOGOLD | PlayerFlag.AUTOSAC)
    attacker.hitroll = 100
    attacker.damroll = 12
    attacker.messages = []

    room = attacker.room
    assert room is not None

    observer = create_test_character("Observer", room.vnum)
    observer.messages = []

    immortal = Character(name="Immortal", is_npc=False)
    immortal.is_admin = True
    immortal.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SACCING)
    immortal.messages = []
    character_registry.append(immortal)

    victim = _make_victim("Victim", room, level=7, hit_points=1)
    _add_loot(victim, 6002, "a sacrificial token")

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    assert all(getattr(obj, "item_type", None) != int(ItemType.CORPSE_NPC) for obj in room.contents)

    expected_reward = max(1, victim.level * 3)
    assert attacker.silver == expected_reward
    assert any("Mota gives" in message for message in attacker.messages)
    assert any("sacrifices" in message for message in observer.messages)
    assert any("burnt offering" in message for message in immortal.messages)


def test_autosacrifice_autosplit_shares_silver(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    leader = create_test_character("Leader", 3001)
    leader.act = int(PlayerFlag.AUTOLOOT | PlayerFlag.AUTOSAC | PlayerFlag.AUTOSPLIT)
    leader.hitroll = 100
    leader.damroll = 12
    leader.messages = []
    leader.silver = 0

    room = leader.room
    assert room is not None

    ally = create_test_character("Ally", room.vnum)
    ally.leader = leader
    ally.messages = []
    ally.silver = 0

    victim = _make_victim("Victim", room, level=7, hit_points=1)
    _add_loot(victim, 6003, "a shared trinket")

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(leader, victim)

    expected_share = (7 * 3) // 2
    expected_remainder = (7 * 3) % 2

    assert leader.silver == expected_share + expected_remainder
    assert ally.silver == expected_share
    assert any("You split 21 silver coins." in msg for msg in leader.messages)
    assert any("Your share is 10 silver" in msg for msg in ally.messages)


def test_autosacrifice_autosplit_solo_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOSAC | PlayerFlag.AUTOSPLIT)
    attacker.hitroll = 100
    attacker.damroll = 12
    attacker.messages = []

    room = attacker.room
    assert room is not None

    victim = _make_victim("Victim", room, level=5, hit_points=1)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    assert any(message == "Just keep it all." for message in attacker.messages)


def test_autosacrifice_requires_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOSAC)
    attacker.hitroll = 100
    attacker.damroll = 12
    attacker.messages = []

    room = attacker.room
    assert room is not None
    room.room_flags |= int(RoomFlag.ROOM_DARK)
    room.light = 0

    victim = _make_victim("Victim", room, level=5, hit_points=1)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    corpses = [obj for obj in room.contents if getattr(obj, "item_type", None) == int(ItemType.CORPSE_NPC)]
    assert corpses, "corpse should remain when attacker cannot see it"
    assert attacker.silver == 0
    assert all("Mota gives" not in message for message in attacker.messages)


def test_autosacrifice_skips_no_sac_corpse(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOSAC)
    attacker.hitroll = 100
    attacker.damroll = 12
    attacker.messages = []

    room = attacker.room
    assert room is not None

    proto = ObjIndex(vnum=OBJ_VNUM_CORPSE_NPC, short_descr="a blocked corpse")
    proto.description = "The corpse of %s is lying here."
    blocked_corpse = Object(instance_id=None, prototype=proto)
    blocked_corpse.item_type = int(ItemType.CORPSE_NPC)
    blocked_corpse.wear_flags = int(WearFlag.TAKE | WearFlag.NO_SAC)
    blocked_corpse.contained_items = []

    monkeypatch.setattr("mud.combat.death.spawn_object", lambda vnum: blocked_corpse)
    victim = _make_victim("Victim", room, level=6, hit_points=1)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    assert blocked_corpse in room.contents
    assert attacker.silver == 0
    assert all("Mota gives" not in message for message in attacker.messages)


def test_autosacrifice_extracts_corpse(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    attacker.act = int(PlayerFlag.AUTOSAC)
    attacker.hitroll = 100
    attacker.damroll = 12

    room = attacker.room
    assert room is not None

    victim = _make_victim("Victim", room, level=5, hit_points=1)

    captured: dict[str, Object] = {}

    import mud.combat.death as death_module

    original_make_corpse = death_module.make_corpse

    def capture_make_corpse(*args, **kwargs):
        corpse = original_make_corpse(*args, **kwargs)
        captured["corpse"] = corpse
        return corpse

    monkeypatch.setattr(death_module, "make_corpse", capture_make_corpse)

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)
    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    corpse = captured.get("corpse")
    assert corpse is not None

    assert corpse not in object_registry
    assert getattr(corpse, "location", None) is None
    assert not getattr(corpse, "contained_items", [])


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


def test_make_corpse_sets_consumable_timers(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    anchor = create_test_character("Anchor", 3001)
    room = anchor.room
    assert room is not None

    victim = _make_victim("Victim", room, hit_points=1)

    potion_proto = ObjIndex(vnum=7100, short_descr="a shimmering potion", description="A shimmering potion lies here.")
    potion = Object(instance_id=None, prototype=potion_proto)
    potion.item_type = int(ItemType.POTION)
    potion.extra_flags = int(ExtraFlag.VIS_DEATH)
    victim.add_object(potion)

    scroll_proto = ObjIndex(vnum=7101, short_descr="an ancient scroll", description="An ancient scroll rests here.")
    scroll = Object(instance_id=None, prototype=scroll_proto)
    scroll.item_type = int(ItemType.SCROLL)
    scroll.extra_flags = int(ExtraFlag.VIS_DEATH)
    victim.add_object(scroll)

    def fake_number_range(low: int, high: int) -> int:
        if (low, high) == (3, 6):
            return 6
        if (low, high) == (25, 40):
            return 40
        if (low, high) == (500, 1000):
            return 600
        if (low, high) == (1000, 2500):
            return 1200
        return high

    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 0)
    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    corpse = raw_kill(victim)

    assert corpse is not None
    assert corpse.short_descr is not None and "Victim" in corpse.short_descr

    potion_in_corpse = next(obj for obj in corpse.contained_items if obj is potion)
    scroll_in_corpse = next(obj for obj in corpse.contained_items if obj is scroll)

    assert potion_in_corpse.timer == 600
    assert scroll_in_corpse.timer == 1200
    assert int(potion_in_corpse.extra_flags) & int(ExtraFlag.VIS_DEATH) == 0
    assert int(scroll_in_corpse.extra_flags) & int(ExtraFlag.VIS_DEATH) == 0


def test_make_corpse_strips_rot_death_and_drops_floating(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    anchor = create_test_character("Anchor", 3001)
    room = anchor.room
    assert room is not None

    prototype = MobIndex(vnum=99991, short_descr="prototype foe", level=12)
    prototype.killed = 0

    victim = _make_victim("Victim", room, hit_points=1)
    victim.prototype = prototype
    victim.level = 12

    floating_proto = ObjIndex(vnum=7200, short_descr="a drifting relic", description="A drifting relic hums here.")
    floating = Object(instance_id=None, prototype=floating_proto)
    floating.item_type = int(ItemType.CONTAINER)
    floating.extra_flags = int(ExtraFlag.ROT_DEATH | ExtraFlag.VIS_DEATH)
    floating.wear_loc = int(WearLocation.FLOAT)

    gem_proto = ObjIndex(vnum=7201, short_descr="a gleaming gem", description="A gleaming gem sparkles here.")
    gem = Object(instance_id=None, prototype=gem_proto)
    gem.item_type = int(ItemType.GEM)
    gem.location = floating
    floating.contained_items.append(gem)

    victim.equip_object(floating, "floating")

    ground_proto = ObjIndex(vnum=7202, short_descr="a cursed idol", description="A cursed idol rests here.")
    ground_item = Object(instance_id=None, prototype=ground_proto)
    ground_item.item_type = int(ItemType.TREASURE)
    ground_item.extra_flags = int(ExtraFlag.ROT_DEATH | ExtraFlag.VIS_DEATH)
    victim.add_object(ground_item)

    def fake_number_range(low: int, high: int) -> int:
        if (low, high) == (3, 6):
            return 6
        if (low, high) == (5, 10):
            return 7
        return high

    monkeypatch.setattr(rng_mm, "number_bits", lambda bits: 0)
    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    corpse = raw_kill(victim)

    assert corpse is not None

    assert ground_item in corpse.contained_items
    assert ground_item.timer == 7
    assert int(ground_item.extra_flags) & int(ExtraFlag.ROT_DEATH) == 0
    assert int(ground_item.extra_flags) & int(ExtraFlag.VIS_DEATH) == 0

    assert floating not in corpse.contained_items
    assert floating not in room.contents
    assert gem in room.contents
    assert getattr(gem, "location", None) is room

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


def test_player_death_dismisses_pet(monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_world()
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Victim", 3001)
    observer = create_test_character("Observer", 3001)
    room = attacker.room
    assert room is not None

    attacker.hitroll = 100
    attacker.damroll = 10
    victim.hit = 1
    victim.max_hit = 1

    pet = Character(name="Loyal Pet", is_npc=True)
    pet.messages = []
    room.add_character(pet)
    character_registry.append(pet)
    add_follower(pet, victim)
    victim.pet = pet

    observer.messages = []

    monkeypatch.setattr(xp_module, "xp_compute", lambda *args, **kwargs: 0)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: high)
    monkeypatch.setattr("mud.combat.engine.calculate_weapon_damage", lambda *args, **kwargs: 50)

    monkeypatch.setattr("mud.combat.engine.check_parry", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_dodge", lambda *args, **kwargs: False)
    monkeypatch.setattr("mud.combat.engine.check_shield_block", lambda *args, **kwargs: False)

    attack_round(attacker, victim)

    assert victim.pet is None
    assert pet.master is None
    assert pet not in room.people
    assert getattr(pet, "room", None) is None
    assert pet not in character_registry
    assert any("slowly fades away" in message.lower() for message in observer.messages)


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


def test_corpse_looting_owner_can_loot_own_corpse(movable_char_factory) -> None:
    """Test that owner can loot their own corpse (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    ch = movable_char_factory("Owner", 3001)
    room = ch.room

    proto = ObjIndex(vnum=11, short_descr="corpse of Owner")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=ch.name, short_descr="corpse of Owner"
    )
    room.add_object(corpse)

    result = do_get(ch, "corpse")
    assert "You pick up" in result


def test_corpse_looting_non_owner_cannot_loot(movable_char_factory) -> None:
    """Test that non-owner cannot loot someone else's corpse (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    owner = movable_char_factory("Owner", 3001)
    thief = movable_char_factory("Thief", 3001)
    room = owner.room

    owner.group = None
    thief.group = None

    proto = ObjIndex(vnum=11, short_descr="corpse of Owner")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=owner.name, short_descr="corpse of Owner"
    )
    room.add_object(corpse)

    result = do_get(thief, "corpse")
    assert "You cannot loot that corpse" in result


def test_corpse_looting_group_member_can_loot(movable_char_factory) -> None:
    """Test that group members can loot each other's corpses (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    owner = movable_char_factory("Owner", 3001)
    friend = movable_char_factory("Friend", 3001)
    room = owner.room

    owner.group = 1
    friend.group = 1

    proto = ObjIndex(vnum=11, short_descr="corpse of Owner")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=owner.name, short_descr="corpse of Owner"
    )
    room.add_object(corpse)

    result = do_get(friend, "corpse")
    assert "You pick up" in result


def test_corpse_looting_canloot_flag_allows_looting(movable_char_factory) -> None:
    """Test that PLR_CANLOOT flag allows anyone to loot (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    owner = movable_char_factory("Owner", 3001)
    thief = movable_char_factory("Thief", 3001)
    room = owner.room

    owner.act |= int(PlayerFlag.CANLOOT)

    proto = ObjIndex(vnum=11, short_descr="corpse of Owner")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=owner.name, short_descr="corpse of Owner"
    )
    room.add_object(corpse)

    result = do_get(thief, "corpse")
    assert "You pick up" in result


def test_corpse_looting_no_owner_allows_looting(movable_char_factory) -> None:
    """Test that corpses without owner can be looted by anyone (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    ch = movable_char_factory("Anyone", 3001)
    room = ch.room

    proto = ObjIndex(vnum=11, short_descr="corpse of Someone")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=None, short_descr="corpse of Someone"
    )
    room.add_object(corpse)

    result = do_get(ch, "corpse")
    assert "You pick up" in result


def test_corpse_looting_npc_corpse_always_lootable(movable_char_factory) -> None:
    """Test that NPC corpses are always lootable (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    ch = movable_char_factory("Player", 3001)
    room = ch.room

    proto = ObjIndex(vnum=10, short_descr="corpse of an orc")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_NPC), pIndexData=proto, owner="Someone", short_descr="corpse of an orc"
    )
    room.add_object(corpse)

    result = do_get(ch, "corpse")
    assert "You pick up" in result


def test_corpse_looting_immortal_can_loot_anything(movable_char_factory) -> None:
    """Test that immortals can loot any corpse (ROM src/act_obj.c:61-89)."""
    from mud.commands.inventory import do_get
    from mud.models.obj import ObjectData, ObjIndex

    _ensure_world()
    owner = movable_char_factory("Owner", 3001)
    immortal = movable_char_factory("Immortal", 3001)
    room = owner.room

    immortal.is_immortal = lambda: True

    proto = ObjIndex(vnum=11, short_descr="corpse of Owner")
    corpse = ObjectData(
        item_type=int(ItemType.CORPSE_PC), pIndexData=proto, owner=owner.name, short_descr="corpse of Owner"
    )
    room.add_object(corpse)

    result = do_get(immortal, "corpse")
    assert "You pick up" in result
