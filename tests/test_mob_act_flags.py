from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()
    character_registry.clear()


def create_mob_with_act_flag(act_flag: ActFlag, level: int = 10, vnum: int = 9998) -> MobInstance:
    if vnum not in mob_registry:
        proto = MobIndex(
            vnum=vnum,
            short_descr=f"test mob with {act_flag.name}",
            long_descr=f"A test mob is here.",
            race="human",
            level=level,
            act_flags=ActFlag.IS_NPC | act_flag,
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


class TestActSentinel:
    def test_sentinel_mob_has_flag(self):
        sentinel = create_mob_with_act_flag(ActFlag.SENTINEL, level=15)
        room = place_mob_in_room(sentinel, 3001)

        assert sentinel.act & ActFlag.SENTINEL, "Sentinel flag should be set"
        assert sentinel.room == room, "Sentinel should be in room"


class TestActScavenger:
    def test_scavenger_mob_has_flag(self):
        scavenger = create_mob_with_act_flag(ActFlag.SCAVENGER, level=10)
        room = place_mob_in_room(scavenger, 3001)

        assert scavenger.act & ActFlag.SCAVENGER, "Scavenger flag should be set"


class TestActAggressive:
    def test_aggressive_mob_has_flag(self):
        aggro = create_mob_with_act_flag(ActFlag.AGGRESSIVE, level=20)
        room = place_mob_in_room(aggro, 3001)

        assert aggro.act & ActFlag.AGGRESSIVE, "Aggressive flag should be set"


class TestActWimpy:
    def test_wimpy_mob_has_flag(self):
        wimpy = create_mob_with_act_flag(ActFlag.WIMPY, level=10)
        room = place_mob_in_room(wimpy, 3001)

        assert wimpy.act & ActFlag.WIMPY, "Wimpy flag should be set"


class TestActUndead:
    def test_undead_mob_has_flag(self):
        undead = create_mob_with_act_flag(ActFlag.UNDEAD, level=25)
        room = place_mob_in_room(undead, 3001)

        assert undead.act & ActFlag.UNDEAD, "Undead flag should be set"


class TestActCleric:
    def test_cleric_mob_has_flag(self):
        cleric = create_mob_with_act_flag(ActFlag.CLERIC, level=20)
        room = place_mob_in_room(cleric, 3001)

        assert cleric.act & ActFlag.CLERIC, "Cleric flag should be set"


class TestActMage:
    def test_mage_mob_has_flag(self):
        mage = create_mob_with_act_flag(ActFlag.MAGE, level=20)
        room = place_mob_in_room(mage, 3001)

        assert mage.act & ActFlag.MAGE, "Mage flag should be set"


class TestActThief:
    def test_thief_mob_has_flag(self):
        thief = create_mob_with_act_flag(ActFlag.THIEF, level=15)
        room = place_mob_in_room(thief, 3001)

        assert thief.act & ActFlag.THIEF, "Thief flag should be set"


class TestActWarrior:
    def test_warrior_mob_has_flag(self):
        warrior = create_mob_with_act_flag(ActFlag.WARRIOR, level=25)
        room = place_mob_in_room(warrior, 3001)

        assert warrior.act & ActFlag.WARRIOR, "Warrior flag should be set"


class TestActPractice:
    def test_practice_mob_has_flag(self):
        trainer = create_mob_with_act_flag(ActFlag.PRACTICE, level=30)
        room = place_mob_in_room(trainer, 3001)

        assert trainer.act & ActFlag.PRACTICE, "Practice flag should be set"


class TestActIsHealer:
    def test_healer_mob_has_flag(self):
        healer = create_mob_with_act_flag(ActFlag.IS_HEALER, level=30)
        room = place_mob_in_room(healer, 3001)

        assert healer.act & ActFlag.IS_HEALER, "Healer flag should be set"


class TestActGain:
    def test_gain_mob_has_flag(self):
        trainer = create_mob_with_act_flag(ActFlag.GAIN, level=35)
        room = place_mob_in_room(trainer, 3001)

        assert trainer.act & ActFlag.GAIN, "Gain flag should be set"


class TestActStayArea:
    def test_stay_area_mob_has_flag(self):
        local = create_mob_with_act_flag(ActFlag.STAY_AREA, level=15)
        room = place_mob_in_room(local, 3001)

        assert local.act & ActFlag.STAY_AREA, "Stay area flag should be set"
