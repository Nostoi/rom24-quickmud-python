from __future__ import annotations

import pytest

from mud.models.constants import (
    ActFlag,
    ImmFlag,
    ResFlag,
    VulnFlag,
)
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance
from mud.world import initialize_world


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


def create_mob_with_defense(
    imm_flags: int = 0, res_flags: int = 0, vuln_flags: int = 0, level: int = 20, vnum: int = 9997
) -> MobInstance:
    if vnum not in mob_registry:
        proto = MobIndex(
            vnum=vnum,
            short_descr="test mob with defenses",
            long_descr="A defensive mob is here.",
            race="human",
            level=level,
            act_flags=ActFlag.IS_NPC,
            immune=imm_flags,  # type: ignore
            resist=res_flags,  # type: ignore
            vuln=vuln_flags,  # type: ignore
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


class TestImmunityFlags:
    def test_fire_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.FIRE)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.FIRE, "Fire immunity should be set"

    def test_cold_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.COLD)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.COLD, "Cold immunity should be set"

    def test_lightning_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.LIGHTNING)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.LIGHTNING, "Lightning immunity should be set"

    def test_acid_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.ACID)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.ACID, "Acid immunity should be set"

    def test_poison_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.POISON)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.POISON, "Poison immunity should be set"

    def test_weapon_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.WEAPON)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.WEAPON, "Weapon immunity should be set"

    def test_bash_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.BASH)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.BASH, "Bash immunity should be set"

    def test_pierce_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.PIERCE)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.PIERCE, "Pierce immunity should be set"

    def test_slash_immunity_flag(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.SLASH)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.SLASH, "Slash immunity should be set"


class TestResistanceFlags:
    def test_fire_resistance_flag(self):
        resist_mob = create_mob_with_defense(res_flags=ResFlag.FIRE)
        place_mob_in_room(resist_mob, 3001)

        assert resist_mob.res_flags & ResFlag.FIRE, "Fire resistance should be set"

    def test_cold_resistance_flag(self):
        resist_mob = create_mob_with_defense(res_flags=ResFlag.COLD)
        place_mob_in_room(resist_mob, 3001)

        assert resist_mob.res_flags & ResFlag.COLD, "Cold resistance should be set"

    def test_lightning_resistance_flag(self):
        resist_mob = create_mob_with_defense(res_flags=ResFlag.LIGHTNING)
        place_mob_in_room(resist_mob, 3001)

        assert resist_mob.res_flags & ResFlag.LIGHTNING, "Lightning resistance should be set"

    def test_magic_resistance_flag(self):
        resist_mob = create_mob_with_defense(res_flags=ResFlag.MAGIC)
        place_mob_in_room(resist_mob, 3001)

        assert resist_mob.res_flags & ResFlag.MAGIC, "Magic resistance should be set"


class TestVulnerabilityFlags:
    def test_fire_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.FIRE)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.FIRE, "Fire vulnerability should be set"

    def test_cold_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.COLD)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.COLD, "Cold vulnerability should be set"

    def test_lightning_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.LIGHTNING)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.LIGHTNING, "Lightning vulnerability should be set"

    def test_iron_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.IRON)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.IRON, "Iron vulnerability should be set"

    def test_wood_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.WOOD)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.WOOD, "Wood vulnerability should be set"

    def test_silver_vulnerability_flag(self):
        vuln_mob = create_mob_with_defense(vuln_flags=VulnFlag.SILVER)
        place_mob_in_room(vuln_mob, 3001)

        assert vuln_mob.vuln_flags & VulnFlag.SILVER, "Silver vulnerability should be set"


class TestMultipleDefenseFlags:
    def test_multiple_immunities(self):
        immune_mob = create_mob_with_defense(imm_flags=ImmFlag.FIRE | ImmFlag.COLD | ImmFlag.LIGHTNING)
        place_mob_in_room(immune_mob, 3001)

        assert immune_mob.imm_flags & ImmFlag.FIRE, "Fire immunity should be set"
        assert immune_mob.imm_flags & ImmFlag.COLD, "Cold immunity should be set"
        assert immune_mob.imm_flags & ImmFlag.LIGHTNING, "Lightning immunity should be set"

    def test_multiple_resistances(self):
        resist_mob = create_mob_with_defense(res_flags=ResFlag.BASH | ResFlag.PIERCE | ResFlag.SLASH)
        place_mob_in_room(resist_mob, 3001)

        assert resist_mob.res_flags & ResFlag.BASH, "Bash resistance should be set"
        assert resist_mob.res_flags & ResFlag.PIERCE, "Pierce resistance should be set"
        assert resist_mob.res_flags & ResFlag.SLASH, "Slash resistance should be set"

    def test_mixed_defenses(self):
        complex_mob = create_mob_with_defense(
            imm_flags=ImmFlag.FIRE, res_flags=ResFlag.COLD, vuln_flags=VulnFlag.LIGHTNING
        )
        place_mob_in_room(complex_mob, 3001)

        assert complex_mob.imm_flags & ImmFlag.FIRE, "Fire immunity should be set"
        assert complex_mob.res_flags & ResFlag.COLD, "Cold resistance should be set"
        assert complex_mob.vuln_flags & VulnFlag.LIGHTNING, "Lightning vulnerability should be set"
