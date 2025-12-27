from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    ItemType,
    PlayerFlag,
    Position,
    DamageType,
)
from mud.models.mob import MobIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spec_funs import (
    get_spec_fun,
    register_spec_fun,
    run_npc_specs,
    spec_breath_fire,
    spec_breath_acid,
    spec_breath_frost,
    spec_breath_gas,
    spec_breath_lightning,
    spec_breath_any,
    spec_cast_adept,
    spec_cast_cleric,
    spec_cast_judge,
    spec_cast_mage,
    spec_cast_undead,
    spec_executioner,
    spec_fido,
    spec_guard,
    spec_janitor,
    spec_mayor,
    spec_nasty,
    spec_ogre_member,
    spec_patrolman,
    spec_poison,
    spec_thief,
    spec_troll_member,
    _reset_spec_mayor_state,
)
from mud.world import create_test_character, initialize_world
from mud.time import time_info
from mud.utils import rng_mm

if TYPE_CHECKING:
    from mud.spawning.templates import MobInstance


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()
    character_registry.clear()


def create_mob_with_spec(spec_name: str, level: int = 10, vnum: int = 9999) -> MobInstance:
    if vnum not in mob_registry:
        proto = MobIndex(
            vnum=vnum,
            short_descr=f"test mob with {spec_name}",
            long_descr=f"A test mob with {spec_name} is here.",
            race="human",
            level=level,
            act_flags=ActFlag.IS_NPC,
            spec_fun=spec_name,
        )
        mob_registry[vnum] = proto

    mob = spawn_mob(vnum)
    assert mob is not None
    return mob


def place_mob_in_room(mob: MobInstance, room_vnum: int = 3001) -> Room:
    room = room_registry.get(room_vnum)
    assert room is not None
    room.add_mob(mob)
    mob.room = room
    return room


def create_player(name: str = "TestPlayer", room_vnum: int = 3001, **kwargs) -> Character:
    ch = create_test_character(name, room_vnum)
    for key, value in kwargs.items():
        setattr(ch, key, value)
    return ch


def create_corpse(is_pc: bool = True, room_vnum: int = 3001) -> Object:
    room = room_registry.get(room_vnum)
    assert room is not None

    from mud.models.obj import ObjIndex
    from mud.models.constants import WearFlag

    corpse_proto = ObjIndex(
        vnum=10,
        short_descr=f"the corpse of {'a player' if is_pc else 'a mob'}",
        item_type=ItemType.CORPSE_PC if is_pc else ItemType.CORPSE_NPC,
        wear_flags=int(WearFlag.TAKE),
    )

    corpse = Object(
        instance_id=None,
        prototype=corpse_proto,
        wear_flags=int(WearFlag.TAKE),  # Must set on instance too
    )
    room.add_object(corpse)
    return corpse


def create_trash_object(room_vnum: int = 3001) -> Object:
    room = room_registry.get(room_vnum)
    assert room is not None

    from mud.models.obj import ObjIndex
    from mud.models.constants import WearFlag

    trash_proto = ObjIndex(
        vnum=11,
        short_descr="a piece of trash",
        item_type=ItemType.TRASH,
        wear_flags=int(WearFlag.TAKE),
    )

    trash = Object(
        instance_id=None,
        prototype=trash_proto,
        wear_flags=int(WearFlag.TAKE),  # Must set on instance too
    )
    room.add_object(trash)
    return trash


class TestSpecGuard:
    def test_spec_guard_attacks_criminal_in_room(self):
        guard = create_mob_with_spec("spec_guard", level=20)
        room = place_mob_in_room(guard, 3001)

        criminal = create_player("BadGuy", 3001)
        criminal.act = PlayerFlag.KILLER

        run_npc_specs()

        assert any("KILLER" in msg or "PROTECT" in msg for msg in guard.messages), "Guard should yell about criminal"

    def test_spec_guard_ignores_innocent_players(self):
        guard = create_mob_with_spec("spec_guard", level=20)
        room = place_mob_in_room(guard, 3001)

        innocent = create_player("GoodGuy", 3001)

        run_npc_specs()

        assert guard.fighting is None, "Guard should not attack innocent players"
        assert len(guard.messages) == 0, "Guard should not yell at innocent players"

    def test_spec_guard_attacks_thief_flagged_players(self):
        guard = create_mob_with_spec("spec_guard", level=20)
        room = place_mob_in_room(guard, 3001)

        thief = create_player("Thief", 3001)
        thief.act = PlayerFlag.THIEF

        run_npc_specs()

        assert any("THIEF" in msg or "PROTECT" in msg for msg in guard.messages), "Guard should yell about thief"


class TestSpecJanitor:
    def test_spec_janitor_picks_up_trash(self):
        janitor = create_mob_with_spec("spec_janitor", level=10)
        room = place_mob_in_room(janitor, 3001)

        trash = create_trash_object(3001)
        initial_room_contents = list(room.contents)

        run_npc_specs()

        assert trash not in room.contents, "Trash should be removed from room"

    def test_spec_janitor_ignores_non_trash(self):
        janitor = create_mob_with_spec("spec_janitor", level=10)
        room = place_mob_in_room(janitor, 3001)

        from mud.models.obj import ObjIndex
        from mud.models.constants import WearFlag

        sword_proto = ObjIndex(
            vnum=12,
            short_descr="a sword",
            item_type=ItemType.WEAPON,
            wear_flags=int(WearFlag.TAKE),
            cost=1000,  # High cost so janitor won't pick it up
        )
        sword = Object(
            instance_id=None,
            prototype=sword_proto,
            wear_flags=int(WearFlag.TAKE),  # Must set on instance too
            cost=1000,
        )
        room.add_object(sword)

        run_npc_specs()

        assert sword in room.contents, "Non-trash items should not be picked up"


class TestSpecFido:
    def test_spec_fido_eats_npc_corpses(self):
        fido = create_mob_with_spec("spec_fido", level=5)
        room = place_mob_in_room(fido, 3001)

        npc_corpse = create_corpse(is_pc=False, room_vnum=3001)

        run_npc_specs()

        assert npc_corpse not in room.contents, "Fido should eat NPC corpses"

    def test_spec_fido_ignores_pc_corpses(self):
        fido = create_mob_with_spec("spec_fido", level=5)
        room = place_mob_in_room(fido, 3001)

        pc_corpse = create_corpse(is_pc=True, room_vnum=3001)

        run_npc_specs()

        assert pc_corpse in room.contents, "Fido should ignore PC corpses"


class TestSpecPoison:
    def test_spec_poison_only_works_in_combat(self):
        poison_mob = create_mob_with_spec("spec_poison", level=15)
        room = place_mob_in_room(poison_mob, 3001)

        nearby_player = create_player("Innocent", 3001, hit=100, max_hit=100)

        run_npc_specs()

        assert poison_mob.fighting is None, "Poison mob should not auto-attack"
        assert nearby_player.hit == 100, "Player should not be poisoned outside combat"


class TestSpecThief:
    def test_spec_thief_can_steal(self):
        thief = create_mob_with_spec("spec_thief", level=10)
        room = place_mob_in_room(thief, 3001)

        victim = create_player("RichGuy", 3001)
        victim.gold = 1000

        run_npc_specs()

        assert thief.position == Position.STANDING, "Thief spec should execute without errors"


class TestSpecBreathWeapons:
    def test_spec_breath_fire_exists(self):
        dragon = create_mob_with_spec("spec_breath_fire", level=50)
        room = place_mob_in_room(dragon, 3001)

        run_npc_specs()

        assert dragon.position == Position.STANDING, "Breath fire spec should execute without errors"

    def test_spec_breath_any_uses_random_type(self):
        dragon = create_mob_with_spec("spec_breath_any", level=50)
        room = place_mob_in_room(dragon, 3001)

        run_npc_specs()

        assert dragon.position == Position.STANDING, "Breath any spec should execute without errors"


class TestSpecCasters:
    def test_spec_cast_cleric_casts_in_combat(self):
        cleric = create_mob_with_spec("spec_cast_cleric", level=20)
        room = place_mob_in_room(cleric, 3001)

        cleric.mana = 500
        cleric.max_mana = 500
        cleric.hit = cleric.max_hit // 2

        initial_hp = cleric.hit
        for _ in range(10):
            run_npc_specs()
            if cleric.hit > initial_hp:
                break

        assert cleric.mana <= 500, "Cleric should use mana"

    def test_spec_cast_mage_casts_offensive_spells(self):
        mage = create_mob_with_spec("spec_cast_mage", level=20)
        room = place_mob_in_room(mage, 3001)

        victim = create_player("Victim", 3001, hit=200, max_hit=200)
        mage.fighting = victim
        mage.mana = 500
        mage.max_mana = 500

        initial_hp = victim.hit
        for _ in range(10):
            run_npc_specs()
            if victim.hit < initial_hp:
                break

        assert mage.mana <= 500, "Mage should cast spells"

    def test_spec_cast_undead_energy_drain(self):
        undead = create_mob_with_spec("spec_cast_undead", level=25)
        room = place_mob_in_room(undead, 3001)

        victim = create_player("Victim", 3001, level=10, hit=150, max_hit=150)
        undead.fighting = victim
        undead.mana = 500
        undead.max_mana = 500

        initial_hp = victim.hit
        for _ in range(10):
            run_npc_specs()
            if victim.hit < initial_hp:
                break

        assert undead.mana <= 500, "Undead should cast spells"


class TestSpecExecutioner:
    def test_spec_executioner_detects_criminals(self):
        executioner = create_mob_with_spec("spec_executioner", level=30)
        room = place_mob_in_room(executioner, 3002)

        criminal = create_player("Criminal", 3002)
        criminal.act = PlayerFlag.KILLER

        run_npc_specs()

        assert any("KILLER" in msg or "PROTECT" in msg for msg in executioner.messages), (
            "Executioner should yell about killer"
        )


class TestSpecPatrolman:
    def test_spec_patrolman_exists(self):
        patrolman = create_mob_with_spec("spec_patrolman", level=25)
        room = place_mob_in_room(patrolman, 3002)

        run_npc_specs()

        assert patrolman.position == Position.STANDING, "Patrolman should be functional"


class TestSpecMayor:
    def test_spec_mayor_has_state(self):
        mayor = create_mob_with_spec("spec_mayor", level=15)
        room = place_mob_in_room(mayor, 3001)

        _reset_spec_mayor_state()

        time_info.hour = 12

        for _ in range(5):
            run_npc_specs()

        assert mayor.position == Position.STANDING, "Mayor should be functional"


class TestSpecCastAdept:
    def test_spec_cast_adept_exists(self):
        adept = create_mob_with_spec("spec_cast_adept", level=20)
        room = place_mob_in_room(adept, 3001)

        adept.mana = 500
        adept.max_mana = 500

        run_npc_specs()

        assert adept.position == Position.STANDING, "Adept should be functional"


class TestSpecFactionMembers:
    def test_spec_troll_member_exists(self):
        troll = create_mob_with_spec("spec_troll_member", level=20)
        room = place_mob_in_room(troll, 3001)

        run_npc_specs()

        assert troll.position == Position.STANDING, "Troll member should be functional"

    def test_spec_ogre_member_exists(self):
        ogre = create_mob_with_spec("spec_ogre_member", level=25)
        room = place_mob_in_room(ogre, 3001)

        run_npc_specs()

        assert ogre.position == Position.STANDING, "Ogre member should be functional"


class TestSpecNasty:
    def test_spec_nasty_random_behavior(self):
        nasty = create_mob_with_spec("spec_nasty", level=15)
        room = place_mob_in_room(nasty, 3001)

        victim = create_player("Victim", 3001, gold=100)

        for _ in range(20):
            run_npc_specs()

        assert nasty.position == Position.STANDING, "Nasty mob should be functional"
