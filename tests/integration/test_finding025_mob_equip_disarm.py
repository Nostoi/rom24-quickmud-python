"""FINDING-025 — mob equipment uses ROM carry-list + wear_loc semantics."""

from __future__ import annotations

from unittest.mock import patch

from mud.combat.engine import get_wielded_weapon
from mud.models.constants import ExtraFlag, ItemType, WeaponType, WearLocation
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills import handlers as skill_handlers
from mud.spawning.templates import MobInstance


def _weapon(object_factory, vnum: int, name: str):
    obj = object_factory(
        {
            "vnum": vnum,
            "name": name,
            "short_descr": f"a {name}",
            "item_type": int(ItemType.WEAPON),
            "value": [int(WeaponType.SWORD), 1, 6, 0, 0],
        }
    )
    obj.extra_flags = 0
    return obj


def _mob(room: Room) -> MobInstance:
    mob = MobInstance(
        name="mob",
        level=1,
        current_hp=100,
        max_hit=100,
        prototype=MobIndex(vnum=3001, short_descr="a mob"),
        room=room,
        perm_stat=[25, 0, 0, 0, 0],
    )
    room.people.append(mob)
    return mob


def test_get_wielded_weapon_finds_mob_wear_loc_inventory(object_factory):
    """ROM src/handler.c:1733 get_eq_char scans ch->carrying for wear_loc."""

    room = Room(vnum=3001, name="Test Room", description="A test room")
    room_registry[3001] = room
    mob = _mob(room)
    sword = _weapon(object_factory, 2601, "reset sword")

    mob.equip(sword, int(WearLocation.WIELD))

    assert get_wielded_weapon(mob) is sword


def test_disarm_mob_equip_weapon_auto_gets_back_to_inventory(
    movable_char_factory,
    object_factory,
):
    """ROM src/fight.c:2257-2265 makes disarmed NPCs get visible weapons back."""

    attacker = movable_char_factory("warrior", 3001)
    attacker.skills["disarm"] = 100
    attacker.level = 20
    attacker.perm_stat = [0, 0, 0, 25, 0]
    attacker.mod_stat = [0, 0, 0, 0, 0]
    attacker.equip_object(_weapon(object_factory, 2602, "attacker sword"), int(WearLocation.WIELD))

    room = attacker.room
    assert room is not None
    room_registry[3001] = room
    victim = _mob(room)

    shield = _weapon(object_factory, 2603, "practice blade")
    victim.add_to_inventory(shield)
    victim_weapon = _weapon(object_factory, 2604, "reset sword")
    victim.equip(victim_weapon, int(WearLocation.WIELD))
    attacker.fighting = victim

    with (
        patch("mud.skills.handlers.get_weapon_sn", return_value="sword"),
        patch("mud.skills.handlers.get_weapon_skill", return_value=100),
        patch("mud.skills.handlers.rng_mm.number_percent", return_value=0),
        patch("mud.skills.handlers.check_improve"),
    ):
        assert skill_handlers.disarm(attacker, target=victim) is True

    assert victim_weapon not in room.contents
    assert victim.inventory[0] is victim_weapon
    assert victim.inventory[1] is shield
    assert victim_weapon.wear_loc == int(WearLocation.NONE)
    assert victim_weapon.carried_by is victim


def test_disarm_mob_nodrop_weapon_stays_on_victim_inventory(
    movable_char_factory,
    object_factory,
):
    """ROM src/fight.c:2258-2260 routes NODROP/INVENTORY through obj_to_char."""

    attacker = movable_char_factory("warrior", 3001)
    attacker.skills["disarm"] = 100
    attacker.level = 20
    attacker.perm_stat = [0, 0, 0, 25, 0]
    attacker.mod_stat = [0, 0, 0, 0, 0]
    attacker.equip_object(_weapon(object_factory, 2612, "attacker sword"), int(WearLocation.WIELD))

    room = attacker.room
    assert room is not None
    victim = _mob(room)
    victim_weapon = _weapon(object_factory, 2614, "bound sword")
    victim_weapon.extra_flags = int(ExtraFlag.NODROP)
    victim.equip(victim_weapon, int(WearLocation.WIELD))

    with (
        patch("mud.skills.handlers.get_weapon_sn", return_value="sword"),
        patch("mud.skills.handlers.get_weapon_skill", return_value=100),
        patch("mud.skills.handlers.rng_mm.number_percent", return_value=0),
        patch("mud.skills.handlers.check_improve"),
    ):
        assert skill_handlers.disarm(attacker, target=victim) is True

    assert victim_weapon in victim.inventory
    assert victim_weapon not in room.contents
    assert victim_weapon.wear_loc == int(WearLocation.NONE)
    assert victim_weapon.carried_by is victim
